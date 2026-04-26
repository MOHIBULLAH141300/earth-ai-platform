"""
EarthAI Platform - API Gateway
FastAPI-based REST API for all Earth system modeling services
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import numpy as np
import json
import logging
from pathlib import Path
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Import our services
import sys
sys.path.append(str(Path(__file__).parent.parent))

from services.data_ingestion import DataIngestionService, SatelliteImagery
from services.model_recommendation_engine import ModelRecommendationEngine, TaskType
from services.ml_dl_training_pipeline import ModelFactory, TrainingConfig, Trainer
from services.rl_module import RLAgent, ModelSelectionRL
from services.expert_fuzzy_systems import LandslideExpertSystem, LandslideFuzzySystem
from services.probabilistic_models import EarthSystemBayesianNetwork
from services.symbolic_ai import EarthSystemOntology

logger = logging.getLogger(__name__)
load_dotenv()

# ==================== API Setup ====================

app = FastAPI(
    title="EarthAI Platform API",
    description="Next-generation AI system for Earth system modeling",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

# ==================== Pydantic Models ====================

class GeoBounds(BaseModel):
    min_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lon: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)
    
    @property
    def to_list(self):
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]

class DateRange(BaseModel):
    start_date: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")
    end_date: str = Field(..., pattern=r"\d{4}-\d{2}-\d{2}")

class DataIngestionRequest(BaseModel):
    bounds: GeoBounds
    date_range: DateRange
    sources: List[str] = ["sentinel", "modis", "terrain"]
    resolution: Optional[float] = 30.0

class ModelTrainingRequest(BaseModel):
    task_type: str = "landslide_susceptibility"
    model_type: Optional[str] = None  # Auto-select if None
    data_path: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    epochs: int = 100
    batch_size: int = 32
    validation_split: float = 0.2
    use_auto_ml: bool = True
    build_ensemble: bool = True

class PredictionRequest(BaseModel):
    model_id: str
    data: Union[List[List[float]], str]  # Array or file path
    data_type: str = "tabular"  # tabular, image, time_series
    return_probabilities: bool = True

class ExpertSystemRequest(BaseModel):
    assessment_type: str = "landslide"
    parameters: Dict[str, Any]
    use_fuzzy: bool = True

class BayesianQueryRequest(BaseModel):
    network_type: str = "landslide"
    evidence: Dict[str, Any]
    query_variables: List[str]
    inference_method: str = "variable_elimination"

class RLTrainingRequest(BaseModel):
    environment_type: str = "model_selection"
    algorithm: str = "PPO"
    total_timesteps: int = 100000
    model_pool: List[str] = []

class OntologyQueryRequest(BaseModel):
    query: str
    query_type: str = "natural_language"  # natural_language, sparql, direct

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

# ==================== In-Memory Job Store ====================

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobStatus] = {}
    
    def create_job(self, job_type: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            result={"job_type": job_type}
        )
        return job_id
    
    def update_job(self, job_id: str, status: str, progress: float = None, result: Dict = None, error: str = None):
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            if progress is not None:
                job.progress = progress
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = datetime.now()
    
    def get_job(self, job_id: str) -> Optional[JobStatus]:
        return self.jobs.get(job_id)

job_manager = JobManager()
MODEL_REGISTRY: Dict[str, Any] = {}

# ==================== Service Instances ====================

data_service = DataIngestionService()
model_recommendation = ModelRecommendationEngine()
ontology = EarthSystemOntology()

# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {
        "name": "EarthAI Platform",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "data": "/api/v1/data",
            "models": "/api/v1/models",
            "training": "/api/v1/training",
            "prediction": "/api/v1/predict",
            "expert_system": "/api/v1/expert",
            "bayesian": "/api/v1/bayesian",
            "rl": "/api/v1/rl",
            "ontology": "/api/v1/ontology",
            "jobs": "/api/v1/jobs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==================== Data Ingestion Endpoints ====================

@app.post("/api/v1/data/ingest")
async def ingest_data(request: DataIngestionRequest, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job("data_ingestion")
    
    async def run_ingestion():
        try:
            job_manager.update_job(job_id, "running", 0.0)
            
            # Ingest data
            results = await data_service.ingest_landslide_data(
                bounds=request.bounds.to_list,
                start_date=request.date_range.start_date,
                end_date=request.date_range.end_date
            )
            
            job_manager.update_job(
                job_id,
                "completed",
                1.0,
                result={
                    "n_images": len(results.get("data", {}).get("imagery", [])),
                    "n_climate_records": len(results.get("data", {}).get("climate", [])),
                    "terrain_keys": list(results.get("data", {}).get("terrain", {}).keys()),
                    "timestamp": results.get("timestamp")
                }
            )
        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            job_manager.update_job(job_id, "failed", error=str(e))
    
    background_tasks.add_task(run_ingestion)
    
    return {"job_id": job_id, "message": "Data ingestion started"}

@app.get("/api/v1/data/status/{job_id}")
async def get_data_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# ==================== Model Training Endpoints ====================

@app.post("/api/v1/models/recommend")
async def recommend_model(data: Dict[str, Any]):
    try:
        # Extract features and labels
        X = np.array(data.get("features", []))
        y = np.array(data.get("labels", []))
        task_type_str = data.get("task_type", "landslide_susceptibility")
        
        task_type = TaskType(task_type_str)
        
        # Get recommendation
        recommendation = model_recommendation.recommend_models(X, y, task_type)
        
        return {
            "recommended_models": [m.value for m in recommendation.recommended_models],
            "confidence": recommendation.confidence_score,
            "reasoning": recommendation.reasoning,
            "hyperparameters": {
                k.value: v for k, v in recommendation.hyperparameter_suggestions.items()
            },
            "ensemble_strategy": recommendation.ensemble_strategy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/training/start")
async def start_training(request: ModelTrainingRequest, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job("model_training")
    
    async def run_training():
        try:
            job_manager.update_job(job_id, "running", 0.0)
            
            # Load data (placeholder - in production, load from data path)
            from sklearn.datasets import make_classification
            X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
            
            task_type = TaskType(request.task_type)
            
            # Train models
            results = model_recommendation.recommend_and_train(
                X, y,
                task_type=task_type,
                optimize_hyperparams=request.use_auto_ml,
                build_ensemble=request.build_ensemble
            )
            
            # Save model
            model_id = str(uuid.uuid4())
            # Persist best available in-memory model for immediate inference
            best_model_name = max(
                results["model_performances"].items(),
                key=lambda kv: kv[1]["mean_auc"]
            )[0]
            model_lookup = {mtype.value: model for mtype, model in results["trained_models"]}
            selected_model = results["ensemble_model"] if results["ensemble_model"] is not None else model_lookup.get(best_model_name)
            if selected_model is not None:
                MODEL_REGISTRY[model_id] = selected_model
            
            job_manager.update_job(
                job_id,
                "completed",
                1.0,
                result={
                    "model_id": model_id,
                    "best_model_name": best_model_name,
                    "task_type": request.task_type,
                    "trained_models": list(results["model_performances"].keys()),
                    "performances": results["model_performances"],
                    "has_ensemble": results["ensemble_model"] is not None
                }
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")
            job_manager.update_job(job_id, "failed", error=str(e))
    
    background_tasks.add_task(run_training)
    
    return {"job_id": job_id, "message": "Training started"}

# ==================== Prediction Endpoints ====================

@app.post("/api/v1/predict")
async def predict(request: PredictionRequest):
    try:
        model = MODEL_REGISTRY.get(request.model_id)
        if model is None:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model_id}' not found in in-memory registry. Train a model first."
            )
        
        # Process data
        if isinstance(request.data, list):
            X = np.array(request.data)
        else:
            # Load from file path
            X = np.load(request.data)
        
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)[:, 1].tolist()
            predictions = [1 if p >= 0.5 else 0 for p in probabilities]
        else:
            predictions = model.predict(X).tolist()
            probabilities = None

        return {
            "predictions": predictions,
            "probabilities": probabilities if request.return_probabilities else None,
            "model_id": request.model_id,
            "data_type": request.data_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Expert System Endpoints ====================

@app.post("/api/v1/expert/assess")
async def expert_assessment(request: ExpertSystemRequest):
    try:
        if request.assessment_type == "landslide":
            # Expert system
            expert_system = LandslideExpertSystem()
            
            results = expert_system.assess(
                slope_angle=request.parameters.get("slope_angle", 0),
                soil_type=request.parameters.get("soil_type", "loam"),
                rainfall_24h=request.parameters.get("rainfall_24h", 0),
                vegetation_cover=request.parameters.get("vegetation_cover", 0.5),
                groundwater_level=request.parameters.get("groundwater_level", 0.5),
                soil_saturation=request.parameters.get("soil_saturation", 0.5),
                earthquake_magnitude=request.parameters.get("earthquake_magnitude", 0)
            )
            
            risk_level, confidence = expert_system.get_risk_level(results)
            
            response = {
                "assessment_type": "landslide",
                "risk_level": risk_level,
                "confidence": confidence,
                "triggered_rules": [
                    {
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "conclusion": r.conclusion,
                        "action": r.action,
                        "confidence": r.confidence
                    }
                    for r in results
                ]
            }
            
            # Fuzzy logic assessment
            if request.use_fuzzy:
                fuzzy_system = LandslideFuzzySystem()
                fuzzy_result = fuzzy_system.assess(
                    slope_angle=request.parameters.get("slope_angle", 0),
                    rainfall=request.parameters.get("rainfall_24h", 0),
                    vegetation=request.parameters.get("vegetation_cover", 0.5)
                )
                
                response["fuzzy_assessment"] = fuzzy_result
            
            return response
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown assessment type: {request.assessment_type}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Bayesian Network Endpoints ====================

@app.post("/api/v1/bayesian/query")
async def bayesian_query(request: BayesianQueryRequest):
    try:
        # Create Bayesian network
        bn = EarthSystemBayesianNetwork(request.network_type)
        
        # Run inference
        results = bn.predict_risk(
            evidence=request.evidence,
            method=request.inference_method
        )
        
        return {
            "network_type": request.network_type,
            "evidence": request.evidence,
            "query_variables": request.query_variables,
            "inference_method": request.inference_method,
            "results": results,
            "highest_probability": max(results, key=results.get),
            "highest_probability_value": max(results.values())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Reinforcement Learning Endpoints ====================

@app.post("/api/v1/rl/train")
async def train_rl_agent(request: RLTrainingRequest, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job("rl_training")
    
    async def run_rl_training():
        try:
            job_manager.update_job(job_id, "running", 0.0)
            
            # Create dummy environment for model selection
            from sklearn.datasets import make_classification
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            
            X, y = make_classification(n_samples=1000, n_features=20, random_state=42)
            
            models = [
                RandomForestClassifier(n_estimators=50),
                GradientBoostingClassifier(n_estimators=50)
            ]
            
            def dummy_data_source():
                return {
                    "features": np.random.randn(100),
                    "missing_ratio": 0.1,
                    "timestamp": np.datetime64('2024-01-01'),
                    "resolution": 30,
                    "n_samples": 1000,
                    "coordinates": (120.0, 30.0),
                    "elevation": 500,
                    "land_cover_type": "forest"
                }
            
            rl_system = ModelSelectionRL(
                data_source=dummy_data_source,
                model_pool=models
            )
            
            rl_system.train(total_timesteps=request.total_timesteps)
            
            job_manager.update_job(
                job_id,
                "completed",
                1.0,
                result={
                    "algorithm": request.algorithm,
                    "total_timesteps": request.total_timesteps,
                    "status": "Training completed"
                }
            )
        except Exception as e:
            logger.error(f"RL training failed: {e}")
            job_manager.update_job(job_id, "failed", error=str(e))
    
    background_tasks.add_task(run_rl_training)
    
    return {"job_id": job_id, "message": "RL training started"}

# ==================== Ontology Endpoints ====================

@app.post("/api/v1/ontology/query")
async def query_ontology(request: OntologyQueryRequest):
    try:
        if request.query_type == "natural_language":
            result = ontology.ask(request.query)
            return {"query": request.query, "response": result, "query_type": "natural_language"}
        
        elif request.query_type == "direct":
            # Parse query as direct fact query
            parts = request.query.split()
            if len(parts) >= 3:
                subject = parts[0]
                predicate = parts[1]
                obj = " ".join(parts[2:])
                
                facts = ontology.query(subject=subject, predicate=predicate, object=obj)
                
                return {
                    "query": request.query,
                    "results": [
                        {"subject": f.subject, "predicate": f.predicate, "object": f.object}
                        for f in facts
                    ]
                }
            else:
                raise HTTPException(status_code=400, detail="Invalid query format")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown query type: {request.query_type}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ontology/concepts")
async def list_concepts(category: Optional[str] = None):
    try:
        concepts = ontology.kb.concepts
        
        if category:
            filtered = {name: concept for name, concept in concepts.items() if concept.category == category}
        else:
            filtered = concepts
        
        return {
            "concepts": [
                {
                    "name": name,
                    "category": concept.category,
                    "properties": concept.properties,
                    "relationships": {k: v for k, v in concept.relationships.items()}
                }
                for name, concept in filtered.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ontology/reason")
async def run_reasoning(goal: Optional[str] = None):
    try:
        inferred = ontology.reason()
        
        return {
            "inferred_facts": [
                {"subject": f.subject, "predicate": f.predicate, "object": f.object}
                for f in inferred
            ],
            "total_inferred": len(inferred)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Job Management Endpoints ====================

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/v1/jobs")
async def list_jobs(status: Optional[str] = None):
    jobs = job_manager.jobs.values()
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status,
                "progress": j.progress,
                "created_at": j.created_at.isoformat(),
                "updated_at": j.updated_at.isoformat() if j.updated_at else None
            }
            for j in jobs
        ]
    }


@app.get("/api/v1/models")
async def list_models():
    return {"models": list(MODEL_REGISTRY.keys()), "count": len(MODEL_REGISTRY)}

# ==================== Streaming Endpoints ====================

@app.get("/api/v1/stream/predictions")
async def stream_predictions(model_id: str):
    async def event_generator():
        while True:
            # Generate dummy prediction (replace with real model)
            prediction = {
                "timestamp": datetime.now().isoformat(),
                "model_id": model_id,
                "prediction": np.random.random(),
                "confidence": np.random.random()
            }
            
            yield f"data: {json.dumps(prediction)}\n\n"
            await asyncio.sleep(5)  # Send every 5 seconds
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
