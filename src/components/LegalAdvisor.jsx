import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Scale, User, Bot } from 'lucide-react';

const LegalAdvisor = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', text: 'Hello! I am your AI Legal Advisor. Ask me anything about EU CBAM regulations, exemptions, or reporting requirements.' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: 'user', text: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const response = await fetch('http://localhost:8000/ai/legal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMsg.text })
            });
            const data = await response.json();

            const botMsg = {
                role: 'assistant',
                text: data.answer,
                citations: data.citations
            };
            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', text: 'Sorry, I encountered an error connecting to the legal database.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur-md rounded-xl border border-gray-700 shadow-xl flex flex-col h-[500px]">
            <div className="p-4 border-b border-gray-700 flex items-center gap-2 bg-gradient-to-r from-blue-900/20 to-transparent rounded-t-xl">
                <Scale className="w-5 h-5 text-purple-400" />
                <h2 className="font-bold text-white">CBAM Legal Advisor</h2>
                <span className="ml-auto text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/30">LLaMA 3.3 70B</span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-purple-600/30 flex items-center justify-center border border-purple-500/50 shrink-0">
                                <Bot className="w-4 h-4 text-purple-300" />
                            </div>
                        )}

                        <div className={`max-w-[80%] rounded-2xl p-3 ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-gray-700/50 text-gray-200 rounded-tl-none border border-gray-600'
                            }`}>
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                            {msg.citations && msg.citations.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-gray-600/50">
                                    <p className="text-xs text-gray-400 font-semibold mb-1">Sources:</p>
                                    <ul className="list-disc list-inside text-xs text-purple-300/80">
                                        {msg.citations.map((cite, i) => <li key={i}>{cite}</li>)}
                                    </ul>
                                </div>
                            )}
                        </div>

                        {msg.role === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-blue-600/30 flex items-center justify-center border border-blue-500/50 shrink-0">
                                <User className="w-4 h-4 text-blue-300" />
                            </div>
                        )}
                    </div>
                ))}
                {loading && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-purple-600/30 flex items-center justify-center border border-purple-500/50">
                            <Bot className="w-4 h-4 text-purple-300" />
                        </div>
                        <div className="bg-gray-700/50 rounded-2xl rounded-tl-none p-4 border border-gray-600 flex items-center gap-2">
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce delay-75"></div>
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce delay-150"></div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSend} className="p-4 border-t border-gray-700 bg-gray-800/30 rounded-b-xl">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about CBAM rules, exemptions, or penalties..."
                        className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </form>
        </div>
    );
};

export default LegalAdvisor;
