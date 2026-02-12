import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console and any error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // You can also log the error to an error reporting service here
    // Example: logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
          <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 max-w-2xl w-full shadow-2xl">
            <div className="text-center">
              <div className="text-6xl mb-4">🎵</div>
              <h1 className="text-3xl font-bold text-white mb-4">Oops! SpotifiMessage Hit a Bump</h1>
              <p className="text-gray-300 mb-6">
                Something went wrong, but don't worry - your data is safe! 
                This is just a temporary hiccup.
              </p>
              
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6 text-left">
                <h3 className="text-red-300 font-semibold mb-2">Error Details:</h3>
                <p className="text-red-200 text-sm font-mono break-all">
                  {this.state.error && this.state.error.toString()}
                </p>
              </div>

              <div className="flex gap-4 justify-center">
                <button
                  onClick={this.handleRetry}
                  className="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg transition-colors font-semibold"
                >
                  Try Again
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg transition-colors font-semibold"
                >
                  Reload Page
                </button>
              </div>

              <div className="mt-6 text-sm text-gray-400">
                <p>If this keeps happening, try:</p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Refreshing the page</li>
                  <li>Clearing your browser cache</li>
                  <li>Checking your internet connection</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
