import React, { useState } from 'react';
import './UserGuide.css';

/**
 * User Guide - Interactive tutorial for new users
 * Explains how to use the platform step by step
 */
export default function UserGuide({ onClose, onStartTutorial }) {
  const [currentStep, setCurrentStep] = useState(0);

  const tutorialSteps = [
    {
      title: "Welcome to EarthAI!",
      content: "This platform makes earth science analysis accessible to everyone. No coding required!",
      image: "🌍",
      action: "Next"
    },
    {
      title: "Choose Your Research",
      content: "Select from pre-made templates like landslide risk, flood prediction, or crop yield analysis.",
      image: "📋",
      action: "Next"
    },
    {
      title: "Pick Your Location",
      content: "Enter a location name, coordinates, or draw on the map. It's that simple!",
      image: "📍",
      action: "Next"
    },
    {
      title: "Watch AI Work",
      content: "Our AI processes data, runs models, and integrates research automatically.",
      image: "🤖",
      action: "Next"
    },
    {
      title: "View Beautiful Results",
      content: "See interactive maps, charts, and detailed reports with your findings.",
      image: "📊",
      action: "Next"
    },
    {
      title: "Download & Share",
      content: "Export your results as maps, PDFs, or data files to use anywhere.",
      image: "📥",
      action: "Get Started!"
    }
  ];

  const handleNext = () => {
    if (currentStep < tutorialSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onStartTutorial();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const currentTutorialStep = tutorialSteps[currentStep];

  return (
    <div className="user-guide-overlay">
      <div className="user-guide-modal">
        <button className="close-btn" onClick={onClose}>×</button>

        <div className="tutorial-content">
          <div className="tutorial-image">
            {currentTutorialStep.image}
          </div>

          <h2>{currentTutorialStep.title}</h2>
          <p>{currentTutorialStep.content}</p>

          <div className="tutorial-progress">
            {tutorialSteps.map((_, index) => (
              <div
                key={index}
                className={`progress-dot ${index <= currentStep ? 'active' : ''}`}
              />
            ))}
          </div>

          <div className="tutorial-actions">
            <button
              className="btn-secondary"
              onClick={handlePrev}
              disabled={currentStep === 0}
            >
              ← Back
            </button>
            <button className="btn-primary" onClick={handleNext}>
              {currentTutorialStep.action}
            </button>
          </div>
        </div>

        <div className="tutorial-skip">
          <button className="skip-btn" onClick={onClose}>
            Skip Tutorial
          </button>
        </div>
      </div>
    </div>
  );
}
