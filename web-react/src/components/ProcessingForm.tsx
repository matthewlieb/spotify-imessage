import React from 'react';

interface ProcessingFormProps {
  playlistName: string;
  setPlaylistName: (name: string) => void;
  playlistId: string;
  setPlaylistId: (id: string) => void;
  showMetadata: boolean;
  setShowMetadata: (show: boolean) => void;
  dryRun: boolean;
  setDryRun: (dry: boolean) => void;
  playlistSearchResult: any;
  isSearchingPlaylist: boolean;
  onPlaylistSearch: () => void;
  onCreatePlaylist: () => void;
  onProcess: () => void;
  isProcessing: boolean;
  canProcess: boolean;
}

export const ProcessingForm: React.FC<ProcessingFormProps> = ({
  playlistName,
  setPlaylistName,
  playlistId,
  setPlaylistId,
  showMetadata,
  setShowMetadata,
  dryRun,
  setDryRun,
  playlistSearchResult,
  isSearchingPlaylist,
  onPlaylistSearch,
  onCreatePlaylist,
  onProcess,
  isProcessing,
  canProcess
}) => {
  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Processing Options</h2>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium mb-2">Spotify Playlist Name</label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={playlistName}
              onChange={(e) => setPlaylistName(e.target.value)}
              placeholder="e.g., My Favorite Songs"
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
            />
            <button
              onClick={onPlaylistSearch}
              disabled={isSearchingPlaylist}
              className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold px-6 py-3 rounded-full transition-colors"
            >
              {isSearchingPlaylist ? 'Searching...' : 'Search Playlist'}
            </button>
            <button
              onClick={onCreatePlaylist}
              disabled={isSearchingPlaylist}
              className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-600 text-white font-semibold px-6 py-3 rounded-full transition-colors"
            >
              {isSearchingPlaylist ? 'Creating...' : 'Create Playlist'}
            </button>
          </div>
          {playlistSearchResult && (
            <div className="mt-4 p-3 bg-white/10 border border-white/20 rounded-lg text-sm text-gray-300">
              {playlistSearchResult.error ? (
                <p className="text-red-300">{playlistSearchResult.error}</p>
              ) : (
                <>
                  <p>Found Playlist: <span className="font-semibold">{playlistSearchResult.name}</span></p>
                  <p>ID: <span className="font-mono text-gray-400">{playlistSearchResult.id}</span></p>
                </>
              )}
            </div>
          )}
        </div>
        
        <div className="space-y-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={showMetadata}
              onChange={(e) => setShowMetadata(e.target.checked)}
              className="text-green-500"
            />
            <span>Show track metadata</span>
          </label>
          
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="text-green-500"
            />
            <span>Dry run (preview only)</span>
          </label>
        </div>
      </div>
      
      <div className="mt-6">
        <button
          onClick={onProcess}
          disabled={isProcessing || canProcess}
          className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-full transition-colors"
        >
          {isProcessing ? 'Processing...' : 'Process Chat'}
        </button>
      </div>
    </div>
  );
};