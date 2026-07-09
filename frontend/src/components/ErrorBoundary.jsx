import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught a runtime crash:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 bg-red-950/20 border border-red-500/30 rounded-lg text-red-400 space-y-3 m-6">
          <h2 className="text-lg font-bold text-red-500">Component Runtime Crash</h2>
          <p className="text-sm">React caught an unhandled rendering error in this view:</p>
          <pre className="p-3 bg-[#030712] rounded border border-red-500/10 font-mono text-xs text-red-300 overflow-auto whitespace-pre-wrap">
            {this.state.error ? this.state.error.toString() : "Unknown Error"}
          </pre>
          <button 
            onClick={() => this.setState({ hasError: false, error: null })} 
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded mr-3"
          >
            Try Again
          </button>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded"
          >
            Reload Tab
          </button>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
