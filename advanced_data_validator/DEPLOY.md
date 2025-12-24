# 🚀 Render.com Deployment Guide

## Quick Deploy Steps (5 minutes)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### Step 2: Deploy to Render.com
1. Go to **[render.com](https://render.com)** → Sign up/Login
2. Click **"New +"** → **"Web Service"**
3. Connect your **GitHub repo**
4. Configure:
   | Setting | Value |
   |---------|-------|
   | Name | `nyx-data-validator` |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

5. Add **Environment Variable**:
   - Key: `GOOGLE_API_KEY`
   - Value: Your Gemini API key

6. Click **"Create Web Service"**

### Step 3: Wait for Deployment
- Render will build and deploy (takes ~3-5 min)
- Get your live URL: `https://nyx-data-validator.onrender.com`

## ✅ Done!
Your app is now live! The backend serves the frontend automatically.
