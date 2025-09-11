import React from 'react';
import { Download, FileText, Plus, Copy, Check } from 'lucide-react';
import { ProcessingJob } from '../types';

interface ResultDisplayProps {
  job: ProcessingJob;
  onDownload: () => void;
  onNewFile: () => void;
}

export const ResultDisplay: React.FC<ResultDisplayProps> = ({
  job,
  onDownload,
  onNewFile,
}) => {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = async () => {
    if (job.output) {
      await navigator.clipboard.writeText(job.output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isSuccess = job.status === 'completed';
  const isError = job.status === 'error';

  return (
    <div className="glass-card p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-full ${
            isSuccess ? 'bg-green-500/20' : 
            isError ? 'bg-red-500/20' : 'bg-spotify-500/20'
          }`}>
            <FileText className={`w-5 h-5 ${
              isSuccess ? 'text-green-400' : 
              isError ? 'text-red-400' : 'text-spotify-400'
            }`} />
          </div>
          <div>
            <h3 className="font-semibold text-white">
              {isSuccess ? 'Processing Complete!' : 
               isError ? 'Processing Failed' : 'Processing Results'}
            </h3>
            <p className="text-white/60 text-sm">{job.file}</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {isSuccess && (
            <button
              onClick={onDownload}
              className="btn-secondary flex items-center space-x-2"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </button>
          )}
          
          <button
            onClick={onNewFile}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>New File</span>
          </button>
        </div>
      </div>

      {job.output && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-white/80">Output</span>
            <button
              onClick={copyToClipboard}
              className="flex items-center space-x-1 text-xs text-white/60 hover:text-white transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          
          <div className="bg-black/30 border border-white/10 rounded-lg p-4 max-h-64 overflow-y-auto">
            <pre className="text-sm text-white/90 whitespace-pre-wrap font-mono">
              {job.output}
            </pre>
          </div>
        </div>
      )}

      {isError && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-red-400 text-sm">{job.message}</p>
        </div>
      )}
    </div>
  );
};
