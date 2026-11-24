import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Sparkles, 
  Zap, 
  Database, 
  Cpu, 
  Sliders, 
  ChevronDown, 
  ChevronUp, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Layers, 
  Terminal,
  Activity,
  ShieldAlert
} from 'lucide-react';
import './App.css';

// Unique session ID per page load
const generateSessionId = () => 's-' + Math.random().toString(36).substring(2, 10);

export default function App() {
  const [sessionId] = useState(() => generateSessionId());
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [healthInfo, setHealthInfo] = useState(null);
  
  // Failover simulation control for live demo
  const [simulateFailHeader, setSimulateFailHeader] = useState('none');
  const [customFailHeader, setCustomFailHeader] = useState('');

  const messagesEndRef = useRef(null);

  // Backend API URL defaults to current origin or fallback
  const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Fetch health on mount
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(data => setHealthInfo(data))
      .catch(err => console.error("Could not fetch health:", err));
  }, [API_BASE]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    const trimmed = inputMessage.trim();
    if (!trimmed || isLoading) return;

    // Add user message to UI immediately
    const userMsg = {
      role: 'user',
      content: trimmed
    };
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const headers = {
        'Content-Type': 'application/json'
      };

      // Handle failover simulation header
      if (simulateFailHeader === 'key_1=429') {
        headers['X-Simulate-Failure'] = 'key_1=429';
      } else if (simulateFailHeader === 'key_1=500') {
        headers['X-Simulate-Failure'] = 'key_1=500';
      } else if (simulateFailHeader === '*=429') {
        headers['X-Simulate-Failure'] = '*=429';
      } else if (simulateFailHeader === 'custom' && customFailHeader.trim()) {
        headers['X-Simulate-Failure'] = customFailHeader.trim();
      }

      const body = {
        session_id: sessionId,
        message: trimmed
      };
      if (systemPrompt.trim()) {
        body.system_prompt = systemPrompt.trim();
      }

      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      });

      const data = await res.json();

      if (!res.ok) {
        // Display readable error message, never crash
        const errorDetail = typeof data.detail === 'string' 
          ? data.detail 
          : JSON.stringify(data.detail || 'An error occurred');
        
        setMessages(prev => [
          ...prev,
          {
            role: 'error',
            content: `Error (${res.status}): ${errorDetail}`
          }
        ]);
      } else {
        // Assistant message successfully received
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: data.reply,
            metadata: data.metadata
          }
        ]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'error',
          content: `Network or Connection Error: ${err.message}`
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="lyftr-container">
      {/* Top Navigation */}
      <header className="lyftr-header">
        <div className="header-brand">
          <div className="brand-logo-glow">
            <Sparkles className="brand-icon" size={20} />
          </div>
          <div>
            <div className="brand-title-wrap">
              <h1 className="brand-title">Lyftr AI</h1>
              <span className="brand-badge">PRO GATEWAY</span>
            </div>
            <p className="brand-subtitle">Resilient LLM Gateway • Key Failover & Disk/Memory Cache</p>
          </div>
        </div>

        <div className="header-meta">
          <div className="meta-pill">
            <Database size={13} className="pill-icon" />
            <span className="pill-label">Session:</span>
            <span className="pill-value session-id-text">{sessionId}</span>
          </div>

          <div className="meta-pill">
            <Activity size={13} className="pill-icon" />
            <span className="pill-label">Health:</span>
            <span className={`status-dot ${healthInfo?.status === 'ok' ? 'active' : ''}`}></span>
            <span className="pill-value">{healthInfo?.status || 'connecting...'}</span>
          </div>

          {healthInfo && (
            <div className="meta-pill keys-pill">
              <Cpu size={13} className="pill-icon" />
              <span className="pill-label">Key Pool:</span>
              <span className="pill-value">{healthInfo.keys_configured} Active</span>
            </div>
          )}
        </div>
      </header>

      {/* Control Bar: System Prompt & Failure Simulation */}
      <div className="controls-bar">
        <div className="controls-left">
          <button 
            type="button"
            className="toggle-button"
            onClick={() => setShowSystemPrompt(!showSystemPrompt)}
          >
            <Sliders size={14} />
            <span>Session System Prompt</span>
            {showSystemPrompt ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>

        {/* Live Failover Simulation Hook selector */}
        <div className="controls-right">
          <div className="sim-selector-wrap">
            <ShieldAlert size={14} className="sim-icon" />
            <span className="sim-label">Simulate Failover:</span>
            <select 
              value={simulateFailHeader} 
              onChange={(e) => setSimulateFailHeader(e.target.value)}
              className="sim-select"
            >
              <option value="none">Normal Operation (Live Keys)</option>
              <option value="key_1=429">Fail key_1 (429 Rate Limit) ➔ Fallback to key_2</option>
              <option value="key_1=500">Fail key_1 (500 Server Error) ➔ Fallback to key_2</option>
              <option value="*=429">Fail All Keys (*=429) ➔ 503 Unavailable</option>
              <option value="custom">Custom Header Pair...</option>
            </select>
          </div>

          {simulateFailHeader === 'custom' && (
            <input 
              type="text" 
              className="sim-custom-input"
              placeholder="e.g. key_1=429,key_2=500" 
              value={customFailHeader}
              onChange={(e) => setCustomFailHeader(e.target.value)}
            />
          )}
        </div>
      </div>

      {/* Expandable System Prompt Drawer */}
      {showSystemPrompt && (
        <div className="system-prompt-drawer">
          <label className="drawer-label" htmlFor="sys-input">
            <Terminal size={14} /> Custom System Instructions for Session
          </label>
          <input
            id="sys-input"
            data-testid="system-prompt-input"
            type="text"
            className="system-prompt-input"
            placeholder="e.g., You are an expert financial consultant with a concise, direct tone."
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
          />
        </div>
      )}

      {/* Main Chat Conversation Area */}
      <main className="chat-window">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-hero">
              <div className="brand-orb">
                <Sparkles size={32} className="orb-icon" />
              </div>
              <h2 className="hero-title">How can Lyftr AI help you today?</h2>
              <p className="hero-subtitle">
                Connected to intelligent multi-key inference with instant cache acceleration.
              </p>
            </div>
            
            <div className="suggestions-grid">
              <button 
                type="button"
                className="suggestion-chip"
                onClick={() => setInputMessage("Explain quantum computing in one simple sentence.")}
              >
                <div className="chip-icon-box"><Zap size={15} /></div>
                <div className="chip-content">
                  <span className="chip-title">Explain quantum computing</span>
                  <span className="chip-sub">Test sub-millisecond cache latency</span>
                </div>
              </button>

              <button 
                type="button"
                className="suggestion-chip"
                onClick={() => {
                  setSimulateFailHeader("key_1=429");
                  setInputMessage("What are the architectural benefits of key failover?");
                }}
              >
                <div className="chip-icon-box failover-box"><ShieldAlert size={15} /></div>
                <div className="chip-content">
                  <span className="chip-title">Simulate 429 Failover</span>
                  <span className="chip-sub">Auto-route from Gemini to Groq</span>
                </div>
              </button>

              <button 
                type="button"
                className="suggestion-chip"
                onClick={() => setInputMessage("Draft a concise product launch email for a developer tool.")}
              >
                <div className="chip-icon-box"><Terminal size={15} /></div>
                <div className="chip-content">
                  <span className="chip-title">Draft developer launch email</span>
                  <span className="chip-sub">Concise, professional release copy</span>
                </div>
              </button>

              <button 
                type="button"
                className="suggestion-chip"
                onClick={() => setInputMessage("Compare SQLite with PostgreSQL for edge architectures.")}
              >
                <div className="chip-icon-box"><Database size={15} /></div>
                <div className="chip-content">
                  <span className="chip-title">SQLite vs PostgreSQL</span>
                  <span className="chip-sub">Storage design tradeoffs</span>
                </div>
              </button>
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, idx) => {
              if (msg.role === 'user') {
                return (
                  <div key={idx} className="message-row user-row">
                    <div className="user-bubble">
                      <div className="message-text">{msg.content}</div>
                    </div>
                  </div>
                );
              }

              if (msg.role === 'error') {
                return (
                  <div key={idx} className="message-row error-row">
                    <div className="error-bubble">
                      <AlertTriangle size={16} className="error-icon" />
                      <div className="message-text">{msg.content}</div>
                    </div>
                  </div>
                );
              }

              // Assistant Reply
              return (
                <div key={idx} className="message-row assistant-row">
                  <div data-testid="assistant-message" className="assistant-card">
                    {/* Header info */}
                    <div className="assistant-card-header">
                      <div className="agent-tag">
                        <Sparkles size={13} className="agent-spark" />
                        <span className="agent-name">Lyftr Assistant</span>
                      </div>
                      
                      {/* Resolution Source Tag */}
                      <div className="source-tag-wrap">
                        <span 
                          data-testid="meta-source" 
                          className={`source-badge ${msg.metadata?.resolution_source === 'LLM_CACHE' ? 'badge-cache' : 'badge-live'}`}
                        >
                          {msg.metadata?.resolution_source === 'LLM_CACHE' ? (
                            <>
                              <Zap size={11} /> LLM_CACHE
                            </>
                          ) : (
                            <>
                              <Activity size={11} /> LIVE_INFERENCE
                            </>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="assistant-text">
                      {msg.content}
                    </div>

                    {/* Rich Metadata Footer */}
                    {msg.metadata && (
                      <div className="assistant-meta-bar">
                        <div className="meta-item">
                          <Cpu size={12} className="meta-icon" />
                          <span className="meta-label">Model:</span>
                          <span data-testid="meta-model" className="meta-val highlight-val">
                            {msg.metadata.model}
                          </span>
                        </div>

                        <div className="meta-item">
                          <Clock size={12} className="meta-icon" />
                          <span className="meta-label">Latency:</span>
                          <span data-testid="meta-latency" className="meta-val">
                            {msg.metadata.latency_ms} ms
                          </span>
                        </div>

                        <div className="meta-item">
                          <Layers size={12} className="meta-icon" />
                          <span className="meta-label">Tokens:</span>
                          <span className="meta-val tokens-val">
                            <span data-testid="meta-input-tokens">{msg.metadata.input_tokens}</span>
                            <span className="tokens-divider">in</span> / 
                            <span data-testid="meta-output-tokens">{msg.metadata.output_tokens}</span>
                            <span className="tokens-divider">out</span>
                          </span>
                        </div>

                        {msg.metadata.key_id && (
                          <div className="meta-item">
                            <CheckCircle2 size={12} className="meta-icon success-icon" />
                            <span className="meta-label">Key:</span>
                            <span className="meta-val key-val">{msg.metadata.key_id}</span>
                          </div>
                        )}

                        {msg.metadata.fallback_attempts > 0 && (
                          <div className="meta-item fallback-alert">
                            <RefreshCw size={12} className="meta-icon warning-icon" />
                            <span className="meta-label">Failovers:</span>
                            <span className="meta-val warning-val">{msg.metadata.fallback_attempts} fallback(s)</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div className="message-row assistant-row">
                <div className="assistant-card loading-card">
                  <div className="loading-dots">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                  <span className="loading-label">Lyftr Gateway processing inference & cache lookup...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Chat Input Dock */}
      <footer className="chat-dock">
        <form onSubmit={handleSend} className="input-container">
          <textarea
            data-testid="chat-input"
            rows="1"
            className="chat-textarea"
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            data-testid="send-button"
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="send-button"
          >
            <Send size={16} />
            <span>Send</span>
          </button>
        </form>
        <div className="dock-hint">
          Persistent SQLite storage • Automatic Key Fallback • Exact Per-Request Token Usage
        </div>
      </footer>
    </div>
  );
}
