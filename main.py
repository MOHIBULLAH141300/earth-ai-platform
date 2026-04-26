#!/usr/bin/env python3
"""
EarthAI Platform - Main Application Entry Point
Integrates all modules for Earth system modeling
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('earth_ai_platform.log')
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()


class EarthAIPlatform:
    """Main platform orchestrator"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.initialized = False
        
        # Service instances
        self.data_service = None
        self.model_recommendation = None
        self.deployment_manager = None
        self.api_server = None
    
    def _load_config(self) -> dict:
        """Load system configuration"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        
        with open(self.config_path, 'r') as f:
            cfg = yaml.safe_load(f) or {}
            return self._expand_env_vars(cfg)

    def _expand_env_vars(self, value):
        """Recursively expand ${VAR} placeholders from environment."""
        if isinstance(value, dict):
            return {k: self._expand_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._expand_env_vars(v) for v in value]
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_key = value[2:-1]
            return os.getenv(env_key, "")
        return value
    
    def initialize(self):
        """Initialize all platform services"""
        logger.info("Initializing EarthAI Platform...")
        
        # Import services
        from services.data_ingestion import DataIngestionService
        from services.model_recommendation_engine import ModelRecommendationEngine
        from monitoring.deployment_manager import DeploymentManager
        
        # Initialize data service
        logger.info("Initializing Data Ingestion Service...")
        self.data_service = DataIngestionService(str(self.config_path))
        
        # Initialize model recommendation
        logger.info("Initializing Model Recommendation Engine...")
        self.model_recommendation = ModelRecommendationEngine(str(self.config_path))
        
        # Initialize deployment manager
        logger.info("Initializing Deployment Manager...")
        self.deployment_manager = DeploymentManager()
        self.deployment_manager.start()
        
        self.initialized = True
        logger.info("EarthAI Platform initialized successfully")
    
    def run_api_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server"""
        if not self.initialized:
            self.initialize()
        
        logger.info(f"Starting API server on {host}:{port}...")
        
        import uvicorn
        from api.main_api import app
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    
    def run_cli(self):
        """Run interactive CLI"""
        if not self.initialized:
            self.initialize()
        
        print("\n" + "="*60)
        print("  EarthAI Platform - Interactive CLI")
        print("="*60 + "\n")
        
        while True:
            print("\nAvailable commands:")
            print("  1. data - Data ingestion and preprocessing")
            print("  2. train - Model training")
            print("  3. predict - Make predictions")
            print("  4. expert - Expert system assessment")
            print("  5. bayesian - Bayesian network inference")
            print("  6. ontology - Query knowledge base")
            print("  7. monitor - System monitoring")
            print("  8. exit - Exit platform")
            
            choice = input("\nEnter command (1-8): ").strip()
            
            if choice == "1" or choice.lower() == "data":
                self._data_menu()
            elif choice == "2" or choice.lower() == "train":
                self._training_menu()
            elif choice == "3" or choice.lower() == "predict":
                self._prediction_menu()
            elif choice == "4" or choice.lower() == "expert":
                self._expert_menu()
            elif choice == "5" or choice.lower() == "bayesian":
                self._bayesian_menu()
            elif choice == "6" or choice.lower() == "ontology":
                self._ontology_menu()
            elif choice == "7" or choice.lower() == "monitor":
                self._monitor_menu()
            elif choice == "8" or choice.lower() == "exit":
                print("Shutting down EarthAI Platform...")
                self.shutdown()
                break
            else:
                print("Invalid command. Please try again.")
    
    def _data_menu(self):
        """Data ingestion menu"""
        print("\n--- Data Ingestion ---")
        print("Select data source:")
        print("  1. Google Earth Engine")
        print("  2. Climate Data (Open-Meteo)")
        print("  3. NASA POWER")
        print("  4. Back")
        
        choice = input("Choice: ").strip()
        
        if choice == "1":
            print("GEE data ingestion selected")
            # Implementation would go here
        elif choice == "2":
            print("Climate data ingestion selected")
            # Implementation would go here
        elif choice == "3":
            print("NASA POWER data ingestion selected")
            # Implementation would go here
        elif choice == "4":
            return
    
    def _training_menu(self):
        """Model training menu"""
        print("\n--- Model Training ---")
        print("Select task type:")
        print("  1. Landslide Susceptibility")
        print("  2. Climate Prediction")
        print("  3. Flood Risk Assessment")
        print("  4. Custom")
        print("  5. Back")
        
        choice = input("Choice: ").strip()
        
        if choice in ["1", "2", "3", "4"]:
            print("Training started...")
            # Implementation would go here
        elif choice == "5":
            return
    
    def _prediction_menu(self):
        """Prediction menu"""
        print("\n--- Prediction ---")
        print("Enter model ID (or 'list' to see available models):")
        model_id = input("Model ID: ").strip()
        
        if model_id.lower() == "list":
            # List available models
            print("Available models:")
            # Implementation would go here
        else:
            print(f"Loading model {model_id}...")
            # Implementation would go here
    
    def _expert_menu(self):
        """Expert system menu"""
        print("\n--- Expert System ---")
        print("Select assessment type:")
        print("  1. Landslide Risk")
        print("  2. Flood Risk")
        print("  3. Drought Risk")
        print("  4. Back")
        
        choice = input("Choice: ").strip()
        
        if choice == "1":
            print("\nEnter parameters:")
            slope = float(input("Slope angle (degrees): "))
            rainfall = float(input("24h rainfall (mm): "))
            vegetation = float(input("Vegetation cover (0-1): "))
            
            # Run expert system
            from services.expert_fuzzy_systems import LandslideExpertSystem, LandslideFuzzySystem
            
            expert = LandslideExpertSystem()
            results = expert.assess(
                slope_angle=slope,
                soil_type="loam",
                rainfall_24h=rainfall,
                vegetation_cover=vegetation
            )
            
            risk_level, confidence = expert.get_risk_level(results)
            print(f"\nRisk Level: {risk_level.upper()}")
            print(f"Confidence: {confidence:.2%}")
            
            # Fuzzy assessment
            fuzzy = LandslideFuzzySystem()
            fuzzy_result = fuzzy.assess(slope, rainfall, vegetation)
            print(f"\nFuzzy Susceptibility: {fuzzy_result.get('susceptibility', 0):.3f}")
            
        elif choice == "4":
            return
    
    def _bayesian_menu(self):
        """Bayesian network menu"""
        print("\n--- Bayesian Network Inference ---")
        print("Select network type:")
        print("  1. Landslide")
        print("  2. Climate")
        print("  3. Flood")
        print("  4. Back")
        
        choice = input("Choice: ").strip()
        
        if choice == "1":
            from services.probabilistic_models import EarthSystemBayesianNetwork
            
            bn = EarthSystemBayesianNetwork("landslide")
            
            print("\nEnter evidence (press Enter to skip):")
            evidence = {}
            
            val = input("Slope (flat/gentle/moderate/steep): ").strip()
            if val:
                evidence["slope"] = val
            
            val = input("Rainfall (dry/normal/wet/heavy): ").strip()
            if val:
                evidence["rainfall"] = val
            
            val = input("Vegetation (sparse/moderate/dense): ").strip()
            if val:
                evidence["vegetation"] = val
            
            if evidence:
                result = bn.predict_risk(evidence)
                print("\nRisk Probabilities:")
                for state, prob in result.items():
                    print(f"  {state}: {prob:.3f}")
            
        elif choice == "4":
            return
    
    def _ontology_menu(self):
        """Ontology query menu"""
        print("\n--- Knowledge Base Query ---")
        query = input("Enter query (or 'list concepts'): ").strip()
        
        if query.lower() == "list concepts":
            from services.symbolic_ai import EarthSystemOntology
            onto = EarthSystemOntology()
            concepts = onto.kb.concepts
            print(f"\nTotal concepts: {len(concepts)}")
            for name, concept in list(concepts.items())[:10]:
                print(f"  - {name} ({concept.category})")
        else:
            from services.symbolic_ai import EarthSystemOntology
            onto = EarthSystemOntology()
            result = onto.ask(query)
            print(f"\nResult: {result}")
    
    def _monitor_menu(self):
        """System monitoring menu"""
        print("\n--- System Monitoring ---")
        
        if self.deployment_manager:
            health = self.deployment_manager.check_system_health()
            print(f"\nSystem Status: {health['status']}")
            print(f"CPU Usage: {health['system_metrics']['cpu_percent']:.1f}%")
            print(f"Memory Usage: {health['system_metrics']['memory_percent']:.1f}%")
            print(f"Disk Usage: {health['system_metrics']['disk_usage']:.1f}%")
            print(f"Deployed Models: {health['deployed_models']}")
            print(f"Active Alerts: {health['active_critical_alerts']}")
        else:
            print("Deployment manager not initialized")
    
    def shutdown(self):
        """Shutdown platform services"""
        logger.info("Shutting down EarthAI Platform...")
        
        if self.deployment_manager:
            self.deployment_manager.stop()
        
        self.initialized = False
        logger.info("EarthAI Platform shutdown complete")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EarthAI Platform - Next-generation AI system for Earth system modeling"
    )
    
    parser.add_argument(
        "--mode",
        choices=["api", "cli", "train", "predict", "monitor"],
        default="cli",
        help="Run mode (default: cli)"
    )
    
    parser.add_argument(
        "--config",
        default="config/system_config.yaml",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="API server host (for api mode)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (for api mode)"
    )
    
    parser.add_argument(
        "--task",
        choices=["landslide", "climate", "flood", "wildfire", "custom"],
        help="Task type (for train/predict mode)"
    )
    
    parser.add_argument(
        "--model-id",
        help="Model ID (for predict mode)"
    )
    
    parser.add_argument(
        "--data-path",
        help="Path to input data"
    )
    
    parser.add_argument(
        "--output",
        help="Output path for results"
    )
    
    args = parser.parse_args()
    
    # Create platform instance
    platform = EarthAIPlatform(config_path=args.config)
    
    try:
        if args.mode == "api":
            # Run API server
            platform.run_api_server(host=args.host, port=args.port)
        
        elif args.mode == "cli":
            # Run interactive CLI
            platform.run_cli()
        
        elif args.mode == "train":
            # Training mode
            if not args.task:
                print("Error: --task required for training mode")
                sys.exit(1)
            
            platform.initialize()
            print(f"Training model for task: {args.task}")
            # Training implementation
        
        elif args.mode == "predict":
            # Prediction mode
            if not args.model_id:
                print("Error: --model-id required for prediction mode")
                sys.exit(1)
            
            platform.initialize()
            print(f"Running prediction with model: {args.model_id}")
            # Prediction implementation
        
        elif args.mode == "monitor":
            # Monitoring mode
            platform.initialize()
            health = platform.deployment_manager.check_system_health()
            print(f"\nSystem Status: {health['status']}")
            print(f"Deployed Models: {health['deployed_models']}")
            print(f"Active Alerts: {health['active_critical_alerts']}")
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        platform.shutdown()


if __name__ == "__main__":
    main()
