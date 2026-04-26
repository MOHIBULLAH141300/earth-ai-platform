/**
 * ChatbotPanel Component
 * Natural language interface for task interaction
 */

import React, { useState, useRef, useEffect } from 'react';
import './ChatbotPanel.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const ChatbotPanel = ({ userId, onIntentDetected, onNotification }) => {
  const [messages, setMessages] = useState([
    {
      type: 'bot',
      text: 'Hello! I\'m the EarthAI Assistant. How can I help you today? You can ask me to:',
      suggestions: [
        'Predict landslide susceptibility',
        'Analyze flood risk',
        'Search latest research',
        'Train a custom model'
      ]
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const messagesEndRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load conversation history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/chat/history/${userId}`);
        if (response.ok) {
          const data = await response.json();
          setHistory(data.history || []);
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
      }
    };

    loadHistory();
  }, [userId]);

  const sendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    // Add user message
    setMessages(prev => [...prev, { type: 'user', text: messageText }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          message: messageText,
          context: { conversation_id: 'web-chat' }
        })
      });

      if (response.ok) {
        const data = await response.json();

        // Add bot response
        setMessages(prev => [...prev, {
          type: 'bot',
          text: data.message,
          intent: data.intent,
          confidence: data.confidence,
          suggestions: data.suggestions
        }]);

        // If intent detected and action needed, trigger task creation
        if (data.action && data.action !== 'help') {
          if (data.confidence > 0.6) {
            setTimeout(() => {
              setMessages(prev => [...prev, {
                type: 'bot',
                text: 'Would you like me to proceed with this task?',
                action: data.action,
                parameters: data.parameters
              }]);
            }, 500);
          }
        }
      } else {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: 'Sorry, I had trouble understanding that. Could you rephrase?'
        }]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        type: 'bot',
        text: 'I encountered an error processing your request.'
      }]);
      onNotification('Error communicating with chatbot', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const handleActionClick = (message) => {
    if (message.action && message.parameters) {
      onIntentDetected(message.action, message.parameters);
      setMessages(prev => [...prev, {
        type: 'bot',
        text: 'Great! I\'ve started the task. You can track progress in the Tasks tab.'
      }]);
    }
  };

  return (
    <div className="chatbot-panel">
      <div className="chatbot-container">
        {/* Chat History */}
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.type}`}>
              <div className="message-content">
                {msg.type === 'bot' ? '🤖' : '👤'} {msg.text}
              </div>

              {msg.confidence && (
                <div className="confidence">
                  Confidence: {(msg.confidence * 100).toFixed(0)}%
                  {msg.intent && <span> | Intent: {msg.intent}</span>}
                </div>
              )}

              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="suggestions">
                  {msg.suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      className="suggestion-btn"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}

              {msg.action && (
                <div className="action-buttons">
                  <button className="action-btn proceed" onClick={() => handleActionClick(msg)}>
                    ✓ Proceed
                  </button>
                  <button className="action-btn cancel" onClick={() => {
                    setMessages(prev => [...prev, {
                      type: 'bot',
                      text: 'Cancelled. How else can I help?'
                    }]);
                  }}>
                    ✗ Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="message message-bot">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          <input
            type="text"
            className="chat-input"
            placeholder="Describe what you want to analyze or predict..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !loading) {
                sendMessage(input);
              }
            }}
            disabled={loading}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>

      {/* Information Panel */}
      <div className="chatbot-info">
        <h3>💡 Tips</h3>
        <ul>
          <li>Ask me to predict hazards for specific regions</li>
          <li>Request analysis of your own data</li>
          <li>Search for latest research papers</li>
          <li>Train custom models</li>
          <li>Be specific about location and timeframe</li>
        </ul>
      </div>
    </div>
  );
};

export default ChatbotPanel;
