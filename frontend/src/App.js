/**
 * EarthAI Platform - React Frontend
 * Main Application Component with Landing Page & Research Wizard
 * Integrates: Landing Page, Research Wizard, Dashboard, Chatbot, Task Management, Visualizations
 */

import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import './components/LandingPage.css';
import './components/ResearchWizard.css';
import './components/UserGuide.css';
import './components/HelpButton.css';
import LandingPage from './components/LandingPage';
import ResearchWizard from './components/ResearchWizard';
import Dashboard from './components/Dashboard';
import ChatbotPanel from './components/ChatbotPanel';
import TaskManager from './components/TaskManager';
import { VisualizationPanel, SystemStatus } from './components/VisualizationPanel';
import HelpButton from './components/HelpButton';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing', 'wizard', 'app'
  const [activeTab, setActiveTab] = useState('dashboard');
  const [userId, setUserId] = useState(localStorage.getItem('userId') || 'guest-' + Date.now());
  const [systemStatus, setSystemStatus] = useState(null);
  const [userTasks, setUserTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);

  // Initialize user ID
  useEffect(() => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', userId);
    }
  }, [userId]);

  // Fetch system status periodically
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/system/status`);
        if (response.ok) {
          const data = await response.json();
          setSystemStatus(data);
        }
      } catch (error) {
        console.error('Failed to fetch system status:', error);
      }
    };

    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Fetch user tasks periodically
  useEffect(() => {
    const fetchUserTasks = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/tasks/user/${userId}?limit=20`);
        if (response.ok) {
          const data = await response.json();
          setUserTasks(data.tasks);
        }
      } catch (error) {
        console.error('Failed to fetch user tasks:', error);
      }
    };

    fetchUserTasks();
    const interval = setInterval(fetchUserTasks, 15000); // Every 15 seconds
    return () => clearInterval(interval);
  }, [userId]);

  // Add notification
  const addNotification = useCallback((message, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  }, []);

  // View handlers
  const handleGetStarted = () => {
    setCurrentView('wizard');
  };

  const handleBackToLanding = () => {
    setCurrentView('landing');
  };

  const handleTaskCreated = (taskId) => {
    setSelectedTask(taskId);
    setCurrentView('app');
    setActiveTab('tasks');
    addNotification('Analysis started! Check the Tasks tab to monitor progress.', 'success');
  };

  // Create new task from chatbot intent
  const createTaskFromIntent = async (intent, parameters) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          task_type: parameters.task_type || intent,
          parameters: parameters,
          priority: parameters.priority || 'normal'
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedTask(data.task_id);
        addNotification('Task created successfully!', 'success');
        setActiveTab('tasks');
        return data.task_id;
      } else {
        addNotification('Failed to create task', 'error');
      }
    } catch (error) {
      console.error('Error creating task:', error);
      addNotification('Error creating task', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Cancel task
  const cancelTask = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/cancel`, {
        method: 'POST'
      });

      if (response.ok) {
        addNotification('Task cancelled', 'info');
        setUserTasks(prev => prev.filter(t => t.task_id !== taskId));
      }
    } catch (error) {
      console.error('Error cancelling task:', error);
      addNotification('Failed to cancel task', 'error');
    }
  };

  // Render different views
  if (currentView === 'landing') {
    return <LandingPage onGetStarted={handleGetStarted} />;
  }

  if (currentView === 'wizard') {
    return <ResearchWizard onTaskCreated={handleTaskCreated} onBackToLanding={handleBackToLanding} />;
  }

  // Main application view
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🌍 EarthAI Platform</h1>
          <p className="subtitle">Real-time AI System for Earth System Modeling</p>
        </div>
        <div className="header-info">
          <button className="back-to-wizard-btn" onClick={() => setCurrentView('wizard')}>
            ← New Analysis
          </button>
          <span className="user-id">User: {userId.substring(0, 8)}...</span>
          {systemStatus && (
            <span className="system-health" title={`System Health: ${systemStatus.system_health}%`}>
              ● {systemStatus.system_health > 80 ? 'Healthy' : 'Monitor'}
            </span>
          )}
        </div>
      </header>

      <div className="app-container">
        {/* Navigation Tabs */}
        <nav className="main-nav">
          <button
            className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`nav-btn ${activeTab === 'chatbot' ? 'active' : ''}`}
            onClick={() => setActiveTab('chatbot')}
          >
            💬 Chatbot
          </button>
          <button
            className={`nav-btn ${activeTab === 'tasks' ? 'active' : ''}`}
            onClick={() => setActiveTab('tasks')}
          >
            📋 Tasks ({userTasks.length})
          </button>
          <button
            className={`nav-btn ${activeTab === 'visualization' ? 'active' : ''}`}
            onClick={() => setActiveTab('visualization')}
          >
            🗺️ Visualizations
          </button>
          <button
            className={`nav-btn ${activeTab === 'status' ? 'active' : ''}`}
            onClick={() => setActiveTab('status')}
          >
            🔧 System Status
          </button>
        </nav>

        {/* Main Content Area */}
        <main className="main-content">
          {activeTab === 'dashboard' && (
            <Dashboard
              userId={userId}
              tasks={userTasks}
              onTaskCreate={createTaskFromIntent}
              onNotification={addNotification}
            />
          )}

          {activeTab === 'chatbot' && (
            <ChatbotPanel
              userId={userId}
              onIntentDetected={createTaskFromIntent}
              onNotification={addNotification}
            />
          )}

          {activeTab === 'tasks' && (
            <TaskManager
              userId={userId}
              tasks={userTasks}
              selectedTask={selectedTask}
              onTaskSelect={setSelectedTask}
              onTaskCancel={cancelTask}
              onNotification={addNotification}
            />
          )}

          {activeTab === 'visualization' && (
            <VisualizationPanel
              userId={userId}
              tasks={userTasks}
              onNotification={addNotification}
            />
          )}

          {activeTab === 'status' && (
            <SystemStatus
              status={systemStatus}
              onNotification={addNotification}
            />
          )}
        </main>
      </div>

      {/* Notifications */}
      <div className="notifications">
        {notifications.map(notif => (
          <div key={notif.id} className={`notification notification-${notif.type}`}>
            {notif.message}
          </div>
        ))}
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Processing...</p>
        </div>
      )}

      {/* Help Button */}
      <HelpButton topic={activeTab} position="bottom-right" />
    </div>
  );
}

export default App;
