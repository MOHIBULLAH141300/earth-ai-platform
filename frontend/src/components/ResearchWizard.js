import React, { useState, useEffect } from 'react';
import './ResearchWizard.css';

/**
 * Research Wizard - Step-by-step guided interface for non-technical users
 * Makes complex earth science analysis accessible to everyone
 */
export default function ResearchWizard({ onTaskCreated, onBackToLanding }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [wizardData, setWizardData] = useState({
    researchType: '',
    location: '',
    locationType: 'name', // 'name', 'coordinates', 'draw'
    coordinates: { lat: '', lng: '' },
    parameters: {},
    urgency: 'normal' // 'low', 'normal', 'high'
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [taskId, setTaskId] = useState(null);

  const researchTypes = [
    {
      id: 'landslide_susceptibility',
      emoji: '🏔️',
      title: 'Landslide Risk Analysis',
      description: 'Identify areas prone to landslides and assess risk factors',
      difficulty: 'Easy',
      time: '3-5 minutes'
    },
    {
      id: 'flood_prediction',
      emoji: '🌊',
      title: 'Flood Risk Assessment',
      description: 'Predict flood zones and understand flood vulnerability',
      difficulty: 'Easy',
      time: '4-6 minutes'
    },
    {
      id: 'crop_yield_prediction',
      emoji: '🌾',
      title: 'Crop Yield Forecasting',
      description: 'Predict agricultural production based on conditions',
      difficulty: 'Medium',
      time: '5-8 minutes'
    },
    {
      id: 'drought_monitoring',
      emoji: '🔥',
      title: 'Drought Monitoring',
      description: 'Track drought conditions and water availability',
      difficulty: 'Easy',
      time: '3-5 minutes'
    },
    {
      id: 'earthquake_damage',
      emoji: '🏛️',
      title: 'Earthquake Impact Analysis',
      description: 'Assess potential earthquake damage and building vulnerability',
      difficulty: 'Medium',
      time: '6-10 minutes'
    },
    {
      id: 'climate_analysis',
      emoji: '🌡️',
      title: 'Climate Pattern Analysis',
      description: 'Understand long-term climate trends and patterns',
      difficulty: 'Advanced',
      time: '8-12 minutes'
    },
    {
      id: 'custom_analysis',
      emoji: '🔬',
      title: 'Custom Research',
      description: 'Describe your specific research question',
      difficulty: 'Variable',
      time: '5-15 minutes'
    }
  ];

  const handleResearchTypeSelect = (typeId) => {
    setWizardData(prev => ({ ...prev, researchType: typeId }));
    setCurrentStep(2);
  };

  const handleLocationSubmit = () => {
    if (wizardData.locationType === 'name' && !wizardData.location.trim()) {
      alert('Please enter a location name');
      return;
    }
    if (wizardData.locationType === 'coordinates' &&
        (!wizardData.coordinates.lat || !wizardData.coordinates.lng)) {
      alert('Please enter both latitude and longitude');
      return;
    }
    setCurrentStep(3);
  };

  const handleParametersSubmit = () => {
    setCurrentStep(4);
  };

  const handleStartAnalysis = async () => {
    setIsProcessing(true);

    try {
      // Create task through API
      const taskData = {
        task_type: wizardData.researchType,
        location: wizardData.location,
        location_type: wizardData.locationType,
        coordinates: wizardData.coordinates,
        parameters: wizardData.parameters,
        urgency: wizardData.urgency,
        user_id: 'wizard_user_' + Date.now()
      };

      const response = await fetch('http://localhost:8000/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData)
      });

      if (!response.ok) {
        throw new Error('Failed to create task');
      }

      const result = await response.json();
      setTaskId(result.task_id);

      // Notify parent component
      onTaskCreated(result.task_id);

      setCurrentStep(5);
    } catch (error) {
      console.error('Error creating task:', error);
      alert('Failed to start analysis. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const renderStep1 = () => (
    <div className="wizard-step">
      <div className="step-header">
        <h2>Step 1: Choose Your Research Topic</h2>
        <p>Select what you want to analyze. Don't worry - you can change this later!</p>
      </div>

      <div className="research-types-grid">
        {researchTypes.map((type) => (
          <div
            key={type.id}
            className={`research-type-card ${wizardData.researchType === type.id ? 'selected' : ''}`}
            onClick={() => handleResearchTypeSelect(type.id)}
          >
            <div className="type-emoji">{type.emoji}</div>
            <h3>{type.title}</h3>
            <p>{type.description}</p>
            <div className="type-meta">
              <span className={`difficulty ${type.difficulty.toLowerCase()}`}>
                {type.difficulty}
              </span>
              <span className="time">{type.time}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="wizard-step">
      <div className="step-header">
        <h2>Step 2: Where Do You Want to Research?</h2>
        <p>Tell us the location for your analysis. You can use a name, coordinates, or draw on a map.</p>
      </div>

      <div className="location-options">
        <div className="location-tabs">
          <button
            className={wizardData.locationType === 'name' ? 'active' : ''}
            onClick={() => setWizardData(prev => ({ ...prev, locationType: 'name' }))}
          >
            📍 Location Name
          </button>
          <button
            className={wizardData.locationType === 'coordinates' ? 'active' : ''}
            onClick={() => setWizardData(prev => ({ ...prev, locationType: 'coordinates' }))}
          >
            📌 Coordinates
          </button>
          <button
            className={wizardData.locationType === 'draw' ? 'active' : ''}
            onClick={() => setWizardData(prev => ({ ...prev, locationType: 'draw' }))}
          >
            ✏️ Draw on Map
          </button>
        </div>

        {wizardData.locationType === 'name' && (
          <div className="location-input">
            <label>Enter a location name:</label>
            <input
              type="text"
              placeholder="e.g., Himalayas, California, Amazon Rainforest"
              value={wizardData.location}
              onChange={(e) => setWizardData(prev => ({ ...prev, location: e.target.value }))}
            />
            <p className="help-text">Try: "Mount Everest", "New York City", "Sahara Desert"</p>
          </div>
        )}

        {wizardData.locationType === 'coordinates' && (
          <div className="coordinates-input">
            <div className="coord-row">
              <div className="coord-field">
                <label>Latitude:</label>
                <input
                  type="number"
                  step="0.000001"
                  placeholder="e.g., 27.9881"
                  value={wizardData.coordinates.lat}
                  onChange={(e) => setWizardData(prev => ({
                    ...prev,
                    coordinates: { ...prev.coordinates, lat: e.target.value }
                  }))}
                />
              </div>
              <div className="coord-field">
                <label>Longitude:</label>
                <input
                  type="number"
                  step="0.000001"
                  placeholder="e.g., 86.9250"
                  value={wizardData.coordinates.lng}
                  onChange={(e) => setWizardData(prev => ({
                    ...prev,
                    coordinates: { ...prev.coordinates, lng: e.target.value }
                  }))}
                />
              </div>
            </div>
            <p className="help-text">Find coordinates on Google Maps or use known locations</p>
          </div>
        )}

        {wizardData.locationType === 'draw' && (
          <div className="map-placeholder">
            <div className="map-preview">
              🗺️ Interactive Map
              <p>Click and draw your area of interest</p>
            </div>
            <p className="help-text">This feature will be available in the full analysis interface</p>
          </div>
        )}
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="wizard-step">
      <div className="step-header">
        <h2>Step 3: Customize Your Analysis</h2>
        <p>Optional settings to make your analysis more specific.</p>
      </div>

      <div className="parameters-section">
        <div className="parameter-group">
          <h3>Analysis Priority</h3>
          <div className="urgency-options">
            <label>
              <input
                type="radio"
                name="urgency"
                value="low"
                checked={wizardData.urgency === 'low'}
                onChange={(e) => setWizardData(prev => ({ ...prev, urgency: e.target.value }))}
              />
              <span>🕐 Low Priority</span>
              <small>Take your time, get detailed results</small>
            </label>
            <label>
              <input
                type="radio"
                name="urgency"
                value="normal"
                checked={wizardData.urgency === 'normal'}
                onChange={(e) => setWizardData(prev => ({ ...prev, urgency: e.target.value }))}
              />
              <span>⚖️ Normal Priority</span>
              <small>Balanced speed and detail</small>
            </label>
            <label>
              <input
                type="radio"
                name="urgency"
                value="high"
                checked={wizardData.urgency === 'high'}
                onChange={(e) => setWizardData(prev => ({ ...prev, urgency: e.target.value }))}
              />
              <span>🚀 High Priority</span>
              <small>Fast results, less detail</small>
            </label>
          </div>
        </div>

        <div className="parameter-group">
          <h3>Additional Options</h3>
          <div className="checkbox-options">
            <label>
              <input
                type="checkbox"
                checked={wizardData.parameters.includeResearch || false}
                onChange={(e) => setWizardData(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, includeResearch: e.target.checked }
                }))}
              />
              Include latest research papers
            </label>
            <label>
              <input
                type="checkbox"
                checked={wizardData.parameters.generateReport || false}
                onChange={(e) => setWizardData(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, generateReport: e.target.checked }
                }))}
              />
              Generate detailed PDF report
            </label>
            <label>
              <input
                type="checkbox"
                checked={wizardData.parameters.compareScenarios || false}
                onChange={(e) => setWizardData(prev => ({
                  ...prev,
                  parameters: { ...prev.parameters, compareScenarios: e.target.checked }
                }))}
              />
              Compare different scenarios
            </label>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="wizard-step">
      <div className="step-header">
        <h2>Step 4: Review & Start Analysis</h2>
        <p>Review your settings and start the analysis!</p>
      </div>

      <div className="review-section">
        <div className="review-card">
          <h3>📋 Your Analysis Summary</h3>
          <div className="review-item">
            <strong>Research Type:</strong>
            {researchTypes.find(t => t.id === wizardData.researchType)?.title}
          </div>
          <div className="review-item">
            <strong>Location:</strong>
            {wizardData.locationType === 'name' && wizardData.location}
            {wizardData.locationType === 'coordinates' &&
              `${wizardData.coordinates.lat}, ${wizardData.coordinates.lng}`}
            {wizardData.locationType === 'draw' && 'Custom drawn area'}
          </div>
          <div className="review-item">
            <strong>Priority:</strong>
            {wizardData.urgency === 'low' && 'Low (Detailed)'}
            {wizardData.urgency === 'normal' && 'Normal (Balanced)'}
            {wizardData.urgency === 'high' && 'High (Fast)'}
          </div>
          <div className="review-item">
            <strong>Options:</strong>
            {Object.entries(wizardData.parameters).filter(([k, v]) => v).map(([k, v]) => k).join(', ') || 'None'}
          </div>
        </div>

        <div className="start-notice">
          <div className="notice-icon">⚡</div>
          <div className="notice-content">
            <h4>Ready to Start!</h4>
            <p>Your analysis will begin immediately and you'll see real-time progress.</p>
            <p>You can watch the progress, view results, and download reports when complete.</p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep5 = () => (
    <div className="wizard-step">
      <div className="step-header">
        <h2>🎉 Analysis Started!</h2>
        <p>Your research is now running. Here's what happens next:</p>
      </div>

      <div className="completion-section">
        <div className="success-card">
          <div className="success-icon">✅</div>
          <h3>Task Created Successfully!</h3>
          <p><strong>Task ID:</strong> {taskId}</p>
        </div>

        <div className="next-steps">
          <h4>What happens now?</h4>
          <div className="steps-list">
            <div className="step-item">
              <span className="step-number">1</span>
              <span>AI analyzes your request and gathers data</span>
            </div>
            <div className="step-item">
              <span className="step-number">2</span>
              <span>Research papers are automatically reviewed</span>
            </div>
            <div className="step-item">
              <span className="step-number">3</span>
              <span>Models run calculations and predictions</span>
            </div>
            <div className="step-item">
              <span className="step-number">4</span>
              <span>Results are visualized and reports generated</span>
            </div>
          </div>
        </div>

        <div className="action-buttons">
          <button className="btn-primary" onClick={() => onTaskCreated(taskId)}>
            View Progress Now →
          </button>
          <button className="btn-secondary" onClick={onBackToLanding}>
            Start Another Analysis
          </button>
        </div>
      </div>
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1: return renderStep1();
      case 2: return renderStep2();
      case 3: return renderStep3();
      case 4: return renderStep4();
      case 5: return renderStep5();
      default: return renderStep1();
    }
  };

  const canGoNext = () => {
    switch (currentStep) {
      case 1: return wizardData.researchType;
      case 2: return wizardData.location ||
               (wizardData.locationType === 'coordinates' &&
                wizardData.coordinates.lat && wizardData.coordinates.lng);
      case 3: return true;
      case 4: return true;
      default: return false;
    }
  };

  const handleNext = () => {
    if (currentStep === 2) {
      handleLocationSubmit();
    } else if (currentStep === 3) {
      handleParametersSubmit();
    } else if (currentStep === 4) {
      handleStartAnalysis();
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    setCurrentStep(prev => prev - 1);
  };

  return (
    <div className="research-wizard">
      {/* Progress Bar */}
      <div className="wizard-progress">
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(currentStep / 5) * 100}%` }}
          ></div>
        </div>
        <div className="progress-steps">
          {[1, 2, 3, 4, 5].map(step => (
            <div
              key={step}
              className={`progress-step ${step <= currentStep ? 'completed' : ''} ${step === currentStep ? 'active' : ''}`}
            >
              {step}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="wizard-content">
        {renderCurrentStep()}
      </div>

      {/* Navigation */}
      {currentStep < 5 && (
        <div className="wizard-navigation">
          <button
            className="btn-back"
            onClick={handleBack}
            disabled={currentStep === 1}
          >
            ← Back
          </button>

          <div className="nav-info">
            Step {currentStep} of 5
          </div>

          <button
            className="btn-next"
            onClick={handleNext}
            disabled={!canGoNext() || isProcessing}
          >
            {currentStep === 4 ? (isProcessing ? 'Starting...' : 'Start Analysis →') : 'Next →'}
          </button>
        </div>
      )}

      {/* Back to Landing */}
      <button className="back-to-landing" onClick={onBackToLanding}>
        ← Back to Home
      </button>
    </div>
  );
}
