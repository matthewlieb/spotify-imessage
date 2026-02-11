# 🚀 Deployment Guide for spotify-message

## 💰 **Cheapest Deployment Options**

### **Option 1: FREE Deployment (Recommended)**
- **Frontend**: Vercel (Free) - React hosting
- **Backend**: Railway (Free tier) - Flask hosting
- **Total Cost**: $0/month

### **Option 2: Ultra-Cheap ($5/month)**
- **Frontend**: Netlify (Free)
- **Backend**: DigitalOcean App Platform ($5/month)
- **Total Cost**: $5/month

---

## 🎯 **Option 1: FREE Deployment (Railway + Vercel)**

### **Step 1: Deploy Backend to Railway (FREE)**

1. **Sign up for Railway**: https://railway.app
2. **Connect GitHub**: Link your repository
3. **Deploy Backend**:
   ```bash
   # In your project root
   cd web-react
   
   # Railway will auto-detect Python and use requirements.txt
   # Make sure these files exist:
   # - Procfile
   # - requirements.txt
   # - runtime.txt
   ```

4. **Set Environment Variables in Railway**:
   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=https://your-railway-app.railway.app/callback
   ```

5. **Get Railway URL**: `https://your-app-name.railway.app`

### **Step 2: Deploy Frontend to Vercel (FREE)**

1. **Sign up for Vercel**: https://vercel.com
2. **Connect GitHub**: Link your repository
3. **Build Settings**:
   - **Framework Preset**: Create React App
   - **Root Directory**: `web-react`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`

4. **Environment Variables in Vercel**:
   ```
   REACT_APP_API_URL=https://your-railway-app.railway.app
   ```

5. **Get Vercel URL**: `https://your-app-name.vercel.app`

### **Step 3: Update Frontend API URL**

Update the React app to use the production API:

```javascript
// In web-react/src/App.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8004';
```

---

## 🎯 **Option 2: DigitalOcean ($5/month)**

### **Step 1: Deploy Backend to DigitalOcean**

1. **Sign up for DigitalOcean**: https://digitalocean.com
2. **Create App Platform App**:
   - **Source**: GitHub repository
   - **Type**: Web Service
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `python server.py`

3. **Set Environment Variables**:
   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=https://your-app.ondigitalocean.app/callback
   ```

### **Step 2: Deploy Frontend to Netlify (FREE)**

1. **Sign up for Netlify**: https://netlify.com
2. **Connect GitHub**: Link your repository
3. **Build Settings**:
   - **Base Directory**: `web-react`
   - **Build Command**: `npm run build`
   - **Publish Directory**: `build`

---

## 🔧 **Pre-Deployment Checklist**

### **Backend Requirements**
- [ ] `Procfile` exists
- [ ] `requirements.txt` exists
- [ ] `runtime.txt` exists
- [ ] Environment variables configured
- [ ] Spotify OAuth redirect URI updated

### **Frontend Requirements**
- [ ] `package.json` has build script
- [ ] API URL updated for production
- [ ] Environment variables configured
- [ ] Build works locally: `npm run build`

### **Spotify App Configuration**
- [ ] Spotify Developer App created
- [ ] Redirect URI added: `https://your-backend-url.com/callback`
- [ ] Client ID and Secret obtained

---

## 🚀 **Quick Deploy Commands**

### **Test Production Build Locally**
```bash
cd web-react
npm run build
python server.py  # Test with PORT=8004
```

### **Deploy to Railway**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway link
railway up
```

### **Deploy to Vercel**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd web-react
vercel --prod
```

---

## 🔍 **Post-Deployment Testing**

1. **Backend Health Check**: `https://your-backend-url.com/api/health`
2. **Frontend Loads**: `https://your-frontend-url.com`
3. **Spotify OAuth**: Test login flow
4. **Track Preview**: Test with real data
5. **Playlist Creation**: Test end-to-end flow

---

## 🆘 **Troubleshooting**

### **Common Issues**
- **CORS Errors**: Make sure frontend URL is in CORS settings
- **OAuth Redirect**: Update Spotify app redirect URI
- **Environment Variables**: Double-check all are set correctly
- **Build Failures**: Check Node.js and Python versions

### **Support**
- Railway: https://railway.app/docs
- Vercel: https://vercel.com/docs
- DigitalOcean: https://docs.digitalocean.com

---

## 💡 **Cost Breakdown**

### **Option 1 (FREE)**
- Railway: $0/month (free tier)
- Vercel: $0/month (free tier)
- **Total**: $0/month

### **Option 2 ($5/month)**
- DigitalOcean: $5/month
- Netlify: $0/month (free tier)
- **Total**: $5/month

### **Option 3 ($3/month)**
- DigitalOcean Droplet: $3/month
- Vercel: $0/month (free tier)
- **Total**: $3/month

---

## 🎯 **Recommended: Start with Option 1 (FREE)**

This gives you:
- ✅ **Zero cost** deployment
- ✅ **Professional URLs** (your-app.railway.app)
- ✅ **Auto-scaling** and SSL
- ✅ **Easy updates** via GitHub
- ✅ **Perfect for portfolio** and testing

Once you get users and feedback, you can always upgrade to paid hosting for better performance!
