"""
EarthAI Platform - Deployment & Monitoring Module
Handles model deployment, real-time monitoring, and system health tracking
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import queue

import numpy as np
import psutil
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server, generate_latest
from prometheus_client import CollectorRegistry, REGISTRY
import redis
from celery import Celery

logger = logging.getLogger(__name__)


# ==================== Metrics Definitions ====================

DEPLOYMENT_REGISTRY = CollectorRegistry()

# Model metrics
model_predictions_total = Counter(
    'model_predictions_total',
    'Total number of predictions',
    ['model_id', 'model_version', 'task_type'],
    registry=DEPLOYMENT_REGISTRY
)

model_prediction_duration = Histogram(
    'model_prediction_duration_seconds',
    'Time spent processing prediction',
    ['model_id', 'model_version'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=DEPLOYMENT_REGISTRY
)

model_prediction_accuracy = Gauge(
    'model_prediction_accuracy',
    'Current prediction accuracy',
    ['model_id', 'model_version'],
    registry=DEPLOYMENT_REGISTRY
)

model_drift_score = Gauge(
    'model_drift_score',
    'Data drift detection score',
    ['model_id', 'drift_type'],
    registry=DEPLOYMENT_REGISTRY
)

# System metrics
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'Current CPU usage percentage',
    registry=DEPLOYMENT_REGISTRY
)

system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'Current memory usage in bytes',
    registry=DEPLOYMENT_REGISTRY
)

system_disk_usage = Gauge(
    'system_disk_usage_percent',
    'Current disk usage percentage',
    registry=DEPLOYMENT_REGISTRY
)

system_gpu_usage = Gauge(
    'system_gpu_usage_percent',
    'Current GPU usage percentage',
    ['gpu_id'],
    registry=DEPLOYMENT_REGISTRY
)

# API metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status_code'],
    registry=DEPLOYMENT_REGISTRY
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=DEPLOYMENT_REGISTRY
)

# Data pipeline metrics
data_ingestion_total = Counter(
    'data_ingestion_total',
    'Total data records ingested',
    ['source', 'data_type'],
    registry=DEPLOYMENT_REGISTRY
)

data_processing_duration = Histogram(
    'data_processing_duration_seconds',
    'Data processing duration',
    ['stage'],
    registry=DEPLOYMENT_REGISTRY
)

# Training metrics
training_epochs_total = Counter(
    'training_epochs_total',
    'Total training epochs completed',
    ['model_id'],
    registry=DEPLOYMENT_REGISTRY
)

training_loss = Gauge(
    'training_loss',
    'Current training loss',
    ['model_id', 'loss_type'],
    registry=DEPLOYMENT_REGISTRY
)

# Business metrics
prediction_confidence = Histogram(
    'prediction_confidence',
    'Distribution of prediction confidence scores',
    ['model_id'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=DEPLOYMENT_REGISTRY
)

alert_count = Counter(
    'alert_count_total',
    'Total number of alerts triggered',
    ['alert_type', 'severity'],
    registry=DEPLOYMENT_REGISTRY
)

# Model info
model_info = Info(
    'deployed_model',
    'Information about deployed model',
    registry=DEPLOYMENT_REGISTRY
)


# ==================== Model Registry ====================

class ModelVersion:
    """Represents a version of a deployed model"""
    def __init__(
        self,
        model_id: str,
        version: str,
        model_path: str,
        metadata: Dict[str, Any],
        deployment_time: datetime = None
    ):
        self.model_id = model_id
        self.version = version
        self.model_path = model_path
        self.metadata = metadata
        self.deployment_time = deployment_time or datetime.now()
        self.status = "active"
        self.prediction_count = 0
        self.last_prediction_time = None
        self.accuracy_history: List[float] = []
        self.latency_history: List[float] = []
        self.drift_scores: Dict[str, List[float]] = defaultdict(list)
    
    def record_prediction(self, latency: float, confidence: float):
        """Record a prediction event"""
        self.prediction_count += 1
        self.last_prediction_time = datetime.now()
        self.latency_history.append(latency)
        
        # Keep only last 10000 entries
        if len(self.latency_history) > 10000:
            self.latency_history = self.latency_history[-10000:]
    
    def record_accuracy(self, accuracy: float):
        """Record accuracy metric"""
        self.accuracy_history.append(accuracy)
        if len(self.accuracy_history) > 10000:
            self.accuracy_history = self.accuracy_history[-10000:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "status": self.status,
            "deployment_time": self.deployment_time.isoformat(),
            "prediction_count": self.prediction_count,
            "last_prediction_time": self.last_prediction_time.isoformat() if self.last_prediction_time else None,
            "avg_latency": np.mean(self.latency_history) if self.latency_history else 0,
            "p99_latency": np.percentile(self.latency_history, 99) if self.latency_history else 0,
            "avg_accuracy": np.mean(self.accuracy_history) if self.accuracy_history else 0,
            "metadata": self.metadata
        }


class ModelRegistry:
    """Registry for managing deployed models"""
    
    def __init__(self, storage_path: str = "./models/registry"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.models: Dict[str, ModelVersion] = {}
        self.model_versions: Dict[str, List[ModelVersion]] = defaultdict(list)
        
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk"""
        registry_file = self.storage_path / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                
                for model_data in data.get("models", []):
                    version = ModelVersion(
                        model_id=model_data["model_id"],
                        version=model_data["version"],
                        model_path=model_data["model_path"],
                        metadata=model_data.get("metadata", {}),
                        deployment_time=datetime.fromisoformat(model_data["deployment_time"])
                    )
                    version.status = model_data.get("status", "active")
                    version.prediction_count = model_data.get("prediction_count", 0)
                    
                    self.models[f"{model_data['model_id']}:{model_data['version']}"] = version
                    self.model_versions[model_data["model_id"]].append(version)
                
                logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save registry to disk"""
        registry_file = self.storage_path / "registry.json"
        
        data = {
            "models": [version.to_dict() for version in self.models.values()],
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            with open(registry_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_model(
        self,
        model_id: str,
        version: str,
        model_path: str,
        metadata: Dict[str, Any] = None
    ) -> ModelVersion:
        """Register a new model version"""
        
        # Deactivate previous versions
        for v in self.model_versions[model_id]:
            v.status = "inactive"
        
        # Create new version
        model_version = ModelVersion(
            model_id=model_id,
            version=version,
            model_path=model_path,
            metadata=metadata or {}
        )
        
        # Add to registry
        key = f"{model_id}:{version}"
        self.models[key] = model_version
        self.model_versions[model_id].append(model_version)
        
        # Update metrics
        model_info.info({
            "model_id": model_id,
            "version": version,
            "task_type": metadata.get("task_type", "unknown") if metadata else "unknown",
            "framework": metadata.get("framework", "unknown") if metadata else "unknown"
        })
        
        # Save registry
        self._save_registry()
        
        logger.info(f"Registered model {model_id} version {version}")
        
        return model_version
    
    def get_model(self, model_id: str, version: Optional[str] = None) -> Optional[ModelVersion]:
        """Get model version"""
        if version:
            return self.models.get(f"{model_id}:{version}")
        
        # Return latest active version
        versions = self.model_versions.get(model_id, [])
        active_versions = [v for v in versions if v.status == "active"]
        
        if active_versions:
            return max(active_versions, key=lambda v: v.deployment_time)
        
        return versions[-1] if versions else None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models"""
        return [version.to_dict() for version in self.models.values()]
    
    def record_prediction(
        self,
        model_id: str,
        version: str,
        latency: float,
        confidence: float
    ):
        """Record a prediction for a model"""
        model = self.get_model(model_id, version)
        if model:
            model.record_prediction(latency, confidence)
            
            # Update Prometheus metrics
            model_predictions_total.labels(
                model_id=model_id,
                model_version=version,
                task_type=model.metadata.get("task_type", "unknown")
            ).inc()
            
            model_prediction_duration.labels(
                model_id=model_id,
                model_version=version
            ).observe(latency)
            
            prediction_confidence.labels(
                model_id=model_id
            ).observe(confidence)
    
    def record_accuracy(self, model_id: str, version: str, accuracy: float):
        """Record accuracy for a model"""
        model = self.get_model(model_id, version)
        if model:
            model.record_accuracy(accuracy)
            
            model_prediction_accuracy.labels(
                model_id=model_id,
                model_version=version
            ).set(accuracy)
    
    def record_drift(self, model_id: str, drift_type: str, score: float):
        """Record drift score"""
        model = self.get_model(model_id)
        if model:
            model.drift_scores[drift_type].append(score)
            
            model_drift_score.labels(
                model_id=model_id,
                drift_type=drift_type
            ).set(score)


# ==================== Drift Detection ====================

class DriftDetector:
    """Detects data and concept drift in deployed models"""
    
    def __init__(
        self,
        reference_data: np.ndarray,
        threshold: float = 0.05,
        window_size: int = 1000
    ):
        self.reference_data = reference_data
        self.threshold = threshold
        self.window_size = window_size
        self.current_window: List[np.ndarray] = []
        
        # Compute reference statistics
        self.reference_mean = np.mean(reference_data, axis=0)
        self.reference_std = np.std(reference_data, axis=0)
        self.reference_dist = self._compute_distribution(reference_data)
    
    def _compute_distribution(self, data: np.ndarray) -> Dict[int, np.ndarray]:
        """Compute feature distributions"""
        distributions = {}
        
        for i in range(data.shape[1]):
            hist, bins = np.histogram(data[:, i], bins=50, density=True)
            distributions[i] = {"hist": hist, "bins": bins}
        
        return distributions
    
    def add_sample(self, sample: np.ndarray):
        """Add a new sample to the detection window"""
        self.current_window.append(sample)
        
        if len(self.current_window) > self.window_size:
            self.current_window.pop(0)
    
    def detect_drift(self) -> Dict[str, Any]:
        """Detect drift in current window compared to reference"""
        if len(self.current_window) < 100:
            return {"drift_detected": False, "reason": "insufficient_samples"}
        
        current_data = np.array(self.current_window)
        
        # 1. Statistical drift (KS test approximation)
        drift_scores = {}
        
        for i in range(min(current_data.shape[1], len(self.reference_mean))):
            # Kolmogorov-Smirnov statistic
            current_hist, _ = np.histogram(current_data[:, i], bins=50, density=True)
            reference_hist = self.reference_dist[i]["hist"]
            
            ks_statistic = np.max(np.abs(current_hist - reference_hist))
            drift_scores[f"feature_{i}"] = ks_statistic
        
        # 2. Mean drift
        current_mean = np.mean(current_data, axis=0)
        mean_drift = np.abs(current_mean - self.reference_mean) / (self.reference_std + 1e-8)
        
        for i, drift in enumerate(mean_drift):
            drift_scores[f"mean_feature_{i}"] = drift
        
        # 3. Overall drift score
        max_drift = max(drift_scores.values())
        avg_drift = np.mean(list(drift_scores.values()))
        
        drift_detected = max_drift > self.threshold or avg_drift > self.threshold / 2
        
        return {
            "drift_detected": drift_detected,
            "max_drift_score": float(max_drift),
            "avg_drift_score": float(avg_drift),
            "drift_scores": {k: float(v) for k, v in drift_scores.items()},
            "threshold": self.threshold,
            "samples_analyzed": len(self.current_window)
        }
    
    def reset(self):
        """Reset detection window"""
        self.current_window = []


# ==================== Alert Manager ====================

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    source: str
    details: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable] = []
        self.alert_queue: queue.Queue = queue.Queue()
        
        # Start alert processing thread
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
    
    def add_handler(self, handler: Callable):
        """Add alert handler"""
        self.alert_handlers.append(handler)
    
    def trigger_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        source: str,
        details: Dict[str, Any] = None
    ):
        """Trigger a new alert"""
        alert = Alert(
            alert_id=f"{alert_type}_{int(time.time())}",
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            source=source,
            details=details or {}
        )
        
        self.alerts.append(alert)
        self.alert_queue.put(alert)
        
        # Update metrics
        alert_count.labels(
            alert_type=alert_type,
            severity=severity.value
        ).inc()
        
        logger.warning(f"Alert triggered: {message} ({severity.value})")
    
    def _process_alerts(self):
        """Process alerts in background thread"""
        while True:
            try:
                alert = self.alert_queue.get(timeout=1)
                
                # Notify handlers
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Alert handler error: {e}")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active (unresolved) alerts"""
        alerts = [a for a in self.alerts if not a.resolved]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False
    
    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]


# ==================== System Monitor ====================

class SystemMonitor:
    """Monitors system health and performance"""
    
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Historical metrics
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.disk_history: List[float] = []
    
    def start(self):
        """Start system monitoring"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop(self):
        """Stop system monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._collect_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(self.interval)
    
    def _collect_metrics(self):
        """Collect system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_history.append(cpu_percent)
        system_cpu_usage.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.used)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        self.disk_history.append(disk_percent)
        system_disk_usage.set(disk_percent)
        
        # GPU usage (if available)
        try:
            import pynvml
            pynvml.nvmlInit()
            
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                system_gpu_usage.labels(gpu_id=str(i)).set(util.gpu)
        except:
            pass
        
        # Keep only last 1000 entries
        if len(self.cpu_history) > 1000:
            self.cpu_history = self.cpu_history[-1000:]
        if len(self.memory_history) > 1000:
            self.memory_history = self.memory_history[-1000:]
        if len(self.disk_history) > 1000:
            self.disk_history = self.disk_history[-1000:]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "cpu_history_avg": np.mean(self.cpu_history) if self.cpu_history else 0,
            "memory_history_avg": np.mean(self.memory_history) if self.memory_history else 0,
            "timestamp": datetime.now().isoformat()
        }


# ==================== A/B Testing ====================

class ABTestManager:
    """Manages A/B testing for model comparison"""
    
    def __init__(self):
        self.experiments: Dict[str, Dict] = {}
        self.results: Dict[str, Dict] = defaultdict(lambda: defaultdict(list))
    
    def create_experiment(
        self,
        experiment_id: str,
        model_a_id: str,
        model_a_version: str,
        model_b_id: str,
        model_b_version: str,
        traffic_split: float = 0.5
    ):
        """Create A/B test experiment"""
        self.experiments[experiment_id] = {
            "model_a": {"id": model_a_id, "version": model_a_version},
            "model_b": {"id": model_b_id, "version": model_b_version},
            "traffic_split": traffic_split,
            "start_time": datetime.now(),
            "status": "running"
        }
        
        logger.info(f"Created A/B test {experiment_id}")
    
    def get_model_for_request(self, experiment_id: str, request_id: str) -> Dict[str, str]:
        """Select model for request based on traffic split"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Deterministic assignment based on request_id hash
        hash_val = hash(request_id) % 1000
        if hash_val < experiment["traffic_split"] * 1000:
            return experiment["model_a"]
        else:
            return experiment["model_b"]
    
    def record_result(
        self,
        experiment_id: str,
        model_assignment: str,
        metric_name: str,
        metric_value: float
    ):
        """Record experiment result"""
        self.results[experiment_id][model_assignment].append({
            "metric": metric_name,
            "value": metric_value,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get experiment results"""
        results = self.results.get(experiment_id, {})
        
        model_a_results = results.get("model_a", [])
        model_b_results = results.get("model_b", [])
        
        return {
            "experiment_id": experiment_id,
            "model_a_count": len(model_a_results),
            "model_b_count": len(model_b_results),
            "model_a_metrics": self._aggregate_metrics(model_a_results),
            "model_b_metrics": self._aggregate_metrics(model_b_results)
        }
    
    def _aggregate_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """Aggregate metrics from results"""
        if not results:
            return {}
        
        metrics = defaultdict(list)
        for r in results:
            metrics[r["metric"]].append(r["value"])
        
        return {
            metric: {
                "mean": np.mean(values),
                "std": np.std(values),
                "count": len(values)
            }
            for metric, values in metrics.items()
        }


# ==================== Deployment Manager ====================

class DeploymentManager:
    """Main deployment and monitoring manager"""
    
    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        alert_manager: Optional[AlertManager] = None,
        system_monitor: Optional[SystemMonitor] = None
    ):
        self.model_registry = model_registry or ModelRegistry()
        self.alert_manager = alert_manager or AlertManager()
        self.system_monitor = system_monitor or SystemMonitor()
        
        self.drift_detectors: Dict[str, DriftDetector] = {}
        self.ab_test_manager = ABTestManager()
        
        # Setup default alert handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        def log_handler(alert: Alert):
            logger.info(f"ALERT [{alert.severity.value.upper()}] {alert.message}")
        
        self.alert_manager.add_handler(log_handler)
    
    def start(self):
        """Start all monitoring services"""
        self.system_monitor.start()
        
        # Start Prometheus metrics server
        try:
            start_http_server(9090)
            logger.info("Prometheus metrics server started on port 9090")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
    
    def stop(self):
        """Stop all monitoring services"""
        self.system_monitor.stop()
    
    def deploy_model(
        self,
        model_id: str,
        version: str,
        model_path: str,
        metadata: Dict[str, Any] = None,
        enable_drift_detection: bool = True,
        reference_data: Optional[np.ndarray] = None
    ) -> ModelVersion:
        """Deploy a new model version"""
        
        # Register model
        model_version = self.model_registry.register_model(
            model_id=model_id,
            version=version,
            model_path=model_path,
            metadata=metadata
        )
        
        # Setup drift detection if enabled
        if enable_drift_detection and reference_data is not None:
            self.drift_detectors[model_id] = DriftDetector(reference_data)
            logger.info(f"Drift detection enabled for model {model_id}")
        
        # Alert deployment
        self.alert_manager.trigger_alert(
            alert_type="model_deployment",
            severity=AlertSeverity.INFO,
            message=f"Model {model_id} version {version} deployed successfully",
            source="deployment_manager",
            details={"model_path": model_path, "metadata": metadata}
        )
        
        return model_version
    
    def record_prediction(
        self,
        model_id: str,
        version: str,
        latency: float,
        confidence: float,
        features: Optional[np.ndarray] = None
    ):
        """Record model prediction for monitoring"""
        
        self.model_registry.record_prediction(model_id, version, latency, confidence)
        
        # Check for drift
        if model_id in self.drift_detectors and features is not None:
            detector = self.drift_detectors[model_id]
            detector.add_sample(features)
            
            drift_result = detector.detect_drift()
            
            if drift_result["drift_detected"]:
                self.model_registry.record_drift(
                    model_id, "data_drift", drift_result["max_drift_score"]
                )
                
                self.alert_manager.trigger_alert(
                    alert_type="model_drift",
                    severity=AlertSeverity.WARNING,
                    message=f"Data drift detected for model {model_id}",
                    source="drift_detector",
                    details=drift_result
                )
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        status = self.system_monitor.get_system_status()
        
        # Check for critical conditions
        alerts = self.alert_manager.get_active_alerts(severity=AlertSeverity.CRITICAL)
        
        health_status = "healthy"
        if status["cpu_percent"] > 90:
            health_status = "degraded"
            self.alert_manager.trigger_alert(
                alert_type="high_cpu",
                severity=AlertSeverity.WARNING,
                message=f"High CPU usage: {status['cpu_percent']:.1f}%",
                source="system_monitor",
                details=status
            )
        
        if status["memory_percent"] > 90:
            health_status = "degraded"
            self.alert_manager.trigger_alert(
                alert_type="high_memory",
                severity=AlertSeverity.WARNING,
                message=f"High memory usage: {status['memory_percent']:.1f}%",
                source="system_monitor",
                details=status
            )
        
        return {
            "status": health_status,
            "system_metrics": status,
            "active_critical_alerts": len(alerts),
            "deployed_models": len(self.model_registry.models),
            "drift_detectors": len(self.drift_detectors),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics"""
        return generate_latest(DEPLOYMENT_REGISTRY)
    
    def get_prometheus_metrics_text(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest(DEPLOYMENT_REGISTRY).decode('utf-8')


# Example usage
if __name__ == "__main__":
    # Create deployment manager
    deployment = DeploymentManager()
    
    # Start monitoring
    deployment.start()
    
    # Deploy a model
    from sklearn.datasets import make_classification
    
    X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
    
    model_version = deployment.deploy_model(
        model_id="landslide_model_v1",
        version="1.0.0",
        model_path="./models/landslide_v1.pkl",
        metadata={
            "task_type": "landslide_susceptibility",
            "framework": "sklearn",
            "accuracy": 0.92
        },
        enable_drift_detection=True,
        reference_data=X
    )
    
    # Simulate predictions
    for i in range(100):
        sample = X[i % len(X)]
        deployment.record_prediction(
            model_id="landslide_model_v1",
            version="1.0.0",
            latency=np.random.uniform(0.01, 0.1),
            confidence=np.random.uniform(0.7, 0.99),
            features=sample
        )
    
    # Check health
    health = deployment.check_system_health()
    print(f"System Health: {health['status']}")
    print(f"Active Alerts: {health['active_critical_alerts']}")
    
    # Print metrics
    metrics_text = deployment.get_prometheus_metrics_text()
    print("\nPrometheus Metrics (first 500 chars):")
    print(metrics_text[:500])
    
    # Stop monitoring
    deployment.stop()
