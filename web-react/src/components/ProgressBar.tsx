import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface ProgressBarProps {
  progress: number;
  message: string;
  status: 'processing' | 'completed' | 'error';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  message,
  status,
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'processing':
        return <Loader2 className="w-5 h-5 text-spotify-400 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'processing':
        return 'text-spotify-400';
      case 'completed':
        return 'text-green-400';
      case 'error':
        return 'text-red-400';
      default:
        return 'text-white/60';
    }
  };

  return (
    <div className="glass-card p-6 animate-fade-in">
      <div className="flex items-center space-x-3 mb-4">
        {getStatusIcon()}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <span className={`font-medium ${getStatusColor()}`}>
              {status === 'processing' ? 'Processing...' : 
               status === 'completed' ? 'Completed!' : 'Error'}
            </span>
            <span className="text-sm text-white/60">{Math.round(progress)}%</span>
          </div>
          
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
      
      <p className="text-white/80 text-sm">{message}</p>
    </div>
  );
};
