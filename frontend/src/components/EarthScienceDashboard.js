import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './EarthScienceDashboard.css';

const EarthScienceDashboard = () => {
  const [mapData, setMapData] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState('sentinel2');
  const [analysisType, setAnalysisType] = useState('landslide');
  const [loading, setLoading] = useState(false);
  const [bounds, setBounds] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [timeRange, setTimeRange] = useState({ start: '2023-01-01', end: '2023-12-31' });

  const datasets = [
    { id: 'sentinel2', name: 'Sentinel-2', description: '10m resolution multispectral' },
    { id: 'landsat8', name: 'Landsat 8', description: '30m resolution multispectral' },
    { id: 'modis', name: 'MODIS', description: 'Daily global coverage' },
    { id: 'srtm', name: 'SRTM Elevation', description: '30m DEM data' }
  ];

  const analysisTypes = [
    { id: 'landslide', name: 'Landslide Susceptibility', icon: '⚠️' },
    { id: 'vegetation', name: 'Vegetation Health', icon: '🌿' },
    { id: 'water', name: 'Water Quality', icon: '💧' },
    { id: 'urban', name: 'Urban Change', icon: '🏙️' },
    { id: 'climate', name: 'Climate Impact', icon: '🌡️' },
    { id: 'deforestation', name: 'Deforestation', icon: '🌲' }
  ];

  useEffect(() => {
    // Initialize map with default bounds
    setBounds({
      north: 40.7128,
      south: 40.4774,
      east: -73.7004,
      west: -74.2591
    });
  }, []);

  const handleMapClick = async (e) => {
    const { lat, lng } = e.latlng;
    setLoading(true);
    
    try {
      const response = await fetch('/api/earth/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lng,
          dataset: selectedDataset,
          analysis: analysisType,
          timeRange: timeRange
        })
      });
      
      const results = await response.json();
      setAnalysisResults(results);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const runRegionalAnalysis = async () => {
    if (!bounds) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/earth/analyze-region', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bounds: bounds,
          dataset: selectedDataset,
          analysis: analysisType,
          timeRange: timeRange
        })
      });
      
      const results = await response.json();
      setMapData(results.geojson);
      setAnalysisResults(results.analysis);
    } catch (error) {
      console.error('Regional analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="earth-science-dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🌍 EarthAI Platform</h1>
          <p>AI-Powered Earth System Analysis</p>
        </div>
        <div className="header-controls">
          <button className="btn btn-primary">🚀 Launch Analysis</button>
          <button className="btn btn-secondary">📊 Dashboard</button>
        </div>
      </header>

      {/* Control Panel */}
      <div className="control-panel">
        <div className="control-section">
          <h3>🛰️ Satellite Data</h3>
          <select 
            value={selectedDataset} 
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="dataset-select"
          >
            {datasets.map(dataset => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} - {dataset.description}
              </option>
            ))}
          </select>
        </div>

        <div className="control-section">
          <h3>🔬 Analysis Type</h3>
          <div className="analysis-grid">
            {analysisTypes.map(type => (
              <button
                key={type.id}
                className={`analysis-btn ${analysisType === type.id ? 'active' : ''}`}
                onClick={() => setAnalysisType(type.id)}
              >
                <span className="analysis-icon">{type.icon}</span>
                <span className="analysis-name">{type.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="control-section">
          <h3>📅 Time Range</h3>
          <div className="time-range">
            <input
              type="date"
              value={timeRange.start}
              onChange={(e) => setTimeRange({...timeRange, start: e.target.value})}
            />
            <span>to</span>
            <input
              type="date"
              value={timeRange.end}
              onChange={(e) => setTimeRange({...timeRange, end: e.target.value})}
            />
          </div>
        </div>

        <div className="control-section">
          <button 
            onClick={runRegionalAnalysis}
            disabled={loading || !bounds}
            className="analyze-btn"
          >
            {loading ? '⏳ Analyzing...' : '🚀 Analyze Region'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Map */}
        <div className="map-container">
          <MapContainer
            center={[40.7128, -74.0060]}
            zoom={10}
            style={{ height: '600px', width: '100%' }}
            onClick={handleMapClick}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            
            {/* Satellite Imagery Overlay */}
            <TileLayer
              url={`https://earthengine.googleapis.com/map/{z}/{x}/{y}?mapid=SATELLITE&token=YOUR_TOKEN`}
              attribution="Google Earth Engine"
              opacity={0.7}
            />
            
            {/* Analysis Results */}
            {mapData && (
              <GeoJSON data={mapData} style={{ color: '#ff0000', weight: 2 }} />
            )}
          </MapContainer>
        </div>

        {/* Results Panel */}
        <div className="results-panel">
          <h3>📊 Analysis Results</h3>
          
          {analysisResults && (
            <div className="results-content">
              <div className="result-metric">
                <h4>Risk Assessment</h4>
                <div className="risk-level">
                  <span className={`risk-indicator ${analysisResults.riskLevel}`}>
                    {analysisResults.riskLevel?.toUpperCase() || 'UNKNOWN'}
                  </span>
                  <span className="confidence-score">
                    Confidence: {analysisResults.confidence || 0}%
                  </span>
                </div>
              </div>

              <div className="result-metric">
                <h4>Key Metrics</h4>
                <ul className="metrics-list">
                  <li>Slope Angle: {analysisResults.slope || 0}°</li>
                  <li>Vegetation Cover: {analysisResults.vegetation || 0}%</li>
                  <li>Soil Moisture: {analysisResults.moisture || 0}%</li>
                  <li>Rainfall (24h): {analysisResults.rainfall || 0}mm</li>
                </ul>
              </div>

              <div className="result-metric">
                <h4>AI Recommendations</h4>
                <div className="recommendations">
                  {analysisResults.recommendations?.map((rec, index) => (
                    <div key={index} className="recommendation-item">
                      <span className="rec-icon">💡</span>
                      <span className="rec-text">{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!analysisResults && (
            <div className="no-results">
              <p>🗺️ Click on the map or run regional analysis to see results</p>
            </div>
          )}
        </div>
      </div>

      {/* Data Catalog */}
      <div className="data-catalog">
        <h3>📚 Available Datasets</h3>
        <div className="catalog-grid">
          <div className="catalog-item">
            <h4>🛰️ Satellite Imagery</h4>
            <p>Sentinel-2, Landsat 8, MODIS</p>
            <span className="data-count">10,000+ scenes</span>
          </div>
          <div className="catalog-item">
            <h4>🌡️ Climate Data</h4>
            <p>Temperature, precipitation, wind</p>
            <span className="data-count">50+ years</span>
          </div>
          <div className="catalog-item">
            <h4>🏔️ Elevation Data</h4>
            <p>SRTM, ASTER GDEM</p>
            <span className="data-count">Global coverage</span>
          </div>
          <div className="catalog-item">
            <h4>🌊 Environmental Data</h4>
            <p>Water quality, air quality</p>
            <span className="data-count">Real-time</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EarthScienceDashboard;
