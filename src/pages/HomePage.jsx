import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import GlobeComponent from '../GlobeComponent';
import CBAMCalculator from '../CBAMCalculator';
import { LiveETSPrice, VesselTracker, AuthModal } from '../components';
import '../components/components.css';
import {
  ArrowUp, BookOpen, Bot, Leaf, Calculator, Ship,
  User, LogOut, TrendingUp, Calendar, Layers3, Sparkles
} from 'lucide-react';

import { API_BASE } from '../config';

const TRADE_SUGGESTIONS = [
  'Explain CBAM Article 6 certificate obligations',
  'India steel export duties under FTP 2023',
  'How does WTO Article XX justify CBAM?',
  'Advance Authorization scheme for steel',
];

function HomePage() {
  const [activeView, setActiveView] = useState('cbam');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [params, setParams] = useState({
    heatwave_level: 0.0,
    conflict_level: 0.0,
    piracy_level: 0.0,
    suez_blocked: false
  });
  const [routeData, setRouteData] = useState(null);

  // TradeGPT state
  const [tradeMessages, setTradeMessages] = useState([]);
  const [tradeInput, setTradeInput] = useState('');
  const [tradeLoading, setTradeLoading] = useState(false);
  const tradeEndRef = useRef(null);
  const tradeInputRef = useRef(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('carbonship_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem('carbonship_user');
        localStorage.removeItem('carbonship_token');
      }
    }
    fetchDashboard();
  }, []);

  useEffect(() => {
    tradeEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [tradeMessages]);

  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('carbonship_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await fetch(`${API_BASE}/dashboard`, { headers });
      const data = await response.json();
      if (data.success) {
        setDashboardData(data.dashboard);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('carbonship_token');
    localStorage.removeItem('carbonship_user');
    setUser(null);
    fetchDashboard();
  };

  const handleAuthSuccess = (userData) => {
    setUser(userData);
    fetchDashboard();
  };

  const runSimulation = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Simulation failed:', error);
    }
    setLoading(false);
  };

  const sendTradeMessage = async (text) => {
    const trimmed = (text || tradeInput).trim();
    if (!trimmed || tradeLoading) return;
    const userMsg = { role: 'user', text: trimmed };
    setTradeMessages((prev) => [...prev, userMsg]);
    setTradeInput('');
    setTradeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/legal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed }),
      });
      const data = await res.json();
      setTradeMessages((prev) => [...prev, { role: 'assistant', text: data.answer, citations: data.citations }]);
    } catch {
      setTradeMessages((prev) => [...prev, { role: 'assistant', text: 'Could not connect to TradeGPT. Is the backend running?' }]);
    } finally {
      setTradeLoading(false);
    }
  };

  const sidebarWidth = activeView === 'tradegpt' ? 'w-[560px]' : 'w-[420px]';

  return (
    <div className="w-screen h-screen bg-black relative overflow-hidden">
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 z-20 p-3 bg-black/80 backdrop-blur-md border-b border-white/10 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/20 rounded-lg">
            <Leaf className="text-emerald-400" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-green-500 bg-clip-text text-transparent leading-tight">
              CarbonShip
            </h1>
            <div className="text-xs text-gray-500">CBAM Compliance Platform</div>
          </div>
        </div>

        <div className="hidden lg:flex items-center gap-3">
          {dashboardData && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp size={14} className="text-emerald-400" />
                <span className="text-gray-400">ETS:</span>
                <span className="text-white font-semibold">EUR {dashboardData.ets_price?.current_eur?.toFixed(2)}</span>
                <span className={`text-xs ${dashboardData.ets_price?.change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {dashboardData.ets_price?.change_24h >= 0 ? '+' : ''}{dashboardData.ets_price?.change_pct?.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Ship size={14} className="text-blue-400" />
                <span className="text-gray-400">Ships:</span>
                <span className="text-white font-semibold">{dashboardData.vessels?.active_count}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar size={14} className="text-orange-400" />
                <span className="text-gray-400">Next Report:</span>
                <span className="text-white font-semibold">{dashboardData.market?.next_reporting_deadline}</span>
              </div>
            </>
          )}
          <Link
            to="/digital-twin/india-steel"
            className="inline-flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:border-cyan-300 hover:bg-cyan-400/15"
          >
            <Layers3 size={16} />
            India Steel Digital Twin
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-sm font-medium text-white">{user.company_name}</div>
                <div className="text-xs text-emerald-400 capitalize">{user.role} plan</div>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-white transition"
                title="Logout"
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setAuthModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 rounded-lg text-white text-sm font-medium hover:bg-emerald-500 transition"
            >
              <User size={16} />
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="absolute top-20 left-4 z-10 bg-black/60 backdrop-blur-md rounded-lg border border-white/20 p-1 flex gap-1">
        <button
          onClick={() => setActiveView('cbam')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'cbam' ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <Calculator size={16} />
          Calculator
        </button>
        <button
          onClick={() => setActiveView('vessels')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'vessels' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <Ship size={16} />
          Vessel Intelligence
        </button>
        <button
          onClick={() => setActiveView('tradegpt')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'tradegpt' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:bg-gray-800'}`}
        >
          <Sparkles size={16} />
          TradeGPT
        </button>
      </div>

      {/* Dark overlay for TradeGPT */}
      {activeView === 'tradegpt' && (
        <div className="absolute inset-0 bg-black/70 z-10 transition-opacity duration-500" />
      )}

      {/* Sidebar / Central panel */}
      <div 
        className={`absolute top-36 bottom-8 ${
          activeView === 'tradegpt' ? 'z-20 left-1/2 -translate-x-1/2 w-[800px] max-w-[95vw]' : 'z-10 left-4 w-[420px]'
        } bg-black/70 backdrop-blur-lg rounded-xl border border-white/10 text-white shadow-2xl overflow-hidden transition-all duration-300`}
      >
        {activeView === 'cbam' ? (
          <CBAMCalculator
            loading={loading}
            results={results}
            params={params}
            setParams={setParams}
            runSimulation={runSimulation}
            onRouteSelect={setRouteData}
          />
        ) : activeView === 'vessels' ? (
          <VesselTracker onVesselSelect={(vessel) => console.log('Selected:', vessel)} />
        ) : activeView === 'tradegpt' ? (
          <div className="h-full flex flex-col">
            {/* TradeGPT Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between shrink-0" style={{ background: 'linear-gradient(90deg, rgba(88,28,135,0.15), transparent)' }}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed, #10b981)' }}>
                  <Sparkles size={18} color="#fff" />
                </div>
                <div>
                  <h2 className="font-bold text-white text-lg leading-tight">TradeGPT</h2>
                  <p className="text-xs text-gray-400">Trade & Regulatory Intelligence</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-1 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/20">LLaMA 3.3 70B</span>
                <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/20">Full-Context RAG</span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {tradeMessages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-4">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.25), rgba(16,185,129,0.25))', border: '1px solid rgba(124,58,237,0.3)' }}>
                    <Sparkles size={26} color="#a78bfa" />
                  </div>
                  <p className="text-gray-400 text-sm max-w-sm leading-relaxed">Ask about CBAM, India export laws, WTO rules, or any trade compliance question.</p>
                  <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
                    {TRADE_SUGGESTIONS.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => sendTradeMessage(s)}
                        className="text-left px-3 py-2.5 rounded-xl text-gray-300 text-sm transition"
                        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                        onMouseEnter={(e) => { e.target.style.background = 'rgba(255,255,255,0.06)'; e.target.style.borderColor = 'rgba(124,58,237,0.25)'; }}
                        onMouseLeave={(e) => { e.target.style.background = 'rgba(255,255,255,0.03)'; e.target.style.borderColor = 'rgba(255,255,255,0.06)'; }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                  <div className="text-center mt-2 flex items-center justify-center gap-4">
                    <Link to="/rag-comparison" className="text-xs text-gray-500 hover:text-purple-300 transition" style={{ textDecoration: 'none' }}>
                      Why vectorless RAG for legal text? →
                    </Link>
                    <Link to="/vector-rag" className="text-xs text-blue-400 hover:text-blue-300 transition" style={{ textDecoration: 'none' }}>
                      Try Vector RAG (Comparison) →
                    </Link>
                  </div>
                </div>
              ) : (
                <>
                  {tradeMessages.map((msg, i) => (
                    <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                        style={msg.role === 'user'
                          ? { background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.3)' }
                          : { background: 'linear-gradient(135deg, #7c3aed, #10b981)' }}
                      >
                        {msg.role === 'user' ? <User size={13} color="#93c5fd" /> : <Bot size={13} color="#fff" />}
                      </div>
                      <div className="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
                        style={msg.role === 'user'
                          ? { background: 'rgba(99,102,241,0.18)', border: '1px solid rgba(99,102,241,0.25)', color: '#e0e7ff', borderTopRightRadius: '4px' }
                          : { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e5e7eb', borderTopLeftRadius: '4px' }}
                      >
                        {msg.text}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-2 pt-2 flex flex-wrap gap-1" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                            {msg.citations.map((c, j) => (
                              <span key={j} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
                                style={{ background: 'rgba(16,185,129,0.12)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,0.18)' }}>
                                <BookOpen size={9} />{c}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {tradeLoading && (
                    <div className="flex gap-3">
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed, #10b981)' }}>
                        <Bot size={13} color="#fff" />
                      </div>
                      <div className="rounded-2xl px-4 py-3 flex items-center gap-1.5" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderTopLeftRadius: '4px' }}>
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" />
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0.15s' }} />
                        <span className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0.3s' }} />
                      </div>
                    </div>
                  )}
                  <div ref={tradeEndRef} />
                </>
              )}
            </div>

            {/* Input bar */}
            <div className="p-3 border-t border-white/10 shrink-0">
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl transition" style={{ border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)' }}>
                <input
                  ref={tradeInputRef}
                  type="text"
                  value={tradeInput}
                  onChange={(e) => setTradeInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendTradeMessage()}
                  placeholder="Ask about CBAM, India export rules, WTO…"
                  className="flex-1 bg-transparent border-none text-white text-sm focus:outline-none"
                />
                <button
                  onClick={() => sendTradeMessage()}
                  disabled={!tradeInput.trim() || tradeLoading}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white disabled:opacity-30 transition"
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #10b981)' }}
                >
                  <ArrowUp size={16} />
                </button>
              </div>
              <div className="mt-1.5 text-center flex items-center justify-center gap-4">
                <Link to="/rag-comparison" className="text-gray-600 hover:text-purple-300 transition" style={{ fontSize: '10px', textDecoration: 'none' }}>
                  Vectorless Full-Context RAG · zero chunking
                </Link>
                <Link to="/vector-rag" className="text-gray-600 hover:text-blue-400 transition" style={{ fontSize: '10px', textDecoration: 'none' }}>
                  Try Vector RAG version
                </Link>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* ETS Price widget */}
      <div className="absolute top-36 right-4 z-10 w-72">
        <LiveETSPrice />
      </div>

      {/* Globe */}
      <GlobeComponent routeData={routeData} />

      {/* Auth modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </div>
  );
}

export default HomePage;
