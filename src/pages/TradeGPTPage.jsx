import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowUp, BookOpen, Bot, Scale, Sparkles, User } from 'lucide-react';
import { API_BASE } from '../config';
import './tradeGPT.css';

const SUGGESTIONS = [
  { icon: Scale, text: 'Explain CBAM Article 6 certificate obligations for Indian steel exporters' },
  { icon: BookOpen, text: 'What are India\'s current export duties on hot-rolled steel coils?' },
  { icon: Scale, text: 'How does WTO Article XX justify CBAM under environmental exceptions?' },
  { icon: BookOpen, text: 'What is the Advance Authorization scheme under India\'s Foreign Trade Policy?' },
];

function TradeGPTPage() {
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
      const response = await fetch(`${API_BASE}/ai/legal`, {
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
    <div className="tradegpt-shell">
      <nav className="tradegpt-topbar">
        <div className="tradegpt-topbar-left">
          <Link to="/" className="tradegpt-back">
            <ArrowLeft size={14} />
            CarbonShip
          </Link>
          <div className="tradegpt-logo">
            <div className="tradegpt-logo-icon">
              <Sparkles size={18} color="#fff" />
            </div>
            <div>
              <h1>TradeGPT</h1>
              <p>International Trade &amp; Regulatory Intelligence</p>
            </div>
          </div>
        </div>
        <div className="tradegpt-badges">
          <span className="tradegpt-badge">LLaMA 3.3 70B</span>
          <span className="tradegpt-badge tradegpt-badge-green">Full-Context RAG</span>
        </div>
      </nav>

      <div className="tradegpt-main">
        {!hasMessages ? (
          <div className="tradegpt-welcome">
            <div className="tradegpt-welcome-icon">
              <Sparkles size={30} color="#a78bfa" />
            </div>
            <h2>What can I help you with?</h2>
            <p>
              Ask about EU CBAM regulations, India export policies, WTO rules,
              or any international trade compliance question. Powered by
              full-context RAG — no chunking, no lost cross-references.
            </p>
            <div className="tradegpt-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  className="tradegpt-suggestion"
                  onClick={() => sendMessage(s.text)}
                >
                  <span className="tradegpt-suggestion-icon">
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
                    msg.role === 'user' ? 'tradegpt-avatar-user' : 'tradegpt-avatar-bot'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <User size={16} color="#93c5fd" />
                  ) : (
                    <Bot size={16} color="#fff" />
                  )}
                </div>
                <div
                  className={`tradegpt-bubble ${
                    msg.role === 'user' ? 'tradegpt-bubble-user' : 'tradegpt-bubble-bot'
                  }`}
                >
                  {msg.text}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="tradegpt-citations">
                      {msg.citations.map((cite, j) => (
                        <span key={j} className="tradegpt-citation">
                          <BookOpen size={10} />
                          {cite}
                        </span>
                      ))}
                    </div>
                  )}
                  {msg.confidence && msg.role !== 'user' && (
                    <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      <span className="tradegpt-citation">{msg.confidence}</span>
                      {msg.source && <span className="tradegpt-citation">{msg.source}</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="tradegpt-msg">
                <div className="tradegpt-avatar tradegpt-avatar-bot">
                  <Bot size={16} color="#fff" />
                </div>
                <div className="tradegpt-bubble tradegpt-bubble-bot">
                  <div className="tradegpt-typing">
                    <span className="tradegpt-dot" />
                    <span className="tradegpt-dot" />
                    <span className="tradegpt-dot" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="tradegpt-input-area">
          <div className="tradegpt-input-box">
            <textarea
              ref={textareaRef}
              rows="1"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                adjustTextarea();
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask about CBAM, India export rules, WTO regulations…"
            />
            <button
              type="button"
              className="tradegpt-send"
              disabled={!input.trim() || loading}
              onClick={() => sendMessage()}
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </div>
      </div>

      <footer className="tradegpt-footer">
        Vectorless Full-Context RAG — zero chunking, full cross-reference integrity ·{' '}
        Regulatory corpus: India FTP, CBAM Regulation 2023/956, WTO GATT/TBT ·{' '}
        <a href="https://lfenergy.org/" target="_blank" rel="noreferrer">
          Built on LF ecosystem principles
        </a>
      </footer>
    </div>
  );
}

export default TradeGPTPage;
