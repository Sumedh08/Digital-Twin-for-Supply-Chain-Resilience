import React from 'react';

class RouteErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      message: ''
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || 'Unexpected application error'
    };
  }

  componentDidCatch(error) {
    console.error('Route render failed:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'grid',
            placeItems: 'center',
            background: 'radial-gradient(circle at top, #0f172a, #020617 65%)',
            color: '#e2e8f0',
            padding: '24px'
          }}
        >
          <div
            style={{
              width: 'min(560px, 100%)',
              borderRadius: '20px',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              background: 'rgba(15, 23, 42, 0.82)',
              padding: '28px',
              boxShadow: '0 30px 80px rgba(2, 6, 23, 0.45)'
            }}
          >
            <p style={{ margin: '0 0 8px', fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#38bdf8' }}>
              Safe Fallback
            </p>
            <h1 style={{ margin: '0 0 12px', fontSize: '28px', lineHeight: 1.1 }}>
              This page hit a render error
            </h1>
            <p style={{ margin: '0 0 20px', color: '#94a3b8', lineHeight: 1.6 }}>
              The application kept a fallback screen up so the presentation does not collapse into a blank page.
            </p>
            <div
              style={{
                marginBottom: '20px',
                borderRadius: '14px',
                border: '1px solid rgba(248, 113, 113, 0.2)',
                background: 'rgba(127, 29, 29, 0.22)',
                padding: '14px 16px',
                color: '#fecaca',
                fontSize: '14px'
              }}
            >
              {this.state.message}
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => window.location.reload()}
                style={{
                  border: 'none',
                  borderRadius: '999px',
                  padding: '10px 16px',
                  background: '#38bdf8',
                  color: '#082f49',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Reload Page
              </button>
              <a
                href="/"
                style={{
                  borderRadius: '999px',
                  padding: '10px 16px',
                  border: '1px solid rgba(148, 163, 184, 0.24)',
                  color: '#e2e8f0',
                  textDecoration: 'none'
                }}
              >
                Return Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default RouteErrorBoundary;
