"""
EarthAI Platform - Reinforcement Learning Module
Implements RL agents for sequential decision-making in Earth system modeling
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO, DQN, A2C, SAC
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RLEnvironmentConfig:
    """Configuration for RL environment"""
    max_steps: int = 1000
    action_space_type: str = "discrete"  # discrete, continuous
    observation_dim: int = 64
    action_dim: int = 10
    reward_type: str = "accuracy_based"
    use_spatial_features: bool = True
    temporal_horizon: int = 30
    penalty_coefficient: float = 0.1


class EarthObservationEnv(gym.Env):
    """
    Custom RL environment for Earth system modeling
    State: Current model predictions, data quality, environmental conditions
    Actions: Model selection, hyperparameter adjustments, data collection decisions
    Reward: Prediction accuracy improvement, data quality, resource efficiency
    """
    
    def __init__(
        self,
        data_source: Callable,
        model_pool: List[Any],
        config: RLEnvironmentConfig
    ):
        super().__init__()
        
        self.data_source = data_source
        self.model_pool = model_pool
        self.config = config
        self.current_step = 0
        self.current_data = None
        self.current_prediction = None
        self.ground_truth = None
        self.model_history = []
        self.performance_history = []
        
        # Define action space
        if config.action_space_type == "discrete":
            # Actions: [select_model_1, ..., select_model_n, collect_new_data, adjust_params, stop]
            self.action_space = spaces.Discrete(len(model_pool) + 3)
        else:
            # Continuous action space for hyperparameter tuning
            self.action_space = spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(config.action_dim,),
                dtype=np.float32
            )
        
        # Define observation space
        # State includes: model performance, data statistics, temporal features, spatial features
        obs_dim = config.observation_dim
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )
        
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize environment state"""
        self.current_data = self.data_source()
        self.current_prediction = None
        self.performance_history = []
        self.model_history = []
    
    def _get_observation(self) -> np.ndarray:
        """Construct current observation from environment state"""
        obs = np.zeros(self.config.observation_dim, dtype=np.float32)
        
        # Data quality metrics (first 16 dims)
        if self.current_data is not None:
            data_stats = self._compute_data_statistics(self.current_data)
            obs[:min(16, len(data_stats))] = data_stats[:16]
        
        # Model performance history (next 16 dims)
        if self.performance_history:
            perf_features = self._extract_performance_features(self.performance_history)
            obs[16:32] = perf_features[:16]
        
        # Temporal features (next 16 dims)
        temporal_features = self._extract_temporal_features(self.current_step)
        obs[32:48] = temporal_features[:16]
        
        # Spatial features (last 16 dims)
        if self.config.use_spatial_features and self.current_data is not None:
            spatial_features = self._extract_spatial_features(self.current_data)
            obs[48:64] = spatial_features[:16]
        
        return obs
    
    def _compute_data_statistics(self, data: Dict[str, Any]) -> np.ndarray:
        """Compute statistics from current data"""
        stats = []
        
        # Data completeness
        if "missing_ratio" in data:
            stats.append(data["missing_ratio"])
        
        # Data variance
        if "features" in data:
            features = data["features"]
            stats.extend([
                np.mean(features),
                np.std(features),
                np.min(features),
                np.max(features),
                np.percentile(features, 25),
                np.percentile(features, 75),
                np.median(features)
            ])
        
        # Data recency
        if "timestamp" in data:
            age = (np.datetime64('now') - data["timestamp"]).astype('timedelta64[D]').astype(float)
            stats.append(age / 365.0)  # Normalized age in years
        
        # Data resolution
        if "resolution" in data:
            stats.append(data["resolution"] / 1000.0)  # km
        
        # Number of samples
        if "n_samples" in data:
            stats.append(np.log1p(data["n_samples"]))
        
        return np.array(stats + [0.0] * (16 - len(stats)))
    
    def _extract_performance_features(self, history: List[float]) -> np.ndarray:
        """Extract features from performance history"""
        if not history:
            return np.zeros(16)
        
        hist_array = np.array(history[-100:])  # Last 100 episodes
        
        features = [
            np.mean(hist_array),
            np.std(hist_array),
            np.max(hist_array),
            np.min(hist_array),
            np.percentile(hist_array, 25),
            np.percentile(hist_array, 75),
            len(history) / 1000.0,  # Normalized episode count
        ]
        
        # Trend features
        if len(hist_array) >= 10:
            recent = hist_array[-10:]
            early = hist_array[:10] if len(hist_array) >= 20 else hist_array[:5]
            features.append(np.mean(recent) - np.mean(early))
            features.append(np.std(recent))
        else:
            features.extend([0.0, 0.0])
        
        return np.array(features + [0.0] * (16 - len(features)))
    
    def _extract_temporal_features(self, step: int) -> np.ndarray:
        """Extract temporal features from current step"""
        # Cyclical encoding of time
        time_norm = step / self.config.max_steps
        
        features = [
            time_norm,
            np.sin(2 * np.pi * time_norm),
            np.cos(2 * np.pi * time_norm),
            step / 100.0,
            1.0 - time_norm,  # Remaining time
            np.exp(-time_norm * 3),  # Decay factor
        ]
        
        # Seasonal features (if we have datetime)
        try:
            import datetime
            now = datetime.datetime.now()
            day_of_year = now.timetuple().tm_yday / 365.0
            features.extend([
                np.sin(2 * np.pi * day_of_year),
                np.cos(2 * np.pi * day_of_year),
                now.month / 12.0,
                now.hour / 24.0,
            ])
        except:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        return np.array(features + [0.0] * (16 - len(features)))
    
    def _extract_spatial_features(self, data: Dict[str, Any]) -> np.ndarray:
        """Extract spatial features from current data"""
        features = []
        
        if "coordinates" in data:
            lon, lat = data["coordinates"]
            features.extend([
                lon / 180.0,  # Normalized longitude
                lat / 90.0,   # Normalized latitude
                np.sin(np.radians(lat)),
                np.cos(np.radians(lat)),
            ])
        
        if "elevation" in data:
            features.append(data["elevation"] / 8848.0)  # Normalized to Everest
        
        if "land_cover_type" in data:
            # One-hot encoded land cover (simplified)
            lc = data["land_cover_type"]
            features.extend([
                1.0 if lc == "forest" else 0.0,
                1.0 if lc == "urban" else 0.0,
                1.0 if lc == "water" else 0.0,
                1.0 if lc == "agriculture" else 0.0,
            ])
        
        return np.array(features + [0.0] * (16 - len(features)))
    
    def _compute_reward(
        self,
        action: int,
        old_performance: float,
        new_performance: float
    ) -> float:
        """Compute reward based on action and performance change"""
        
        if self.config.reward_type == "accuracy_based":
            # Primary reward: performance improvement
            improvement = new_performance - old_performance
            reward = improvement * 10.0  # Scale up
            
            # Bonus for high absolute performance
            if new_performance > 0.9:
                reward += 5.0
            
            # Penalty for switching models too frequently
            if len(self.model_history) > 1 and self.model_history[-1] != self.model_history[-2]:
                reward -= self.config.penalty_coefficient
            
            # Penalty for resource usage (data collection is expensive)
            if action >= len(self.model_pool):
                reward -= 2.0  # Cost of data collection
            
        elif self.config.reward_type == "efficiency_based":
            # Reward considers both accuracy and efficiency
            accuracy_component = new_performance
            efficiency_component = 1.0 - (len(self.model_history) / self.config.max_steps)
            reward = 0.7 * accuracy_component + 0.3 * efficiency_component
            
        else:
            reward = new_performance - old_performance
        
        return reward
    
    def reset(self, seed=None, options=None):
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self._initialize_state()
        
        observation = self._get_observation()
        info = {
            "episode": len(self.performance_history),
            "available_models": len(self.model_pool)
        }
        
        return observation, info
    
    def step(self, action):
        """Execute action and return new state"""
        
        # Record action
        self.model_history.append(action)
        
        # Get current performance before action
        old_performance = self.performance_history[-1] if self.performance_history else 0.5
        
        # Execute action
        if action < len(self.model_pool):
            # Select a model from the pool
            selected_model = self.model_pool[action]
            self.current_prediction = self._run_model(selected_model, self.current_data)
            
        elif action == len(self.model_pool):
            # Collect new data
            self.current_data = self.data_source()
            self.current_prediction = None
            
        elif action == len(self.model_pool) + 1:
            # Adjust model hyperparameters (simplified)
            # In practice, this would call the hyperparameter optimizer
            pass
            
        else:
            # Stop/terminal action
            new_performance = self._evaluate_current_state()
            reward = self._compute_reward(action, old_performance, new_performance)
            self.performance_history.append(new_performance)
            
            observation = self._get_observation()
            terminated = True
            truncated = False
            info = {"final_performance": new_performance}
            
            return observation, reward, terminated, truncated, info
        
        # Evaluate new state
        new_performance = self._evaluate_current_state()
        reward = self._compute_reward(action, old_performance, new_performance)
        self.performance_history.append(new_performance)
        
        # Update step counter
        self.current_step += 1
        
        # Check termination conditions
        terminated = False
        truncated = self.current_step >= self.config.max_steps
        
        # Check if we've reached target performance
        if new_performance > 0.95:
            terminated = True
            reward += 10.0  # Big bonus for reaching target
        
        observation = self._get_observation()
        info = {
            "performance": new_performance,
            "improvement": new_performance - old_performance,
            "step": self.current_step
        }
        
        return observation, reward, terminated, truncated, info
    
    def _run_model(self, model: Any, data: Dict[str, Any]) -> Any:
        """Run model prediction on current data"""
        try:
            if hasattr(model, 'predict'):
                features = data.get("features", np.zeros(10))
                return model.predict(features.reshape(1, -1))[0]
            else:
                return 0.5
        except Exception as e:
            logger.error(f"Model prediction error: {e}")
            return 0.5
    
    def _evaluate_current_state(self) -> float:
        """Evaluate current prediction quality"""
        if self.current_prediction is None or self.ground_truth is None:
            return 0.5
        
        # Compute accuracy or other metric
        if isinstance(self.current_prediction, (int, float)) and isinstance(self.ground_truth, (int, float)):
            accuracy = 1.0 - abs(self.current_prediction - self.ground_truth)
            return max(0.0, min(1.0, accuracy))
        
        return 0.5


class EarthObservationFeatureExtractor(BaseFeaturesExtractor):
    """Custom feature extractor for RL agent"""
    
    def __init__(self, observation_space: spaces.Box, features_dim: int = 256):
        super().__init__(observation_space, features_dim)
        
        input_dim = observation_space.shape[0]
        
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, features_dim),
            nn.ReLU()
        )
    
    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        return self.network(observations)


class RLTrainingCallback(BaseCallback):
    """Custom callback for RL training monitoring"""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.best_mean_reward = -np.inf
    
    def _on_step(self) -> bool:
        # Log training metrics
        if len(self.model.ep_info_buffer) > 0:
            episode_info = self.model.ep_info_buffer[-1]
            self.episode_rewards.append(episode_info["r"])
            self.episode_lengths.append(episode_info["l"])
            
            # Log to wandb if available
            try:
                import wandb
                wandb.log({
                    "episode_reward": episode_info["r"],
                    "episode_length": episode_info["l"],
                    "timesteps": self.num_timesteps
                })
            except:
                pass
            
            # Check for new best model
            if len(self.episode_rewards) >= 100:
                mean_reward = np.mean(self.episode_rewards[-100:])
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    if self.verbose > 0:
                        logger.info(f"New best mean reward: {mean_reward:.2f}")
        
        return True


class RLAgent:
    """Reinforcement Learning Agent for Earth system modeling"""
    
    def __init__(
        self,
        algorithm: str = "PPO",
        policy: str = "MlpPolicy",
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        features_dim: int = 256
    ):
        self.algorithm = algorithm
        self.policy = policy
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.features_dim = features_dim
        self.model = None
    
    def create_agent(
        self,
        env: gym.Env,
        policy_kwargs: Optional[Dict] = None
    ):
        """Create RL agent"""
        
        if policy_kwargs is None:
            policy_kwargs = {
                "features_extractor_class": EarthObservationFeatureExtractor,
                "features_extractor_kwargs": {"features_dim": self.features_dim}
            }
        
        # Vectorize environment
        if isinstance(env, DummyVecEnv):
            vec_env = env
        else:
            vec_env = DummyVecEnv([lambda: env])
        
        # Create model based on algorithm
        if self.algorithm == "PPO":
            self.model = PPO(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                n_steps=self.n_steps,
                batch_size=self.batch_size,
                n_epochs=self.n_epochs,
                gamma=self.gamma,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./logs/rl"
            )
        elif self.algorithm == "DQN":
            self.model = DQN(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                buffer_size=100000,
                learning_starts=1000,
                batch_size=self.batch_size,
                gamma=self.gamma,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./logs/rl"
            )
        elif self.algorithm == "A2C":
            self.model = A2C(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                n_steps=self.n_steps,
                gamma=self.gamma,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./logs/rl"
            )
        elif self.algorithm == "SAC":
            self.model = SAC(
                self.policy,
                vec_env,
                learning_rate=self.learning_rate,
                buffer_size=100000,
                batch_size=self.batch_size,
                gamma=self.gamma,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./logs/rl"
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        return self.model
    
    def train(
        self,
        total_timesteps: int = 100000,
        callback: Optional[BaseCallback] = None,
        eval_freq: int = 10000,
        save_freq: int = 10000
    ):
        """Train RL agent"""
        
        if self.model is None:
            raise RuntimeError("Agent not created. Call create_agent() first.")
        
        if callback is None:
            callback = RLTrainingCallback(verbose=1)
        
        logger.info(f"Starting RL training for {total_timesteps} timesteps...")
        
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            progress_bar=True
        )
        
        logger.info("RL training completed")
    
    def predict(self, observation: np.ndarray, deterministic: bool = True) -> Tuple[int, Dict]:
        """Get action from trained agent"""
        
        if self.model is None:
            raise RuntimeError("Agent not trained")
        
        action, _states = self.model.predict(observation, deterministic=deterministic)
        info = {"state_value": None}  # Could be extended with value function output
        
        return int(action), info
    
    def save(self, path: str):
        """Save trained agent"""
        if self.model:
            self.model.save(path)
            logger.info(f"Agent saved to {path}")
    
    def load(self, path: str, env: Optional[gym.Env] = None):
        """Load trained agent"""
        
        if self.algorithm == "PPO":
            self.model = PPO.load(path, env=env)
        elif self.algorithm == "DQN":
            self.model = DQN.load(path, env=env)
        elif self.algorithm == "A2C":
            self.model = A2C.load(path, env=env)
        elif self.algorithm == "SAC":
            self.model = SAC.load(path, env=env)
        
        logger.info(f"Agent loaded from {path}")


class ModelSelectionRL:
    """RL-based model selection for Earth system modeling"""
    
    def __init__(
        self,
        data_source: Callable,
        model_pool: List[Any],
        config: Optional[RLEnvironmentConfig] = None
    ):
        self.data_source = data_source
        self.model_pool = model_pool
        self.config = config or RLEnvironmentConfig()
        self.env = None
        self.agent = None
    
    def setup(self):
        """Setup RL environment and agent"""
        # Create environment
        self.env = EarthObservationEnv(
            self.data_source,
            self.model_pool,
            self.config
        )
        
        # Create and setup agent
        self.agent = RLAgent(algorithm="PPO")
        self.agent.create_agent(self.env)
    
    def train(
        self,
        total_timesteps: int = 100000,
        **kwargs
    ):
        """Train RL agent for model selection"""
        if self.agent is None:
            self.setup()
        
        self.agent.train(total_timesteps=total_timesteps, **kwargs)
    
    def select_model(self, observation: np.ndarray) -> Tuple[int, float]:
        """Select best model using trained RL agent"""
        if self.agent is None:
            raise RuntimeError("Agent not trained")
        
        action, info = self.agent.predict(observation)
        
        if action < len(self.model_pool):
            return action, 1.0  # Confidence score
        else:
            return -1, 0.0  # Special action (collect data, etc.)


# Example usage
if __name__ == "__main__":
    # Create dummy data source
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
    
    # Create dummy model pool
    from sklearn.ensemble import RandomForestClassifier
    dummy_models = [RandomForestClassifier(n_estimators=10) for _ in range(3)]
    
    # Create RL system
    rl_system = ModelSelectionRL(
        data_source=dummy_data_source,
        model_pool=dummy_models
    )
    
    # Setup and train
    rl_system.setup()
    rl_system.train(total_timesteps=10000)
    
    # Test prediction
    obs = rl_system.env.reset()[0]
    action, confidence = rl_system.select_model(obs)
    print(f"Selected model: {action}, Confidence: {confidence:.2f}")
