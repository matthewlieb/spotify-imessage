import React from 'react';
import { Settings, Filter, Play, Calendar, Music, BarChart3 } from 'lucide-react';
import { ProcessingOptions } from '../types';

interface ProcessingFormProps {
  options: ProcessingOptions;
  onOptionsChange: (options: ProcessingOptions) => void;
  onSubmit: () => void;
  isProcessing: boolean;
}

export const ProcessingForm: React.FC<ProcessingFormProps> = ({
  options,
  onOptionsChange,
  onSubmit,
  isProcessing,
}) => {
  const handleChange = (key: keyof ProcessingOptions, value: any) => {
    onOptionsChange({
      ...options,
      [key]: value,
    });
  };

  const handleCheckboxChange = (key: keyof ProcessingOptions) => {
    onOptionsChange({
      ...options,
      [key]: !options[key],
    });
  };

  return (
    <div className="space-y-6">
      {/* Processing Options */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Settings className="w-5 h-5 text-spotify-400" />
          <h3 className="text-lg font-semibold">Processing Options</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">File Type</label>
            <select
              value={options.command_type}
              onChange={(e) => handleChange('command_type', e.target.value)}
              className="input-field w-full"
            >
              <option value="android">Android Messages Export</option>
              <option value="file">Generic Text File</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">
              Spotify Playlist ID
            </label>
            <input
              type="text"
              value={options.playlist_id || ''}
              onChange={(e) => handleChange('playlist_id', e.target.value)}
              placeholder="22-character playlist ID"
              className="input-field w-full"
            />
          </div>
        </div>
      </div>

      {/* Date Filtering */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="w-5 h-5 text-spotify-400" />
          <h3 className="text-lg font-semibold">Date Filtering</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Start Date</label>
            <div className="relative">
              <Calendar className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" />
              <input
                type="date"
                value={options.start_date || ''}
                onChange={(e) => handleChange('start_date', e.target.value)}
                className="input-field w-full pl-10"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">End Date</label>
            <div className="relative">
              <Calendar className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-white/40" />
              <input
                type="date"
                value={options.end_date || ''}
                onChange={(e) => handleChange('end_date', e.target.value)}
                className="input-field w-full pl-10"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Days Back</label>
            <input
              type="number"
              value={options.days_back || ''}
              onChange={(e) => handleChange('days_back', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="e.g., 30"
              min="1"
              max="365"
              className="input-field w-full"
            />
          </div>
        </div>
      </div>

      {/* Additional Options */}
      <div className="glass-card p-6">
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="w-5 h-5 text-spotify-400" />
          <h3 className="text-lg font-semibold">Additional Options</h3>
        </div>
        
        <div className="space-y-3">
          <label className="flex items-center space-x-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={options.show_metadata}
              onChange={() => handleCheckboxChange('show_metadata')}
              className="w-5 h-5 text-spotify-500 bg-white/10 border-white/20 rounded focus:ring-spotify-500 focus:ring-2"
            />
            <div className="flex items-center space-x-2">
              <Music className="w-4 h-4 text-spotify-400" />
              <span className="group-hover:text-spotify-400 transition-colors">
                Show track metadata (artist/title)
              </span>
            </div>
          </label>
          
          <label className="flex items-center space-x-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={options.dry_run}
              onChange={() => handleCheckboxChange('dry_run')}
              className="w-5 h-5 text-spotify-500 bg-white/10 border-white/20 rounded focus:ring-spotify-500 focus:ring-2"
            />
            <div className="flex items-center space-x-2">
              <Play className="w-4 h-4 text-spotify-400" />
              <span className="group-hover:text-spotify-400 transition-colors">
                Dry run (don't add to playlist)
              </span>
            </div>
          </label>
          
          <label className="flex items-center space-x-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={options.stats}
              onChange={() => handleCheckboxChange('stats')}
              className="w-5 h-5 text-spotify-500 bg-white/10 border-white/20 rounded focus:ring-spotify-500 focus:ring-2"
            />
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-spotify-400" />
              <span className="group-hover:text-spotify-400 transition-colors">
                Show detailed statistics
              </span>
            </div>
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <button
        onClick={onSubmit}
        disabled={isProcessing}
        className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isProcessing ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            <span>Processing...</span>
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            <span>Process File</span>
          </>
        )}
      </button>
    </div>
  );
};
