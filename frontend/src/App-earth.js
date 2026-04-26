import React, { useState } from 'react';
import EarthScienceDashboard from './components/EarthScienceDashboard';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');

  return (
    <div className="App">
      <EarthScienceDashboard />
    </div>
  );
}

export default App;
