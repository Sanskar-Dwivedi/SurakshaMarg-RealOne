import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AppShell } from './components/layout/AppShell';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[GauKavach Error Boundary Caught]:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-cream text-charcoal flex flex-col items-center justify-center p-6 font-sans">
          <div className="bg-surface border-2 border-accent-terracotta/40 p-8 rounded-2xl shadow-card max-w-xl text-center space-y-4">
            <div className="inline-flex p-3 rounded-xl bg-tint-amber text-accent-terracotta font-black text-2xl font-serif">
              GauKavach Command Center
            </div>
            <h2 className="text-2xl font-serif font-black text-charcoal">
              Application Render Exception
            </h2>
            <p className="text-sm font-sans font-bold text-charcoal-muted">
              An unexpected render error occurred inside the dashboard UI.
            </p>
            <div className="bg-charcoal text-cream text-left p-4 rounded-xl font-mono text-xs overflow-x-auto border border-charcoal-light">
              {this.state.error?.message || 'Unknown Error'}
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 rounded-xl bg-accent-olive text-cream font-bold text-sm font-sans shadow-card hover:bg-accent-olive/90 transition-colors"
            >
              Reload Command Center
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function App() {
  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  );
}

export default App;
