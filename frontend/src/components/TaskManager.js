/**
 * TaskManager Component
 * Manage and track task execution
 */

import React, { useState, useEffect, useCallback } from 'react';
import './TaskManager.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const TaskManager = ({ userId, tasks, selectedTask, onTaskSelect, onTaskCancel, onNotification }) => {
  const [logs, setLogs] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!selectedTask) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${wsProtocol}//${window.location.host}/ws/tasks/${selectedTask}`
    );

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      // Receive real-time task updates
      const data = JSON.parse(event.data);
      console.log('Task update:', data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    return () => ws.close();
  }, [selectedTask]);

  // Fetch task logs
  useEffect(() => {
    if (!selectedTask) return;

    const fetchLogs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${selectedTask}/logs`);
        if (response.ok) {
          const data = await response.json();
          setLogs(data.logs || []);
        }
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [selectedTask]);

  const filteredTasks = tasks.filter(task => {
    if (filterStatus === 'all') return true;
    return task.status === filterStatus;
  });

  const currentTask = selectedTask ? tasks.find(t => t.task_id === selectedTask) : null;

  return (
    <div className="task-manager">
      <div className="task-list-section">
        <h2>Tasks</h2>

        {/* Filter */}
        <div className="filter-controls">
          <label>Filter by status:</label>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {/* Task List */}
        <div className="task-list">
          {filteredTasks.length === 0 ? (
            <p className="empty-message">No tasks found</p>
          ) : (
            filteredTasks.map(task => (
              <div
                key={task.task_id}
                className={`task-item ${task.task_id === selectedTask ? 'selected' : ''}`}
                onClick={() => onTaskSelect(task.task_id)}
              >
                <div className="task-header">
                  <h4>{task.task_type}</h4>
                  <span className={`status-badge status-${task.status}`}>
                    {task.status}
                  </span>
                </div>

                <p className="task-id">ID: {task.task_id.substring(0, 8)}...</p>

                <div className="progress-container">
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${task.progress}%` }}></div>
                  </div>
                  <span className="progress-text">{task.progress.toFixed(0)}%</span>
                </div>

                <p className="task-time">
                  {new Date(task.created_at).toLocaleDateString()} {new Date(task.created_at).toLocaleTimeString()}
                </p>

                {task.estimated_completion && (
                  <p className="task-eta">
                    ETA: {new Date(task.estimated_completion).toLocaleTimeString()}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Task Details Section */}
      <div className="task-details-section">
        {currentTask ? (
          <>
            <h2>Task Details</h2>

            <div className="task-details-header">
              <h3>{currentTask.task_type}</h3>
              <span className={`status-badge status-${currentTask.status}`}>
                {currentTask.status}
              </span>
            </div>

            {/* Basic Info */}
            <div className="details-grid">
              <div className="detail-item">
                <label>Task ID:</label>
                <span>{currentTask.task_id}</span>
              </div>
              <div className="detail-item">
                <label>Status:</label>
                <span>{currentTask.status}</span>
              </div>
              <div className="detail-item">
                <label>Progress:</label>
                <span>{currentTask.progress.toFixed(0)}%</span>
              </div>
              <div className="detail-item">
                <label>Created:</label>
                <span>{new Date(currentTask.created_at).toLocaleString()}</span>
              </div>
              {currentTask.started_at && (
                <div className="detail-item">
                  <label>Started:</label>
                  <span>{new Date(currentTask.started_at).toLocaleString()}</span>
                </div>
              )}
              {currentTask.completed_at && (
                <div className="detail-item">
                  <label>Completed:</label>
                  <span>{new Date(currentTask.completed_at).toLocaleString()}</span>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="progress-section">
              <div className="progress-bar-large">
                <div className="progress-fill" style={{ width: `${currentTask.progress}%` }}></div>
              </div>
            </div>

            {/* Pipeline Stages */}
            {currentTask.stages && Object.keys(currentTask.stages).length > 0 && (
              <div className="stages-section">
                <h4>Pipeline Stages</h4>
                <div className="stages-list">
                  {Object.entries(currentTask.stages).map(([stageName, stageData]) => (
                    <div key={stageName} className={`stage-item stage-${stageData.status}`}>
                      <span className="stage-name">{stageName}</span>
                      <span className={`stage-status status-${stageData.status}`}>
                        {stageData.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Error Message */}
            {currentTask.error_message && (
              <div className="error-section">
                <h4>Error:</h4>
                <p className="error-message">{currentTask.error_message}</p>
              </div>
            )}

            {/* Execution Logs */}
            {logs.length > 0 && (
              <div className="logs-section">
                <h4>Execution Logs</h4>
                <div className="logs-container">
                  {logs.map((log, idx) => (
                    <div key={idx} className={`log-entry log-${log.status}`}>
                      <span className="log-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className="log-stage">{log.stage}</span>
                      <span className="log-message">{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* WebSocket Status */}
            {selectedTask && (
              <div className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
                {wsConnected ? '🟢 Real-time updates' : '⚪ Offline mode'}
              </div>
            )}

            {/* Actions */}
            {['pending', 'in_progress'].includes(currentTask.status) && (
              <div className="actions">
                <button
                  className="btn btn-danger"
                  onClick={() => {
                    onTaskCancel(currentTask.task_id);
                  }}
                >
                  Cancel Task
                </button>
              </div>
            )}

            {currentTask.result && (
              <div className="result-section">
                <h4>Results</h4>
                <pre>{JSON.stringify(currentTask.result, null, 2)}</pre>
              </div>
            )}
          </>
        ) : (
          <div className="empty-message">
            <p>Select a task to view details</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskManager;
