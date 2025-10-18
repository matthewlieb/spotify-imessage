import React, { useState, useEffect } from 'react';

const SpotifyPlayer = ({ track, onClose }) => {
  const [player, setPlayer] = useState(null);
  const [deviceId, setDeviceId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [token, setToken] = useState(null);

  useEffect(() => {
    if (!track) return;

    // Initialize Spotify Web Playback SDK
    const initializePlayer = () => {
      // Wait for Spotify SDK to load
      if (typeof window === 'undefined' || !window.Spotify) {
        setError('Spotify Web Playback SDK not loaded. Please refresh the page.');
        return;
      }

      const tokenData = localStorage.getItem('spotify_token');
      if (!tokenData) {
        setError('Spotify authentication required. Please log in to Spotify first.');
        return;
      }
      
      let extractedToken;
      try {
        const parsed = JSON.parse(tokenData);
        extractedToken = parsed.access_token;
      } catch (e) {
        // Fallback for old format
        extractedToken = tokenData;
      }
      
      if (!extractedToken) {
        setError('Invalid Spotify token. Please log in again.');
        return;
      }
      
      // Store token in state for use in other functions
      setToken(extractedToken);

      try {
        const spotifyPlayer = new window.Spotify.Player({
          name: 'Spotify Message Player',
          getOAuthToken: cb => cb(extractedToken),
          volume: 0.5
        });

      // Error handling
      spotifyPlayer.addListener('initialization_error', ({ message }) => {
        setError(`Initialization error: ${message}`);
      });

      spotifyPlayer.addListener('authentication_error', ({ message }) => {
        setError(`Authentication error: ${message}`);
      });

      spotifyPlayer.addListener('account_error', ({ message }) => {
        setError(`Account error: ${message}`);
      });

      spotifyPlayer.addListener('playback_error', ({ message }) => {
        setError(`Playback error: ${message}`);
      });

      // Playback status updates
      spotifyPlayer.addListener('player_state_changed', state => {
        if (!state) return;
        setIsPlaying(!state.paused);
      });

      // Ready
      spotifyPlayer.addListener('ready', ({ device_id }) => {
        console.log('Ready with Device ID', device_id);
        setDeviceId(device_id);
        setPlayer(spotifyPlayer);
        setIsLoading(false);
      });

      // Not Ready
      spotifyPlayer.addListener('not_ready', ({ device_id }) => {
        console.log('Device ID has gone offline', device_id);
      });

        // Connect to the player
        spotifyPlayer.connect();

        setPlayer(spotifyPlayer);
        setIsLoading(true);
      } catch (err) {
        setError(`Failed to initialize Spotify player: ${err.message}`);
        setIsLoading(false);
      }
    };

    initializePlayer();

    // Cleanup
    return () => {
      if (player) {
        player.disconnect();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track]);

  const playTrack = async () => {
    if (!player || !deviceId || !track) return;

    try {
      setIsLoading(true);
      setError(null);

      // Transfer playback to our device
      const response = await fetch(`https://api.spotify.com/v1/me/player`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          device_ids: [deviceId],
          play: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to transfer playback');
      }

      // Play the track
      const playResponse = await fetch(`https://api.spotify.com/v1/me/player/play?device_id=${deviceId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          uris: [track.spotify_url]
        })
      });

      if (!playResponse.ok) {
        throw new Error('Failed to play track');
      }

      setIsPlaying(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const pauseTrack = () => {
    if (player) {
      player.pause();
      setIsPlaying(false);
    }
  };

  const stopTrack = () => {
    if (player) {
      player.pause();
      setIsPlaying(false);
    }
  };

  if (!track) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-white/20 rounded-2xl p-6 max-w-md w-full">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">Preview Track</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <div className="space-y-4">
          {/* Track Info */}
          <div className="flex items-center space-x-4">
            {track.album_art && (
              <img
                src={track.album_art}
                alt={`${track.album} cover`}
                className="w-16 h-16 rounded-lg object-cover"
              />
            )}
            <div className="flex-1">
              <h4 className="font-semibold text-lg">{track.name}</h4>
              <p className="text-gray-300">{track.artist}</p>
              <p className="text-gray-400 text-sm">{track.album}</p>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3">
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}

          {/* Player Controls */}
          <div className="flex items-center justify-center space-x-4">
            {isLoading ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-500"></div>
                <span className="text-gray-400">Loading...</span>
              </div>
            ) : (
              <>
                {!isPlaying ? (
                  <button
                    onClick={playTrack}
                    className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-lg transition-colors flex items-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                    </svg>
                    <span>Play</span>
                  </button>
                ) : (
                  <button
                    onClick={pauseTrack}
                    className="bg-yellow-500 hover:bg-yellow-600 text-white px-6 py-2 rounded-lg transition-colors flex items-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 00-1 1v2a1 1 0 102 0V9a1 1 0 00-1-1zm4 0a1 1 0 00-1 1v2a1 1 0 102 0V9a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span>Pause</span>
                  </button>
                )}
                
                <button
                  onClick={stopTrack}
                  className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Stop
                </button>
              </>
            )}
          </div>

          {/* Track Link */}
          <div className="text-center">
            <a
              href={track.spotify_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-green-400 hover:text-green-300 text-sm"
            >
              Open in Spotify
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SpotifyPlayer;
