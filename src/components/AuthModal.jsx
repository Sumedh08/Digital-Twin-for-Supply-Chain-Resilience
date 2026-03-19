import React, { useState } from 'react';
import { User, Mail, Lock, Building, Phone, FileText, X, LogIn, UserPlus } from 'lucide-react';

import { API_BASE } from '../config';

/**
 * AuthModal Component
 * Login and Registration modal for user authentication
 */
const AuthModal = ({ isOpen, onClose, onAuthSuccess }) => {
    const [mode, setMode] = useState('login'); // 'login' or 'register'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [formData, setFormData] = useState({
        email: '',
        password: '',
        company_name: '',
        gstin: '',
        phone: ''
    });

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        setError(null);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
            const body = mode === 'login'
                ? { email: formData.email, password: formData.password }
                : formData;

            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Authentication failed');
            }

            // Store token
            localStorage.setItem('carbonship_token', data.access_token);
            localStorage.setItem('carbonship_user', JSON.stringify(data.user));

            if (onAuthSuccess) {
                onAuthSuccess(data.user);
            }
            onClose();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="auth-modal-overlay" onClick={onClose} style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
            <div className="auth-modal" onClick={(e) => e.stopPropagation()} style={{ background: '#111827', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '16px', padding: '24px', width: '100%', maxWidth: '400px', position: 'relative', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
                <button className="close-btn" onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer' }}>
                    <X size={20} />
                </button>

                <div className="auth-header" style={{ marginBottom: '24px' }}>
                    <div className="auth-tabs" style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', padding: '4px', borderRadius: '8px' }}>
                        <button
                            className={`tab ${mode === 'login' ? 'active' : ''}`}
                            onClick={() => setMode('login')}
                            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '8px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: mode === 'login' ? '#10b981' : 'transparent', color: mode === 'login' ? 'white' : '#9ca3af', fontWeight: '500', transition: 'all 0.2s' }}
                        >
                            <LogIn size={16} />
                            Login
                        </button>
                        <button
                            className={`tab ${mode === 'register' ? 'active' : ''}`}
                            onClick={() => setMode('register')}
                            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '8px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: mode === 'register' ? '#10b981' : 'transparent', color: mode === 'register' ? 'white' : '#9ca3af', fontWeight: '500', transition: 'all 0.2s' }}
                        >
                            <UserPlus size={16} />
                            Register
                        </button>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="auth-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {error && (
                        <div className="auth-error" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '12px', borderRadius: '8px', fontSize: '14px' }}>
                            {error}
                        </div>
                    )}

                    <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#d1d5db' }}>
                            <Mail size={16} />
                            Email
                        </label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="you@company.com"
                            required
                            style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '10px 12px', color: 'white', fontSize: '14px', outline: 'none' }}
                        />
                    </div>

                    <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#d1d5db' }}>
                            <Lock size={16} />
                            Password
                        </label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="••••••••"
                            minLength={8}
                            required
                            style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '10px 12px', color: 'white', fontSize: '14px', outline: 'none' }}
                        />
                    </div>

                    {mode === 'register' && (
                        <>
                            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#d1d5db' }}>
                                    <Building size={16} />
                                    Company Name
                                </label>
                                <input
                                    type="text"
                                    name="company_name"
                                    value={formData.company_name}
                                    onChange={handleChange}
                                    placeholder="Tata Steel Limited"
                                    required
                                    style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '10px 12px', color: 'white', fontSize: '14px', outline: 'none' }}
                                />
                            </div>

                            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#d1d5db' }}>
                                    <FileText size={16} />
                                    GSTIN (Optional)
                                </label>
                                <input
                                    type="text"
                                    name="gstin"
                                    value={formData.gstin}
                                    onChange={handleChange}
                                    placeholder="27AAACC1206D1ZM"
                                    style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '10px 12px', color: 'white', fontSize: '14px', outline: 'none' }}
                                />
                            </div>

                            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#d1d5db' }}>
                                    <Phone size={16} />
                                    Phone (Optional)
                                </label>
                                <input
                                    type="tel"
                                    name="phone"
                                    value={formData.phone}
                                    onChange={handleChange}
                                    placeholder="+91 9876543210"
                                    style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '10px 12px', color: 'white', fontSize: '14px', outline: 'none' }}
                                />
                            </div>
                        </>
                    )}

                    <button type="submit" className="submit-btn" disabled={loading} style={{ background: '#10b981', color: 'white', border: 'none', borderRadius: '8px', padding: '12px', fontSize: '16px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '8px', opacity: loading ? 0.7 : 1 }}>
                        {loading ? (
                            <span className="loading-spinner" style={{ width: '20px', height: '20px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                        ) : mode === 'login' ? (
                            <>
                                <LogIn size={16} />
                                Sign In
                            </>
                        ) : (
                            <>
                                <UserPlus size={16} />
                                Create Account
                            </>
                        )}
                    </button>
                </form>

                <div className="auth-footer" style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: '#9ca3af' }}>
                    {mode === 'login' ? (
                        <p>
                            Don't have an account?{' '}
                            <button onClick={() => setMode('register')} style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', fontWeight: '500' }}>Register free</button>
                        </p>
                    ) : (
                        <p>
                            Already registered?{' '}
                            <button onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: '#10b981', cursor: 'pointer', fontWeight: '500' }}>Sign in</button>
                        </p>
                    )}
                    <p className="tier-info" style={{ marginTop: '12px', fontSize: '12px', color: '#6b7280', background: 'rgba(255, 255, 255, 0.05)', padding: '8px', borderRadius: '6px', display: 'inline-block' }}>
                        🎁 Free tier: 5 calculations/month
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AuthModal;
