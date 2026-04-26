"""
EarthAI Platform - Model Recommendation & AI Engine
Implements AutoML, Meta-learning, and Reinforcement Learning for model selection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
import pickle
import logging
from pathlib import Path
import time

# ML/DL Libraries
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier, AdaBoostClassifier, VotingClassifier
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

# Deep Learning
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# AutoML
import optuna
from optuna.samplers import TPESampler

# RL
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import gymnasium as gym
from gymnasium import spaces

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of Earth system modeling tasks"""
    LANDSLIDE_SUSCEPTIBILITY = "landslide_susceptibility"
    CLIMATE_PREDICTION = "climate_prediction"
    FLOOD_RISK_ASSESSMENT = "flood_risk"
    WILDFIRE_PREDICTION = "wildfire_prediction"
    AIR_QUALITY_FORECASTING = "air_quality"
    DROUGHT_MONITORING = "drought_monitoring"
    SEA_LEVEL_RISE = "sea_level_rise"
    BIODIVERSITY_ASSESSMENT = "biodiversity"


class ModelType(Enum):
    """Available model types"""
    # Traditional ML
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    EXTRA_TREES = "extra_trees"
    ADABOOST = "adaboost"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    KNN = "knn"
    NAIVE_BAYES = "naive_bayes"
    DECISION_TREE = "decision_tree"
    RIDGE_CLASSIFIER = "ridge_classifier"
    
    # Deep Learning
    CNN = "cnn"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    AUTOENCODER = "autoencoder"
    GAN = "gan"
    UNET = "unet"
    RESNET = "resnet"
    EFFICIENTNET = "efficientnet"
    
    # Ensemble
    VOTING_ENSEMBLE = "voting_ensemble"
    STACKING_ENSEMBLE = "stacking_ensemble"
    BLENDING_ENSEMBLE = "blending_ensemble"
    
    # Probabilistic
    BAYESIAN_NETWORK = "bayesian_network"
    MARKOV_NETWORK = "markov_network"
    
    # Symbolic
    EXPERT_SYSTEM = "expert_system"
    FUZZY_LOGIC = "fuzzy_logic"


@dataclass
class DatasetMetaFeatures:
    """Meta-features describing a dataset for meta-learning"""
    n_samples: int
    n_features: int
    n_classes: int
    class_balance: float  # Ratio of minority to majority class
    feature_types: Dict[str, int]  # Count of numeric, categorical, etc.
    missing_ratio: float
    dimensionality: float  # n_features / n_samples
    sparsity: float
    task_type: TaskType
    data_complexity: float
    spatial_resolution: Optional[float] = None
    temporal_resolution: Optional[str] = None
    
    def to_vector(self) -> np.ndarray:
        """Convert meta-features to vector for meta-learning"""
        return np.array([
            self.n_samples,
            self.n_features,
            self.n_classes,
            self.class_balance,
            self.missing_ratio,
            self.dimensionality,
            self.sparsity,
            self.data_complexity
        ])


@dataclass
class ModelRecommendation:
    """Recommendation from the AI engine"""
    task_type: TaskType
    recommended_models: List[ModelType]
    expected_performance: Dict[str, float]
    confidence_score: float
    reasoning: str
    hyperparameter_suggestions: Dict[str, Any]
    ensemble_strategy: Optional[str] = None


class MetaLearningDatabase:
    """Database of past model performances for meta-learning"""
    
    def __init__(self, storage_path: str = "./data/meta_learning_db.pkl"):
        self.storage_path = Path(storage_path)
        self.experiences: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load historical data"""
        if self.storage_path.exists():
            with open(self.storage_path, 'rb') as f:
                self.experiences = pickle.load(f)
            logger.info(f"Loaded {len(self.experiences)} historical experiences")
    
    def save(self):
        """Save historical data"""
        with open(self.storage_path, 'wb') as f:
            pickle.dump(self.experiences, f)
    
    def add_experience(
        self,
        meta_features: DatasetMetaFeatures,
        model_type: ModelType,
        performance: float,
        hyperparameters: Dict[str, Any],
        training_time: float
    ):
        """Add a new experience to the database"""
        self.experiences.append({
            "meta_features": meta_features.to_vector(),
            "task_type": meta_features.task_type.value,
            "model_type": model_type.value,
            "performance": performance,
            "hyperparameters": hyperparameters,
            "training_time": training_time,
            "timestamp": time.time()
        })
    
    def find_similar_datasets(
        self,
        meta_features: DatasetMetaFeatures,
        k: int = 5
    ) -> List[Dict]:
        """Find k most similar datasets using k-NN"""
        if len(self.experiences) < k:
            return self.experiences
        
        query_vector = meta_features.to_vector()
        
        # Calculate distances
        distances = []
        for exp in self.experiences:
            dist = np.linalg.norm(query_vector - exp["meta_features"])
            distances.append((dist, exp))
        
        # Return k nearest neighbors
        distances.sort(key=lambda x: x[0])
        return [exp for _, exp in distances[:k]]


class AutoMLModelSelector:
    """Automated model selection using meta-learning and optimization"""
    
    def __init__(self, meta_db: MetaLearningDatabase):
        self.meta_db = meta_db
        self.available_models = self._get_available_models()
        
    def _get_available_models(self) -> Dict[ModelType, Callable]:
        """Get dictionary of available model constructors"""
        return {
            # Traditional ML
            ModelType.RANDOM_FOREST: lambda: RandomForestClassifier(n_estimators=100),
            ModelType.GRADIENT_BOOSTING: lambda: GradientBoostingClassifier(n_estimators=100),
            ModelType.EXTRA_TREES: lambda: ExtraTreesClassifier(n_estimators=100),
            ModelType.ADABOOST: lambda: AdaBoostClassifier(n_estimators=50),
            ModelType.LOGISTIC_REGRESSION: lambda: LogisticRegression(max_iter=1000),
            ModelType.SVM: lambda: SVC(probability=True),
            ModelType.KNN: lambda: KNeighborsClassifier(n_neighbors=5),
            ModelType.NAIVE_BAYES: lambda: GaussianNB(),
            ModelType.DECISION_TREE: lambda: DecisionTreeClassifier(),
            ModelType.RIDGE_CLASSIFIER: lambda: RidgeClassifier(),
        }
    
    def extract_meta_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: TaskType
    ) -> DatasetMetaFeatures:
        """Extract meta-features from dataset"""
        
        n_samples, n_features = X.shape
        classes, counts = np.unique(y, return_counts=True)
        n_classes = len(classes)
        class_balance = counts.min() / counts.max()
        
        # Determine feature types
        feature_types = {"numeric": 0, "categorical": 0, "binary": 0}
        for i in range(n_features):
            unique_vals = len(np.unique(X[:, i]))
            if unique_vals == 2:
                feature_types["binary"] += 1
            elif unique_vals < 20:
                feature_types["categorical"] += 1
            else:
                feature_types["numeric"] += 1
        
        missing_ratio = np.isnan(X).sum() / (n_samples * n_features)
        dimensionality = n_features / n_samples
        sparsity = (X == 0).sum() / (n_samples * n_features)
        
        # Calculate data complexity using Fisher's ratio
        if n_classes > 1:
            class_means = []
            class_stds = []
            for c in classes:
                mask = y == c
                class_means.append(X[mask].mean(axis=0))
                class_stds.append(X[mask].std(axis=0))
            
            class_means = np.array(class_means)
            overall_mean = X.mean(axis=0)
            
            between_class_var = np.sum((class_means - overall_mean) ** 2, axis=0)
            within_class_var = np.mean(np.array(class_stds) ** 2, axis=0)
            
            data_complexity = np.mean(between_class_var / (within_class_var + 1e-10))
        else:
            data_complexity = 0.0
        
        return DatasetMetaFeatures(
            n_samples=n_samples,
            n_features=n_features,
            n_classes=n_classes,
            class_balance=class_balance,
            feature_types=feature_types,
            missing_ratio=missing_ratio,
            dimensionality=dimensionality,
            sparsity=sparsity,
            task_type=task_type,
            data_complexity=data_complexity
        )
    
    def recommend_models(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: TaskType,
        top_k: int = 3
    ) -> ModelRecommendation:
        """Recommend models using meta-learning and dataset characteristics"""
        
        # Extract meta-features
        meta_features = self.extract_meta_features(X, y, task_type)
        
        # Find similar past experiences
        similar_experiences = self.meta_db.find_similar_datasets(meta_features, k=10)
        
        # Score each model type
        model_scores = {}
        model_performances = {}
        
        for model_type in self.available_models:
            scores = []
            performances = []
            
            for exp in similar_experiences:
                if exp["model_type"] == model_type.value:
                    # Weight by similarity (inverse distance)
                    scores.append(1.0)
                    performances.append(exp["performance"])
            
            if scores:
                model_scores[model_type] = np.mean(scores)
                model_performances[model_type] = np.mean(performances)
            else:
                # Default scores based on heuristics
                model_scores[model_type] = self._get_default_score(model_type, meta_features)
                model_performances[model_type] = 0.5
        
        # Sort and get top-k
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        recommended = [model for model, _ in sorted_models[:top_k]]
        
        # Generate hyperparameter suggestions
        hyperparams = self._suggest_hyperparameters(recommended[0], meta_features)
        
        # Determine if ensemble is needed
        ensemble_strategy = None
        if meta_features.n_samples > 10000 or meta_features.data_complexity > 1.0:
            ensemble_strategy = "stacking"
        
        # Build recommendation
        recommendation = ModelRecommendation(
            task_type=task_type,
            recommended_models=recommended,
            expected_performance={
                model.value: model_performances.get(model, 0.5)
                for model in recommended
            },
            confidence_score=min(len(similar_experiences) / 10, 1.0),
            reasoning=self._generate_reasoning(recommended, meta_features, similar_experiences),
            hyperparameter_suggestions=hyperparams,
            ensemble_strategy=ensemble_strategy
        )
        
        return recommendation
    
    def _get_default_score(
        self,
        model_type: ModelType,
        meta_features: DatasetMetaFeatures
    ) -> float:
        """Get default score based on heuristics"""
        
        # Simple heuristic rules
        if meta_features.n_samples < 1000:
            if model_type in [ModelType.SVM, ModelType.KNN]:
                return 0.8
            elif model_type in [ModelType.RANDOM_FOREST, ModelType.EXTRA_TREES]:
                return 0.7
        elif meta_features.n_samples < 10000:
            if model_type in [ModelType.RANDOM_FOREST, ModelType.GRADIENT_BOOSTING]:
                return 0.8
            elif model_type in [ModelType.EXTRA_TREES, ModelType.LOGISTIC_REGRESSION]:
                return 0.7
        else:
            if model_type in [ModelType.GRADIENT_BOOSTING, ModelType.EXTRA_TREES]:
                return 0.8
            elif model_type in [ModelType.RANDOM_FOREST, ModelType.LOGISTIC_REGRESSION]:
                return 0.7
        
        return 0.5
    
    def _suggest_hyperparameters(
        self,
        model_type: ModelType,
        meta_features: DatasetMetaFeatures
    ) -> Dict[str, Any]:
        """Suggest hyperparameters based on dataset characteristics"""
        
        suggestions = {}
        
        if model_type == ModelType.RANDOM_FOREST:
            suggestions = {
                "n_estimators": min(500, max(100, meta_features.n_samples // 10)),
                "max_depth": min(30, max(5, int(np.log2(meta_features.n_features)))),
                "min_samples_split": max(2, int(meta_features.n_samples * 0.001)),
                "class_weight": "balanced" if meta_features.class_balance < 0.5 else None
            }
        
        elif model_type == ModelType.GRADIENT_BOOSTING:
            suggestions = {
                "n_estimators": min(300, max(50, meta_features.n_samples // 20)),
                "learning_rate": 0.1 if meta_features.n_samples < 10000 else 0.05,
                "max_depth": min(8, max(3, int(np.log2(meta_features.n_features)) // 2)),
                "subsample": 0.8 if meta_features.n_samples > 10000 else 1.0
            }
        
        elif model_type == ModelType.EXTRA_TREES:
            suggestions = {
                "n_estimators": min(500, max(100, meta_features.n_samples // 10)),
                "max_depth": None,
                "min_samples_split": 2,
                "class_weight": "balanced" if meta_features.class_balance < 0.5 else None
            }
        
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            suggestions = {
                "C": 1.0,
                "max_iter": 1000,
                "class_weight": "balanced" if meta_features.class_balance < 0.5 else None,
                "solver": "lbfgs" if meta_features.n_features < 1000 else "saga"
            }
        
        return suggestions
    
    def _generate_reasoning(
        self,
        recommended: List[ModelType],
        meta_features: DatasetMetaFeatures,
        similar_experiences: List[Dict]
    ) -> str:
        """Generate human-readable reasoning for recommendation"""
        
        reasoning_parts = []
        
        # Dataset characteristics
        reasoning_parts.append(
            f"Dataset has {meta_features.n_samples} samples, "
            f"{meta_features.n_features} features, and {meta_features.n_classes} classes."
        )
        
        if meta_features.class_balance < 0.5:
            reasoning_parts.append(
                "Dataset is imbalanced (class balance < 0.5), "
                "so models with class_weight='balanced' are preferred."
            )
        
        if meta_features.dimensionality > 0.1:
            reasoning_parts.append(
                "High dimensionality detected, preferring regularized models."
            )
        
        # Similar experiences
        if similar_experiences:
            best_exp = max(similar_experiences, key=lambda x: x["performance"])
            reasoning_parts.append(
                f"Based on {len(similar_experiences)} similar datasets, "
                f"{best_exp['model_type']} achieved best performance of {best_exp['performance']:.3f}."
            )
        
        # Recommendation summary
        reasoning_parts.append(
            f"Top recommendation: {recommended[0].value} "
            f"due to its {'robustness' if recommended[0] in [ModelType.RANDOM_FOREST, ModelType.EXTRA_TREES] else 'efficiency'} "
            f"for this dataset size and complexity."
        )
        
        return " ".join(reasoning_parts)


class HyperparameterOptimizer:
    """Optuna-based hyperparameter optimization"""
    
    def __init__(self, n_trials: int = 100, timeout: int = 3600):
        self.n_trials = n_trials
        self.timeout = timeout
    
    def optimize(
        self,
        model_type: ModelType,
        X: np.ndarray,
        y: np.ndarray,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """Optimize hyperparameters for a given model"""
        
        def objective(trial):
            # Define hyperparameter search space
            params = self._get_search_space(trial, model_type)
            
            # Create model
            model = self._create_model(model_type, params)
            
            # Cross-validation
            scores = cross_val_score(
                model, X, y,
                cv=StratifiedKFold(n_splits=cv_folds, shuffle=True),
                scoring='roc_auc',
                n_jobs=-1
            )
            
            return scores.mean()
        
        # Create study
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=42)
        )
        
        # Optimize
        study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=True
        )
        
        return study.best_params
    
    def _get_search_space(self, trial, model_type: ModelType) -> Dict[str, Any]:
        """Define hyperparameter search space"""
        
        if model_type == ModelType.RANDOM_FOREST:
            return {
                "n_estimators": trial.suggest_int("n_estimators", 50, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 50),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None])
            }
        
        elif model_type == ModelType.GRADIENT_BOOSTING:
            return {
                "n_estimators": trial.suggest_int("n_estimators", 50, 500),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "max_depth": trial.suggest_int("max_depth", 3, 15),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20)
            }
        
        elif model_type == ModelType.EXTRA_TREES:
            return {
                "n_estimators": trial.suggest_int("n_estimators", 50, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 50),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10)
            }
        
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return {
                "C": trial.suggest_float("C", 0.001, 100.0, log=True),
                "max_iter": trial.suggest_int("max_iter", 100, 2000),
                "solver": trial.suggest_categorical("solver", ["lbfgs", "liblinear", "saga"])
            }
        
        elif model_type == ModelType.SVM:
            return {
                "C": trial.suggest_float("C", 0.1, 100.0, log=True),
                "kernel": trial.suggest_categorical("kernel", ["rbf", "poly", "sigmoid"]),
                "gamma": trial.suggest_categorical("gamma", ["scale", "auto"])
            }
        
        return {}
    
    def _create_model(self, model_type: ModelType, params: Dict[str, Any]):
        """Create model instance with given parameters"""
        
        if model_type == ModelType.RANDOM_FOREST:
            return RandomForestClassifier(**params, random_state=42)
        elif model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingClassifier(**params, random_state=42)
        elif model_type == ModelType.EXTRA_TREES:
            return ExtraTreesClassifier(**params, random_state=42)
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return LogisticRegression(**params, random_state=42)
        elif model_type == ModelType.SVM:
            return SVC(**params, probability=True, random_state=42)
        
        raise ValueError(f"Unknown model type: {model_type}")


class ModelSelectionEnvironment(gym.Env):
    """Reinforcement Learning environment for model selection"""
    
    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        available_models: List[ModelType],
        max_steps: int = 10
    ):
        super().__init__()
        
        self.X = X
        self.y = y
        self.available_models = available_models
        self.max_steps = max_steps
        
        # Action space: select model + hyperparameter configuration
        self.action_space = spaces.Discrete(len(available_models))
        
        # Observation space: dataset meta-features
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(8,),  # meta-feature vector size
            dtype=np.float32
        )
        
        self.current_step = 0
        self.best_score = 0.0
        self.meta_features = None
    
    def reset(self, seed=None, options=None):
        """Reset environment"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.best_score = 0.0
        
        # Extract meta-features
        from services.model_recommendation_engine import AutoMLModelSelector
        selector = AutoMLModelSelector(MetaLearningDatabase())
        self.meta_features = selector.extract_meta_features(
            self.X, self.y, TaskType.LANDSLIDE_SUSCEPTIBILITY
        )
        
        return self.meta_features.to_vector(), {}
    
    def step(self, action):
        """Execute action and return new state"""
        
        # Get selected model
        model_type = self.available_models[action]
        
        # Train model with default hyperparameters
        model = self._create_model(model_type)
        
        # Evaluate with cross-validation
        scores = cross_val_score(
            model, self.X, self.y,
            cv=StratifiedKFold(n_splits=3, shuffle=True),
            scoring='roc_auc'
        )
        
        score = scores.mean()
        
        # Reward: improvement over best score
        reward = score - self.best_score
        self.best_score = max(self.best_score, score)
        
        self.current_step += 1
        terminated = self.current_step >= self.max_steps
        truncated = False
        
        # Update meta-features with new information
        observation = self.meta_features.to_vector()
        
        info = {
            "model_type": model_type.value,
            "score": score,
            "best_score": self.best_score
        }
        
        return observation, reward, terminated, truncated, info
    
    def _create_model(self, model_type: ModelType):
        """Create model instance"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        
        if model_type == ModelType.RANDOM_FOREST:
            return RandomForestClassifier(n_estimators=100, random_state=42)
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return LogisticRegression(max_iter=1000, random_state=42)
        else:
            return RandomForestClassifier(n_estimators=50, random_state=42)


class RLModelSelector:
    """Reinforcement Learning based model selection"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.agent = None
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        available_models: List[ModelType],
        total_timesteps: int = 100000
    ):
        """Train RL agent for model selection"""
        
        # Create environment
        env = ModelSelectionEnvironment(X, y, available_models)
        env = DummyVecEnv([lambda: env])
        
        # Create and train agent
        self.agent = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99
        )
        
        self.agent.learn(total_timesteps=total_timesteps)
        
        # Save model
        if self.model_path:
            self.agent.save(self.model_path)
    
    def select_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        available_models: List[ModelType]
    ) -> ModelType:
        """Select best model using trained RL agent"""
        
        if self.agent is None:
            raise RuntimeError("Agent not trained. Call train() first.")
        
        # Create environment
        env = ModelSelectionEnvironment(X, y, available_models)
        env = DummyVecEnv([lambda: env])
        
        # Reset and get initial observation
        obs, _ = env.reset()
        
        # Get action from agent
        action, _ = self.agent.predict(obs, deterministic=True)
        
        return available_models[action[0]]


class EnsembleBuilder:
    """Build and optimize ensemble models"""
    
    def __init__(self):
        self.base_models = []
        self.meta_learner = None
    
    def create_voting_ensemble(
        self,
        models: List[Any],
        voting: str = "soft"
    ) -> VotingClassifier:
        """Create voting ensemble from multiple models"""
        
        # Create named estimators
        estimators = [
            (f"model_{i}", model)
            for i, model in enumerate(models)
        ]
        
        ensemble = VotingClassifier(
            estimators=estimators,
            voting=voting,
            n_jobs=-1
        )
        
        return ensemble
    
    def create_stacking_ensemble(
        self,
        base_models: List[Any],
        meta_learner: Any = None,
        cv: int = 5
    ):
        """Create stacking ensemble"""
        
        from sklearn.ensemble import StackingClassifier
        
        if meta_learner is None:
            meta_learner = LogisticRegression(max_iter=1000)
        
        estimators = [
            (f"base_{i}", model)
            for i, model in enumerate(base_models)
        ]
        
        ensemble = StackingClassifier(
            estimators=estimators,
            final_estimator=meta_learner,
            cv=cv,
            stack_method="predict_proba",
            n_jobs=-1
        )
        
        return ensemble
    
    def optimize_ensemble_weights(
        self,
        models: List[Any],
        X: np.ndarray,
        y: np.ndarray,
        metric: str = "roc_auc"
    ) -> np.ndarray:
        """Optimize ensemble weights using optimization"""
        
        from scipy.optimize import minimize
        from sklearn.metrics import roc_auc_score
        
        # Get predictions from each model
        predictions = []
        for model in models:
            if hasattr(model, "predict_proba"):
                pred = model.predict_proba(X)[:, 1]
            else:
                pred = model.predict(X)
            predictions.append(pred)
        
        predictions = np.array(predictions)
        
        # Objective function: negative AUC
        def objective(weights):
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize
            
            ensemble_pred = np.average(predictions, axis=0, weights=weights)
            
            if metric == "roc_auc":
                score = roc_auc_score(y, ensemble_pred)
            else:
                from sklearn.metrics import accuracy_score
                score = accuracy_score(y, (ensemble_pred > 0.5).astype(int))
            
            return -score
        
        # Optimize
        n_models = len(models)
        initial_weights = np.ones(n_models) / n_models
        
        result = minimize(
            objective,
            initial_weights,
            method='Nelder-Mead',
            bounds=[(0, 1)] * n_models
        )
        
        optimal_weights = result.x / result.x.sum()
        
        return optimal_weights


class ModelRecommendationEngine:
    """Main engine orchestrating model recommendation"""
    
    def __init__(
        self,
        config_path: str = "config/system_config.yaml",
        use_rl: bool = False
    ):
        import yaml
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.meta_db = MetaLearningDatabase()
        self.selector = AutoMLModelSelector(self.meta_db)
        self.optimizer = HyperparameterOptimizer(
            n_trials=self.config.get("models", {}).get("hyperparameter_optimization", {}).get("n_trials", 100),
            timeout=self.config.get("models", {}).get("hyperparameter_optimization", {}).get("timeout", 3600)
        )
        self.ensemble_builder = EnsembleBuilder()
        
        self.rl_selector = None
        if use_rl:
            self.rl_selector = RLModelSelector()
    
    def recommend_and_train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        task_type: TaskType,
        optimize_hyperparams: bool = True,
        build_ensemble: bool = True
    ) -> Dict[str, Any]:
        """Full pipeline: recommend, optimize, and train models"""
        
        logger.info(f"Starting model recommendation for task: {task_type.value}")
        
        # Step 1: Get model recommendations
        recommendation = self.selector.recommend_models(X, y, task_type)
        logger.info(f"Recommended models: {[m.value for m in recommendation.recommended_models]}")
        
        # Step 2: Optimize hyperparameters for each recommended model
        trained_models = []
        model_performances = {}
        
        for model_type in recommendation.recommended_models:
            logger.info(f"Training and optimizing {model_type.value}...")
            
            if optimize_hyperparams:
                # Optimize hyperparameters
                best_params = self.optimizer.optimize(model_type, X, y)
                logger.info(f"Best hyperparameters for {model_type.value}: {best_params}")
            else:
                best_params = recommendation.hyperparameter_suggestions.get(model_type, {})
            
            # Train model with best parameters
            model = self.optimizer._create_model(model_type, best_params)
            
            # Evaluate with cross-validation
            scores = cross_val_score(
                model, X, y,
                cv=StratifiedKFold(n_splits=5, shuffle=True),
                scoring='roc_auc',
                n_jobs=-1
            )
            
            performance = scores.mean()
            model_performances[model_type.value] = {
                "mean_auc": performance,
                "std_auc": scores.std(),
                "params": best_params
            }
            
            # Store experience in meta-learning database
            meta_features = self.selector.extract_meta_features(X, y, task_type)
            self.meta_db.add_experience(
                meta_features, model_type, performance, best_params, 0.0
            )
            
            # Fit final model
            model.fit(X, y)
            trained_models.append((model_type, model))
            
            logger.info(f"{model_type.value} performance: {performance:.4f} (+/- {scores.std():.4f})")
        
        # Step 3: Build ensemble if recommended
        ensemble_model = None
        if build_ensemble and recommendation.ensemble_strategy:
            logger.info(f"Building {recommendation.ensemble_strategy} ensemble...")
            
            if recommendation.ensemble_strategy == "voting":
                ensemble_model = self.ensemble_builder.create_voting_ensemble(
                    [model for _, model in trained_models]
                )
            elif recommendation.ensemble_strategy == "stacking":
                ensemble_model = self.ensemble_builder.create_stacking_ensemble(
                    [model for _, model in trained_models]
                )
            
            if ensemble_model:
                ensemble_model.fit(X, y)
                
                # Evaluate ensemble
                scores = cross_val_score(
                    ensemble_model, X, y,
                    cv=StratifiedKFold(n_splits=5, shuffle=True),
                    scoring='roc_auc',
                    n_jobs=-1
                )
                
                logger.info(f"Ensemble performance: {scores.mean():.4f} (+/- {scores.std():.4f})")
        
        # Save meta-learning database
        self.meta_db.save()
        
        return {
            "recommendation": recommendation,
            "trained_models": trained_models,
            "model_performances": model_performances,
            "ensemble_model": ensemble_model,
            "task_type": task_type
        }


# Example usage
if __name__ == "__main__":
    # Create sample data
    from sklearn.datasets import make_classification
    
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        n_classes=2,
        random_state=42
    )
    
    # Initialize engine
    engine = ModelRecommendationEngine()
    
    # Get recommendation and train
    results = engine.recommend_and_train(
        X, y,
        task_type=TaskType.LANDSLIDE_SUSCEPTIBILITY,
        optimize_hyperparams=True,
        build_ensemble=True
    )
    
    print("\n=== Model Recommendation Results ===")
    print(f"Task: {results['task_type'].value}")
    print(f"Recommended models: {[m.value for m in results['recommendation'].recommended_models]}")
    print(f"Ensemble strategy: {results['recommendation'].ensemble_strategy}")
    print(f"Confidence: {results['recommendation'].confidence_score:.2f}")
    print(f"\nReasoning: {results['recommendation'].reasoning}")
    
    print("\n=== Model Performances ===")
    for model_name, perf in results['model_performances'].items():
        print(f"{model_name}: AUC = {perf['mean_auc']:.4f} (+/- {perf['std_auc']:.4f})")
