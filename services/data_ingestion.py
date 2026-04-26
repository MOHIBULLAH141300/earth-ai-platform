"""
EarthAI Platform - Data Ingestion Service
Handles real-time and batch data collection from multiple Earth observation sources
"""

import ee
import requests
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import xarray as xr
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
import numpy as np
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    enabled: bool
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    timeout: int = 30


@dataclass
class SatelliteImagery:
    """Satellite imagery data container"""
    image_id: str
    collection: str
    date: datetime
    bounds: Tuple[float, float, float, float]  # minx, miny, maxx, maxy
    bands: Dict[str, np.ndarray]
    resolution: float
    crs: str
    cloud_cover: float
    metadata: Dict[str, Any]


@dataclass
class ClimateData:
    """Climate data container"""
    timestamp: datetime
    temperature: Optional[float] = None
    precipitation: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    pressure: Optional[float] = None
    location: Optional[Tuple[float, float]] = None  # lon, lat
    metadata: Dict[str, Any] = None


class GoogleEarthEngineConnector:
    """Connector for Google Earth Engine data"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize GEE connection"""
        try:
            ee.Initialize(project=self.project_id)
            self.initialized = True
            logger.info(f"GEE initialized for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize GEE: {e}")
            raise
    
    def get_sentinel_imagery(
        self,
        bounds: List[float],
        start_date: str,
        end_date: str,
        cloud_cover_threshold: float = 20.0,
        bands: List[str] = ["B2", "B3", "B4", "B8", "B11", "B12"]
    ) -> List[SatelliteImagery]:
        """Fetch Sentinel-2 imagery from GEE"""
        
        if not self.initialized:
            raise RuntimeError("GEE not initialized")
        
        # Create region of interest
        roi = ee.Geometry.Rectangle(bounds)
        
        # Filter Sentinel-2 collection
        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                     .filterBounds(roi)
                     .filterDate(start_date, end_date)
                     .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_threshold))
                     .sort("CLOUDY_PIXEL_PERCENTAGE"))
        
        # Get image list
        image_list = collection.toList(collection.size())
        size = collection.size().getInfo()
        
        imagery_list = []
        for i in range(min(size, 100)):  # Limit to 100 images
            try:
                image = ee.Image(image_list.get(i))
                
                # Get metadata
                date = image.date().format("YYYY-MM-dd").getInfo()
                cloud_cover = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
                image_id = image.get("system:id").getInfo()
                
                # Select bands and download
                selected = image.select(bands)
                
                # Sample data for bounds
                sample = selected.sampleRectangle(region=roi, defaultValue=0)
                
                # Extract band data
                band_data = {}
                for band in bands:
                    try:
                        data = np.array(sample.get(band).getInfo())
                        band_data[band] = data
                    except:
                        logger.warning(f"Failed to extract band {band} from {image_id}")
                
                # Create SatelliteImagery object
                imagery = SatelliteImagery(
                    image_id=image_id,
                    collection="COPERNICUS/S2_SR_HARMONIZED",
                    date=datetime.strptime(date, "%Y-%m-%d"),
                    bounds=tuple(bounds),
                    bands=band_data,
                    resolution=10.0,  # Sentinel-2 10m resolution
                    crs="EPSG:4326",
                    cloud_cover=cloud_cover,
                    metadata={
                        "processing_level": image.get("PROCESSING_BASELINE").getInfo(),
                        "tile_id": image.get("MGRS_TILE").getInfo()
                    }
                )
                
                imagery_list.append(imagery)
                
            except Exception as e:
                logger.error(f"Error processing image {i}: {e}")
                continue
        
        logger.info(f"Retrieved {len(imagery_list)} Sentinel-2 images")
        return imagery_list
    
    def get_modis_data(
        self,
        bounds: List[float],
        start_date: str,
        end_date: str,
        product: str = "MODIS/061/MOD13Q1"
    ) -> xr.Dataset:
        """Fetch MODIS vegetation index data"""
        
        roi = ee.Geometry.Rectangle(bounds)
        
        collection = (ee.ImageCollection(product)
                     .filterBounds(roi)
                     .filterDate(start_date, end_date))
        
        # Select NDVI and EVI bands
        ndvi = collection.select("NDVI").mean()
        evi = collection.select("EVI").mean()
        
        # Get data as numpy arrays
        # Note: In production, use ee.batch.Export for large areas
        sample_ndvi = ndvi.sampleRectangle(region=roi, defaultValue=0)
        sample_evi = evi.sampleRectangle(region=roi, defaultValue=0)
        
        ndvi_data = np.array(sample_ndvi.get("NDVI").getInfo())
        evi_data = np.array(sample_evi.get("EVI").getInfo())
        
        # Create xarray Dataset
        lats = np.linspace(bounds[1], bounds[3], ndvi_data.shape[0])
        lons = np.linspace(bounds[0], bounds[2], ndvi_data.shape[1])
        
        ds = xr.Dataset(
            {
                "NDVI": (["latitude", "longitude"], ndvi_data),
                "EVI": (["latitude", "longitude"], evi_data)
            },
            coords={
                "latitude": lats,
                "longitude": lons
            }
        )
        
        ds.attrs["product"] = product
        ds.attrs["date_range"] = f"{start_date} to {end_date}"
        
        return ds
    
    def get_terrain_data(
        self,
        bounds: List[float]
    ) -> Dict[str, np.ndarray]:
        """Get SRTM elevation and slope data"""
        
        roi = ee.Geometry.Rectangle(bounds)
        
        # Get elevation
        elevation = ee.Image("USGS/SRTMGL1_003").clip(roi)
        
        # Calculate slope and aspect
        slope = ee.Terrain.slope(elevation)
        aspect = ee.Terrain.aspect(elevation)
        
        # Sample data
        elev_sample = elevation.sampleRectangle(region=roi, defaultValue=0)
        slope_sample = slope.sampleRectangle(region=roi, defaultValue=0)
        aspect_sample = aspect.sampleRectangle(region=roi, defaultValue=0)
        
        return {
            "elevation": np.array(elev_sample.get("elevation").getInfo()),
            "slope": np.array(slope_sample.get("slope").getInfo()),
            "aspect": np.array(aspect_sample.get("aspect").getInfo())
        }


class ClimateDataConnector:
    """Connector for climate and weather data sources"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.session = requests.Session()
    
    async def fetch_open_meteo(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str
    ) -> List[ClimateData]:
        """Fetch historical weather data from Open-Meteo"""
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_mean",
                "windspeed_10m_max",
                "surface_pressure_mean"
            ],
            "timezone": "auto"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert to ClimateData objects
                    climate_data = []
                    daily = data.get("daily", {})
                    
                    for i in range(len(daily.get("time", []))):
                        climate_data.append(ClimateData(
                            timestamp=datetime.strptime(daily["time"][i], "%Y-%m-%d"),
                            temperature=(daily.get("temperature_2m_max", [None]*len(daily["time"])))[i],
                            precipitation=(daily.get("precipitation_sum", [None]*len(daily["time"])))[i],
                            humidity=(daily.get("relative_humidity_2m_mean", [None]*len(daily["time"])))[i],
                            wind_speed=(daily.get("windspeed_10m_max", [None]*len(daily["time"])))[i],
                            pressure=(daily.get("surface_pressure_mean", [None]*len(daily["time"])))[i],
                            location=(longitude, latitude),
                            metadata={"source": "Open-Meteo"}
                        ))
                    
                    return climate_data
                else:
                    logger.error(f"Open-Meteo API error: {response.status}")
                    return []
    
    def fetch_nasa_power(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str
    ) -> Dict[str, np.ndarray]:
        """Fetch NASA POWER climate data"""
        
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        
        params = {
            "parameters": "PRECTOTCORR,T2M,RH2M,WS10M,PS",
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date.replace("-", ""),
            "end": end_date.replace("-", ""),
            "format": "JSON"
        }
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            properties = data.get("properties", {})
            
            return {
                "precipitation": np.array(properties.get("parameter", {}).get("PRECTOTCORR", [])),
                "temperature": np.array(properties.get("parameter", {}).get("T2M", [])),
                "humidity": np.array(properties.get("parameter", {}).get("RH2M", [])),
                "wind_speed": np.array(properties.get("parameter", {}).get("WS10M", [])),
                "pressure": np.array(properties.get("parameter", {}).get("PS", []))
            }
        else:
            logger.error(f"NASA POWER API error: {response.status_code}")
            return {}


class DataPreprocessingPipeline:
    """Pipeline for preprocessing Earth observation data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.normalization_method = config.get("normalization_method", "standard")
        self.target_resolution = config.get("default_resolution", 30)
    
    def normalize(
        self,
        data: np.ndarray,
        method: Optional[str] = None
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """Normalize data using specified method"""
        
        method = method or self.normalization_method
        stats = {}
        
        if method == "standard":
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            normalized = (data - mean) / (std + 1e-8)
            stats = {"mean": mean, "std": std}
            
        elif method == "minmax":
            min_val = np.min(data, axis=0)
            max_val = np.max(data, axis=0)
            normalized = (data - min_val) / (max_val - min_val + 1e-8)
            stats = {"min": min_val, "max": max_val}
            
        elif method == "robust":
            median = np.median(data, axis=0)
            q75 = np.percentile(data, 75, axis=0)
            q25 = np.percentile(data, 25, axis=0)
            iqr = q75 - q25
            normalized = (data - median) / (iqr + 1e-8)
            stats = {"median": median, "iqr": iqr}
            
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        return normalized, stats
    
    def resample_raster(
        self,
        data: np.ndarray,
        current_resolution: float,
        target_resolution: Optional[float] = None,
        method: str = "bilinear"
    ) -> np.ndarray:
        """Resample raster data to target resolution"""
        
        target_resolution = target_resolution or self.target_resolution
        
        if current_resolution == target_resolution:
            return data
        
        scale_factor = current_resolution / target_resolution
        new_shape = (
            int(data.shape[0] * scale_factor),
            int(data.shape[1] * scale_factor)
        )
        
        if method == "nearest":
            from scipy.ndimage import zoom
            return zoom(data, scale_factor, order=0)
        elif method == "bilinear":
            from scipy.ndimage import zoom
            return zoom(data, scale_factor, order=1)
        elif method == "cubic":
            from scipy.ndimage import zoom
            return zoom(data, scale_factor, order=3)
        else:
            raise ValueError(f"Unknown resampling method: {method}")
    
    def handle_missing_values(
        self,
        data: np.ndarray,
        strategy: str = "interpolation"
    ) -> np.ndarray:
        """Handle missing values in data"""
        
        if strategy == "interpolation":
            from scipy.interpolate import griddata
            
            # Find missing values
            mask = np.isnan(data)
            if not mask.any():
                return data
            
            # Create coordinate grids
            y, x = np.indices(data.shape)
            
            # Interpolate
            valid = ~mask
            interpolated = griddata(
                (x[valid], y[valid]),
                data[valid],
                (x, y),
                method="linear"
            )
            
            # Fill any remaining NaN with mean
            nan_mask = np.isnan(interpolated)
            if nan_mask.any():
                interpolated[nan_mask] = np.nanmean(data)
            
            return interpolated
            
        elif strategy == "mean":
            mean_val = np.nanmean(data)
            return np.where(np.isnan(data), mean_val, data)
            
        elif strategy == "median":
            median_val = np.nanmedian(data)
            return np.where(np.isnan(data), median_val, data)
            
        else:
            raise ValueError(f"Unknown missing value strategy: {strategy}")
    
    def extract_features(
        self,
        imagery: SatelliteImagery,
        indices: List[str] = ["NDVI", "NDWI", "NDBI"]
    ) -> Dict[str, np.ndarray]:
        """Extract spectral indices from satellite imagery"""
        
        bands = imagery.bands
        features = {}
        
        for index in indices:
            if index == "NDVI" and all(b in bands for b in ["B4", "B8"]):
                # NDVI = (NIR - Red) / (NIR + Red)
                features["NDVI"] = (bands["B8"] - bands["B4"]) / (bands["B8"] + bands["B4"] + 1e-8)
                
            elif index == "NDWI" and all(b in bands for b in ["B3", "B8"]):
                # NDWI = (Green - NIR) / (Green + NIR)
                features["NDWI"] = (bands["B3"] - bands["B8"]) / (bands["B3"] + bands["B8"] + 1e-8)
                
            elif index == "NDBI" and all(b in bands for b in ["B8", "B11"]):
                # NDBI = (SWIR - NIR) / (SWIR + NIR)
                features["NDBI"] = (bands["B11"] - bands["B8"]) / (bands["B11"] + bands["B8"] + 1e-8)
                
            elif index == "EVI" and all(b in bands for b in ["B2", "B4", "B8"]):
                # EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
                features["EVI"] = 2.5 * (bands["B8"] - bands["B4"]) / (bands["B8"] + 6*bands["B4"] - 7.5*bands["B2"] + 1)
        
        return features
    
    def create_training_patches(
        self,
        data: Dict[str, np.ndarray],
        patch_size: int = 256,
        stride: int = 128,
        labels: Optional[np.ndarray] = None
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """Create training patches from raster data"""
        
        patches = []
        patch_labels = []
        
        # Stack bands
        stacked = np.stack(list(data.values()), axis=-1)
        height, width, bands = stacked.shape
        
        for y in range(0, height - patch_size + 1, stride):
            for x in range(0, width - patch_size + 1, stride):
                patch = stacked[y:y+patch_size, x:x+patch_size, :]
                
                # Skip patches with too many NaN values
                if np.isnan(patch).mean() > 0.1:
                    continue
                
                patches.append(patch)
                
                # Extract label for patch center if available
                if labels is not None:
                    center_y = y + patch_size // 2
                    center_x = x + patch_size // 2
                    patch_labels.append(labels[center_y, center_x])
        
        return patches, patch_labels


class DataIngestionService:
    """Main service orchestrating data ingestion from multiple sources"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        import yaml
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f) or {}
        self.config = self._expand_env_vars(raw_config)
        
        self.data_config = self.config.get("data", {})
        self.sources = self.data_config.get("sources", {})
        self.storage = self.data_config.get("storage", {})
        
        # Initialize connectors
        self.gee_connector = None
        self.climate_connector = None
        self.preprocessing = DataPreprocessingPipeline(self.data_config.get("preprocessing", {}))
        
        self._initialize_connectors()

    def _expand_env_vars(self, value):
        if isinstance(value, dict):
            return {k: self._expand_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._expand_env_vars(v) for v in value]
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_key = value[2:-1]
            return os.getenv(env_key, "")
        return value
    
    def _initialize_connectors(self):
        """Initialize data source connectors"""
        
        # Initialize GEE if enabled
        if self.sources.get("google_earth_engine", {}).get("enabled", False):
            try:
                project_id = self.sources["google_earth_engine"].get("project_id")
                if project_id:
                    self.gee_connector = GoogleEarthEngineConnector(project_id)
            except Exception as e:
                logger.error(f"Failed to initialize GEE connector: {e}")
        
        # Initialize climate connector if any climate sources enabled
        api_keys = {}
        for source_name, source_config in self.sources.items():
            if source_config.get("enabled") and "api_key" in source_config:
                api_keys[source_name] = source_config["api_key"]
        
        if api_keys:
            self.climate_connector = ClimateDataConnector(api_keys)
    
    async def ingest_landslide_data(
        self,
        bounds: List[float],
        start_date: str,
        end_date: str,
        include_climate: bool = True
    ) -> Dict[str, Any]:
        """Ingest comprehensive data for landslide susceptibility modeling"""
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "bounds": bounds,
            "date_range": {"start": start_date, "end": end_date},
            "data": {}
        }
        
        # Fetch satellite imagery
        if self.gee_connector:
            logger.info("Fetching Sentinel-2 imagery...")
            imagery = self.gee_connector.get_sentinel_imagery(
                bounds, start_date, end_date
            )
            results["data"]["imagery"] = imagery
            
            # Extract spectral indices
            if imagery:
                features = self.preprocessing.extract_features(imagery[0])
                results["data"]["spectral_indices"] = features
        
        # Fetch terrain data
        if self.gee_connector:
            logger.info("Fetching terrain data...")
            terrain = self.gee_connector.get_terrain_data(bounds)
            results["data"]["terrain"] = terrain
        
        # Fetch climate data
        if include_climate and self.climate_connector:
            logger.info("Fetching climate data...")
            
            # Calculate center point
            center_lon = (bounds[0] + bounds[2]) / 2
            center_lat = (bounds[1] + bounds[3]) / 2
            
            climate_data = await self.climate_connector.fetch_open_meteo(
                center_lat, center_lon, start_date, end_date
            )
            results["data"]["climate"] = climate_data
        
        return results
    
    def preprocess_for_training(
        self,
        raw_data: Dict[str, Any],
        patch_size: int = 256
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """Preprocess raw data for model training"""
        
        # Combine all raster data
        raster_data = {}
        
        if "spectral_indices" in raw_data["data"]:
            raster_data.update(raw_data["data"]["spectral_indices"])
        
        if "terrain" in raw_data["data"]:
            raster_data.update(raw_data["data"]["terrain"])
        
        # Handle missing values
        for key in raster_data:
            raster_data[key] = self.preprocessing.handle_missing_values(
                raster_data[key],
                strategy="interpolation"
            )
        
        # Normalize
        for key in raster_data:
            raster_data[key], stats = self.preprocessing.normalize(
                raster_data[key]
            )
        
        # Create patches
        patches, labels = self.preprocessing.create_training_patches(
            raster_data,
            patch_size=patch_size
        )
        
        return patches, labels


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = DataIngestionService()
    
    # Define study area (example: some region)
    bounds = [66.5, 24.5, 67.5, 25.5]  # [min_lon, min_lat, max_lon, max_lat]
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    # Run ingestion
    import asyncio
    results = asyncio.run(service.ingest_landslide_data(
        bounds, start_date, end_date
    ))
    
    print(f"Ingested {len(results['data'].get('imagery', []))} images")
    print(f"Terrain data keys: {list(results['data'].get('terrain', {}).keys())}")
    print(f"Climate records: {len(results['data'].get('climate', []))}")
