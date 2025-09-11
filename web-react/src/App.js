import React, { useState, useEffect } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState('smart-detect');
  const [chatName, setChatName] = useState('');
  const [selectedChat, setSelectedChat] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [playlistName, setPlaylistName] = useState('');
  const [playlistId, setPlaylistId] = useState('');
  const [showMetadata, setShowMetadata] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [chats, setChats] = useState([]);
  const [scanError, setScanError] = useState('');
  const [playlistSearchResult, setPlaylistSearchResult] = useState(null);
  const [isSearchingPlaylist, setIsSearchingPlaylist] = useState(false);
  
  const [showProcessingOptions, setShowProcessingOptions] = useState(false);

  // API base URL - automatically detected from environment or smart defaults
  const getApiBaseUrl = () => {
    // First try environment variable
    if (process.env.REACT_APP_API_URL) {
      return process.env.REACT_APP_API_URL;
    }
    
    // Fallback to localhost with common ports
    const ports = [8004, 8000, 5000, 3001];
    
    // Try to detect if backend is running on any of these ports
    for (const port of ports) {
      try {
        // This is a simple check - in production you'd want more sophisticated detection
        if (typeof window !== 'undefined') {
          // We're in the browser, use the current port
          return `http://localhost:${port}`;
        }
      } catch (e) {
        continue;
      }
    }
    
    // Default fallback
    return 'http://localhost:8004';
  };

  const API_BASE_URL = getApiBaseUrl();

  const handleSmartScan = async () => {
    setIsScanning(true);
    setScanError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/scan-imessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (data.success) {
        setChats(data.chats);
        if (data.chats.length === 0) {
          setScanError(''); // Clear error, let the info message show instead
        }
      } else {
        setScanError(data.error || 'Failed to scan messages');
      }
    } catch (error) {
      setScanError('Error connecting to server');
      console.error('Scan error:', error);
    } finally {
      setIsScanning(false);
    }
  };

  const handlePlaylistSearch = async () => {
    if (!playlistName.trim()) {
      alert('Please enter a playlist name');
      return;
    }

    setIsSearchingPlaylist(true);
    setPlaylistSearchResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/playlist/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: playlistName }),
      });

      const data = await response.json();

      if (data.success) {
        setPlaylistSearchResult(data.playlist);
        setPlaylistId(data.playlist.id);
      } else {
        setPlaylistSearchResult({ error: data.message });
      }
    } catch (error) {
      setPlaylistSearchResult({ error: 'Error connecting to server' });
      console.error('Playlist search error:', error);
    } finally {
      setIsSearchingPlaylist(false);
    }
  };

  const handleCreatePlaylist = async () => {
    if (!playlistName.trim()) {
      alert('Please enter a playlist name');
      return;
    }

    setIsSearchingPlaylist(true);
    setPlaylistSearchResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/playlist/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          name: playlistName,
          description: `Created by spotify-message from chat messages`
        }),
      });

      const data = await response.json();

      if (data.success) {
        setPlaylistSearchResult(data.playlist);
        setPlaylistId(data.playlist.id);
      } else {
        setPlaylistSearchResult({ error: data.message });
      }
    } catch (error) {
      setPlaylistSearchResult({ error: 'Error connecting to server' });
      console.error('Playlist creation error:', error);
    } finally {
      setIsSearchingPlaylist(false);
    }
  };

  const handleProcessChat = async (chat) => {
    if (!playlistId.trim()) {
      alert('Please search for or create a playlist first');
      return;
    }

    setIsProcessing(true);
    setCurrentJob({
      id: Date.now().toString(),
      status: 'processing',
      progress: 0,
      message: 'Starting extraction...'
    });

    try {
      const response = await fetch(`${API_BASE_URL}/api/process-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_name: chat.name,
          command_type: 'imessage',
          options: {
            playlist_id: playlistId,
            show_metadata: showMetadata,
            dry_run: dryRun
          }
        }),
      });

      const data = await response.json();
      
      if (data.job_id) {
        // Poll for job status
        pollJobStatus(data.job_id);
      } else {
        throw new Error(data.error || 'Failed to start processing');
      }
    } catch (error) {
      setCurrentJob(prev => prev ? {
        ...prev,
        status: 'error',
        message: error.message,
        progress: 100,
      } : null);
      setIsProcessing(false);
    }
  };

  const pollJobStatus = async (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
        const jobStatus = await response.json();
        
        setCurrentJob(jobStatus);
        
        if (jobStatus.status === 'completed' || jobStatus.status === 'error') {
          clearInterval(pollInterval);
          setIsProcessing(false);
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        clearInterval(pollInterval);
        setIsProcessing(false);
      }
    }, 1000);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      alert(`File selected: ${file.name}`);
      // Handle file processing here
    }
  };

  const handleTabChange = (newTab) => {
    setActiveTab(newTab);
    
    // Clear ALL state when switching tabs to prevent carry-over
    setSelectedChat(null);
    setChatName('');
    setChats([]);
    setScanError('');
    setPlaylistName('');
    setPlaylistId('');
    setPlaylistSearchResult(null);
    setCurrentJob(null);
    setShowProcessingOptions(false);
    
    // Reset form states
    setShowMetadata(false);
    setDryRun(false);
  };


  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            🎵 spotify-message
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Extract Spotify tracks from your message exports and create amazing playlists
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          {/* Tab Navigation */}
          <div className="flex flex-wrap justify-center gap-2 mb-8">
            <button
              onClick={() => handleTabChange('smart-detect')}
              className={`px-4 py-2 rounded-full transition-colors ${
                activeTab === 'smart-detect' 
                  ? 'bg-green-500 text-white' 
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              Smart Detection
            </button>
            <button
              onClick={() => handleTabChange('chat-name')}
              className={`px-4 py-2 rounded-full transition-colors ${
                activeTab === 'chat-name' 
                  ? 'bg-green-500 text-white' 
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              Chat Name
            </button>
            <button
              onClick={() => handleTabChange('file-upload')}
              className={`px-4 py-2 rounded-full transition-colors ${
                activeTab === 'file-upload' 
                  ? 'bg-green-500 text-white' 
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              File Upload
            </button>
          </div>

          {/* Smart Detection Tab */}
          {activeTab === 'smart-detect' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold mb-4">Smart Message Detection</h2>
                <p className="text-gray-300 mb-6">
                  Let us scan your messages to find conversations with Spotify links
                </p>
                <button
                  onClick={handleSmartScan}
                  disabled={isScanning}
                  className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-full transition-colors"
                >
                  {isScanning ? 'Scanning...' : 'Scan Messages'}
                </button>
              </div>

              {scanError && (
                <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 mb-6">
                  <p className="text-red-300">{scanError}</p>
                </div>
              )}

              {!isScanning && !scanError && chats.length === 0 && (
                <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4 mb-6">
                  <p className="text-blue-300 mb-2">
                    <strong>No conversations with Spotify links found.</strong>
                  </p>
                  <p className="text-blue-200 text-sm">
                    This could mean you don't have any Spotify links in your messages, or try using the "Chat Name" tab for manual entry.
                  </p>
                </div>
              )}

              {/* Display found conversations */}
              {chats.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold mb-4">Found Conversations</h3>
                  
                  {chats.map((chat, index) => (
                    <div key={index} className="bg-white/5 border border-white/10 rounded-lg p-4">
                      <div className="flex justify-between items-center">
                        <div className="flex-1">
                          <h4 className="font-semibold text-lg">{chat.name}</h4>
                          <p className="text-gray-300">{chat.trackCount} tracks</p>
                          <p className="text-sm text-gray-400">{chat.lastActivity}</p>
                        </div>
                        
                        <button
                          onClick={() => {
                            setSelectedChat(chat);
                            setShowProcessingOptions(true);
                          }}
                          className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          Select Chat
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Chat Name Tab */}
          {activeTab === 'chat-name' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <h2 className="text-2xl font-bold mb-4">Enter Chat Name</h2>
              <p className="text-gray-300 mb-6">
                Type the exact name of your iMessage or Android Messages chat
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Chat Name</label>
                  <input
                    type="text"
                    value={chatName}
                    onChange={(e) => setChatName(e.target.value)}
                    placeholder="e.g., My daughter is dating Kodak Black"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                  />
                </div>
                

              </div>
            </div>
          )}

          {/* File Upload Tab */}
          {activeTab === 'file-upload' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <h2 className="text-2xl font-bold mb-4">Upload Export File</h2>
              <p className="text-gray-300 mb-6">
                Upload your exported message file (TXT format)
              </p>
              
              <div className="border-2 border-dashed border-white/20 rounded-lg p-8 text-center">
                <p className="text-gray-300 mb-4">
                  Drag and drop your export file here, or click to browse
                </p>
                <input
                  type="file"
                  accept=".txt"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="bg-green-500 hover:bg-green-600 text-white font-semibold px-6 py-3 rounded-full transition-colors cursor-pointer"
                >
                  Choose File
                </label>
              </div>
              
              {/* Toggle for Processing Options */}
              <div className="mt-6 text-center">
                <button
                  onClick={() => setShowProcessingOptions(!showProcessingOptions)}
                  className="text-gray-400 hover:text-white transition-colors flex items-center space-x-2 mx-auto"
                >
                  <span>{showProcessingOptions ? '▼' : '▶'}</span>
                  <span>{showProcessingOptions ? 'Hide' : 'Show'} Processing Options</span>
                </button>
              </div>
            </div>
          )}

          {/* Processing Options */}
          {((activeTab === 'smart-detect' && selectedChat) || 
            (activeTab === 'chat-name' && chatName.trim()) || 
            (activeTab === 'file-upload' && showProcessingOptions)) && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Processing Options</h2>
                {activeTab === 'file-upload' && (
                  <span className="bg-yellow-500/20 border border-yellow-500/50 text-yellow-200 text-xs px-2 py-1 rounded-full">
                    ⭐ Premium
                  </span>
                )}
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
                      onClick={handlePlaylistSearch}
                      disabled={isSearchingPlaylist}
                      className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 text-white font-semibold px-6 py-3 rounded-full transition-colors"
                    >
                      {isSearchingPlaylist ? 'Searching...' : 'Search Playlist'}
                    </button>
                    <button
                      onClick={handleCreatePlaylist}
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
                  onClick={() => {
                    if (selectedChat) {
                      handleProcessChat(selectedChat);
                    } else if (chatName.trim()) {
                      handleProcessChat({ name: chatName.trim() });
                    }
                  }}
                  disabled={isProcessing || !playlistId.trim() || (!selectedChat && !chatName.trim())}
                  className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-full transition-colors"
                >
                  {isProcessing ? 'Processing...' : 'Process Chat'}
                </button>
              </div>
            </div>
          )}

          {/* Progress Bar */}
          {currentJob && currentJob.status === 'processing' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <h3 className="text-lg font-semibold mb-4">Processing Progress</h3>
              <div className="space-y-4">
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${currentJob.progress}%` }}
                  ></div>
                </div>
                <p className="text-gray-300">{currentJob.message}</p>
              </div>
            </div>
          )}

          {/* Results */}
          {currentJob && currentJob.status === 'completed' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <div className="text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🎵</span>
                </div>
                <h3 className="text-2xl font-bold mb-2">Processing Complete!</h3>
                <p className="text-gray-300 mb-6">
                  Successfully processed {currentJob.tracks_added || 0} tracks
                </p>
                
                <div className="space-y-4">
                  <button
                    onClick={() => {
                      setCurrentJob(null);
                      setSelectedChat(null);
                      setChatName('');
                    }}
                    className="bg-green-500 hover:bg-green-600 text-white font-semibold px-6 py-3 rounded-full transition-colors"
                  >
                    Process Another Chat
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Error Results */}
          {currentJob && currentJob.status === 'error' && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">❌</span>
                </div>
                <h3 className="text-2xl font-bold mb-2">Processing Failed</h3>
                <p className="text-gray-300 mb-6">
                  {currentJob.message}
                </p>
                
                <div className="space-y-4">
                  <button
                    onClick={() => {
                      setCurrentJob(null);
                      setSelectedChat(null);
                      setChatName('');
                    }}
                    className="bg-gray-500 hover:bg-gray-600 text-white font-semibold px-6 py-3 rounded-full transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
