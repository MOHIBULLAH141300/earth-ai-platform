"""
Real-Time Task Orchestrator
Manages task execution workflow through all system components
Handles asynchronous execution, monitoring, and result aggregation
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DATA_COLLECTION = "data_collection"
    LITERATURE_INTEGRATION = "literature_integration"
    MODEL_SELECTION = "model_selection"
    MODEL_TRAINING = "model_training"
    INFERENCE = "inference"
    VISUALIZATION = "visualization"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TaskMetadata:
    """Task metadata and execution tracking"""
    task_id: str
    user_id: str
    task_type: str
    created_at: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0  # 0-100%
    estimated_completion: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    stages: Dict[str, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "status": self.status.value,
            "priority": self.priority.value
        }


@dataclass
class ExecutionStage:
    """Represents a stage in task execution"""
    name: str
    description: str
    estimated_duration: int  # seconds
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TaskPipeline:
    """Defines the execution pipeline for tasks"""
    
    # Standard pipeline stages
    PIPELINE = {
        "data_collection": ExecutionStage(
            name="Data Collection",
            description="Fetch relevant geospatial and climate data",
            estimated_duration=60,
            dependencies=[]
        ),
        "literature_integration": ExecutionStage(
            name="Literature Integration",
            description="Scrape and integrate latest research",
            estimated_duration=30,
            dependencies=["data_collection"]
        ),
        "model_selection": ExecutionStage(
            name="Model Selection",
            description="Select optimal model based on data and research",
            estimated_duration=20,
            dependencies=["data_collection", "literature_integration"]
        ),
        "model_training": ExecutionStage(
            name="Model Training",
            description="Train selected model on collected data",
            estimated_duration=180,
            dependencies=["model_selection", "data_collection"]
        ),
        "inference": ExecutionStage(
            name="Inference & Prediction",
            description="Run model on target region for predictions",
            estimated_duration=60,
            dependencies=["model_training"]
        ),
        "visualization": ExecutionStage(
            name="Results Visualization",
            description="Generate interactive maps and charts",
            estimated_duration=30,
            dependencies=["inference"]
        )
    }
    
    @classmethod
    def get_pipeline_stages(cls) -> Dict[str, ExecutionStage]:
        """Get all pipeline stages"""
        return cls.PIPELINE
    
    @classmethod
    def calculate_total_duration(cls) -> int:
        """Calculate estimated total duration"""
        return sum(stage.estimated_duration for stage in cls.PIPELINE.values())


class TaskDatabase:
    """SQLite database for task persistence"""
    
    def __init__(self, db_path: str = "data/task_queue.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT,
                task_type TEXT,
                created_at TEXT,
                status TEXT,
                priority INTEGER,
                parameters TEXT,
                progress REAL,
                estimated_completion TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result TEXT,
                stages TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                timestamp TEXT,
                stage TEXT,
                message TEXT,
                status TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON tasks(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        """)
        
        conn.commit()
        conn.close()
    
    def save_task(self, metadata: TaskMetadata):
        """Save task metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO tasks 
                (task_id, user_id, task_type, created_at, status, priority, parameters, 
                 progress, estimated_completion, started_at, completed_at, error_message, result, stages)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.task_id,
                metadata.user_id,
                metadata.task_type,
                metadata.created_at,
                metadata.status.value,
                metadata.priority.value,
                json.dumps(metadata.parameters),
                metadata.progress,
                metadata.estimated_completion,
                metadata.started_at,
                metadata.completed_at,
                metadata.error_message,
                json.dumps(metadata.result) if metadata.result else None,
                json.dumps({k: v for k, v in metadata.stages.items()})
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving task: {e}")
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """Retrieve task metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_metadata(row)
        except Exception as e:
            logger.error(f"Error retrieving task: {e}")
        finally:
            conn.close()
        
        return None
    
    def get_user_tasks(self, user_id: str, limit: int = 50) -> List[TaskMetadata]:
        """Get tasks for user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tasks = []
        try:
            cursor.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
            
            for row in cursor.fetchall():
                tasks.append(self._row_to_metadata(row))
        except Exception as e:
            logger.error(f"Error retrieving user tasks: {e}")
        finally:
            conn.close()
        
        return tasks
    
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 50) -> List[TaskMetadata]:
        """Get tasks by status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tasks = []
        try:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT ?",
                (status.value, limit)
            )
            
            for row in cursor.fetchall():
                tasks.append(self._row_to_metadata(row))
        except Exception as e:
            logger.error(f"Error retrieving tasks by status: {e}")
        finally:
            conn.close()
        
        return tasks
    
    def log_stage(self, task_id: str, stage: str, message: str, status: str):
        """Log stage execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO task_logs (task_id, timestamp, stage, message, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                datetime.now().isoformat(),
                stage,
                message,
                status
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging stage: {e}")
        finally:
            conn.close()
    
    def get_task_logs(self, task_id: str) -> List[Dict]:
        """Get execution logs for task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logs = []
        try:
            cursor.execute(
                "SELECT timestamp, stage, message, status FROM task_logs WHERE task_id = ? ORDER BY timestamp ASC",
                (task_id,)
            )
            
            for row in cursor.fetchall():
                logs.append({
                    "timestamp": row[0],
                    "stage": row[1],
                    "message": row[2],
                    "status": row[3]
                })
        except Exception as e:
            logger.error(f"Error retrieving task logs: {e}")
        finally:
            conn.close()
        
        return logs
    
    def _row_to_metadata(self, row: tuple) -> TaskMetadata:
        """Convert database row to TaskMetadata"""
        return TaskMetadata(
            task_id=row[0],
            user_id=row[1],
            task_type=row[2],
            created_at=row[3],
            status=TaskStatus(row[4]),
            priority=TaskPriority(row[5]),
            parameters=json.loads(row[6]) if row[6] else {},
            progress=row[7] or 0.0,
            estimated_completion=row[8],
            started_at=row[9],
            completed_at=row[10],
            error_message=row[11],
            result=json.loads(row[12]) if row[12] else None,
            stages=json.loads(row[13]) if row[13] else {}
        )


class TaskOrchestrator:
    """Main orchestrator for task execution"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.db = TaskDatabase()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.service_callbacks: Dict[str, Callable] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    
    def register_service_callback(self, stage_name: str, callback: Callable):
        """Register callback for a pipeline stage"""
        self.service_callbacks[stage_name] = callback
        logger.info(f"Registered callback for stage: {stage_name}")
    
    def create_task(
        self,
        user_id: str,
        task_type: str,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        
        total_duration = TaskPipeline.calculate_total_duration()
        estimated_completion = (
            datetime.now() + timedelta(seconds=total_duration)
        ).isoformat()
        
        metadata = TaskMetadata(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            created_at=datetime.now().isoformat(),
            status=TaskStatus.PENDING,
            priority=priority,
            parameters=parameters,
            estimated_completion=estimated_completion
        )
        
        self.db.save_task(metadata)
        logger.info(f"Created task {task_id} for user {user_id}")
        
        return task_id
    
    async def execute_task(self, task_id: str):
        """Execute task through entire pipeline"""
        metadata = self.db.get_task(task_id)
        if not metadata:
            logger.error(f"Task {task_id} not found")
            return
        
        try:
            # Update status
            metadata.status = TaskStatus.IN_PROGRESS
            metadata.started_at = datetime.now().isoformat()
            self.db.save_task(metadata)
            
            logger.info(f"Starting execution of task {task_id}")
            
            # Execute pipeline stages
            pipeline_stages = TaskPipeline.get_pipeline_stages()
            completed_stages = []
            
            for stage_name, stage_def in pipeline_stages.items():
                # Check dependencies
                if not all(dep in completed_stages for dep in stage_def.dependencies):
                    logger.debug(f"Skipping stage {stage_name}, dependencies not met")
                    continue
                
                try:
                    # Update status
                    metadata.status = TaskStatus[stage_name.upper()]
                    metadata.progress = (
                        len(completed_stages) / len(pipeline_stages)
                    ) * 100
                    self.db.save_task(metadata)
                    
                    logger.info(f"Executing stage: {stage_name}")
                    
                    # Execute stage
                    if stage_name in self.service_callbacks:
                        result = await self._execute_stage(
                            stage_name,
                            metadata
                        )
                        metadata.stages[stage_name] = {
                            "status": "completed",
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        logger.debug(f"No callback registered for {stage_name}, simulating...")
                        await asyncio.sleep(stage_def.estimated_duration / 10)
                        metadata.stages[stage_name] = {
                            "status": "completed",
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    completed_stages.append(stage_name)
                    self.db.log_stage(task_id, stage_name, "Stage completed successfully", "success")
                    self.db.save_task(metadata)
                
                except Exception as e:
                    logger.error(f"Stage {stage_name} failed: {e}")
                    metadata.status = TaskStatus.FAILED
                    metadata.error_message = f"Failed at stage {stage_name}: {str(e)}"
                    self.db.log_stage(task_id, stage_name, str(e), "error")
                    self.db.save_task(metadata)
                    return
            
            # Task completed
            metadata.status = TaskStatus.COMPLETED
            metadata.completed_at = datetime.now().isoformat()
            metadata.progress = 100.0
            self.db.save_task(metadata)
            
            logger.info(f"Task {task_id} completed successfully")
        
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            metadata.status = TaskStatus.FAILED
            metadata.error_message = str(e)
            metadata.completed_at = datetime.now().isoformat()
            self.db.save_task(metadata)
    
    async def _execute_stage(self, stage_name: str, metadata: TaskMetadata) -> Optional[Dict]:
        """Execute a single pipeline stage"""
        callback = self.service_callbacks.get(stage_name)
        if not callback:
            return None
        
        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback(metadata)
            else:
                return callback(metadata)
        except Exception as e:
            logger.error(f"Stage callback failed: {e}")
            raise
    
    async def queue_and_execute(self, task_id: str):
        """Queue task for execution"""
        metadata = self.db.get_task(task_id)
        if not metadata:
            return
        
        # Add to queue with priority
        priority_value = (
            metadata.priority.value,
            datetime.fromisoformat(metadata.created_at).timestamp()
        )
        
        await self.task_queue.put((priority_value, task_id))
        
        # Try to execute if slots available
        while self.active_tasks and len(self.active_tasks) >= self.max_concurrent_tasks:
            await asyncio.sleep(1)
        
        if len(self.active_tasks) < self.max_concurrent_tasks:
            _, task_id_to_exec = await self.task_queue.get()
            task = asyncio.create_task(self.execute_task(task_id_to_exec))
            self.active_tasks[task_id_to_exec] = task
            
            task.add_done_callback(lambda t: self.active_tasks.pop(task_id_to_exec, None))
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current task status"""
        metadata = self.db.get_task(task_id)
        if not metadata:
            return None
        
        return metadata.to_dict()
    
    def get_user_tasks_status(self, user_id: str) -> List[Dict]:
        """Get all tasks for user with status"""
        tasks = self.db.get_user_tasks(user_id)
        return [task.to_dict() for task in tasks]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        metadata = self.db.get_task(task_id)
        if not metadata:
            return False
        
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
        
        metadata.status = TaskStatus.CANCELLED
        metadata.completed_at = datetime.now().isoformat()
        self.db.save_task(metadata)
        
        logger.info(f"Task {task_id} cancelled")
        return True


# Global instance
_orchestrator = None

def get_task_orchestrator() -> TaskOrchestrator:
    """Get or create task orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator(max_concurrent_tasks=3)
    return _orchestrator
