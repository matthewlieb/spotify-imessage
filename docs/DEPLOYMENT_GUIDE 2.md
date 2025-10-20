# 🚀 Zingaroo Deployment Guide

## Free Deployment Options

### 🌐 Frontend: Netlify (Free)
- **URL**: `https://zingaroo.netlify.app` (free subdomain)
- **Custom Domain**: `zingaroo.com` or `zingaroo.app` (if available)
- **SSL**: Automatic HTTPS
- **CDN**: Global content delivery

### 🔧 Backend: Railway (Free Tier)
- **URL**: `https://zingaroo-backend.railway.app`
- **Free Tier**: 500 hours/month
- **Database**: PostgreSQL included
- **Environment Variables**: Secure storage

## 🎯 Deployment Steps

### 1. Deploy Frontend to Netlify

#### Option A: Drag & Drop (Easiest)
1. Go to [netlify.com](https://netlify.com)
2. Sign up/login with GitHub
3. Drag the `build/` folder to Netlify
4. Get instant deployment at `zingaroo.netlify.app`

#### Option B: GitHub Integration
1. Push code to GitHub repository
2. Connect Netlify to GitHub repo
3. Auto-deploy on every push
4. Custom domain setup

### 2. Deploy Backend to Railway

#### Quick Deploy:
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Connect your repository
4. Deploy Flask app
5. Set environment variables

#### Environment Variables Needed:
```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://zingaroo.netlify.app/callback
FLASK_SECRET_KEY=your_secret_key
```

### 3. Custom Domain Setup

#### Free Domain Options:
- **Netlify Subdomain**: `zingaroo.netlify.app` (instant)
- **Custom Domain**: Check availability at:
  - `zingaroo.com`
  - `zingaroo.app`
  - `zingaroo.dev`
  - `getzingaroo.com`

#### Domain Registration (if needed):
- **Namecheap**: ~$10/year for .com domains
- **Google Domains**: ~$12/year
- **Cloudflare**: Competitive pricing

## 🔧 Configuration Updates

### Update API URLs:
```javascript
// In src/App.js
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://zingaroo-backend.railway.app'
  : 'http://localhost:8004';
```

### Environment Variables:
```bash
# Frontend (.env.production)
REACT_APP_API_URL=https://zingaroo-backend.railway.app

# Backend (Railway)
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=https://zingaroo.netlify.app/callback
FLASK_SECRET_KEY=your_secret_key
```

## 🎉 Launch Checklist

- [ ] Build React app (`npm run build`)
- [ ] Deploy frontend to Netlify
- [ ] Deploy backend to Railway
- [ ] Update API URLs
- [ ] Test Spotify OAuth flow
- [ ] Set up custom domain (optional)
- [ ] Update Spotify app redirect URI
- [ ] Test all features
- [ ] Share the live URL!

## 💰 Cost Breakdown

### Free Tier:
- **Netlify**: Free (100GB bandwidth/month)
- **Railway**: Free (500 hours/month)
- **Domain**: Free subdomain included

### Optional Upgrades:
- **Custom Domain**: $10-15/year
- **Railway Pro**: $5/month (if needed)
- **Netlify Pro**: $19/month (if needed)

## 🚀 Quick Start Commands

```bash
# Build for production
npm run build

# Test production build locally
npx serve -s build -l 3000

# Deploy to Netlify (after setup)
netlify deploy --prod --dir=build
```

## 🔗 Useful Links

- [Netlify](https://netlify.com) - Frontend hosting
- [Railway](https://railway.app) - Backend hosting
- [Namecheap](https://namecheap.com) - Domain registration
- [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

---

**Ready to launch Zingaroo! 🦘🎵**
