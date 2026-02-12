import React from 'react';

// Global error handling utilities
export const handleError = (error, context = 'Unknown') => {
  // Don't handle null, undefined, or empty errors
  if (!error || error === null || error === undefined) {
    return null;
  }
  
  // Don't log script errors to avoid noise
  if (error && error.message && error.message.includes('Script error')) {
    console.warn(`[${context}] Script error suppressed:`, error);
    return null;
  }
  
  console.error(`[${context}] Error:`, error);
  
  // Log to error reporting service if available
  if (window.gtag) {
    window.gtag('event', 'exception', {
      description: error.toString(),
      fatal: false
    });
  }
  
  return {
    message: 'Something went wrong. Please try again.',
    context,
    timestamp: new Date().toISOString()
  };
};

export const handleAsyncError = async (asyncFn, context = 'Async Operation') => {
  try {
    return await asyncFn();
  } catch (error) {
    return handleError(error, context);
  }
};

export const safeExecute = (fn, fallback = null, context = 'Safe Execute') => {
  try {
    return fn();
  } catch (error) {
    console.error(`[${context}] Safe execute error:`, error);
    return fallback;
  }
};

// React error boundary helper
export const withErrorHandling = (Component) => {
  return class extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
      return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
      handleError(error, 'Component Error Boundary');
    }

    render() {
      if (this.state.hasError) {
        return (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 m-4">
            <h3 className="text-red-300 font-semibold mb-2">Component Error</h3>
            <p className="text-red-200 text-sm">
              This component encountered an error. Please refresh the page.
            </p>
          </div>
        );
      }

      return <Component {...this.props} />;
    }
  };
};

// API error handling
export const handleApiError = (error, endpoint = 'Unknown API') => {
  let message = 'An error occurred while processing your request.';
  
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    switch (status) {
      case 400:
        message = 'Invalid request. Please check your input.';
        break;
      case 401:
        message = 'Authentication required. Please sign in again.';
        break;
      case 403:
        message = 'Access denied. You don\'t have permission for this action.';
        break;
      case 404:
        message = 'The requested resource was not found.';
        break;
      case 429:
        message = 'Too many requests. Please wait a moment and try again.';
        break;
      case 500:
        message = 'Server error. Please try again later.';
        break;
      default:
        message = `Server error (${status}). Please try again.`;
    }
  } else if (error.request) {
    // Network error
    message = 'Network error. Please check your connection and try again.';
  } else {
    // Other error
    message = error.message || 'An unexpected error occurred.';
  }

  console.error(`[${endpoint}] API Error:`, error);
  
  return {
    message,
    status: error.response?.status,
    endpoint,
    timestamp: new Date().toISOString()
  };
};

// Promise error handling
export const safePromise = (promise, context = 'Promise') => {
  return promise
    .then(result => ({ success: true, data: result, error: null }))
    .catch(error => {
      const handledError = handleError(error, context);
      return { success: false, data: null, error: handledError };
    });
};

// State update error handling
export const safeStateUpdate = (setState, newState, context = 'State Update') => {
  try {
    setState(newState);
  } catch (error) {
    handleError(error, context);
    // Attempt to reset to a safe state
    try {
      setState(prevState => ({ ...prevState, error: true }));
    } catch (resetError) {
      console.error('Failed to reset state after error:', resetError);
    }
  }
};
