# Spotify OAuth Setup Guide

This guide will help you set up Spotify OAuth authentication for the spotify-message web app, so users can sign in directly through Spotify instead of manually configuring API keys.

## Prerequisites

- A Spotify account (free or premium)
- Access to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

## Step 1: Create a Spotify App

1. **Go to the Spotify Developer Dashboard**
   - Visit: https://developer.spotify.com/dashboard
   - Log in with your Spotify account

2. **Create a New App**
   - Click "Create App"
   - Fill in the app details:
     - **App name**: `spotify-message` (or any name you prefer)
     - **App description**: `Extract Spotify tracks from message exports and create playlists`
     - **Website**: `http://localhost:3000` (for development)
     - **Redirect URI**: `http://127.0.0.1:8004/callback`
     - **API/SDKs**: Check "Web API"
   - Click "Save"

3. **Get Your Credentials**
   - After creating the app, you'll see your app dashboard
   - Note down your **Client ID** and **Client Secret**
   - Click "Show Client Secret" to reveal it

## Step 2: Configure Environment Variables

Create a `.env` file in the `web-react` directory with your Spotify credentials:

```bash
# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8004/callback

# Flask Session Secret (optional - will auto-generate if not provided)
FLASK_SECRET_KEY=your_secret_key_here
```

## Step 3: Update Redirect URIs (Important!)

1. **Go back to your Spotify app settings**
2. **Add additional redirect URIs** for different environments:
   - `http://127.0.0.1:8004/callback` (development)
   - `http://localhost:8004/callback` (alternative development)
   - `https://yourdomain.com/callback` (production - when you deploy)

3. **Save the changes**

## Step 4: Test the Setup

1. **Start the application**:
   ```bash
   cd web-react
   ./start.sh  # macOS/Linux
   # or
   start.bat   # Windows
   ```

2. **Open the web app**:
   - Go to `http://localhost:3000`
   - You should see a "Connect to Spotify" button

3. **Test the OAuth flow**:
   - Click "Sign in with Spotify"
   - You'll be redirected to Spotify's authorization page
   - Grant the requested permissions
   - You'll be redirected back to the app
   - You should see your Spotify profile information

## OAuth Scopes

The app requests the following Spotify permissions:
- `playlist-modify-public`: Create and modify public playlists
- `playlist-modify-private`: Create and modify private playlists  
- `playlist-read-private`: Read your private playlists
- `user-read-private`: Read your profile information

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI" error**
   - Make sure the redirect URI in your Spotify app settings exactly matches `http://127.0.0.1:8004/callback`
   - Check for typos in the URI

2. **"Invalid client" error**
   - Verify your Client ID and Client Secret are correct
   - Make sure they're properly set in your `.env` file

3. **Session not persisting**
   - Check that `FLASK_SECRET_KEY` is set in your environment
   - Clear your browser cookies and try again

4. **CORS errors**
   - Make sure the Flask server is running on the correct port
   - Check that the frontend is making requests to the right backend URL

### Development vs Production

**Development Setup:**
- Use `http://127.0.0.1:8004/callback` as redirect URI
- Run both frontend and backend locally

**Production Setup:**
- Update redirect URI to your production domain
- Set up proper SSL certificates
- Update environment variables for production

## Security Notes

- **Never commit your `.env` file** to version control
- **Use environment variables** in production
- **Rotate your Client Secret** periodically
- **Use HTTPS** in production for secure OAuth flow

## Next Steps

Once OAuth is working:
1. Users can sign in with their Spotify accounts
2. No manual API key configuration needed
3. Playlist creation and management works seamlessly
4. Users can access their own playlists and create new ones

## Support

If you encounter issues:
1. Check the browser console for errors
2. Check the Flask server logs
3. Verify your Spotify app settings
4. Ensure all environment variables are set correctly
