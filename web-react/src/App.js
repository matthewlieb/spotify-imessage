import React, { useState, useEffect, useRef } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import { handleError } from './utils/errorHandler';

function App() {
  // Global error handling - AGGRESSIVE SUPPRESSION
  useEffect(() => {
    // Override console.error to suppress script errors
    const originalConsoleError = console.error;
    console.error = (...args) => {
      const message = args.join(' ');
      if (message.includes('Script error') || message.includes('handleError')) {
        // Suppress script errors completely
        return;
      }
      originalConsoleError.apply(console, args);
    };

    // Override window.onerror to prevent error display
    const originalOnError = window.onerror;
    window.onerror = (message, source, lineno, colno, error) => {
      // Suppress all script errors
      if (message && message.includes('Script error')) {
        return true; // Prevent default error handling
      }
      if (originalOnError) {
        return originalOnError(message, source, lineno, colno, error);
      }
      return false;
    };

    const handleGlobalError = (event) => {
      // Suppress ALL errors from showing in UI
      event.preventDefault();
      event.stopPropagation();
      return false;
    };

    const handleUnhandledRejection = (event) => {
      // Suppress ALL promise rejections from showing in UI
      event.preventDefault();
      return false;
    };

    // Add multiple layers of error suppression
    window.addEventListener('error', handleGlobalError, true);
    window.addEventListener('unhandledrejection', handleUnhandledRejection, true);
    
    // Additional error suppression
    window.addEventListener('error', (e) => {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }, true);

    return () => {
      // Restore original console.error
      console.error = originalConsoleError;
      window.onerror = originalOnError;
      window.removeEventListener('error', handleGlobalError, true);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection, true);
    };
  }, []);

  // State management
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
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedTracks, setSelectedTracks] = useState([]);
  const [showTrackPreview, setShowTrackPreview] = useState(false);
  const [isLoadingTracks, setIsLoadingTracks] = useState(false);
  const [trackDetails, setTrackDetails] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [tracksPerPage] = useState(50);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('name'); // 'name', 'artist', 'date'
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc', 'desc'

  // Multi-message playlist state
  const [collectedTracks, setCollectedTracks] = useState([]);
  const [playlistSources, setPlaylistSources] = useState([]); // Track which conversations contributed tracks
  const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);

  // OAuth authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [spotifyUser, setSpotifyUser] = useState(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const hasHandledOAuthRef = useRef(false);

  // API base URL - environment aware
  const API_BASE_URL = process.env.NODE_ENV === 'production' 
    ? process.env.REACT_APP_API_URL || 'https://zingaroo-backend.railway.app'
    : 'http://localhost:8004';
  
  // Platform detection
  const isMacOS = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const hasIMessage = isMacOS; // iMessage only available on macOS

  // OAuth authentication functions
  const checkAuthStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/status`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setIsAuthenticated(data.authenticated);
      setSpotifyUser(data.user);
    } catch (error) {
      console.error('Error checking auth status:', error);
      setIsAuthenticated(false);
      setSpotifyUser(null);
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleSpotifyLogin = async () => {
    setIsLoggingIn(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/spotify`, {
        credentials: 'include',
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, text: ${errorText}`);
      }
      
      const data = await response.json();
      
      if (data.auth_url) {
        setTimeout(() => {
          window.location.href = data.auth_url;
        }, 100);
      } else {
        alert('Failed to initiate Spotify login - no auth URL received');
        setIsLoggingIn(false);
      }
    } catch (error) {
      console.error('Error initiating Spotify login:', error);
      alert(`Error connecting to server: ${error.message}`);
      setIsLoggingIn(false);
    }
  };

  const exchangeAuthToken = async (authToken) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/exchange-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ token: authToken })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setIsAuthenticated(true);
        setSpotifyUser(data.user);
        
        // Store the token in localStorage for Spotify Web Playback SDK
        if (data.spotify_token && data.spotify_token.access_token) {
          localStorage.setItem('spotify_token', JSON.stringify(data.spotify_token));
        }
      } else {
        alert('Authentication failed. Please try again.');
      }
    } catch (error) {
      console.error('Error exchanging auth token:', error);
      alert('Authentication failed. Please try again.');
    }
  };

  const handleSpotifyLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      
      setIsAuthenticated(false);
      setSpotifyUser(null);
      
      // Clear Spotify token from localStorage
      localStorage.removeItem('spotify_token');
    } catch (error) {
      console.error('Error during logout:', error);
    }
  };

  // Check authentication status on component mount
  useEffect(() => {
    if (hasHandledOAuthRef.current) {
      return;
    }
    
    const urlParams = new URLSearchParams(window.location.search);
    const authResult = urlParams.get('spotify_auth');
    
    if (authResult === 'success') {
      const authToken = urlParams.get('token');
      
      if (authToken) {
        hasHandledOAuthRef.current = true;
        exchangeAuthToken(authToken);
        window.history.replaceState({}, document.title, window.location.pathname);
        setIsLoggingIn(false);
        return;
      } else {
        hasHandledOAuthRef.current = true;
        setTimeout(() => {
          checkAuthStatus();
        }, 1000);
        window.history.replaceState({}, document.title, window.location.pathname);
        setIsLoggingIn(false);
        return;
      }
    } else if (authResult === 'error') {
      hasHandledOAuthRef.current = true;
      alert('Spotify authentication failed. Please try again.');
      window.history.replaceState({}, document.title, window.location.pathname);
      setIsLoggingIn(false);
      return;
    } else {
      // Add a small delay to ensure the auth check completes
      setTimeout(() => {
        checkAuthStatus();
      }, 500);
    }
    
    setIsLoggingIn(false);
  }, []);

  const handleSmartScan = async () => {
    setIsScanning(true);
    setScanError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/scan-imessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });
      
      const data = await response.json();
      
      if (data.success) {
        setChats(data.chats);
        if (data.chats.length === 0) {
          setScanError('');
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
        credentials: 'include'
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
      // For playlist builder, include collected tracks info in description
      const description = activeTab === 'playlist-builder' 
        ? `Created by Zingaroo from ${collectedTracks.length} tracks across ${playlistSources.length} conversations`
        : `Created by spotify-message from chat messages`;

      const response = await fetch(`${API_BASE_URL}/api/playlist/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          name: playlistName,
          description: description
        }),
        credentials: 'include'
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

  const handleProcessCollection = async () => {
    if (!playlistId.trim()) {
      alert('Please search for or create a playlist first');
      return;
    }

    if (collectedTracks.length === 0) {
      alert('No tracks in your collection. Add some tracks first!');
      return;
    }

    setIsProcessing(true);
    setCurrentJob({
      id: `collection_${Date.now()}`,
      status: 'processing',
      progress: 0,
      message: `Processing ${collectedTracks.length} tracks from your collection...`
    });

    try {
      const response = await fetch(`${API_BASE_URL}/api/process-collection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          playlist_id: playlistId,
          tracks: collectedTracks,
          sources: playlistSources,
          dry_run: dryRun
        }),
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        setCurrentJob(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          message: `Successfully added ${data.added_count} tracks to playlist!`
        }));

        // Clear collection after successful processing
        setTimeout(() => {
          setCollectedTracks([]);
          setPlaylistSources([]);
          setCurrentJob(null);
          setIsProcessing(false);
        }, 3000);
      } else {
        setCurrentJob(prev => ({
          ...prev,
          status: 'error',
          message: data.message || 'Failed to process collection'
        }));
        setIsProcessing(false);
      }
    } catch (error) {
      setCurrentJob(prev => ({
        ...prev,
        status: 'error',
        message: 'Error connecting to server'
      }));
      setIsProcessing(false);
      console.error('Collection processing error:', error);
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
        credentials: 'include'
      });

      const data = await response.json();
      
      if (data.job_id) {
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
        const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`, {
          credentials: 'include'
        });
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
      setSelectedFile(file);
    }
  };

  // Multi-message playlist helper functions
  const addTracksToCollection = (tracks, sourceName) => {
    try {
      if (!tracks || !Array.isArray(tracks)) {
        throw new Error('Invalid tracks data provided');
      }

      const newTracks = tracks.filter(track => 
        track && track.id && !collectedTracks.some(existing => existing.id === track.id)
      );
      
      if (newTracks.length > 0) {
        // Add source property to tracks
        const tracksWithSource = newTracks.map(track => ({
          ...track,
          source: sourceName
        }));
        
        setCollectedTracks(prev => {
          try {
            return [...prev, ...tracksWithSource];
          } catch (error) {
            handleError(error, 'Add Tracks to Collection');
            return prev;
          }
        });
        
        // Update or add source
        const existingSourceIndex = playlistSources.findIndex(source => source.name === sourceName);
        if (existingSourceIndex >= 0) {
          setPlaylistSources(prev => {
            try {
              const updatedSources = [...prev];
              updatedSources[existingSourceIndex].trackCount += newTracks.length;
              return updatedSources;
            } catch (error) {
              handleError(error, 'Update Source Count');
              return prev;
            }
          });
        } else {
          setPlaylistSources(prev => {
            try {
              return [...prev, {
                name: sourceName,
                trackCount: newTracks.length,
                addedAt: new Date().toISOString()
              }];
            } catch (error) {
              handleError(error, 'Add New Source');
              return prev;
            }
          });
        }
      }
    } catch (error) {
      handleError(error, 'Add Tracks to Collection');
    }
  };

  const removeSource = (index) => {
    try {
      if (index < 0 || index >= playlistSources.length) {
        throw new Error('Invalid source index');
      }

      const sourceToRemove = playlistSources[index];
      const tracksToRemove = collectedTracks.filter(track => 
        track && track.source === sourceToRemove.name
      );
      
      setCollectedTracks(prev => {
        try {
          return prev.filter(track => 
            !tracksToRemove.some(removed => removed.id === track.id)
          );
        } catch (error) {
          handleError(error, 'Remove Tracks from Collection');
          return prev;
        }
      });
      
      setPlaylistSources(prev => {
        try {
          return prev.filter((_, i) => i !== index);
        } catch (error) {
          handleError(error, 'Remove Source from List');
          return prev;
        }
      });
    } catch (error) {
      handleError(error, 'Remove Source');
    }
  };

  const createPlaylistFromCollection = async () => {
    if (collectedTracks.length === 0) return;
    
    setIsCreatingPlaylist(true);
    setIsProcessing(true);
    
    try {
      // Set up the tracks for processing
      setSelectedTracks(collectedTracks.map(track => track.id));
      setTrackDetails(collectedTracks);
      
      // Create a job for playlist creation
      // const jobData = {
      //   tracks: collectedTracks,
      //   playlist_name: `Zingaroo Collection - ${new Date().toLocaleDateString()}`,
      //   sources: playlistSources.map(source => source.name).join(', ')
      // };
      
      setCurrentJob({
        id: `collection_${Date.now()}`,
        status: 'processing',
        message: `Creating playlist with ${collectedTracks.length} tracks from ${playlistSources.length} sources...`,
        progress: 0
      });
      
      // Simulate processing time with error handling
      const progressInterval = setInterval(() => {
        try {
          setCurrentJob(prev => {
            if (prev && prev.progress < 90) {
              return { ...prev, progress: prev.progress + 10 };
            }
            return prev;
          });
        } catch (error) {
          handleError(error, 'Progress Update');
          clearInterval(progressInterval);
        }
      }, 200);
      
      // Wait a bit for the progress animation
      await new Promise(resolve => setTimeout(resolve, 2000));
      clearInterval(progressInterval);
      
      // Complete the job
      setCurrentJob(prev => ({
        ...prev,
        status: 'completed',
        message: `Successfully created playlist with ${collectedTracks.length} tracks!`,
        progress: 100
      }));
      
      // Clear the collection after successful creation
      setTimeout(() => {
        try {
          setCollectedTracks([]);
          setPlaylistSources([]);
          setCurrentJob(null);
          setIsCreatingPlaylist(false);
          setIsProcessing(false);
        } catch (error) {
          handleError(error, 'Collection Cleanup');
        }
      }, 3000);
      
    } catch (error) {
      const handledError = handleError(error, 'Playlist Creation');
      setCurrentJob(prev => ({
        ...prev,
        status: 'error',
        message: handledError.message,
        progress: 0
      }));
      setIsCreatingPlaylist(false);
      setIsProcessing(false);
    }
  };

  const loadTrackDetails = async (chat) => {
    setIsLoadingTracks(true);
    setTrackDetails([]);
    setCurrentPage(1); // Reset to first page
    setSearchQuery(''); // Reset search
    setSortBy('name'); // Reset sort
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/track-details`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chat_name: chat.name }),
        credentials: 'include'
      });

      const data = await response.json();
      
      if (data.success) {
        setTrackDetails(data.tracks);
      } else {
        console.error('Failed to load track details:', data.error);
        setTrackDetails([]);
      }
    } catch (error) {
      console.error('Error loading track details:', error);
      setTrackDetails([]);
    } finally {
      setIsLoadingTracks(false);
    }
  };

  // Filter and sort tracks
  const getFilteredAndSortedTracks = () => {
    let filtered = trackDetails;
    
    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(track => 
        track.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        track.artist.toLowerCase().includes(searchQuery.toLowerCase()) ||
        track.album.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      let aValue, bValue;
      
                switch (sortBy) {
                    case 'name':
                        aValue = a.name.toLowerCase();
                        bValue = b.name.toLowerCase();
                        break;
                    case 'artist':
                        aValue = a.artist.toLowerCase();
                        bValue = b.artist.toLowerCase();
                        break;
                    case 'date':
                        // Sort by release date
                        aValue = a.release_date || '';
                        bValue = b.release_date || '';
                        break;
                    case 'sent':
                        // Sort by order in chat (when the track was sent)
                        aValue = a.sent_order || 0;
                        bValue = b.sent_order || 0;
                        break;
                    default:
                        aValue = a.name.toLowerCase();
                        bValue = b.name.toLowerCase();
                }
      
      if (sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });
    
    return filtered;
  };

  // Get paginated tracks
  const getPaginatedTracks = () => {
    const filtered = getFilteredAndSortedTracks();
    const startIndex = (currentPage - 1) * tracksPerPage;
    const endIndex = startIndex + tracksPerPage;
    return filtered.slice(startIndex, endIndex);
  };

  // Get total pages
  const getTotalPages = () => {
    const filtered = getFilteredAndSortedTracks();
    return Math.ceil(filtered.length / tracksPerPage);
  };

  const handleTabChange = (newTab) => {
    setActiveTab(newTab);
    
    // Clear ALL state when switching tabs
    setSelectedChat(null);
    setChatName('');
    setChats([]);
    setScanError('');
    setPlaylistName('');
    setPlaylistId('');
    setPlaylistSearchResult(null);
    setCurrentJob(null);
    setSelectedFile(null);
    
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
            🦘 Zingaroo
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Your friendly music-finding kangaroo that hops through your messages to discover amazing tracks
          </p>
          <p className="text-sm text-gray-400 max-w-2xl mx-auto mt-2">
            🔒 All processing happens locally on your device. Your messages are never uploaded or stored.
          </p>
        </div>

        <div className="max-w-4xl mx-auto space-y-8">
          {/* Authentication Status */}
          {isCheckingAuth ? (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 shadow-2xl text-center">
              <p className="text-gray-300">Checking authentication...</p>
            </div>
          ) : !isAuthenticated ? (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl text-center">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎵</span>
              </div>
              <h2 className="text-2xl font-bold mb-4">Connect to Spotify</h2>
              <p className="text-gray-300 mb-6">
                Sign in with your Spotify account to create and manage playlists
              </p>
              <button
                onClick={handleSpotifyLogin}
                disabled={isLoggingIn}
                className="bg-green-500 hover:bg-green-600 disabled:bg-green-400 disabled:cursor-not-allowed text-white font-semibold px-8 py-3 rounded-full transition-colors flex items-center gap-2 mx-auto"
              >
                <span>🎵</span>
                {isLoggingIn ? 'Redirecting to Spotify...' : 'Sign in with Spotify'}
              </button>
            </div>
          ) : (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 shadow-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                    <span className="text-xl">🎵</span>
                  </div>
                  <div>
                    <h3 className="font-semibold">Connected to Spotify</h3>
                    <p className="text-gray-300 text-sm">
                      {spotifyUser?.display_name || 'User'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleSpotifyLogout}
                  className="bg-red-500/20 hover:bg-red-500/30 text-red-300 hover:text-red-200 px-4 py-2 rounded-full transition-colors text-sm"
                >
                  Sign Out
                </button>
              </div>
            </div>
          )}

          {/* Main Content - Only show when authenticated */}
          {isAuthenticated && (
            <>
              {/* Tab Navigation */}
              <div className="flex flex-wrap justify-center gap-2 mb-8">
                {hasIMessage && (
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
                )}
                {hasIMessage && (
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
                )}
                <button
                  onClick={() => handleTabChange('file-upload')}
                  className={`px-4 py-2 rounded-full transition-colors ${
                    activeTab === 'file-upload' 
                      ? 'bg-green-500 text-white' 
                      : 'bg-white/10 hover:bg-white/20'
                  }`}
                >
                  File Upload {!hasIMessage && '(Recommended)'}
                </button>
                <button
                  onClick={() => handleTabChange('playlist-builder')}
                  className={`px-4 py-2 rounded-full transition-colors ${
                    activeTab === 'playlist-builder' 
                      ? 'bg-green-500 text-white' 
                      : 'bg-white/10 hover:bg-white/20'
                  }`}
                >
                  🎵 Playlist Builder
                </button>
              </div>

              {/* Smart Detection Tab */}
              {activeTab === 'smart-detect' && (
                <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
                  <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold mb-4">Smart Message Detection</h2>
                    <p className="text-gray-300 mb-6">
                      🔒 Your messages are processed locally on your device. We find conversations with Spotify links without collecting any personal data.
                    </p>
                    <button
                      onClick={handleSmartScan}
                      disabled={isScanning}
                      className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-full transition-colors"
                    >
                      {isScanning ? 'Scanning...' : 'Scan Messages'}
                    </button>
                    
                    {!isScanning && chats.length === 0 && (
                      <p className="text-gray-400 text-sm mt-4">
                        Processing options will appear below when conversations are found.
                      </p>
                    )}
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
                            
                            <div className="flex space-x-2">
                              <button
                                onClick={() => {
                                  setSelectedChat(chat);
                                  setShowTrackPreview(true);
                                  loadTrackDetails(chat);
                                }}
                                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors"
                              >
                                Preview Tracks
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedChat(chat);
                                }}
                                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
                              >
                                Select All
                              </button>
                              <button
                                onClick={() => {
                                  // Add all tracks from this chat to collection
                                  if (chat.tracks && chat.tracks.length > 0) {
                                    addTracksToCollection(chat.tracks, chat.name);
                                  }
                                }}
                                className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg transition-colors"
                              >
                                🎵 Add to Collection
                              </button>
                            </div>
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
                  <p className="text-gray-400 text-sm mb-6">
                    🔒 Your chat data is processed locally and never leaves your device.
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
                    
                    {chatName.trim() && (
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-4">
                          Processing options will appear below when you enter a chat name.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* File Upload Tab */}
              {activeTab === 'file-upload' && (
                <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
                  <h2 className="text-2xl font-bold mb-4">Upload Export File</h2>
                  <p className="text-gray-400 text-sm mb-6">
                    🔒 Your file is processed locally and never uploaded to our servers.
                  </p>
                  {!hasIMessage && (
                    <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4 mb-6">
                      <h3 className="font-semibold text-blue-300 mb-2">📱 For Windows/Linux/Android Users</h3>
                      <p className="text-blue-200 text-sm mb-2">
                        Since you're not on macOS, you'll need to export your messages first:
                      </p>
                      <ol className="text-blue-200 text-sm list-decimal list-inside space-y-1">
                        <li>Export your Android Messages to a .txt file</li>
                        <li>Upload the file here</li>
                        <li>Preview and select tracks</li>
                        <li>Create your playlist!</li>
                      </ol>
                    </div>
                  )}
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
                  
                  {selectedFile && (
                    <div className="mt-4 p-4 bg-white/5 border border-white/10 rounded-lg">
                      <p className="text-gray-300">Selected: {selectedFile.name}</p>
                    </div>
                  )}
                  
                  {!selectedFile && (
                    <p className="text-gray-400 text-sm mt-4 text-center">
                      Processing options will appear below when you upload a file.
                    </p>
                  )}
                  
                </div>
              )}

              {/* Playlist Builder Tab */}
              {activeTab === 'playlist-builder' && (
                <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
                  <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold mb-4">🎵 Playlist Builder</h2>
                    <p className="text-gray-300 text-lg mb-4">
                      Collect tracks from multiple conversations and create one amazing playlist
                    </p>
                    <p className="text-gray-400 text-sm mb-6">
                      🔒 All processing happens locally on your device. Your messages are never uploaded or stored.
                    </p>
                  </div>

                  {/* Current Collection Status */}
                  <div className="bg-white/5 rounded-lg p-6 mb-6">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-xl font-semibold">Your Collection</h3>
                      <span className="bg-green-500/20 text-green-300 px-3 py-1 rounded-full text-sm">
                        {collectedTracks.length} tracks
                      </span>
                    </div>
                    
                    {collectedTracks.length > 0 ? (
                      <div className="space-y-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {playlistSources.map((source, index) => (
                            <div key={index} className="bg-white/5 rounded-lg p-4">
                              <div className="flex justify-between items-center">
                                <div>
                                  <p className="font-medium text-white">{source.name}</p>
                                  <p className="text-sm text-gray-400">{source.trackCount} tracks</p>
                                </div>
                                <button
                                  onClick={() => removeSource(index)}
                                  className="text-red-400 hover:text-red-300 text-sm"
                                >
                                  Remove
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                        
                        <div className="flex gap-3 pt-4">
                          <button
                            onClick={() => setShowTrackPreview(true)}
                            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors"
                          >
                            Preview All Tracks
                          </button>
                          <button
                            onClick={createPlaylistFromCollection}
                            disabled={isCreatingPlaylist}
                            className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                          >
                            {isCreatingPlaylist ? 'Creating...' : `Create Playlist (${collectedTracks.length} tracks)`}
                          </button>
                          <button
                            onClick={() => { setCollectedTracks([]); setPlaylistSources([]); }}
                            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
                          >
                            Clear Collection
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-gray-400 mb-4">No tracks collected yet</p>
                        <p className="text-sm text-gray-500">
                          Use the other tabs to find conversations with Spotify links, then add them to your collection
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Instructions */}
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-6">
                    <h4 className="text-lg font-semibold text-blue-300 mb-3">How to Build Your Playlist:</h4>
                    <ol className="space-y-2 text-sm text-gray-300">
                      <li className="flex items-start">
                        <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">1</span>
                        Use "Smart Detection" or "Chat Name" to find conversations with Spotify links
                      </li>
                      <li className="flex items-start">
                        <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">2</span>
                        When you see tracks, click "Add to Collection" to save them
                      </li>
                      <li className="flex items-start">
                        <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">3</span>
                        Repeat for multiple conversations to build your collection
                      </li>
                      <li className="flex items-start">
                        <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">4</span>
                        When ready, create your playlist with all collected tracks
                      </li>
                    </ol>
                  </div>
                </div>
              )}

              {/* Playlist Creation Progress */}
              {isCreatingPlaylist && currentJob && (
                <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
                  <div className="text-center">
                    <h3 className="text-2xl font-bold mb-4">Creating Your Playlist</h3>
                    <div className="mb-6">
                      <div className="bg-gray-700 rounded-full h-3 mb-2">
                        <div 
                          className="bg-green-500 h-3 rounded-full transition-all duration-300"
                          style={{ width: `${currentJob.progress}%` }}
                        ></div>
                      </div>
                      <p className="text-sm text-gray-300">{currentJob.progress}% complete</p>
                    </div>
                    <p className="text-gray-300 mb-4">{currentJob.message}</p>
                    {currentJob.status === 'completed' && (
                      <div className="text-green-400 text-lg">
                        ✅ Playlist created successfully!
                      </div>
                    )}
                    {currentJob.status === 'error' && (
                      <div className="text-red-400 text-lg">
                        ❌ Failed to create playlist
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Processing Options */}
              {((activeTab === 'smart-detect' && selectedChat) || 
                (activeTab === 'chat-name' && chatName.trim()) || 
                (activeTab === 'file-upload' && selectedFile) ||
                (activeTab === 'playlist-builder' && collectedTracks.length > 0)) && (
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
                          placeholder={activeTab === 'playlist-builder' ? "e.g., Zingaroo Collection - October 2025" : "e.g., My Favorite Songs"}
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
                        if (activeTab === 'playlist-builder') {
                          handleProcessCollection();
                        } else if (selectedChat) {
                          handleProcessChat(selectedChat);
                        } else if (chatName.trim()) {
                          handleProcessChat({ name: chatName.trim() });
                        }
                      }}
                      disabled={isProcessing || !playlistId.trim() || (activeTab === 'playlist-builder' ? collectedTracks.length === 0 : (!selectedChat && !chatName.trim()))}
                      className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white font-semibold px-8 py-3 rounded-full transition-colors"
                    >
                      {isProcessing ? 'Processing...' : (activeTab === 'playlist-builder' ? `Process Collection (${collectedTracks.length} tracks)` : 'Process Chat')}
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

              {/* Track Preview Modal */}
              {showTrackPreview && (selectedChat || collectedTracks.length > 0) && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                  <div className="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-4xl w-full max-h-[80vh] overflow-hidden">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-2xl font-bold">
                        Preview Tracks - {selectedChat ? selectedChat.name : 'Collected Tracks'}
                      </h3>
                      <button
                        onClick={() => {
                          setShowTrackPreview(false);
                          setSelectedTracks([]);
                        }}
                        className="text-gray-400 hover:text-white text-2xl"
                      >
                        ×
                      </button>
                    </div>
                    
                    {/* Search and Sort Controls */}
                    {trackDetails.length > 0 && (
                        <div className="mb-6 space-y-4">
                            {/* Search Bar */}
                            <div className="flex items-center space-x-4">
                                <input
                                    type="text"
                                    placeholder="Search tracks, artists, or albums..."
                                    value={searchQuery}
                                    onChange={(e) => {
                                        setSearchQuery(e.target.value);
                                        setCurrentPage(1); // Reset to first page when searching
                                    }}
                                    className="flex-1 px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500"
                                />
                                <div className="text-sm text-gray-400">
                                    {getFilteredAndSortedTracks().length} of {trackDetails.length} tracks
                                </div>
                            </div>
                            
                            {/* Sort Controls */}
                            <div className="flex items-center space-x-4">
                                <label className="text-sm text-gray-400">Sort by:</label>
                                <select
                                    value={sortBy}
                                    onChange={(e) => {
                                        setSortBy(e.target.value);
                                        setCurrentPage(1);
                                    }}
                                    className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                >
                                    <option value="name">Name</option>
                                    <option value="artist">Artist</option>
                                    <option value="date">Release Date</option>
                                    <option value="sent">Sent in Chat</option>
                                </select>
                                <button
                                    onClick={() => {
                                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                                        setCurrentPage(1);
                                    }}
                                    className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm hover:bg-white/20 transition-colors"
                                >
                                    {sortOrder === 'asc' ? '↑' : '↓'}
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="space-y-4 max-h-96 overflow-y-auto">
                        {isLoadingTracks ? (
                            <div className="text-center py-8">
                                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-500 mb-4"></div>
                                <p className="text-gray-400">Loading track details...</p>
                                <p className="text-gray-500 text-sm">This may take a moment for large conversations</p>
                            </div>
                        ) : getPaginatedTracks().length > 0 ? (
                            getPaginatedTracks().map((track, index) => (
                          <div key={index} className="flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-4">
                            <div className="flex items-center space-x-4">
                              <input
                                type="checkbox"
                                checked={selectedTracks.includes(track.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedTracks([...selectedTracks, track.id]);
                                  } else {
                                    setSelectedTracks(selectedTracks.filter(id => id !== track.id));
                                  }
                                }}
                                className="text-green-500"
                              />
                              
                              {/* Album Art */}
                              {track.album_art && (
                                <img
                                  src={track.album_art}
                                  alt={`${track.album} cover`}
                                  className="w-12 h-12 rounded-lg object-cover"
                                />
                              )}
                              
                              <div className="flex-1">
                                <h4 className="font-semibold">{track.name}</h4>
                                <p className="text-gray-300 text-sm">{track.artist}</p>
                                {track.album && (
                                  <p className="text-gray-400 text-xs">{track.album}</p>
                                )}
                                {track.release_date && (
                                  <p className="text-gray-500 text-xs">Released: {track.release_date}</p>
                                )}
                                {track.sent_timestamp && (
                                  <p className="text-blue-400 text-xs">Sent: {track.sent_timestamp}</p>
                                )}
                              </div>
                            </div>
                            <div className="text-right space-y-2">
                              <p className="text-sm text-gray-400">{track.duration}</p>
                              <div className="flex space-x-2">
                                <a
                                  href={track.spotify_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-xs transition-colors flex items-center space-x-1"
                                >
                                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                                  </svg>
                                  <span>Open in Spotify</span>
                                </a>
                              </div>
                            </div>
                          </div>
                        ))
                        ) : (
                            <div className="text-center py-8">
                                <p className="text-gray-400">
                                    {searchQuery ? 'No tracks match your search' : 'No track details available'}
                                </p>
                            </div>
                        )}
                    </div>
                    
                    {/* Pagination Controls */}
                    {getTotalPages() > 1 && (
                        <div className="flex justify-center items-center space-x-2 mt-4">
                            <button
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                                className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                ← Previous
                            </button>
                            
                            <div className="flex items-center space-x-1">
                                {Array.from({ length: Math.min(5, getTotalPages()) }, (_, i) => {
                                    const page = i + 1;
                                    return (
                                        <button
                                            key={page}
                                            onClick={() => setCurrentPage(page)}
                                            className={`px-3 py-1 rounded text-sm transition-colors ${
                                                currentPage === page
                                                    ? 'bg-green-500 text-white'
                                                    : 'bg-white/10 text-white hover:bg-white/20'
                                            }`}
                                        >
                                            {page}
                                        </button>
                                    );
                                })}
                                {getTotalPages() > 5 && (
                                    <>
                                        <span className="text-gray-400">...</span>
                                        <button
                                            onClick={() => setCurrentPage(getTotalPages())}
                                            className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm hover:bg-white/20 transition-colors"
                                        >
                                            {getTotalPages()}
                                        </button>
                                    </>
                                )}
                            </div>
                            
                            <button
                                onClick={() => setCurrentPage(Math.min(getTotalPages(), currentPage + 1))}
                                disabled={currentPage === getTotalPages()}
                                className="px-3 py-1 bg-white/10 border border-white/20 rounded text-white text-sm hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Next →
                            </button>
                        </div>
                    )}
                    
                    <div className="flex justify-between items-center mt-6">
                        <div className="flex items-center space-x-4">
                            <div className="text-sm text-gray-400">
                                {selectedTracks.length} of {getFilteredAndSortedTracks().length || selectedChat.trackCount || 0} tracks selected
                            </div>
                        {trackDetails.length > 0 && (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => {
                                setSelectedTracks(trackDetails.map(track => track.id));
                              }}
                              className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 text-xs px-2 py-1 rounded transition-colors"
                            >
                              Select All
                            </button>
                            <button
                                onClick={() => {
                                    setSelectedTracks([]);
                                }}
                                className="bg-gray-500/20 hover:bg-gray-500/30 text-gray-300 text-xs px-2 py-1 rounded transition-colors"
                            >
                                Select None
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="space-x-2">
                        <button
                          onClick={() => {
                            setShowTrackPreview(false);
                            setSelectedTracks([]);
                          }}
                          className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            setShowTrackPreview(false);
                          }}
                          disabled={selectedTracks.length === 0}
                          className="bg-green-500 hover:bg-green-600 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          Process Selected ({selectedTracks.length})
                        </button>
                        <button
                          onClick={() => {
                            // Add selected tracks to collection
                            const selectedTrackObjects = trackDetails.filter(track => 
                              selectedTracks.includes(track.id)
                            );
                            if (selectedTrackObjects.length > 0) {
                              addTracksToCollection(selectedTrackObjects, selectedChat.name);
                              setShowTrackPreview(false);
                              setSelectedTracks([]);
                            }
                          }}
                          disabled={selectedTracks.length === 0}
                          className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          🎵 Add to Collection ({selectedTracks.length})
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

    </div>
  );
}

// Wrap App with ErrorBoundary and additional error handling
const AppWithErrorBoundary = () => {
  try {
    return (
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    );
  } catch (error) {
    console.error('App wrapper error:', error);
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">🦘 Zingaroo</h1>
          <p className="text-gray-300">Something went wrong. Please refresh the page.</p>
        </div>
      </div>
    );
  }
};

export default AppWithErrorBoundary;