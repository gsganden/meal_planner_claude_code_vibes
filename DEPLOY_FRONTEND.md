# Deploying the Frontend

## Prerequisites

1. Backend deployed on Modal (see DEPLOY_MODAL.md)
2. Your Modal backend URL (e.g., `https://gsganden--recipe-chat-assistant-fastapi-app.modal.run`)

## Setup for Production

### 1. Create Frontend Environment File

Create `frontend_app/.env.production`:
```bash
cd frontend_app
cp .env.example .env.production
```

Edit `.env.production` with your Modal backend URL:
```env
VITE_API_URL=https://gsganden--recipe-chat-assistant-fastapi-app.modal.run
VITE_ENVIRONMENT=production
```

### 2. Build for Production

```bash
cd frontend_app
npm install
npm run build
```

This creates an optimized production build in `frontend_app/dist/`.

## Deployment Options

### Option 1: Vercel (Recommended)

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
cd frontend_app
vercel
```

3. Follow the prompts:
   - Link to existing project or create new
   - Set project name
   - Choose build settings (auto-detected for Vite)

4. Set environment variables in Vercel dashboard:
   - Go to your project settings
   - Add environment variable:
     - Name: `VITE_API_URL`
     - Value: Your Modal backend URL

### Option 2: Netlify

1. Install Netlify CLI:
```bash
npm install -g netlify-cli
```

2. Deploy:
```bash
cd frontend_app
netlify deploy --prod --dir=dist
```

3. Set environment variables in Netlify dashboard:
   - Go to Site settings → Environment variables
   - Add `VITE_API_URL` with your Modal backend URL

### Option 3: GitHub Pages

1. Install gh-pages:
```bash
npm install --save-dev gh-pages
```

2. Add to `package.json`:
```json
{
  "scripts": {
    "predeploy": "npm run build",
    "deploy": "gh-pages -d dist"
  }
}
```

3. Deploy:
```bash
npm run deploy
```

Note: GitHub Pages requires additional configuration for client-side routing.

## Local Testing of Production Build

Test the production build locally before deploying:

```bash
cd frontend_app
npm run build
npm run preview
```

## CORS Configuration

Ensure your Modal backend allows requests from your frontend domain. Update the backend's CORS settings if needed:

```python
# In your Modal secrets or backend config
CORS_ORIGINS="https://your-frontend-domain.vercel.app,https://your-frontend.netlify.app"
```

## Post-Deployment Checklist

- [ ] Frontend loads without errors
- [ ] Can create new account (signup)
- [ ] Can login with existing account
- [ ] Can view recipe list
- [ ] Can create new recipes
- [ ] WebSocket chat connects successfully
- [ ] Can generate recipes via chat
- [ ] Autosave works correctly

## Troubleshooting

### API Connection Issues
- Check browser console for CORS errors
- Verify `VITE_API_URL` is set correctly
- Ensure backend is running and accessible

### WebSocket Connection Failed
- Check that WebSocket URL uses `wss://` for HTTPS backends
- Verify CORS allows WebSocket connections
- Check browser console for specific errors

### Build Failures
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for TypeScript/ESLint errors: `npm run lint`
- Ensure all environment variables are defined