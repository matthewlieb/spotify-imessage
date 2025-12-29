/**
 * Spotify Message - Simple, Fast, Secure
 * 
 * Flow:
 * 1. Sign in with Spotify (SSO)
 * 2. Scan your iMessage chats
 * 3. View songs found in each chat (with selection)
 * 4. Create playlist and add selected tracks
 */

import React, { useState, useEffect } from 'react';
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
  const [playlistId, setPlaylistId] = useState(null);
  const [addingTracks, setAddingTracks] = useState(false);
  const [success, setSuccess] = useState('');

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

  // Handle OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (params.get('spotify_auth') === 'success' && token) {
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
          window.history.replaceState({}, '', '/');
        }
      });
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
    
    try {
      const response = await fetch(`${API_BASE}/scan-imessage`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.error) {
        alert(`Scan failed: ${data.error}`);
      } else if (data.chats && data.chats.length > 0) {
        setChats(data.chats);
      } else {
        alert('No chats with Spotify tracks found');
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setScanning(false);
    }
  };

  const loadTracks = async (chatName) => {
    setSelectedChat(chatName);
    setLoadingTracks(true);
    setTracks([]);
    setSelectedTracks(new Set());
    
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
        alert(`Failed to load tracks: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
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

  const createPlaylist = async () => {
    if (!playlistName.trim()) {
      alert('Please enter a playlist name');
      return;
    }
    
    setCreatingPlaylist(true);
    
    try {
      const response = await fetch(`${API_BASE}/playlist/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          name: playlistName.trim(),
          description: `Tracks from ${selectedChat || 'messages'}`
        })
      });
      const data = await response.json();
      
      if (data.success) {
        setPlaylistId(data.playlist.id);
        setSuccess(`✅ Created playlist: ${data.playlist.name}`);
      } else {
        alert(`Failed to create playlist: ${data.message || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setCreatingPlaylist(false);
    }
  };

  const addTracksToPlaylist = async () => {
    if (!playlistId) {
      alert('Please create a playlist first');
      return;
    }
    
    if (selectedTracks.size === 0) {
      alert('Please select at least one track');
      return;
    }
    
    setAddingTracks(true);
    setSuccess('');
    
    try {
      // Use the new endpoint to add specific tracks
      const trackIds = Array.from(selectedTracks);
      const response = await fetch(`${API_BASE}/playlist/add-tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          playlist_id: playlistId,
          track_ids: trackIds
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setAddingTracks(false);
        setSuccess(`✅ Successfully added ${data.tracks_added || selectedTracks.size} track${selectedTracks.size !== 1 ? 's' : ''} to playlist!`);
      } else {
        setAddingTracks(false);
        alert(`Error: ${data.error || 'Failed to add tracks'}`);
      }
    } catch (error) {
      setAddingTracks(false);
      alert(`Error: ${error.message}`);
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
            <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
              {chats.map((chat, idx) => (
                <button
                  key={idx}
                  onClick={() => loadTracks(chat.name)}
                  className={`w-full text-left p-4 rounded-lg border transition-all ${
                    selectedChat === chat.name
                      ? 'bg-spotify-500/20 border-spotify-500/50'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{chat.name}</p>
                      <p className="text-sm text-gray-400 mt-1">
                        {chat.trackCount} track{chat.trackCount !== 1 ? 's' : ''} • {chat.lastActivity}
                      </p>
                    </div>
                    {selectedChat === chat.name && loadingTracks && (
                      <div className="animate-spin">⏳</div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Step 2: View & Select Tracks */}
        {tracks.length > 0 && (
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-2xl font-semibold mb-1">2. Select Tracks</h2>
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

        {/* Step 3: Create Playlist & Add Tracks */}
        {tracks.length > 0 && (
          <div className="glass-card p-6">
            <h2 className="text-2xl font-semibold mb-4">3. Create Playlist & Add Selected Tracks</h2>
            
            {!playlistId ? (
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
                    onKeyPress={(e) => e.key === 'Enter' && createPlaylist()}
                  />
                </div>
                <button
                  onClick={createPlaylist}
                  disabled={creatingPlaylist || !playlistName.trim()}
                  className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {creatingPlaylist ? 'Creating...' : '✨ Create Playlist'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-green-500/20 border border-green-500/50 rounded-lg">
                  <p className="text-green-300">
                    ✅ Playlist "{playlistName}" created!
                  </p>
                </div>
                <button
                  onClick={addTracksToPlaylist}
                  disabled={addingTracks || selectedTracks.size === 0}
                  className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {addingTracks ? (
                    <>
                      <span className="animate-spin inline-block mr-2">⏳</span>
                      Adding {selectedTracks.size} tracks...
                    </>
                  ) : (
                    `➕ Add ${selectedTracks.size} Selected Track${selectedTracks.size !== 1 ? 's' : ''} to Playlist`
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
