import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowUp, BookOpen, Bot, Scale, Sparkles, User, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../config';
import './tradeGPT.css';

const SUGGESTIONS = [
  { icon: Scale, text: 'Explain CBAM Article 6 certificate obligations for Indian steel exporters' },
  { icon: BookOpen, text: 'What are India\'s current export duties on hot-rolled steel coils?' },
  { icon: Scale, text: 'How does WTO Article XX justify CBAM under environmental exceptions?' },
  { icon: BookOpen, text: 'What is the Advance Authorization scheme under India\'s Foreign Trade Policy?' },
];

function VectorRAGPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const adjustTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  };

  const sendMessage = async (text) => {
    const trimmed = (text || input).trim();
    if (!trimmed || loading) return;

    const userMsg = { role: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/ai/legal/vector`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed }),
      });
      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
          citations: data.citations,
          confidence: data.confidence,
          source: data.source,
          retrieved_chunks: data.retrieved_chunks,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Sorry, I could not connect to the TradeGPT backend. Please ensure the server is running.',
          citations: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="tradegpt-shell" style={{ background: '#111827' }}>
      <nav className="tradegpt-topbar" style={{ background: 'rgba(17, 24, 39, 0.8)', borderBottom: '1px solid rgba(239, 68, 68, 0.2)' }}>
        <div className="tradegpt-topbar-left">
          <Link to="/" className="tradegpt-back">
            <ArrowLeft size={14} />
            CarbonShip
          </Link>
          <div className="tradegpt-logo">
            <div className="tradegpt-logo-icon" style={{ background: 'rgba(59, 130, 246, 0.2)', border: '1px solid rgba(59, 130, 246, 0.5)' }}>
              <Bot size={18} color="#60a5fa" />
            </div>
            <div>
              <h1 style={{ color: '#60a5fa' }}>TradeGPT Legal Advisor</h1>
              <p>Powered by chunked vector retrieval</p>
            </div>
          </div>
        </div>
        <div className="tradegpt-badges">
          <span className="tradegpt-badge" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.2)' }}>LLaMA 3.3 70B</span>
          <span className="tradegpt-badge" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.2)' }}>TF-IDF Vector Index</span>
        </div>
      </nav>

      <div className="tradegpt-main">
        {!hasMessages ? (
          <div className="tradegpt-welcome">
            <div className="tradegpt-welcome-icon" style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
              <Bot size={30} color="#60a5fa" />
            </div>
            <h2>TradeGPT Legal Advisor</h2>
            <p>
              Powered by chunked TF-IDF retrieval plus the same answer model used by TradeGPT. This is the comparison path against the full-context mode.
            </p>
            <div className="tradegpt-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  className="tradegpt-suggestion"
                  style={{ border: '1px solid rgba(239, 68, 68, 0.2)', '&:hover': { background: 'rgba(239, 68, 68, 0.05)' } }}
                  onClick={() => sendMessage(s.text)}
                >
                  <span className="tradegpt-suggestion-icon" style={{ color: '#fca5a5' }}>
                    <s.icon size={16} />
                  </span>
                  {s.text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="tradegpt-messages">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`tradegpt-msg ${msg.role === 'user' ? 'tradegpt-msg-user' : ''}`}
              >
                <div
                  className={`tradegpt-avatar ${
                    msg.role === 'user' ? 'tradegpt-avatar-user' : ''
                  }`}
                  style={msg.role !== 'user' ? { background: '#7f1d1d', border: '1px solid #ef4444' } : {}}
                >
                  {msg.role === 'user' ? (
                    <User size={16} color="#93c5fd" />
                  ) : (
                    <AlertTriangle size={16} color="#fca5a5" />
                  )}
                </div>
                <div
                  className={`tradegpt-bubble ${
                    msg.role === 'user' ? 'tradegpt-bubble-user' : 'tradegpt-bubble-bot'
                  }`}
                  style={msg.role !== 'user' ? { border: '1px solid rgba(239, 68, 68, 0.2)' } : {}}
                >
                  {msg.text}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="tradegpt-citations">
                      {msg.citations.map((cite, j) => (
                        <span key={j} className="tradegpt-citation" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                          <BookOpen size={10} />
                          {cite}
                        </span>
                      ))}
                      </div>
                    )}
                  {msg.retrieved_chunks && msg.retrieved_chunks.length > 0 && (
                    <div style={{ marginTop: '10px', display: 'grid', gap: '6px' }}>
                      {msg.retrieved_chunks.map((chunk, index) => (
                        <div key={`${chunk.document}-${chunk.chunk_id}-${index}`} style={{ fontSize: '11px', color: '#bfdbfe', border: '1px solid rgba(59, 130, 246, 0.18)', borderRadius: '8px', padding: '8px 10px', background: 'rgba(30, 41, 59, 0.35)' }}>
                          {chunk.document} chunk {chunk.chunk_id} · score {chunk.score}
                        </div>
                      ))}
                    </div>
                  )}
                  {msg.confidence && msg.role !== 'user' && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: '#fca5a5', padding: '4px 8px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '4px', display: 'inline-block' }}>
                      {msg.confidence}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="tradegpt-msg">
                <div className="tradegpt-avatar" style={{ background: '#7f1d1d', border: '1px solid #ef4444' }}>
                  <AlertTriangle size={16} color="#fca5a5" />
                </div>
                <div className="tradegpt-bubble tradegpt-bubble-bot" style={{ border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <div className="tradegpt-typing">
                    <span className="tradegpt-dot" style={{ background: '#fca5a5' }} />
                    <span className="tradegpt-dot" style={{ background: '#fca5a5' }} />
                    <span className="tradegpt-dot" style={{ background: '#fca5a5' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="tradegpt-input-area" style={{ background: 'rgba(17, 24, 39, 0.8)', borderTop: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <div className="tradegpt-input-box" style={{ background: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <textarea
              ref={textareaRef}
              rows="1"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                adjustTextarea();
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask a legal query regarding EU CBAM regulations..."
            />
            <button
              type="button"
              className="tradegpt-send"
              disabled={!input.trim() || loading}
              onClick={() => sendMessage()}
              style={{ background: '#2563eb' }}
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </div>
      </div>

      <footer className="tradegpt-footer" style={{ borderTop: '1px solid rgba(59, 130, 246, 0.2)' }}>
        Chunked TF-IDF vector retrieval for comparison. Always verify legal regulations independently.
      </footer>
    </div>
  );
}

export default VectorRAGPage;
