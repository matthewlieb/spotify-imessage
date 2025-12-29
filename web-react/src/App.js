/**
 * Spotify Message - Simple, Fast, Secure
 * 
 * Flow:
 * 1. Sign in with Spotify (SSO)
 * 2. Scan your iMessage chats
 * 3. Select a chat -> dropdown shows all tracks
 * 4. Name playlist and click create -> creates playlist with selected tracks
 */

import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_BASE = 'http://localhost:8004/api';

function App() {
  // Auth state
  const [auth, setAuth] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Chat scanning
  const [chats, setChats] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [selectedChat, setSelectedChat] = useState(null);
  const [tracks, setTracks] = useState([]);
  const [selectedTracks, setSelectedTracks] = useState(new Set());
  const [loadingTracks, setLoadingTracks] = useState(false);
  
  // Playlist creation
  const [playlistName, setPlaylistName] = useState('');
  const [creatingPlaylist, setCreatingPlaylist] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Check authentication
  useEffect(() => {
    fetch(`${API_BASE}/auth/status`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        setAuth(d.authenticated);
        setUser(d.user);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Handle OAuth callback - backend stores token in session, we just verify
  // Using useRef to prevent double execution in React StrictMode
  const callbackHandled = useRef(false);
  
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const authStatus = params.get('spotify_auth');
    
    // Prevent double execution (React StrictMode in development)
    if (callbackHandled.current) return;
    
    if (authStatus === 'success') {
      callbackHandled.current = true;
      
      // Backend already stored token in session during callback
      // Just check auth status - session is source of truth
      fetch(`${API_BASE}/auth/status`, { credentials: 'include' })
        .then(r => r.json())
        .then(status => {
          if (status.authenticated) {
            setAuth(true);
            setUser(status.user);
            setError('');
            window.history.replaceState({}, '', '/');
          } else {
            // Fallback: try token exchange if session check failed
            const token = params.get('token');
            if (token) {
              fetch(`${API_BASE}/auth/exchange-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ token })
              })
              .then(r => r.json())
              .then(d => {
                if (d.success) {
                  setAuth(true);
                  setUser(d.user);
                  setError('');
                } else {
                  setError('Authentication failed. Please try logging in again.');
                }
                window.history.replaceState({}, '', '/');
              })
              .catch(() => {
                setError('Authentication failed. Please try logging in again.');
                window.history.replaceState({}, '', '/');
              });
            } else {
              setError('Authentication failed. Please try logging in again.');
              window.history.replaceState({}, '', '/');
            }
          }
        })
        .catch(() => {
          setError('Authentication failed. Please try logging in again.');
          window.history.replaceState({}, '', '/');
        });
    } else if (authStatus === 'error') {
      callbackHandled.current = true;
      setError('Spotify authentication failed. Please try again.');
      window.history.replaceState({}, '', '/');
    }
  }, []);

  const login = () => {
    fetch(`${API_BASE}/auth/spotify`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (d.auth_url) window.location.href = d.auth_url;
      });
  };

  const scanChats = async () => {
    setScanning(true);
    setChats([]);
    setSelectedChat(null);
    setTracks([]);
    setSelectedTracks(new Set());
    setError('');
    
    try {
      const response = await fetch(`${API_BASE}/scan-imessage`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.error) {
        setError(`Scan failed: ${data.error}`);
      } else if (data.chats && data.chats.length > 0) {
        setChats(data.chats);
      } else {
        setError('No chats with Spotify tracks found');
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setScanning(false);
    }
  };

  const loadTracks = async (chatName) => {
    setSelectedChat(chatName);
    setLoadingTracks(true);
    setTracks([]);
    setSelectedTracks(new Set());
    setError('');
    setSuccess('');
    
    try {
      const response = await fetch(`${API_BASE}/track-details`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ chat_name: chatName })
      });
      const data = await response.json();
      
      if (data.success && data.tracks) {
        setTracks(data.tracks);
        // Select all tracks by default
        setSelectedTracks(new Set(data.tracks.map(t => t.id)));
      } else {
        // If auth error, suggest re-login
        if (data.requires_auth || (data.error && data.error.includes('authentication'))) {
          setError('Spotify authentication required. Please log out and sign in again.');
        } else {
          setError(`Failed to load tracks: ${data.error || 'Unknown error'}`);
        }
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setLoadingTracks(false);
    }
  };

  const toggleTrack = (trackId) => {
    const newSelected = new Set(selectedTracks);
    if (newSelected.has(trackId)) {
      newSelected.delete(trackId);
    } else {
      newSelected.add(trackId);
    }
    setSelectedTracks(newSelected);
  };

  const selectAllTracks = () => {
    setSelectedTracks(new Set(tracks.map(t => t.id)));
  };

  const deselectAllTracks = () => {
    setSelectedTracks(new Set());
  };

  const createPlaylistWithTracks = async () => {
    if (!playlistName.trim()) {
      setError('Please enter a playlist name');
      return;
    }
    
    if (selectedTracks.size === 0) {
      setError('Please select at least one track');
      return;
    }
    
    setCreatingPlaylist(true);
    setError('');
    setSuccess('');
    
    try {
      // Step 1: Create playlist
      const createResponse = await fetch(`${API_BASE}/playlist/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          name: playlistName.trim(),
          description: `Tracks from ${selectedChat || 'messages'}`
        })
      });
      const createData = await createResponse.json();
      
      if (!createData.success || !createData.playlist) {
        setError(`Failed to create playlist: ${createData.message || 'Unknown error'}`);
        setCreatingPlaylist(false);
        return;
      }
      
      const playlistId = createData.playlist.id;
      
      // Step 2: Add selected tracks
      const trackIds = Array.from(selectedTracks);
      const addResponse = await fetch(`${API_BASE}/playlist/add-tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          playlist_id: playlistId,
          track_ids: trackIds
        })
      });
      
      const addData = await addResponse.json();
      
      if (addData.success) {
        setSuccess(`✅ Created playlist "${playlistName}" and added ${addData.tracks_added || selectedTracks.size} track${selectedTracks.size !== 1 ? 's' : ''}!`);
        // Reset form
        setPlaylistName('');
        setSelectedTracks(new Set());
      } else {
        setError(`Playlist created but failed to add tracks: ${addData.error || 'Unknown error'}`);
      }
    } catch (error) {
      setError(`Error: ${error.message}`);
    } finally {
      setCreatingPlaylist(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-black to-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-spotify-500 mx-auto"></div>
          <p className="mt-4 text-white/60">Loading...</p>
        </div>
      </div>
    );
  }

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-black to-gray-900">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="mb-8">
            <h1 className="text-5xl font-bold mb-3 spotify-gradient-text">Spotify Message</h1>
            <p className="text-gray-400 text-lg">Turn your messages into playlists</p>
          </div>
          
          <button 
            onClick={login} 
            className="btn-primary text-lg px-8 py-4 w-full max-w-xs"
          >
            Sign in with Spotify
          </button>
          
          <p className="mt-6 text-sm text-gray-500">
            Secure • Fast • Simple
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold spotify-gradient-text">Spotify Message</h1>
            <p className="text-sm text-gray-400">Logged in as {user?.display_name}</p>
          </div>
          <button
            onClick={() => {
              fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
                .then(() => {
                  setAuth(false);
                  setUser(null);
                });
            }}
            className="btn-secondary text-sm"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {success && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-xl text-green-300">
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-300">
            {error}
          </div>
        )}

        {/* Step 1: Scan Chats */}
        <div className="glass-card p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-semibold mb-1">1. Scan Your Messages</h2>
              <p className="text-sm text-gray-400">Find all your group chats with Spotify links</p>
            </div>
            <button
              onClick={scanChats}
              disabled={scanning}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {scanning ? (
                <>
                  <span className="animate-spin inline-block mr-2">⏳</span>
                  Scanning...
                </>
              ) : (
                '🔍 Scan Messages'
              )}
            </button>
          </div>

          {chats.length > 0 && (
            <div className="mt-4">
              <label className="block text-sm font-medium mb-2 text-gray-300">
                2. Select a Chat
              </label>
              <select
                value={selectedChat || ''}
                onChange={(e) => {
                  if (e.target.value) {
                    loadTracks(e.target.value);
                  } else {
                    setSelectedChat(null);
                    setTracks([]);
                    setSelectedTracks(new Set());
                  }
                }}
                className="input-field w-full"
              >
                <option value="">-- Select a chat --</option>
                {chats.map((chat, idx) => (
                  <option key={idx} value={chat.name}>
                    {chat.name} ({chat.trackCount} tracks)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Step 2: View & Select Tracks (Dropdown) */}
        {tracks.length > 0 && (
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-2xl font-semibold mb-1">3. Select Tracks</h2>
                <p className="text-sm text-gray-400">
                  {selectedTracks.size} of {tracks.length} track{tracks.length !== 1 ? 's' : ''} selected
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={selectAllTracks}
                  className="btn-secondary text-sm"
                >
                  Select All
                </button>
                <button
                  onClick={deselectAllTracks}
                  className="btn-secondary text-sm"
                >
                  Deselect All
                </button>
              </div>
            </div>
            
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {tracks.map((track, idx) => (
                <div
                  key={idx}
                  onClick={() => toggleTrack(track.id)}
                  className={`flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedTracks.has(track.id)
                      ? 'bg-spotify-500/20 border-spotify-500/50'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedTracks.has(track.id)}
                    onChange={() => toggleTrack(track.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-5 h-5 rounded border-white/30 bg-white/10 text-spotify-500 focus:ring-spotify-500 focus:ring-2"
                  />
                  {track.album_art && (
                    <img
                      src={track.album_art}
                      alt={track.name}
                      className="w-12 h-12 rounded object-cover"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{track.name}</p>
                    <p className="text-sm text-gray-400 truncate">{track.artist}</p>
                  </div>
                  <div className="text-sm text-gray-500">{track.duration}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Create Playlist with Selected Tracks */}
        {tracks.length > 0 && (
          <div className="glass-card p-6">
            <h2 className="text-2xl font-semibold mb-4">4. Create Playlist</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-300">
                  Playlist Name
                </label>
                <input
                  type="text"
                  value={playlistName}
                  onChange={(e) => setPlaylistName(e.target.value)}
                  placeholder="My Awesome Playlist"
                  className="input-field w-full"
                  onKeyPress={(e) => e.key === 'Enter' && createPlaylistWithTracks()}
                />
              </div>
              <button
                onClick={createPlaylistWithTracks}
                disabled={creatingPlaylist || !playlistName.trim() || selectedTracks.size === 0}
                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creatingPlaylist ? (
                  <>
                    <span className="animate-spin inline-block mr-2">⏳</span>
                    Creating playlist and adding {selectedTracks.size} tracks...
                  </>
                ) : (
                  `✨ Create Playlist with ${selectedTracks.size} Selected Track${selectedTracks.size !== 1 ? 's' : ''}`
                )}
              </button>
            </div>
          </div>
        )}

        {loadingTracks && (
          <div className="glass-card p-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-spotify-500 mx-auto"></div>
            <p className="mt-4 text-gray-400">Loading tracks...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
