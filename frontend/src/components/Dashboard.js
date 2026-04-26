/**
 * Dashboard Component
 * Main overview of platform status and quick actions
 */

import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const Dashboard = ({ userId, tasks, onTaskCreate, onNotification }) => {
  const [stats, setStats] = useState({
    totalTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    activeTasks: 0
  });
  const [analytics, setAnalytics] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  // Load user analytics
  useEffect(() => {
    const loadAnalytics = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/analytics`);
        if (response.ok) {
          const data = await response.json();
          setAnalytics(data);
        }
      } catch (error) {
        console.error('Failed to load analytics:', error);
      }
    };

    loadAnalytics();
  }, [userId]);

  // Update stats from tasks
  useEffect(() => {
    const completed = tasks.filter(t => t.status === 'completed').length;
    const failed = tasks.filter(t => t.status === 'failed').length;
    const active = tasks.filter(t => t.status === 'in_progress').length;

    setStats({
      totalTasks: tasks.length,
      completedTasks: completed,
      failedTasks: failed,
      activeTasks: active
    });
  }, [tasks]);

  // Task templates for quick actions
  const taskTemplates = [
    {
      id: 'landslide',
      title: '🏔️ Landslide Susceptibility',
      description: 'Predict landslide risk for a region',
      parameters: { task_type: 'landslide_susceptibility' }
    },
    {
      id: 'flood',
      title: '🌊 Flood Prediction',
      description: 'Analyze flood risk and extent',
      parameters: { task_type: 'flood_prediction' }
    },
    {
      id: 'earthquake',
      title: '⚡ Earthquake Impact',
      description: 'Assess earthquake damage potential',
      parameters: { task_type: 'earthquake_damage' }
    },
    {
      id: 'drought',
      title: '🌱 Drought Monitoring',
      description: 'Monitor and predict drought conditions',
      parameters: { task_type: 'drought_monitoring' }
    },
    {
      id: 'crop',
      title: '🌾 Crop Yield',
      description: 'Predict agricultural yield',
      parameters: { task_type: 'crop_yield_prediction' }
    },
    {
      id: 'climate',
      title: '🌡️ Climate Analysis',
      description: 'Analyze climate trends and patterns',
      parameters: { task_type: 'climate_analysis' }
    }
  ];

  const createQuickTask = async (template) => {
    setSelectedTemplate(template.id);
    
    // Show parameter collection dialog or proceed with defaults
    const parameters = {
      ...template.parameters,
      bounds: {
        min_lon: -180,
        max_lon: 180,
        min_lat: -90,
        max_lat: 90
      },
      date_range: {
        start_date: new Date(Date.now() - 365*24*60*60*1000).toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0]
      }
    };

    await onTaskCreate(template.parameters.task_type, parameters);
    setSelectedTemplate(null);
  };

  return (
    <div className="dashboard">
      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Tasks</h3>
          <p className="stat-value">{stats.totalTasks}</p>
          <p className="stat-label">All time</p>
        </div>
        <div className="stat-card">
          <h3>Completed</h3>
          <p className="stat-value success">{stats.completedTasks}</p>
          <p className="stat-label">Successfully finished</p>
        </div>
        <div className="stat-card">
          <h3>Active</h3>
          <p className="stat-value info">{stats.activeTasks}</p>
          <p className="stat-label">Currently running</p>
        </div>
        <div className="stat-card">
          <h3>Failed</h3>
          <p className="stat-value error">{stats.failedTasks}</p>
          <p className="stat-label">Need attention</p>
        </div>
      </div>

      {/* Analytics Section */}
      {analytics && (
        <div className="analytics-section">
          <h2>Your Activity</h2>
          <div className="analytics-details">
            <div className="analytics-item">
              <span>Favorite Task:</span>
              <strong>{analytics.favorite_task_type || 'N/A'}</strong>
            </div>
            <div className="analytics-item">
              <span>Avg Completion Time:</span>
              <strong>{Math.round(analytics.average_completion_time / 60)}m</strong>
            </div>
            <div className="analytics-item">
              <span>Success Rate:</span>
              <strong>
                {analytics.total_tasks > 0
                  ? Math.round((analytics.completed_tasks / analytics.total_tasks) * 100)
                  : 0}%
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* Quick Action Templates */}
      <div className="templates-section">
        <h2>Quick Start - Common Tasks</h2>
        <div className="templates-grid">
          {taskTemplates.map(template => (
            <div
              key={template.id}
              className={`template-card ${selectedTemplate === template.id ? 'loading' : ''}`}
              onClick={() => !selectedTemplate && createQuickTask(template)}
            >
              <div className="template-header">{template.title}</div>
              <p className="template-description">{template.description}</p>
              <button className="template-btn">
                {selectedTemplate === template.id ? 'Creating...' : 'Start'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="recent-section">
        <h2>Recent Tasks</h2>
        {tasks.length === 0 ? (
          <p className="empty-message">No tasks yet. Create one using the templates above!</p>
        ) : (
          <div className="recent-list">
            {tasks.slice(0, 5).map(task => (
              <div key={task.task_id} className="recent-item">
                <div className="task-info">
                  <h4>{task.task_type}</h4>
                  <p className="task-time">
                    {new Date(task.created_at).toLocaleDateString()} {new Date(task.created_at).toLocaleTimeString()}
                  </p>
                </div>
                <div className={`status-badge status-${task.status}`}>
                  {task.status}
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${task.progress}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Getting Started Guide */}
      <div className="guide-section">
        <h2>📖 Getting Started</h2>
        <div className="guide-steps">
          <div className="step">
            <span className="step-number">1</span>
            <div>
              <h4>Choose a Task</h4>
              <p>Select from predefined tasks or use the chatbot for custom analysis</p>
            </div>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <div>
              <h4>Define Parameters</h4>
              <p>Specify location, time range, and data sources for your analysis</p>
            </div>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <div>
              <h4>Review Results</h4>
              <p>View predictions, visualizations, and detailed analysis reports</p>
            </div>
          </div>
          <div className="step">
            <span className="step-number">4</span>
            <div>
              <h4>Export & Share</h4>
              <p>Download maps, datasets, and reports for sharing or further analysis</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
