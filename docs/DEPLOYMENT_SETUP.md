# 🚀 Zingaroo Deployment Setup Guide

## 📋 Branch Strategy (Best Practices)

### **Branch Structure:**
- **`main`** - Production-ready code (deploys to live sites)
- **`develop`** - Development integration branch (staging/preview)
- **`feature/*`** - Individual feature branches

### **Workflow:**
1. Create feature branches from `develop`
2. Merge features into `develop` for testing
3. Merge `develop` into `main` for production releases

## 🌐 Netlify Setup (Frontend)

### **1. Connect Repository:**
1. Go to [netlify.com](https://netlify.com) → "New site from Git"
2. Connect GitHub repo: `matthewlieb/spotify-imessage`
3. Select branch: **`main`** (for production)
4. Build settings are auto-configured from `.netlify.toml`

### **2. Environment Variables (if needed):**
- Go to Site settings → Build & deploy → Environment variables
- Add any frontend environment variables here
- **Never commit sensitive keys to GitHub**

### **3. Custom Domain (optional):**
- Go to Domain management → Add custom domain
- Configure DNS settings as instructed

## 🚂 Railway Setup (Backend)

### **1. Connect Repository:**
1. Go to [railway.app](https://railway.app) → "New Project"
2. Connect GitHub repo: `matthewlieb/spotify-imessage`
3. Select branch: **`main`** (for production)
4. Railway will auto-detect configuration from `railway.json`

### **2. Environment Variables (REQUIRED):**
Go to your Railway service → Variables tab and add:

```
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=https://your-railway-url.railway.app/callback
FLASK_SECRET_KEY=your_flask_secret_key
```

### **3. Get Railway URL:**
- After deployment, copy your Railway URL
- Update `SPOTIPY_REDIRECT_URI` with the Railway URL + `/callback`
- Update Netlify's API proxy in `.netlify.toml` with the Railway URL

## 🔄 Continuous Deployment

### **Production (main branch):**
- **Netlify**: Auto-deploys from `main` branch
- **Railway**: Auto-deploys from `main` branch
- **URLs**: Live production URLs

### **Development (develop branch):**
- **Netlify**: Creates deploy previews for PRs
- **Railway**: Can create preview deployments
- **URLs**: Preview/staging URLs

## 🛡️ Security Best Practices

### **Environment Variables:**
- ✅ **DO**: Set in platform UI (Netlify/Railway)
- ❌ **DON'T**: Commit to GitHub
- ✅ **DO**: Use `.env.example` files for documentation

### **Branch Protection:**
1. Go to GitHub → Settings → Branches
2. Add rule for `main` branch:
   - Require pull request reviews
   - Require status checks to pass
   - Restrict pushes to `main`

## 📊 Monitoring & Health Checks

### **Railway Health Check:**
- Endpoint: `/api/health`
- Railway monitors this automatically
- Configured in `railway.json`

### **Netlify Build Status:**
- Check build logs in Netlify dashboard
- Monitor deploy status and build times

## 🔧 Troubleshooting

### **Common Issues:**

1. **Build Failures:**
   - Check build logs in platform dashboards
   - Verify environment variables are set
   - Ensure all dependencies are in `requirements.txt`

2. **API Connection Issues:**
   - Verify Railway URL is correct in Netlify proxy
   - Check CORS settings in Flask server
   - Ensure health check endpoint is working

3. **Environment Variables:**
   - Double-check all required variables are set
   - Verify Spotify redirect URI matches Railway URL
   - Test locally with same environment variables

## 🎯 Next Steps

1. **Set up Netlify** with `main` branch
2. **Set up Railway** with `main` branch  
3. **Configure environment variables** in both platforms
4. **Test the full deployment** end-to-end
5. **Set up branch protection** on GitHub
6. **Create your first feature branch** from `develop`

## 📞 Support

If you encounter issues:
1. Check the build logs in Netlify/Railway dashboards
2. Verify all environment variables are set correctly
3. Test the health check endpoint: `https://your-railway-url.railway.app/api/health`
4. Review the deployment configuration files in the repository
