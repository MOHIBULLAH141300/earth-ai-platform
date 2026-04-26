from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import json
from datetime import datetime, timedelta

from services.data_ingestion import DataIngestionService
from services.model_recommendation_engine import ModelRecommendationEngine
from services.expert_fuzzy_systems import LandslideExpertSystem
from services.ml_dl_training_pipeline import MLTrainingPipeline

router = APIRouter(prefix="/api/earth", tags=["Earth Science"])

class AnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    dataset: str = "sentinel2"
    analysis: str = "landslide"
    time_range: Dict[str, str] = {"start": "2023-01-01", "end": "2023-12-31"}

class RegionalAnalysisRequest(BaseModel):
    bounds: Dict[str, float]
    dataset: str = "sentinel2"
    analysis: str = "landslide"
    time_range: Dict[str, str] = {"start": "2023-01-01", "end": "2023-12-31"}

class SatelliteDataRequest(BaseModel):
    dataset: str
    bounds: Dict[str, float]
    time_range: Dict[str, str]
    bands: Optional[List[str]] = None

class EarthScienceService:
    def __init__(self):
        self.data_service = DataIngestionService()
        self.model_engine = ModelRecommendationEngine()
        self.expert_system = LandslideExpertSystem()
        self.ml_pipeline = MLTrainingPipeline()
    
    async def get_satellite_imagery(self, dataset: str, bounds: Dict, time_range: Dict):
        """Get satellite imagery for specified area and time"""
        try:
            if dataset == "sentinel2":
                # Simulate Sentinel-2 data retrieval
                return {
                    "dataset": "sentinel2",
                    "resolution": "10m",
                    "bands": ["B2", "B3", "B4", "B8"],  # Blue, Green, Red, NIR
                    "cloud_cover": "< 10%",
                    "processing_level": "L2A",
                    "tile_url": f"https://earthengine.googleapis.com/map/{{z}}/{{x}}/{{y}}?dataset=sentinel2&bounds={bounds}"
                }
            elif dataset == "landsat8":
                return {
                    "dataset": "landsat8",
                    "resolution": "30m",
                    "bands": ["B2", "B3", "B4", "B5"],  # Blue, Green, Red, NIR
                    "cloud_cover": "< 20%",
                    "processing_level": "L1TP"
                }
            elif dataset == "modis":
                return {
                    "dataset": "modis",
                    "resolution": "250m",
                    "bands": ["sur_refl_b01", "sur_refl_b02", "sur_refl_b06"],
                    "temporal_resolution": "daily",
                    "coverage": "global"
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve satellite data: {str(e)}")
    
    async def analyze_point_location(self, request: AnalysisRequest):
        """Analyze specific point location"""
        try:
            # Get environmental data for the point
            env_data = await self.get_environmental_data(
                request.latitude, 
                request.longitude, 
                request.time_range
            )
            
            # Run AI analysis based on type
            if request.analysis == "landslide":
                results = await self.landslide_analysis(env_data)
            elif request.analysis == "vegetation":
                results = await self.vegetation_analysis(env_data)
            elif request.analysis == "water":
                results = await self.water_quality_analysis(env_data)
            elif request.analysis == "urban":
                results = await self.urban_change_analysis(env_data)
            elif request.analysis == "climate":
                results = await self.climate_impact_analysis(env_data)
            elif request.analysis == "deforestation":
                results = await self.deforestation_analysis(env_data)
            else:
                raise HTTPException(status_code=400, detail="Invalid analysis type")
            
            return {
                "location": {
                    "latitude": request.latitude,
                    "longitude": request.longitude
                },
                "dataset": request.dataset,
                "analysis_type": request.analysis,
                "time_range": request.time_range,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    async def get_environmental_data(self, lat: float, lon: float, time_range: Dict):
        """Get environmental data for a location"""
        # Simulate environmental data retrieval
        return {
            "elevation": 1250,  # meters
            "slope": 25.5,  # degrees
            "aspect": 180,  # degrees
            "vegetation_cover": 0.65,  # NDVI
            "soil_moisture": 0.35,  # volumetric
            "rainfall_24h": 45.2,  # mm
            "rainfall_7d": 120.5,  # mm
            "temperature": 22.5,  # Celsius
            "humidity": 0.75,  # relative
            "wind_speed": 3.2,  # m/s
            "land_cover": "forest",
            "geology": "sedimentary",
            "distance_to_rivers": 250,  # meters
            "distance_to_roads": 500,  # meters
            "population_density": 50  # per km2
        }
    
    async def landslide_analysis(self, env_data: Dict):
        """Landslide susceptibility analysis"""
        # Use expert system for landslide assessment
        expert_results = self.expert_system.assess(
            slope_angle=env_data["slope"],
            rainfall_24h=env_data["rainfall_24h"],
            vegetation_cover=env_data["vegetation_cover"],
            soil_type="clay_loam"
        )
        
        # Get risk level from expert system
        risk_level, confidence = self.expert_system.get_risk_level(expert_results)
        
        # Calculate additional metrics
        factors = {
            "slope": env_data["slope"],
            "vegetation": env_data["vegetation_cover"] * 100,
            "moisture": env_data["soil_moisture"] * 100,
            "rainfall": env_data["rainfall_24h"]
        }
        
        # Generate recommendations
        recommendations = self.generate_landslide_recommendations(risk_level, factors)
        
        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "factors": factors,
            "recommendations": recommendations,
            "expert_system_output": expert_results
        }
    
    async def vegetation_analysis(self, env_data: Dict):
        """Vegetation health analysis"""
        ndvi = env_data["vegetation_cover"]
        
        if ndvi > 0.6:
            health = "excellent"
            color = "#00ff00"
        elif ndvi > 0.4:
            health = "good"
            color = "#90ee90"
        elif ndvi > 0.2:
            health = "moderate"
            color = "#ffff00"
        else:
            health = "poor"
            color = "#ff0000"
        
        return {
            "health_status": health,
            "ndvi": ndvi,
            "color_code": color,
            "biomass_estimate": ndvi * 150,  # tons per hectare
            "recommendations": [
                "Monitor for changes in vegetation patterns",
                "Consider soil moisture management",
                "Assess need for reforestation" if ndvi < 0.3 else "Maintain current vegetation cover"
            ]
        }
    
    async def water_quality_analysis(self, env_data: Dict):
        """Water quality analysis"""
        # Simulate water quality parameters
        return {
            "quality_index": 75,  # out of 100
            "turbidity": 2.5,  # NTU
            "ph": 7.2,
            "dissolved_oxygen": 8.5,  # mg/L
            "temperature": env_data["temperature"],
            "pollution_indicators": ["low", "moderate", "high"][1],  # moderate
            "recommendations": [
                "Regular monitoring of water parameters",
                "Check for nearby pollution sources",
                "Implement watershed management practices"
            ]
        }
    
    async def urban_change_analysis(self, env_data: Dict):
        """Urban change detection analysis"""
        return {
            "urban_density": env_data["population_density"] / 1000,  # normalized
            "change_rate": 0.05,  # 5% annual change
            "land_use_classification": "mixed",
            "development_pressure": "moderate",
            "recommendations": [
                "Monitor urban sprawl patterns",
                "Plan for sustainable development",
                "Protect green spaces within urban areas"
            ]
        }
    
    async def climate_impact_analysis(self, env_data: Dict):
        """Climate impact assessment"""
        return {
            "temperature_anomaly": 1.2,  # degrees above baseline
            "precipitation_change": -0.15,  # 15% decrease
            "extreme_events_risk": "moderate",
            "adaptation_priority": "medium",
            "recommendations": [
                "Implement climate adaptation measures",
                "Monitor for extreme weather events",
                "Develop drought contingency plans"
            ]
        }
    
    async def deforestation_analysis(self, env_data: Dict):
        """Deforestation detection and analysis"""
        return {
            "forest_cover_change": -0.08,  # 8% loss
            "deforestation_rate": 0.02,  # annual rate
            "fragmentation_index": 0.35,
            "biodiversity_impact": "moderate",
            "recommendations": [
                "Implement reforestation programs",
                "Establish protected forest areas",
                "Promote sustainable logging practices"
            ]
        }
    
    def generate_landslide_recommendations(self, risk_level: str, factors: Dict):
        """Generate landslide risk recommendations"""
        recommendations = []
        
        if risk_level in ["high", "very_high"]:
            recommendations.extend([
                "Immediate evacuation recommended",
                "Install slope stabilization measures",
                "Implement drainage systems",
                "Continuous monitoring required"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Regular monitoring advised",
                "Consider slope reinforcement",
                "Improve drainage infrastructure",
                "Community awareness programs"
            ])
        else:
            recommendations.extend([
                "Periodic monitoring sufficient",
                "Maintain vegetation cover",
                "Monitor rainfall patterns"
            ])
        
        # Factor-specific recommendations
        if factors["slope"] > 30:
            recommendations.append("Slope angle critical - requires engineering intervention")
        
        if factors["vegetation"] < 30:
            recommendations.append("Increase vegetation cover to improve slope stability")
        
        if factors["rainfall"] > 50:
            recommendations.append("Heavy rainfall increases risk - monitor weather forecasts")
        
        return recommendations

# Initialize service
earth_service = EarthScienceService()

@router.post("/analyze")
async def analyze_point_location(request: AnalysisRequest):
    """Analyze specific point location for environmental risks"""
    result = await earth_service.analyze_point_location(request)
    return result

@router.post("/analyze-region")
async def analyze_region(request: RegionalAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze entire region and return GeoJSON results"""
    try:
        # This would be a long-running process in production
        # For now, return simulated results
        
        # Generate GeoJSON for the region
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [request.bounds["west"], request.bounds["south"]],
                            [request.bounds["east"], request.bounds["south"]],
                            [request.bounds["east"], request.bounds["north"]],
                            [request.bounds["west"], request.bounds["north"]],
                            [request.bounds["west"], request.bounds["south"]]
                        ]]
                    },
                    "properties": {
                        "analysis_type": request.analysis,
                        "risk_level": "medium",
                        "confidence": 0.75,
                        "dataset": request.dataset
                    }
                }
            ]
        }
        
        # Run regional analysis in background
        analysis_results = await earth_service.analyze_point_location(
            AnalysisRequest(
                latitude=(request.bounds["north"] + request.bounds["south"]) / 2,
                longitude=(request.bounds["east"] + request.bounds["west"]) / 2,
                dataset=request.dataset,
                analysis=request.analysis,
                time_range=request.time_range
            )
        )
        
        return {
            "geojson": geojson_data,
            "analysis": analysis_results["results"],
            "bounds": request.bounds,
            "dataset": request.dataset,
            "analysis_type": request.analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regional analysis failed: {str(e)}")

@router.get("/satellite-data")
async def get_satellite_data(dataset: str, bounds: str, time_range: str):
    """Get satellite imagery data"""
    try:
        bounds_dict = json.loads(bounds)
        time_range_dict = json.loads(time_range)
        
        data = await earth_service.get_satellite_imagery(dataset, bounds_dict, time_range_dict)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get satellite data: {str(e)}")

@router.get("/datasets")
async def get_available_datasets():
    """Get list of available satellite datasets"""
    return {
        "datasets": [
            {
                "id": "sentinel2",
                "name": "Sentinel-2",
                "description": "10m resolution multispectral imagery",
                "coverage": "Global",
                "temporal_resolution": "5 days",
                "bands": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B9", "B10", "B11", "B12"]
            },
            {
                "id": "landsat8",
                "name": "Landsat 8",
                "description": "30m resolution multispectral imagery",
                "coverage": "Global",
                "temporal_resolution": "16 days",
                "bands": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11"]
            },
            {
                "id": "modis",
                "name": "MODIS",
                "description": "250m-500m resolution daily imagery",
                "coverage": "Global",
                "temporal_resolution": "Daily",
                "bands": ["sur_refl_b01", "sur_refl_b02", "sur_refl_b03", "sur_refl_b04", "sur_refl_b05", "sur_refl_b06", "sur_refl_b07"]
            },
            {
                "id": "srtm",
                "name": "SRTM",
                "description": "30m resolution digital elevation model",
                "coverage": "Global (60°S-60°N)",
                "temporal_resolution": "Static",
                "bands": ["elevation"]
            }
        ]
    }

@router.get("/analysis-types")
async def get_analysis_types():
    """Get available analysis types"""
    return {
        "analysis_types": [
            {
                "id": "landslide",
                "name": "Landslide Susceptibility",
                "description": "Assess landslide risk using AI and expert systems",
                "icon": "⚠️"
            },
            {
                "id": "vegetation",
                "name": "Vegetation Health",
                "description": "Analyze vegetation health using NDVI and ML",
                "icon": "🌿"
            },
            {
                "id": "water",
                "name": "Water Quality",
                "description": "Assess water quality parameters",
                "icon": "💧"
            },
            {
                "id": "urban",
                "name": "Urban Change",
                "description": "Detect and analyze urban development patterns",
                "icon": "🏙️"
            },
            {
                "id": "climate",
                "name": "Climate Impact",
                "description": "Assess climate change impacts",
                "icon": "🌡️"
            },
            {
                "id": "deforestation",
                "name": "Deforestation",
                "description": "Monitor forest cover changes",
                "icon": "🌲"
            }
        ]
    }
