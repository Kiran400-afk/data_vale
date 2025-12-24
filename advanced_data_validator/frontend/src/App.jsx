import React, { useState } from 'react'
import axios from 'axios'

// API Base URL - uses environment variable for production (Render) or defaults to relative path for local dev
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
axios.defaults.baseURL = API_BASE_URL
import nyxLogo from './assets/nyxlo.png'
import nyxLogoLarge from './assets/nyx_logo_large.png'
import { Upload, Sparkles, LayoutDashboard, Database, MessageSquareText, Download, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,
    LineElement,
    RadialLinearScale,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js'
import { Bar, Radar } from 'react-chartjs-2'

ChartJS.register(
    CategoryScale, LinearScale, BarElement, PointElement,
    LineElement, RadialLinearScale, Title, Tooltip, Legend, Filler
)

// Particle effect component
function Particles() {
    return (
        <div className="particles">
            {[...Array(10)].map((_, i) => (
                <div key={i} className="particle" style={{
                    animationDuration: `${15 + Math.random() * 10}s`,
                    left: `${Math.random() * 100}%`
                }} />
            ))}
        </div>
    )
}

// Glowing orbs background
function GlowOrbs() {
    return (
        <>
            <div className="glow-orb purple" />
            <div className="glow-orb pink" />
        </>
    )
}

export default function App() {
    const [files, setFiles] = useState({ gold: null, growth: null })
    const [loading, setLoading] = useState(false)
    const [session, setSession] = useState(null)
    const [results, setResults] = useState(null)
    const [aiInsight, setAiInsight] = useState(null)
    const [activeTab, setActiveTab] = useState('summary')

    // Authentication state
    const [isAuthenticated, setIsAuthenticated] = useState(false)
    const [authUser, setAuthUser] = useState(null)
    const [authLoading, setAuthLoading] = useState(true)
    const [authStep, setAuthStep] = useState('entry') // 'entry' | 'login'

    // Column mapping state
    const [step, setStep] = useState('welcome') // 'welcome' | 'upload' | 'mapping' | 'results'
    const [columnPreview, setColumnPreview] = useState(null)
    const [columnMappings, setColumnMappings] = useState({})
    const [selectedMetrics, setSelectedMetrics] = useState([]) // Track which columns user mapped

    // Check authentication on app load
    React.useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('nyx_token')
            if (!token) {
                setAuthLoading(false)
                return
            }
            try {
                const res = await axios.get('/auth/verify', {
                    headers: { Authorization: `Bearer ${token}` }
                })
                setIsAuthenticated(true)
                setAuthUser(res.data.username)
            } catch (err) {
                localStorage.removeItem('nyx_token')
                localStorage.removeItem('nyx_user')
            }
            setAuthLoading(false)
        }
        checkAuth()
    }, [])

    // Login handler
    const handleLogin = async (username, password) => {
        try {
            const res = await axios.post('/auth/login', { username, password })
            localStorage.setItem('nyx_token', res.data.access_token)
            localStorage.setItem('nyx_user', res.data.username)
            setIsAuthenticated(true)
            setAuthUser(res.data.username)
            return { success: true }
        } catch (err) {
            return { success: false, error: err.response?.data?.detail || 'Login failed' }
        }
    }

    // Logout handler
    const handleLogout = async () => {
        const token = localStorage.getItem('nyx_token')
        try {
            await axios.post('/auth/logout', {}, {
                headers: { Authorization: `Bearer ${token}` }
            })
        } catch (err) {
            // Ignore logout errors
        }
        localStorage.removeItem('nyx_token')
        localStorage.removeItem('nyx_user')
        setIsAuthenticated(false)
        setAuthUser(null)
        setStep('welcome')
        setSession(null)
        setResults(null)
    }


    // Preview columns for mapping
    const handlePreviewColumns = async () => {
        if (!files.gold || !files.growth) {
            alert('Please select both Gold and Growth files')
            return
        }

        setLoading(true)
        const formData = new FormData()
        formData.append('gold_file', files.gold)
        formData.append('growth_file', files.growth)

        try {
            const res = await axios.post('/preview-columns', formData)
            setColumnPreview(res.data)

            // Initialize mappings from suggestions
            const initialMappings = {}
            res.data.suggested_mappings.forEach(m => {
                initialMappings[m.target] = {
                    gold: m.gold_column,
                    growth: m.growth_column
                }
            })
            setColumnMappings(initialMappings)
            setStep('mapping')
        } catch (err) {
            console.error(err)
            alert("❌ ERROR: " + (err.response?.data?.detail || "Failed to preview columns"))
        } finally {
            setLoading(false)
        }
    }

    // Run validation with custom mappings
    const handleValidateWithMappings = async () => {
        setLoading(true)

        // Convert mappings to backend format - separate Gold and Growth mappings
        const growthMappings = {}
        const goldMappings = {}
        Object.entries(columnMappings).forEach(([target, cols]) => {
            if (cols.growth) {
                growthMappings[target] = cols.growth
            }
            if (cols.gold) {
                goldMappings[target] = cols.gold
            }
        })

        const formData = new FormData()
        formData.append('session_id', columnPreview.session_id)
        formData.append('gold_path', columnPreview.gold_path)
        formData.append('growth_path', columnPreview.growth_path)
        formData.append('growth_mappings', JSON.stringify(growthMappings))
        formData.append('gold_mappings', JSON.stringify(goldMappings))
        formData.append('threshold', 3.0)

        try {
            const res = await axios.post('/validate-with-mappings', formData)
            // Set session with the response data (includes session_id)
            const sessionData = { ...res.data, session_id: columnPreview.session_id }
            setSession(sessionData)

            // Track which columns user selected for display in dashboard
            const metrics = Object.entries(columnMappings)
                .filter(([key, cols]) => cols.growth && cols.gold)
                .map(([key]) => key)
            setSelectedMetrics(metrics)

            // Reset step to show results (no longer 'mapping')
            setStep('results')
            // Fetch full results
            fetchResults(columnPreview.session_id)
        } catch (err) {
            console.error(err)
            alert("❌ ERROR: " + (err.response?.data?.detail || "Validation failed"))
        } finally {
            setLoading(false)
        }
    }

    const handleFileUpload = async () => {
        if (!files.gold || !files.growth) {
            alert('Please select both Gold and Growth files')
            return
        }

        setLoading(true)
        const formData = new FormData()
        formData.append('gold_file', files.gold)
        formData.append('growth_file', files.growth)
        formData.append('threshold', 3.0)

        try {
            const res = await axios.post('/upload', formData)
            setSession(res.data)
            fetchResults(res.data.session_id)
        } catch (err) {
            console.error(err)
            if (!err.response) {
                alert("🔴 BACKEND NOT RUNNING\n\nPlease run: py run_app.py")
            } else {
                alert("❌ ERROR: " + (err.response?.data?.detail || "Upload failed"))
            }
        } finally {
            setLoading(false)
        }
    }

    const fetchResults = async (id) => {
        try {
            const res = await axios.get(`/results/${id}`)
            setResults(res.data)

            // Fetch AI insights in background
            axios.get(`/results/${id}/ai-insight`)
                .then(r => setAiInsight(r.data.summary))
                .catch(() => setAiInsight("AI analysis unavailable"))
        } catch (err) {
            console.error(err)
        }
    }

    const downloadReport = async () => {
        if (!session?.session_id) return
        window.open(`/results/${session.session_id}/export/html`, '_blank')
    }

    return (
        <>
            <Particles />
            <GlowOrbs />
            <div className="container">
                {/* Show loading while checking auth */}
                {authLoading ? (
                    <div className="glass-card animate-in" style={{ padding: '100px', textAlign: 'center' }}>
                        <Loader2 className="spin" size={48} style={{ color: '#667eea' }} />
                        <p style={{ marginTop: '20px', color: 'var(--text-sub)' }}>Loading...</p>
                    </div>
                ) : !isAuthenticated && authStep === 'entry' ? (
                    <EntryPage onGoToLogin={() => setAuthStep('login')} />
                ) : !isAuthenticated && authStep === 'login' ? (
                    <LoginPage onLogin={handleLogin} onBack={() => setAuthStep('entry')} />
                ) : step === 'welcome' ? (
                    <WelcomePage onGetStarted={() => setStep('upload')} onLogout={handleLogout} user={authUser} />
                ) : step === 'upload' && !session ? (
                    <LandingPage
                        files={files}
                        setFiles={setFiles}
                        onSubmit={handleFileUpload}
                        onPreview={handlePreviewColumns}
                        loading={loading}
                        onLogout={handleLogout}
                        user={authUser}
                    />
                ) : step === 'mapping' ? (
                    <ColumnMappingPage
                        columnPreview={columnPreview}
                        columnMappings={columnMappings}
                        setColumnMappings={setColumnMappings}
                        onValidate={handleValidateWithMappings}
                        onBack={() => setStep('upload')}
                        loading={loading}
                    />
                ) : !results ? (
                    <div className="glass-card animate-in" style={{ padding: '100px', textAlign: 'center' }}>
                        <div className="loading-spinner" style={{ margin: '0 auto 28px' }}></div>
                        <p className="gradient-text" style={{ fontSize: '1.5rem', fontWeight: 800 }}>Analyzing Your Data...</p>
                        <p style={{ color: 'var(--text-sub)', marginTop: '12px' }}>Running comprehensive validation across all segments</p>
                    </div>
                ) : (
                    <>
                        <header style={{ marginBottom: '40px' }} className="animate-in">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                    <img
                                        src={nyxLogo}
                                        alt="NYX"
                                        style={{
                                            height: '50px',
                                            borderRadius: '8px',
                                            boxShadow: '0 8px 30px rgba(102, 126, 234, 0.3)'
                                        }}
                                    />
                                    <div>
                                        <h1 style={{ fontSize: '1.75rem', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: '4px' }}>
                                            <span className="gradient-text">Validator</span>
                                        </h1>
                                        <p style={{ color: 'var(--text-sub)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                                            <Sparkles size={14} style={{ color: '#667eea' }} />
                                            Validation Complete
                                        </p>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button className="btn-secondary" onClick={() => { setSession(null); setResults(null); setAiInsight(null); setStep('upload'); setColumnPreview(null); setColumnMappings({}); setSelectedMetrics([]); }}>
                                        ← Back
                                    </button>
                                    <button className="btn-primary" onClick={downloadReport}>
                                        <Download size={18} /> Export Report
                                    </button>
                                    <button className="btn-primary" onClick={() => { setSession(null); setResults(null); setAiInsight(null); setStep('upload'); setColumnPreview(null); setColumnMappings({}); setSelectedMetrics([]); }}>
                                        <Upload size={18} /> New Validation
                                    </button>
                                </div>
                            </div>
                        </header>
                        <main className="animate-in" style={{ animationDelay: '0.15s' }}>
                            <Dashboard
                                session={session}
                                results={results}
                                aiInsight={aiInsight}
                                activeTab={activeTab}
                                setActiveTab={setActiveTab}
                                selectedMetrics={selectedMetrics}
                            />
                        </main>
                    </>
                )}
            </div>
        </>
    )
}

// Entry Page Component (before login)
function EntryPage({ onGoToLogin }) {
    return (
        <div className="animate-in welcome-page" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '40px 20px',
            position: 'relative',
            overflow: 'hidden',
            background: 'linear-gradient(180deg, #0a0a1a 0%, #1a1030 50%, #0d0d20 100%)'
        }}>
            {/* Starfield Background */}
            <div className="starfield">
                {[...Array(50)].map((_, i) => (
                    <div
                        key={i}
                        className="star"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 3}s`,
                            animationDuration: `${1.5 + Math.random() * 2}s`,
                            width: `${1 + Math.random() * 2}px`,
                            height: `${1 + Math.random() * 2}px`
                        }}
                    />
                ))}
            </div>

            {/* Glowing stars */}
            <div className="glow-star" style={{ top: '15%', left: '10%', animationDelay: '0s' }}></div>
            <div className="glow-star" style={{ top: '25%', right: '15%', animationDelay: '1s' }}></div>
            <div className="glow-star" style={{ bottom: '30%', left: '20%', animationDelay: '2s' }}></div>
            <div className="glow-star" style={{ bottom: '20%', right: '25%', animationDelay: '0.5s' }}></div>

            {/* Large NYX Logo */}
            <img
                src={nyxLogoLarge}
                alt="NYX"
                style={{
                    maxWidth: '400px',
                    width: '80%',
                    marginBottom: '40px',
                    filter: 'drop-shadow(0 20px 60px rgba(102, 126, 234, 0.4))'
                }}
            />

            {/* Title */}
            <h1 style={{
                fontSize: 'clamp(2.5rem, 6vw, 4rem)',
                fontWeight: 900,
                marginBottom: '16px',
                letterSpacing: '-0.03em'
            }}>
                <span className="gradient-text">NYX Data Validator</span>
            </h1>

            {/* Subtitle */}
            <p style={{
                color: 'var(--text-sub)',
                fontSize: 'clamp(1rem, 2vw, 1.25rem)',
                maxWidth: '600px',
                marginBottom: '48px',
                lineHeight: 1.7
            }}>
                Enterprise-grade data validation powered by AI.
                Compare your Growth tables against Gold standards with precision, speed, and intelligent insights.
            </p>

            {/* Login Button */}
            <button
                className="btn-primary btn-get-started"
                onClick={onGoToLogin}
                style={{
                    fontSize: '1.25rem',
                    padding: '20px 56px',
                    borderRadius: '16px',
                    fontWeight: 700
                }}
            >
                <Sparkles size={24} /> Login
            </button>

            {/* Feature badges */}
            <div style={{
                display: 'flex',
                gap: '16px',
                marginTop: '60px',
                flexWrap: 'wrap',
                justifyContent: 'center'
            }}>
                <div className="feature-badge">
                    <Database size={18} /> Smart Column Mapping
                </div>
                <div className="feature-badge">
                    <Sparkles size={18} /> AI-Powered Analysis
                </div>
                <div className="feature-badge">
                    <CheckCircle size={18} /> Multi-Format Support
                </div>
            </div>
        </div>
    )
}

// Login Page Component
function LoginPage({ onLogin, onBack }) {
    const [username, setUsername] = React.useState('')
    const [password, setPassword] = React.useState('')
    const [error, setError] = React.useState('')
    const [loading, setLoading] = React.useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        const result = await onLogin(username, password)

        if (!result.success) {
            setError(result.error)
        }
        setLoading(false)
    }

    return (
        <div className="animate-in welcome-page" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '40px 20px',
            position: 'relative',
            overflow: 'hidden',
            background: 'linear-gradient(180deg, #0a0a1a 0%, #1a1030 50%, #0d0d20 100%)'
        }}>
            {/* Starfield Background */}
            <div className="starfield">
                {[...Array(50)].map((_, i) => (
                    <div
                        key={i}
                        className="star"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 3}s`,
                            animationDuration: `${1.5 + Math.random() * 2}s`,
                            width: `${1 + Math.random() * 2}px`,
                            height: `${1 + Math.random() * 2}px`
                        }}
                    />
                ))}
            </div>

            {/* Glowing stars */}
            <div className="glow-star" style={{ top: '15%', left: '10%', animationDelay: '0s' }}></div>
            <div className="glow-star" style={{ top: '25%', right: '15%', animationDelay: '1s' }}></div>
            <div className="glow-star" style={{ bottom: '30%', left: '20%', animationDelay: '2s' }}></div>
            <div className="glow-star" style={{ bottom: '20%', right: '25%', animationDelay: '0.5s' }}></div>

            {/* NYX Logo */}
            <img
                src={nyxLogoLarge}
                alt="NYX"
                style={{
                    maxWidth: '200px',
                    width: '50%',
                    marginBottom: '30px',
                    filter: 'drop-shadow(0 20px 60px rgba(102, 126, 234, 0.4))'
                }}
            />

            {/* Login Card */}
            <div className="glass-card" style={{
                padding: '40px',
                width: '100%',
                maxWidth: '400px',
                borderRadius: '24px'
            }}>
                <h2 style={{
                    marginBottom: '8px',
                    fontSize: '1.75rem',
                    fontWeight: 800
                }}>
                    <span className="gradient-text">Welcome Back</span>
                </h2>
                <p style={{
                    color: 'var(--text-sub)',
                    marginBottom: '32px',
                    fontSize: '0.95rem'
                }}>
                    Sign in to access NYX Data Validator
                </p>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '20px', textAlign: 'left' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '8px',
                            color: 'var(--text-sub)',
                            fontSize: '0.9rem',
                            fontWeight: 600
                        }}>
                            Username
                        </label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Enter your username"
                            required
                            style={{
                                width: '100%',
                                padding: '14px 16px',
                                borderRadius: '12px',
                                border: '1px solid rgba(255,255,255,0.15)',
                                background: 'rgba(255,255,255,0.05)',
                                color: 'var(--text-main)',
                                fontSize: '1rem',
                                outline: 'none',
                                transition: 'border-color 0.3s ease'
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: '24px', textAlign: 'left' }}>
                        <label style={{
                            display: 'block',
                            marginBottom: '8px',
                            color: 'var(--text-sub)',
                            fontSize: '0.9rem',
                            fontWeight: 600
                        }}>
                            Password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            required
                            style={{
                                width: '100%',
                                padding: '14px 16px',
                                borderRadius: '12px',
                                border: '1px solid rgba(255,255,255,0.15)',
                                background: 'rgba(255,255,255,0.05)',
                                color: 'var(--text-main)',
                                fontSize: '1rem',
                                outline: 'none',
                                transition: 'border-color 0.3s ease'
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            padding: '12px 16px',
                            borderRadius: '10px',
                            background: 'rgba(239, 68, 68, 0.15)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            color: '#f87171',
                            marginBottom: '20px',
                            fontSize: '0.9rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <XCircle size={18} /> {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn-primary btn-get-started"
                        disabled={loading}
                        style={{
                            width: '100%',
                            padding: '16px',
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            borderRadius: '14px'
                        }}
                    >
                        {loading ? (
                            <><Loader2 className="spin" size={20} /> Signing in...</>
                        ) : (
                            <><Sparkles size={20} /> Sign In</>
                        )}
                    </button>
                </form>
            </div>
        </div>
    )
}

// Welcome Landing Page with NYX Logo
function WelcomePage({ onGetStarted, onLogout, user }) {
    return (
        <div className="animate-in welcome-page" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '40px 20px',
            position: 'relative',
            overflow: 'hidden',
            background: 'linear-gradient(180deg, #0a0a1a 0%, #1a1030 50%, #0d0d20 100%)'
        }}>
            {/* Starfield Background */}
            <div className="starfield">
                {[...Array(50)].map((_, i) => (
                    <div
                        key={i}
                        className="star"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 3}s`,
                            animationDuration: `${1.5 + Math.random() * 2}s`,
                            width: `${1 + Math.random() * 2}px`,
                            height: `${1 + Math.random() * 2}px`
                        }}
                    />
                ))}
            </div>

            {/* Large Glowing Stars */}
            <div className="glow-star" style={{ top: '15%', left: '10%', animationDelay: '0s' }}></div>
            <div className="glow-star" style={{ top: '25%', right: '15%', animationDelay: '1s' }}></div>
            <div className="glow-star" style={{ bottom: '30%', left: '20%', animationDelay: '2s' }}></div>
            <div className="glow-star" style={{ bottom: '20%', right: '25%', animationDelay: '0.5s' }}></div>
            <div className="glow-star" style={{ top: '60%', left: '5%', animationDelay: '1.5s' }}></div>
            <div className="glow-star" style={{ top: '40%', right: '8%', animationDelay: '2.5s' }}></div>

            {/* Large NYX Logo */}
            <img
                src={nyxLogoLarge}
                alt="NYX"
                style={{
                    maxWidth: '400px',
                    width: '80%',
                    marginBottom: '40px',
                    filter: 'drop-shadow(0 20px 60px rgba(102, 126, 234, 0.4))'
                }}
            />

            {/* Title */}
            <h1 style={{
                fontSize: 'clamp(2.5rem, 6vw, 4rem)',
                fontWeight: 900,
                marginBottom: '16px',
                letterSpacing: '-0.03em'
            }}>
                <span className="gradient-text">NYX Data Validator</span>
            </h1>

            {/* Subtitle */}
            <p style={{
                color: 'var(--text-sub)',
                fontSize: 'clamp(1rem, 2vw, 1.25rem)',
                maxWidth: '600px',
                marginBottom: '48px',
                lineHeight: 1.7
            }}>
                Enterprise-grade data validation powered by AI.
                Compare your Growth tables against Gold standards with precision, speed, and intelligent insights.
            </p>

            {/* Get Started Button */}
            <button
                className="btn-primary btn-get-started"
                onClick={onGetStarted}
                style={{
                    fontSize: '1.25rem',
                    padding: '20px 56px',
                    borderRadius: '16px',
                    fontWeight: 700
                }}
            >
                <Sparkles size={24} /> Get Started
            </button>

            {/* User info and Logout */}
            {user && (
                <div style={{
                    marginTop: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px'
                }}>
                    <span style={{ color: 'var(--text-sub)', fontSize: '0.95rem' }}>
                        Logged in as <strong style={{ color: 'var(--text-main)' }}>{user}</strong>
                    </span>
                    <button
                        onClick={onLogout}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '8px',
                            border: '1px solid rgba(239, 68, 68, 0.5)',
                            background: 'rgba(239, 68, 68, 0.1)',
                            color: '#f87171',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease'
                        }}
                    >
                        Logout
                    </button>
                </div>
            )}

            {/* Feature badges */}
            <div style={{
                display: 'flex',
                gap: '16px',
                marginTop: '40px',
                flexWrap: 'wrap',
                justifyContent: 'center'
            }}>
                <div className="feature-badge">
                    <Database size={18} /> Smart Column Mapping
                </div>
                <div className="feature-badge">
                    <Sparkles size={18} /> AI-Powered Analysis
                </div>
                <div className="feature-badge">
                    <CheckCircle size={18} /> Multi-Format Support
                </div>
            </div>
        </div>
    )
}

function LandingPage({ files, setFiles, onSubmit, onPreview, loading, onLogout, user }) {
    return (
        <div className="animate-in">
            {/* Hero Section */}
            <section className="hero-section">
                {/* Animated background elements */}
                <div className="floating-rings">
                    <div className="ring"></div>
                    <div className="ring"></div>
                    <div className="ring"></div>
                </div>

                {/* Sparkles */}
                <div className="sparkle"></div>
                <div className="sparkle"></div>
                <div className="sparkle"></div>
                <div className="sparkle"></div>
                <div className="sparkle"></div>
                <div className="sparkle"></div>

                {/* Geometric shapes */}
                <div className="geo-shape triangle"></div>
                <div className="geo-shape square"></div>
                <div className="geo-shape circle"></div>
                <div className="geo-shape diamond"></div>

                <img
                    src={nyxLogo}
                    alt="NYX"
                    className="hero-logo"
                    style={{
                        height: '140px',
                        marginBottom: '24px',
                        borderRadius: '16px',
                        position: 'relative',
                        zIndex: 2
                    }}
                />
                <h1 className="hero-title" style={{ fontSize: '2rem', marginTop: '16px' }}>
                    <span className="gradient-text">Data Validator</span>
                </h1>
                <p className="hero-subtitle">
                    Enterprise-grade data validation powered by AI. Compare your Growth tables against
                    Gold standards with precision, speed, and intelligent insights.
                </p>
                <div className="hero-features">
                    <div className="feature-badge">
                        <Database size={18} />
                        11 Validation Segments
                    </div>
                    <div className="feature-badge">
                        <Sparkles size={18} />
                        AI-Powered Analysis
                    </div>
                    <div className="feature-badge">
                        <CheckCircle size={18} />
                        2% Threshold Matching
                    </div>
                </div>
            </section>

            {/* Upload Card */}
            <div className="glass-card" style={{ padding: '56px', maxWidth: '900px', margin: '0 auto' }}>
                <div style={{ textAlign: 'center', marginBottom: '48px' }}>
                    <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '16px' }}>
                        <span className="gradient-text">Start Validation</span>
                    </h2>
                    <p style={{ color: 'var(--text-sub)', maxWidth: '500px', margin: '0 auto', lineHeight: 1.7 }}>
                        Upload your Gold (source of truth) and Growth (to validate) files.
                        Supports CSV, XLSX, and XLS formats.
                    </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px', marginBottom: '40px' }}>
                    <FileDropZone
                        label="Gold File"
                        sublabel="Source of Truth"
                        file={files.gold}
                        onChange={(e) => setFiles({ ...files, gold: e.target.files[0] })}
                        icon={<Database size={32} style={{ color: '#667eea', marginBottom: '16px' }} />}
                    />
                    <FileDropZone
                        label="Growth File"
                        sublabel="To Validate"
                        file={files.growth}
                        onChange={(e) => setFiles({ ...files, growth: e.target.files[0] })}
                        icon={<Upload size={32} style={{ color: '#a855f7', marginBottom: '16px' }} />}
                    />
                </div>

                <div style={{ textAlign: 'center', display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button
                        className="btn-secondary"
                        onClick={onPreview}
                        disabled={loading || !files.gold || !files.growth}
                        style={{ fontSize: '1.1rem', padding: '20px 36px' }}
                    >
                        {loading ? (
                            <><Loader2 size={20} className="animate-spin" /> Fetching Columns...</>
                        ) : (
                            <><Database size={20} /> Fetch Columns & Map</>
                        )}
                    </button>
                    <button
                        className="btn-primary"
                        onClick={onSubmit}
                        disabled={loading || !files.gold || !files.growth}
                        style={{ fontSize: '1.1rem', padding: '20px 36px' }}
                    >
                        {loading ? (
                            <><Loader2 size={20} className="animate-spin" /> Validating...</>
                        ) : (
                            <><Sparkles size={20} /> Quick Validate</>
                        )}
                    </button>
                </div>
            </div>

            {/* Stats Section */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '24px',
                marginTop: '60px',
                maxWidth: '900px',
                margin: '60px auto 0'
            }}>
                {[
                    { number: '11', label: 'Segments' },
                    { number: '2%', label: 'Threshold' },
                    { number: '20+', label: 'Mappings' },
                    { number: 'AI', label: 'Powered' }
                ].map((stat, i) => (
                    <div key={i} className="metric-card" style={{ textAlign: 'center', animationDelay: `${0.1 * i}s` }}>
                        <div className="stat-number gradient-text">{stat.number}</div>
                        <div className="stat-label">{stat.label}</div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// Column Mapping Page Component
function ColumnMappingPage({ columnPreview, columnMappings, setColumnMappings, onValidate, onBack, loading }) {
    // DYNAMIC: Generate target columns from the suggested mappings
    const targetColumns = React.useMemo(() => {
        if (!columnPreview?.suggested_mappings) return []

        // Required columns are: cost, impressions, clicks (if present)
        const requiredKeys = ['cost', 'impressions', 'clicks']

        return columnPreview.suggested_mappings.map(m => ({
            key: m.target,
            label: m.target.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            required: requiredKeys.includes(m.target.toLowerCase()),
            autoMatched: m.auto_matched
        }))
    }, [columnPreview])

    const updateMapping = (target, source, colName) => {
        setColumnMappings(prev => ({
            ...prev,
            [target]: { ...prev[target], [source]: colName }
        }))
    }

    const requiredMapped = targetColumns
        .filter(c => c.required)
        .every(c => columnMappings[c.key]?.growth && columnMappings[c.key]?.gold)

    if (!columnPreview) return null

    const selectStyle = {
        width: '100%',
        padding: '10px 12px',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.1)',
        background: 'rgba(0,0,0,0.3)',
        color: 'var(--text-main)',
        fontSize: '0.85rem'
    }

    return (
        <div className="animate-in glass-card" style={{ padding: '40px' }}>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                <h2 className="gradient-text" style={{ fontSize: '2rem', fontWeight: 900, marginBottom: '8px' }}>
                    Column Mapping
                </h2>
                <p style={{ color: 'var(--text-sub)' }}>
                    Map columns from both files to validate the correct data
                </p>
            </div>

            <div style={{ marginBottom: '24px', padding: '16px', background: 'rgba(102, 126, 234, 0.1)', borderRadius: '12px', border: '1px solid rgba(102, 126, 234, 0.2)' }}>
                <p style={{ color: 'var(--text-sub)', fontSize: '0.9rem' }}>
                    <strong style={{ color: '#10b981' }}>✓ Required:</strong> Cost, Impressions, Clicks (map from both files) &nbsp;|&nbsp;
                    <strong style={{ color: '#667eea' }}>◐ Optional:</strong> Reach, Purchases, Conv Value, Campaign, Date, etc.
                </p>
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table className="data-table" style={{ width: '100%' }}>
                    <thead>
                        <tr>
                            <th style={{ width: '15%' }}>Target</th>
                            <th style={{ width: '22%', background: 'rgba(16, 185, 129, 0.2)' }}>Gold File Column</th>
                            <th style={{ width: '18%', background: 'rgba(16, 185, 129, 0.1)' }}>Gold Sample</th>
                            <th style={{ width: '22%', background: 'rgba(99, 102, 241, 0.2)' }}>Growth File Column</th>
                            <th style={{ width: '18%', background: 'rgba(99, 102, 241, 0.1)' }}>Growth Sample</th>
                        </tr>
                    </thead>
                    <tbody>
                        {targetColumns.map(col => {
                            const goldMapping = columnMappings[col.key]?.gold
                            const growthMapping = columnMappings[col.key]?.growth
                            const goldCol = columnPreview.gold_columns.find(c => c.name === goldMapping)
                            const growthCol = columnPreview.growth_columns.find(c => c.name === growthMapping)

                            return (
                                <tr key={col.key}>
                                    <td style={{ fontWeight: 600 }}>
                                        {col.label}
                                        {col.required && <span style={{ color: '#10b981', marginLeft: '4px' }}>*</span>}
                                    </td>
                                    {/* Gold File Column */}
                                    <td style={{ background: 'rgba(16, 185, 129, 0.05)' }}>
                                        <select
                                            value={goldMapping || ''}
                                            onChange={(e) => updateMapping(col.key, 'gold', e.target.value)}
                                            style={selectStyle}
                                        >
                                            <option value="">-- Select --</option>
                                            {columnPreview.gold_columns.map(gc => (
                                                <option key={gc.name} value={gc.name}>{gc.name}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td style={{ color: 'var(--text-sub)', fontSize: '0.8rem', background: 'rgba(16, 185, 129, 0.02)' }}>
                                        {goldCol ? goldCol.sample.slice(0, 2).join(', ') : '-'}
                                    </td>
                                    {/* Growth File Column */}
                                    <td style={{ background: 'rgba(99, 102, 241, 0.05)' }}>
                                        <select
                                            value={growthMapping || ''}
                                            onChange={(e) => updateMapping(col.key, 'growth', e.target.value)}
                                            style={selectStyle}
                                        >
                                            <option value="">-- Select --</option>
                                            {columnPreview.growth_columns.map(gc => (
                                                <option key={gc.name} value={gc.name}>{gc.name}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td style={{ color: 'var(--text-sub)', fontSize: '0.8rem', background: 'rgba(99, 102, 241, 0.02)' }}>
                                        {growthCol ? growthCol.sample.slice(0, 2).join(', ') : '-'}
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '32px', flexWrap: 'wrap', gap: '16px' }}>
                <button className="btn-secondary" onClick={onBack} style={{ padding: '14px 32px' }}>
                    ← Back to Upload
                </button>
                <button
                    className="btn-primary"
                    onClick={onValidate}
                    disabled={loading || !requiredMapped}
                    style={{ padding: '14px 32px' }}
                >
                    {loading ? (
                        <><Loader2 size={18} className="animate-spin" /> Validating...</>
                    ) : (
                        <><Sparkles size={18} /> Run Validation →</>
                    )}
                </button>
            </div>

            {!requiredMapped && (
                <p style={{ color: '#f59e0b', textAlign: 'center', marginTop: '16px', fontSize: '0.9rem' }}>
                    ⚠️ Please map all required columns (*) from BOTH files
                </p>
            )}
        </div>
    )
}

function FileDropZone({ label, sublabel, file, onChange, icon }) {
    const inputRef = React.useRef(null);

    const handleClick = (e) => {
        // Prevent double triggering
        e.stopPropagation();
        inputRef.current?.click();
    };

    return (
        <div
            className={`file-drop ${file ? 'has-file' : ''}`}
            onClick={handleClick}
            style={{ cursor: 'pointer', position: 'relative' }}
        >
            {icon}
            <p style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '1rem', marginBottom: '4px' }}>
                {label}
            </p>
            {sublabel && (
                <p style={{ color: 'var(--text-sub)', fontSize: '0.875rem', marginBottom: '20px' }}>
                    {sublabel}
                </p>
            )}
            <input
                ref={inputRef}
                type="file"
                onChange={onChange}
                accept=".csv,.xlsx,.xls"
                style={{ display: 'none' }}
            />
            {file ? (
                <p style={{ color: '#10b981', fontWeight: 600, fontSize: '0.875rem' }}>
                    ✓ {file.name}
                </p>
            ) : (
                <p style={{ color: 'var(--text-sub)', fontSize: '0.8rem', marginTop: '8px' }}>
                    Click to browse files
                </p>
            )}
        </div>
    )
}

function Dashboard({ session, results, aiInsight, activeTab, setActiveTab, selectedMetrics }) {
    return (
        <div>
            <div style={{ display: 'flex', gap: '12px', marginBottom: '32px' }}>
                <button className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`} onClick={() => setActiveTab('summary')}>
                    <LayoutDashboard size={18} /> Overview
                </button>
                <button className={`tab-btn ${activeTab === 'tables' ? 'active' : ''}`} onClick={() => setActiveTab('tables')}>
                    <Database size={18} /> Deep Dive
                </button>
                <button className={`tab-btn ${activeTab === 'ai' ? 'active' : ''}`} onClick={() => setActiveTab('ai')}>
                    <MessageSquareText size={18} /> AI Assistant
                </button>
            </div>

            {activeTab === 'summary' && <SummaryTab session={session} />}
            {activeTab === 'tables' && <TablesTab results={results} selectedMetrics={selectedMetrics} />}
            {activeTab === 'ai' && <AITab aiInsight={aiInsight} sessionId={session?.session_id} />}
        </div>
    )
}

function SummaryTab({ session }) {
    const summary = session?.summary || {}
    const details = summary?.details || []

    const chartData = {
        labels: details.map(d => d.type.replace(/_/g, ' ')),
        datasets: [{
            label: 'Match Rate (%)',
            data: details.map(d => d.percent),
            backgroundColor: details.map(d =>
                d.percent > 95 ? 'rgba(16, 185, 129, 0.7)' :
                    d.percent > 80 ? 'rgba(251, 191, 36, 0.7)' :
                        'rgba(239, 68, 68, 0.7)'
            ),
            borderRadius: 8,
            borderWidth: 0
        }]
    }

    return (
        <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginBottom: '32px' }}>
                <div className="metric-card">
                    <p style={{ color: 'var(--text-sub)', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px' }}>
                        Overall Match Rate
                    </p>
                    <p className="gradient-text" style={{ fontSize: '3rem', fontWeight: 900 }}>
                        {summary?.overall_match_rate?.toFixed(1) || 0}%
                    </p>
                </div>
                <div className="metric-card">
                    <p style={{ color: 'var(--text-sub)', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px' }}>
                        Segments Passing
                    </p>
                    <p className="gradient-text" style={{ fontSize: '3rem', fontWeight: 900 }}>
                        {summary?.passing_segments || 0}/{summary?.total_segments || 0}
                    </p>
                </div>
                <div className="metric-card">
                    <p style={{ color: 'var(--text-sub)', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px' }}>
                        Threshold
                    </p>
                    <p className="gradient-text" style={{ fontSize: '3rem', fontWeight: 900 }}>
                        ±3%
                    </p>
                </div>
            </div>

            <div className="glass-card" style={{ padding: '24px' }}>
                <h3 style={{ marginBottom: '24px', fontWeight: 700 }}>Segment Performance</h3>
                <div style={{ height: '350px' }}>
                    <Bar
                        data={chartData}
                        options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    max: 100,
                                    grid: { color: 'rgba(255,255,255,0.05)' },
                                    ticks: { color: '#94a3b8' }
                                },
                                x: {
                                    grid: { display: false },
                                    ticks: { color: '#94a3b8' }
                                }
                            }
                        }}
                    />
                </div>
            </div>
        </div>
    )
}

function TablesTab({ results, selectedMetrics }) {
    const segments = [
        { key: 'overall', title: 'Overall Totals', isOverall: true },
        { key: 'by_date', title: 'By Date' },
        { key: 'by_campaign', title: 'By Campaign' },
        { key: 'by_platform', title: 'By Platform' },
        { key: 'by_placement', title: 'By Placement' },
        { key: 'by_device', title: 'By Device' },
        { key: 'by_gender', title: 'By Gender' },
        { key: 'by_age', title: 'By Age' },
        { key: 'by_camp_date', title: 'By Campaign + Date' },
        { key: 'by_camp_gender', title: 'By Campaign + Gender' },
        { key: 'by_date_gender_age', title: 'By Date + Gender + Age' }
    ]

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
            {segments.map(seg => {
                const data = results?.results?.[seg.key] || []
                if (!data.length) return null

                return (
                    <div key={seg.key} className="glass-card" style={{ padding: '24px', overflow: 'hidden' }}>
                        <h3 style={{ marginBottom: '16px', fontWeight: 700 }}>{seg.title}</h3>
                        <div style={{ overflowX: 'auto' }}>
                            {seg.isOverall ? (
                                <OverallTable data={data} selectedMetrics={selectedMetrics} />
                            ) : (
                                <SegmentTable data={data} selectedMetrics={selectedMetrics} />
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

function OverallTable({ data, selectedMetrics }) {
    // Filter data to only show selected metrics (or all if none selected - Quick Validate)
    const metricMapping = {
        'cost': 'cost',
        'impressions': 'impressions',
        'clicks': 'clicks',
        'reach': 'reach',
        'purchases': 'purchases',
        'conversion_value': 'conversion_value'
    }

    const filteredData = data.filter(row => {
        if (!selectedMetrics || selectedMetrics.length === 0) return true // Show all for Quick Validate
        const metricKey = Object.keys(metricMapping).find(k =>
            row.metric?.toLowerCase().includes(k)
        )
        return metricKey ? selectedMetrics.includes(metricKey) : false
    })

    if (!filteredData.length) return <p style={{ color: 'var(--text-sub)' }}>No data for selected metrics</p>

    return (
        <table className="data-table">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Growth Value</th>
                    <th>Gold Value</th>
                    <th>Difference</th>
                    <th>Diff %</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {filteredData.map((row, i) => (
                    <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{row.metric}</td>
                        <td>{row.csv?.toLocaleString() ?? '-'}</td>
                        <td>{row.fabric?.toLocaleString() ?? '-'}</td>
                        <td>{row.diff?.toLocaleString() ?? '-'}</td>
                        <td>{row.diff_pct != null ? `${row.diff_pct.toFixed(2)}%` : '-'}</td>
                        <td className={row.match ? 'status-pass' : 'status-fail'}>
                            {row.match ? <><CheckCircle size={14} /> PASS</> : <><XCircle size={14} /> FAIL</>}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}

function SegmentTable({ data, selectedMetrics }) {
    if (!data.length) return <p style={{ color: 'var(--text-sub)' }}>No data</p>

    // Determine the join key(s)
    const sample = data[0]
    const joinKeys = Object.keys(sample).filter(k =>
        !k.includes('_csv') && !k.includes('_fab') && k !== 'perfect_match'
    )

    // Helper to format numbers with commas
    const fmt = (val) => {
        if (val === null || val === undefined) return '-'
        return typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val
    }

    // Helper to calculate diff percentage
    const calcDiffPct = (growth, gold) => {
        if (gold === null || gold === undefined || gold === 0) return '-'
        const pct = ((growth - gold) / gold * 100).toFixed(2)
        return `${pct}%`
    }

    // Define all possible metrics with their display names
    const allMetrics = [
        { key: 'cost', label: 'Cost', csvKey: 'cost_csv', fabKey: 'cost_fab' },
        { key: 'impressions', label: 'Impr', csvKey: 'impressions_csv', fabKey: 'impressions_fab' },
        { key: 'clicks', label: 'Clicks', csvKey: 'clicks_csv', fabKey: 'clicks_fab' },
        { key: 'reach', label: 'Reach', csvKey: 'reach_csv', fabKey: 'reach_fab' },
        { key: 'purchases', label: 'Purchases', csvKey: 'purchases_csv', fabKey: 'purchases_fab' },
        { key: 'conversion_value', label: 'Conv Value', csvKey: 'conversion_value_csv', fabKey: 'conversion_value_fab' }
    ]

    // Filter metrics: show only selected ones if selectedMetrics exists & has items, otherwise show all available
    const metricsToShow = allMetrics.filter(m => {
        const hasData = m.csvKey in sample || m.fabKey in sample
        if (!hasData) return false
        // If selectedMetrics is provided and not empty, filter by it
        if (selectedMetrics && selectedMetrics.length > 0) {
            return selectedMetrics.includes(m.key)
        }
        // Otherwise show all available (for Quick Validate)
        return true
    })

    return (
        <table className="data-table">
            <thead>
                <tr>
                    {joinKeys.map(k => <th key={k}>{k.replace(/_/g, ' ').toUpperCase()}</th>)}
                    {metricsToShow.map(m => (
                        <React.Fragment key={m.key}>
                            <th>{m.label} Growth</th>
                            <th>{m.label} Gold</th>
                            <th>{m.label} Diff %</th>
                        </React.Fragment>
                    ))}
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {data.slice(0, 100).map((row, i) => (
                    <tr key={i}>
                        {joinKeys.map(k => <td key={k} style={{ fontWeight: 600 }}>{row[k]}</td>)}
                        {metricsToShow.map(m => {
                            const growth = row[m.csvKey]
                            const gold = row[m.fabKey]
                            const diffPct = calcDiffPct(growth, gold)
                            const diffVal = parseFloat(diffPct)
                            const diffColor = isNaN(diffVal) ? 'var(--text-sub)' : (Math.abs(diffVal) > 2 ? '#e74c3c' : '#27ae60')
                            return (
                                <React.Fragment key={m.key}>
                                    <td>{fmt(growth)}</td>
                                    <td>{fmt(gold)}</td>
                                    <td style={{ color: diffColor }}>{diffPct}</td>
                                </React.Fragment>
                            )
                        })}
                        <td className={row.perfect_match ? 'status-pass' : 'status-fail'}>
                            {row.perfect_match ? <><CheckCircle size={14} /> PASS</> : <><XCircle size={14} /> FAIL</>}
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}

function AITab({ aiInsight, sessionId }) {
    const [messages, setMessages] = React.useState([]);
    const [input, setInput] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const messagesEndRef = React.useRef(null);

    // Add initial AI insight as first message
    React.useEffect(() => {
        if (aiInsight && messages.length === 0) {
            setMessages([{
                role: 'assistant',
                content: aiInsight
            }]);
        }
    }, [aiInsight]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    React.useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        try {
            const res = await axios.post(`/results/${sessionId}/chat`, { question: userMessage });
            setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer }]);
        } catch (err) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '❌ Sorry, I encountered an error. Please try again.',
                isError: true
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const suggestedQuestions = [
        "What are the main issues found?",
        "Which campaigns have the largest discrepancies?",
        "Explain the cost differences by date",
        "How can I fix the failing validations?"
    ];

    return (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '600px' }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginBottom: '20px',
                paddingBottom: '16px',
                borderBottom: '1px solid rgba(255,255,255,0.1)'
            }}>
                <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #667eea, #764ba2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <Sparkles size={22} color="white" />
                </div>
                <div>
                    <h3 style={{ fontWeight: 700, fontSize: '1.1rem' }}>NYX Assistant</h3>
                    <p style={{ color: 'var(--text-sub)', fontSize: '0.8rem' }}>
                        Powered by Gemini 3 Flash • Ask anything about your validation
                    </p>
                </div>
            </div>

            {/* Messages Container */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                marginBottom: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
            }}>
                {messages.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                        <Sparkles size={48} style={{ color: '#667eea', marginBottom: '16px' }} />
                        <h4 style={{ marginBottom: '12px', fontWeight: 700 }}>Ask me anything!</h4>
                        <p style={{ color: 'var(--text-sub)', marginBottom: '24px', fontSize: '0.9rem' }}>
                            I can help you understand your validation results, identify issues, and suggest fixes.
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
                            {suggestedQuestions.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => setInput(q)}
                                    style={{
                                        padding: '10px 16px',
                                        borderRadius: '20px',
                                        border: '1px solid rgba(102, 126, 234, 0.3)',
                                        background: 'rgba(102, 126, 234, 0.1)',
                                        color: '#a5b4fc',
                                        fontSize: '0.85rem',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseOver={(e) => e.target.style.background = 'rgba(102, 126, 234, 0.2)'}
                                    onMouseOut={(e) => e.target.style.background = 'rgba(102, 126, 234, 0.1)'}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} style={{
                            display: 'flex',
                            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                        }}>
                            <div style={{
                                maxWidth: '80%',
                                padding: '14px 18px',
                                borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                                background: msg.role === 'user'
                                    ? 'linear-gradient(135deg, #667eea, #764ba2)'
                                    : msg.isError
                                        ? 'rgba(239, 68, 68, 0.2)'
                                        : 'rgba(255,255,255,0.08)',
                                color: msg.role === 'user' ? 'white' : 'var(--text-main)',
                                fontSize: '0.95rem',
                                lineHeight: '1.6',
                                whiteSpace: 'pre-wrap'
                            }}>
                                {msg.content}
                            </div>
                        </div>
                    ))
                )}

                {loading && (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <div style={{
                            padding: '14px 18px',
                            borderRadius: '18px 18px 18px 4px',
                            background: 'rgba(255,255,255,0.08)',
                            display: 'flex',
                            gap: '6px'
                        }}>
                            <span className="typing-dot"></span>
                            <span className="typing-dot" style={{ animationDelay: '0.2s' }}></span>
                            <span className="typing-dot" style={{ animationDelay: '0.4s' }}></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{
                display: 'flex',
                gap: '12px',
                padding: '12px',
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '16px',
                border: '1px solid rgba(255,255,255,0.1)'
            }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about your validation results..."
                    disabled={loading}
                    style={{
                        flex: 1,
                        padding: '14px 18px',
                        borderRadius: '12px',
                        border: 'none',
                        background: 'rgba(255,255,255,0.05)',
                        color: 'var(--text-main)',
                        fontSize: '0.95rem',
                        outline: 'none'
                    }}
                />
                <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    style={{
                        padding: '14px 24px',
                        borderRadius: '12px',
                        border: 'none',
                        background: loading || !input.trim()
                            ? 'rgba(255,255,255,0.1)'
                            : 'linear-gradient(135deg, #667eea, #764ba2)',
                        color: 'white',
                        fontWeight: 700,
                        cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        transition: 'all 0.2s'
                    }}
                >
                    {loading ? <Loader2 size={18} className="animate-spin" /> : <MessageSquareText size={18} />}
                    Send
                </button>
            </div>
        </div>
    )
}
