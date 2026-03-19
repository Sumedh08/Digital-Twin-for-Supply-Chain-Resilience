import React, { useState, useEffect } from 'react';
import GlobeComponent from './GlobeComponent';
import CBAMCalculator from './CBAMCalculator';
import { LiveETSPrice, VesselTracker, AuthModal, LegalAdvisor, DocParser } from './components';
import BlockchainLedger from './components/BlockchainLedger';
import './components/components.css';
import {
  ShieldAlert,
  MessageSquare, X, Send, Leaf, Calculator, Ship,
  User, LogOut, TrendingUp, Calendar
} from 'lucide-react';

import { API_BASE } from './config';

function App() {
  // View toggle: 'cbam', 'imec', or 'vessels'
  const [activeView, setActiveView] = useState('cbam');

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  // Auth state
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  // Dashboard data
  const [dashboardData, setDashboardData] = useState(null);

  // Simulation State
  const [params, setParams] = useState({
    heatwave_level: 0.0,
    conflict_level: 0.0,
    piracy_level: 0.0,
    suez_blocked: false
  });

  // Chat State
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    { role: 'system', content: 'Hello! I am your CBAM Compliance Advisor. Ask me anything about carbon emissions, EU regulations, or shipping routes.' }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Route comparison data for globe
  const [routeData, setRouteData] = useState(null);

  // Check for existing auth on mount
  useEffect(() => {
    const storedUser = localStorage.getItem('carbonship_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        localStorage.removeItem('carbonship_user');
        localStorage.removeItem('carbonship_token');
      }
    }
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('carbonship_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
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

  const handleChat = async () => {
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: chatInput,
          simulation_context: params.suez_blocked ? "Suez is blocked" : "Normal operations"
        })
      });
      const data = await response.json();
      setChatMessages(prev => [...prev, { role: 'system', content: data.reply }]);
    } catch (error) {
      setChatMessages(prev => [...prev, { role: 'system', content: "Error: Could not reach AI server." }]);
    }
    setChatLoading(false);
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
      console.error("Simulation failed:", error);
    }
    setLoading(false);
  };

  return (
    <div className="w-screen h-screen bg-black relative overflow-hidden">
      {/* TOP BAR */}
      <div className="absolute top-0 left-0 right-0 z-20 p-3 bg-black/80 backdrop-blur-md border-b border-white/10 flex justify-between items-center">
        {/* Logo */}
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

        {/* Center Stats */}
        <div className="hidden md:flex items-center gap-6">
          {dashboardData && (
            <>
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp size={14} className="text-emerald-400" />
                <span className="text-gray-400">ETS:</span>
                <span className="text-white font-semibold">€{dashboardData.ets_price?.current_eur?.toFixed(2)}</span>
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
        </div>

        {/* User Section */}
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

      {/* VIEW TOGGLE */}
      <div className="absolute top-20 left-4 z-10 bg-black/60 backdrop-blur-md rounded-lg border border-white/20 p-1 flex gap-1">
        <button
          onClick={() => setActiveView('cbam')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'cbam'
            ? 'bg-emerald-600 text-white'
            : 'text-gray-400 hover:bg-gray-800'
            }`}
        >
          <Calculator size={16} />
          Calculator
        </button>
        <button
          onClick={() => setActiveView('vessels')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'vessels'
            ? 'bg-blue-600 text-white'
            : 'text-gray-400 hover:bg-gray-800'
            }`}
        >
          <Ship size={16} />
          Vessel Intelligence
        </button>
        <button
          onClick={() => setActiveView('ai')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'ai'
            ? 'bg-purple-600 text-white'
            : 'text-gray-400 hover:bg-gray-800'
            }`}
        >
          <ShieldAlert size={16} />
          AI Tools
        </button>
        <button
          onClick={() => setActiveView('ledger')}
          className={`py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${activeView === 'ledger'
            ? 'bg-amber-600 text-white'
            : 'text-gray-400 hover:bg-gray-800'
            }`}
        >
          ⛓️
          Audit Trail
        </button>
      </div>

      {/* LEFT PANEL */}
      <div className="absolute top-36 left-4 bottom-8 z-10 w-[420px] bg-black/70 backdrop-blur-lg rounded-xl border border-white/10 text-white shadow-2xl overflow-hidden">
        {activeView === 'cbam' ? (
          <CBAMCalculator onRouteSelect={setRouteData} />
        ) : activeView === 'vessels' ? (
          <VesselTracker onVesselSelect={(vessel) => console.log('Selected:', vessel)} />
        ) : activeView === 'ai' ? (
          /* AI TOOLS PANEL - Full Page (Not Popup) */
          <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <ShieldAlert className="text-purple-400" size={24} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">AI Tools</h2>
                <p className="text-xs text-gray-400">Carbon Verification Node: #SEPOLIA-REGISTRY-V1</p>
              </div>
            </div>

            {/* Trade Legal Advisor */}
            <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-white/5 font-semibold text-emerald-300 flex items-center gap-2">
                <ShieldAlert size={18} /> Trade Legal Advisor
              </div>
              <div className="p-4">
                <LegalAdvisor />
              </div>
            </div>

            {/* Smart Document Parser */}
            <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-white/5 font-semibold text-blue-300 flex items-center gap-2">
                <MessageSquare size={18} /> Smart Document Parser
              </div>
              <div className="p-4">
                <DocParser />
              </div>
            </div>
          </div>
        ) : activeView === 'ledger' ? (
          /* COMPLIANCE LEDGER - Full Page */
          <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-500/20 rounded-lg">
                <span className="text-xl">⛓️</span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Compliance Ledger</h2>
                <p className="text-xs text-gray-400">Immutable Audit Trail</p>
              </div>
            </div>

            <BlockchainLedger />
          </div>
        ) : null}
      </div>

      {/* RIGHT PANEL - ETS Price Widget */}
      <div className="absolute top-36 right-4 z-10 w-72">
        <LiveETSPrice />
      </div>

      {/* GLOBE */}
      <GlobeComponent />

      {/* CHATBOT FLOATING UI */}
      {
        !chatOpen && (
          <button
            onClick={() => setChatOpen(true)}
            className="absolute bottom-8 right-8 z-20 p-4 bg-emerald-600 rounded-full shadow-lg hover:bg-emerald-500 transition-all hover:scale-110"
          >
            <MessageSquare size={24} fill="white" />
          </button>
        )
      }

      {
        chatOpen && (
          <div className="absolute bottom-8 right-8 z-20 w-80 h-96 bg-black/90 backdrop-blur-xl rounded-xl border border-white/20 flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-300">
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex justify-between items-center bg-emerald-500/10 rounded-t-xl">
              <div className="flex items-center gap-2 font-bold text-white">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                CBAM Advisor
              </div>
              <button onClick={() => setChatOpen(false)} className="text-gray-400 hover:text-white">
                <X size={18} />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-2 rounded-lg text-sm ${msg.role === 'user' ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-gray-200'}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatLoading && <div className="text-xs text-gray-500 animate-pulse">AI is thinking...</div>}
            </div>

            {/* Input */}
            <div className="p-3 border-t border-white/10 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleChat()}
                placeholder="Ask about CBAM..."
                className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
              <button onClick={handleChat} className="p-2 bg-emerald-600 rounded-lg hover:bg-emerald-500">
                <Send size={16} fill="white" />
              </button>
            </div>
          </div>
        )
      }

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </div>
  );
}

export default App;
