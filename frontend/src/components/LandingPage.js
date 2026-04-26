import React, { useState, useEffect } from 'react';
import './LandingPage.css';
import UserGuide from './UserGuide';

/**
 * Landing Page - First impression of the platform
 * Guides users through what they can do without any coding
 */
export default function LandingPage({ onGetStarted }) {
  const [activeTab, setActiveTab] = useState('features');
  const [scrolled, setScrolled] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleShowTutorial = () => {
    setShowTutorial(true);
  };

  const handleCloseTutorial = () => {
    setShowTutorial(false);
  };

  const handleTutorialComplete = () => {
    setShowTutorial(false);
    onGetStarted();
  };
    {
      icon: '🤖',
      title: 'Talk to AI',
      description: 'Just describe what you want to analyze in plain English. No coding needed!'
    },
    {
      icon: '📚',
      title: 'Research Powered',
      description: 'Automatically integrates the latest research papers to improve accuracy'
    },
    {
      icon: '🗺️',
      title: 'Beautiful Maps',
      description: 'See your results on interactive maps and visualizations'
    },
    {
      icon: '⚡',
      title: 'Real-time Progress',
      description: 'Watch your analysis progress in real-time with detailed updates'
    },
    {
      icon: '📊',
      title: 'Export Results',
      description: 'Download reports, maps, and data in multiple formats'
    },
    {
      icon: '🔄',
      title: 'Try Multiple Scenarios',
      description: 'Run different analyses and compare results instantly'
    }
  ];

  const useCases = [
    {
      emoji: '🏔️',
      title: 'Landslide Risk',
      description: 'Identify areas vulnerable to landslides and understand risk factors'
    },
    {
      emoji: '🌊',
      title: 'Flood Prediction',
      description: 'Predict flood zones and prepare for flooding events'
    },
    {
      emoji: '🌾',
      title: 'Crop Yield',
      description: 'Forecast crop production based on weather and soil conditions'
    },
    {
      emoji: '🔥',
      title: 'Drought Monitoring',
      description: 'Track drought conditions and plan water resources'
    },
    {
      emoji: '🏛️',
      title: 'Earthquake Damage',
      description: 'Assess earthquake damage potential and building vulnerability'
    },
    {
      emoji: '🌡️',
      title: 'Climate Analysis',
      description: 'Understand climate patterns and long-term trends'
    }
  ];

  const steps = [
    {
      number: '1',
      title: 'Choose Your Research Topic',
      description: 'Select from pre-made templates or describe your own question'
    },
    {
      number: '2',
      title: 'Select Your Location',
      description: 'Click on a map or enter a location name - no coordinates needed'
    },
    {
      number: '3',
      title: 'Let AI Work',
      description: 'Our AI processes data and research. Watch the real-time progress'
    },
    {
      number: '4',
      title: 'Get Beautiful Results',
      description: 'View interactive maps, charts, and detailed reports'
    }
  ];

  const testimonials = [
    {
      name: 'Maria Chen',
      role: 'Environmental Manager',
      quote: 'I had no tech background but could use this platform immediately. Saved us weeks of analysis!'
    },
    {
      name: 'Dr. James Wilson',
      role: 'Climate Researcher',
      description: 'The research integration is incredible. Automatically found relevant papers I would have missed.'
    },
    {
      name: 'Sarah Ahmed',
      role: 'City Planner',
      quote: 'Finally, a tool that makes data accessible to non-technical staff. Everyone loves it!'
    }
  ];

  return (
    <div className="landing-page">
      {/* Navigation Header */}
      <header className={`navbar ${scrolled ? 'scrolled' : ''}`}>
        <div className="nav-container">
          <div className="logo">
            <span className="logo-emoji">🌍</span>
            <span className="logo-text">EarthAI</span>
          </div>
          <nav className="nav-links">
            <a href="#features" onClick={() => setActiveTab('features')}>Features</a>
            <a href="#use-cases" onClick={() => setActiveTab('use-cases')}>What You Can Do</a>
            <a href="#how" onClick={() => setActiveTab('how')}>How It Works</a>
            <a href="#faq" onClick={() => setActiveTab('faq')}>FAQ</a>
          </nav>
          <button className="btn-get-started" onClick={onGetStarted}>
            Get Started →
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1>Earth Science Analysis Made Simple</h1>
          <p>No coding. No training. Just simple, powerful tools for anyone to understand our planet.</p>
          <button className="btn-primary-large" onClick={onGetStarted}>
            Start Your First Analysis
          </button>
          <p className="hero-subtitle">Free to use. Takes 2 minutes to get results.</p>
          <button className="btn-tutorial" onClick={handleShowTutorial}>
            📚 Show Me How It Works
          </button>
        </div>
        <div className="hero-graphic">
          <div className="graphic-element">🗺️</div>
          <div className="graphic-element">📊</div>
          <div className="graphic-element">🤖</div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features">
        <h2>Why Choose EarthAI?</h2>
        <div className="features-grid">
          {features.map((feature, idx) => (
            <div key={idx} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Use Cases Section */}
      <section id="use-cases" className="use-cases">
        <h2>What Can You Research?</h2>
        <div className="use-cases-grid">
          {useCases.map((useCase, idx) => (
            <div key={idx} className="use-case-card">
              <div className="use-case-emoji">{useCase.emoji}</div>
              <h3>{useCase.title}</h3>
              <p>{useCase.description}</p>
              <button className="btn-small">Try Now →</button>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how" className="how-it-works">
        <h2>4 Simple Steps</h2>
        <div className="steps-container">
          {steps.map((step, idx) => (
            <div key={idx} className="step-card">
              <div className="step-number">{step.number}</div>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              {idx < steps.length - 1 && <div className="step-arrow">→</div>}
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="testimonials">
        <h2>People Love It</h2>
        <div className="testimonials-grid">
          {testimonials.map((testimonial, idx) => (
            <div key={idx} className="testimonial-card">
              <div className="testimonial-content">
                <p className="quote">"{testimonial.quote || testimonial.description}"</p>
              </div>
              <div className="testimonial-author">
                <p className="author-name">{testimonial.name}</p>
                <p className="author-role">{testimonial.role}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="faq">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-grid">
          <div className="faq-item">
            <h4>Do I need to know programming?</h4>
            <p>Absolutely not! EarthAI is designed for anyone. Just describe what you want to analyze and we handle the rest.</p>
          </div>
          <div className="faq-item">
            <h4>How long does an analysis take?</h4>
            <p>Most analyses complete in 2-10 minutes depending on complexity. You can watch the progress in real-time.</p>
          </div>
          <div className="faq-item">
            <h4>What locations can I analyze?</h4>
            <p>Anywhere in the world! Use a location name, coordinates, or just draw on the map. No limits.</p>
          </div>
          <div className="faq-item">
            <h4>Can I download my results?</h4>
            <p>Yes! Export as maps, PDFs, spreadsheets, or raw data for use in other tools.</p>
          </div>
          <div className="faq-item">
            <h4>Is this based on real science?</h4>
            <p>100%! We integrate latest research papers, satellite data, and peer-reviewed models automatically.</p>
          </div>
          <div className="faq-item">
            <h4>Is it free?</h4>
            <p>Yes, EarthAI is completely free to use. No hidden fees or limitations.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-final">
        <h2>Ready to Explore Earth Science?</h2>
        <p>Start analyzing in seconds. No sign-up required.</p>
        <button className="btn-primary-large" onClick={onGetStarted}>
          Launch Platform Now
        </button>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>EarthAI</h4>
            <p>Making earth science accessible to everyone.</p>
          </div>
          <div className="footer-section">
            <h4>Learn</h4>
            <ul>
              <li><a href="#docs">Documentation</a></li>
              <li><a href="#tutorials">Tutorials</a></li>
              <li><a href="#examples">Examples</a></li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>Support</h4>
            <ul>
              <li><a href="#help">Help & FAQ</a></li>
              <li><a href="#contact">Contact Us</a></li>
              <li><a href="#feedback">Send Feedback</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2024 EarthAI Platform. Built with ❤️ for earth science.</p>
        </div>
      </footer>

      {/* User Guide Tutorial */}
      {showTutorial && (
        <UserGuide
          onClose={handleCloseTutorial}
          onStartTutorial={handleTutorialComplete}
        />
      )}
    </div>
  );
}
