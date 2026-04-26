/**
 * VisualizationPanel Component
 * Display interactive maps, charts, and results visualization
 */

import React, { useState, useEffect } from 'react';
import './VisualizationPanel.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const VisualizationPanel = ({ userId, tasks, onNotification }) => {
  const [selectedTask, setSelectedTask] = useState(null);
  const [visualizations, setVisualizations] = useState([]);
  const [loading, setLoading] = useState(false);

  const completedTasks = tasks.filter(t => t.status === 'completed');

  const generateVisualization = async (taskId, format) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/visualizations/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          output_format: format,
          include_metrics: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        setVisualizations(prev => [...prev, data]);
        onNotification('Visualization created!', 'success');
      }
    } catch (error) {
      console.error('Error creating visualization:', error);
      onNotification('Failed to create visualization', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="visualization-panel">
      <h2>Results Visualization</h2>

      <div className="viz-container">
        <div className="viz-selector">
          <h3>Select a Completed Task</h3>
          {completedTasks.length === 0 ? (
            <p className="empty-message">No completed tasks available for visualization</p>
          ) : (
            <div className="task-buttons">
              {completedTasks.map(task => (
                <button
                  key={task.task_id}
                  className={`task-btn ${selectedTask === task.task_id ? 'active' : ''}`}
                  onClick={() => setSelectedTask(task.task_id)}
                >
                  {task.task_type}
                  <span className="task-badge">{new Date(task.created_at).toLocaleDateString()}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {selectedTask && (
          <div className="viz-options">
            <h3>Visualization Format</h3>
            <div className="format-buttons">
              <button
                className="format-btn"
                onClick={() => generateVisualization(selectedTask, 'map')}
                disabled={loading}
              >
                🗺️ Map
              </button>
              <button
                className="format-btn"
                onClick={() => generateVisualization(selectedTask, 'chart')}
                disabled={loading}
              >
                📊 Charts
              </button>
              <button
                className="format-btn"
                onClick={() => generateVisualization(selectedTask, 'table')}
                disabled={loading}
              >
                📋 Table
              </button>
              <button
                className="format-btn"
                onClick={() => generateVisualization(selectedTask, 'report')}
                disabled={loading}
              >
                📄 Report
              </button>
            </div>
          </div>
        )}

        <div className="visualizations">
          <h3>Generated Visualizations</h3>
          {visualizations.length === 0 ? (
            <p className="empty-message">No visualizations generated yet</p>
          ) : (
            <div className="viz-list">
              {visualizations.map((viz, idx) => (
                <div key={idx} className="viz-item">
                  <h4>{viz.format} Visualization</h4>
                  <p>Created: {new Date().toLocaleString()}</p>
                  <button className="view-btn">View</button>
                  <button className="download-btn">Download</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * SystemStatus Component
 * Display system health, services, and monitoring
 */

export const SystemStatus = ({ status, onNotification }) => {
  const getServiceColor = (serviceStatus) => {
    if (serviceStatus === 'active') return '#4CAF50';
    if (serviceStatus === 'warning') return '#FFC107';
    return '#F44336';
  };

  return (
    <div className="system-status">
      <h2>System Status & Monitoring</h2>

      {status ? (
        <>
          <div className="status-header">
            <div className="health-indicator">
              <div
                className="health-circle"
                style={{
                  backgroundColor: status.system_health > 80 ? '#4CAF50' : '#FFC107'
                }}
              >
                {status.system_health}%
              </div>
              <h3>{status.system_health > 80 ? 'Healthy' : 'Monitor'}</h3>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat">
              <h4>Active Tasks</h4>
              <p className="stat-value">{status.active_tasks}</p>
            </div>
            <div className="stat">
              <h4>Queued Tasks</h4>
              <p className="stat-value">{status.queued_tasks}</p>
            </div>
            <div className="stat">
              <h4>Completed</h4>
              <p className="stat-value success">{status.completed_tasks}</p>
            </div>
            <div className="stat">
              <h4>Failed</h4>
              <p className="stat-value error">{status.failed_tasks}</p>
            </div>
          </div>

          <div className="services-section">
            <h3>Services Status</h3>
            <div className="services-list">
              {Object.entries(status.services).map(([service, state]) => (
                <div key={service} className="service-item">
                  <span className="service-name">{service}</span>
                  <span
                    className="service-indicator"
                    style={{ backgroundColor: getServiceColor(state) }}
                  >
                    {state}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="resources-section">
            <h3>Resource Usage</h3>
            <div className="resource-item">
              <label>Memory Usage</label>
              <div className="resource-bar">
                <div className="resource-fill" style={{ width: `${status.memory_usage}%` }}></div>
              </div>
              <span>{status.memory_usage.toFixed(1)}%</span>
            </div>
            <div className="resource-item">
              <label>CPU Usage</label>
              <div className="resource-bar">
                <div className="resource-fill" style={{ width: `${status.cpu_usage}%` }}></div>
              </div>
              <span>{status.cpu_usage.toFixed(1)}%</span>
            </div>
          </div>
        </>
      ) : (
        <p className="loading">Loading system status...</p>
      )}
    </div>
  );
};

export default VisualizationPanel;
