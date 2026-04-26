import React, { useState } from 'react';
import './HelpButton.css';

/**
 * Help Button - Contextual help system
 * Provides tooltips and guidance throughout the application
 */
export default function HelpButton({ topic, position = 'bottom-right' }) {
  const [isOpen, setIsOpen] = useState(false);

  const helpTopics = {
    landing: {
      title: "Getting Started",
      content: "Click 'Start Your First Analysis' to begin. Choose from templates like landslide risk or flood prediction. No coding required!"
    },
    wizard: {
      title: "Research Wizard",
      content: "Follow the 4 simple steps: 1) Choose research type, 2) Select location, 3) Set parameters, 4) Start analysis. Each step is guided."
    },
    dashboard: {
      title: "Dashboard Overview",
      content: "View your recent tasks, system statistics, and quick-start templates. Click any template to start a new analysis."
    },
    tasks: {
      title: "Task Management",
      content: "Monitor your analyses in real-time. Click any task to see progress, logs, and results. Green = completed, blue = running."
    },
    chatbot: {
      title: "AI Chatbot",
      content: "Talk naturally! Say things like 'Predict floods in California' or 'Show me landslide research'. The AI understands plain English."
    },
    visualizations: {
      title: "Results & Maps",
      content: "View interactive maps, charts, and reports. Select a completed task and choose your preferred format (map, chart, or table)."
    },
    system: {
      title: "System Status",
      content: "Monitor platform health, active tasks, and resource usage. Green indicators mean everything is working well."
    }
  };

  const currentHelp = helpTopics[topic] || helpTopics.landing;

  const toggleHelp = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className={`help-button ${position}`}>
      <button
        className="help-btn"
        onClick={toggleHelp}
        title="Click for help"
      >
        ?
      </button>

      {isOpen && (
        <div className="help-tooltip">
          <div className="help-header">
            <h4>{currentHelp.title}</h4>
            <button className="close-help" onClick={toggleHelp}>×</button>
          </div>
          <div className="help-content">
            <p>{currentHelp.content}</p>
          </div>
          <div className="help-footer">
            <button className="got-it-btn" onClick={toggleHelp}>
              Got it!
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
