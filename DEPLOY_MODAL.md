# Deploying to Modal

## Prerequisites

1. Modal account and CLI installed:
```bash
pip install modal
modal setup
```

2. Your `.env` file configured with:
   - `GOOGLE_API_KEY` from https://ai.google.dev
   - `JWT_SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
   - `CORS_ORIGINS` updated with your frontend URLs (e.g., `"http://localhost:3000,https://your-app.vercel.app"`)

## Deployment Steps

### 1. Create Modal Secrets from .env

```bash
# Create Modal secrets from your .env file
python create_modal_secrets.py

# Or if you need to update existing secrets:
modal secret delete recipe-chat-secrets
python create_modal_secrets.py
```

### 2. Deploy the Backend

```bash
# Deploy the FastAPI app
modal deploy modal_app.py
```

### 3. Initialize the Database

```bash
# Run the database initialization
modal run modal_app.py::init_deployment
```

### 4. Get Your Backend URL

After deployment, Modal will show your app URL:
```
https://[your-username]--recipe-chat-assistant-fastapi-app.modal.run
```

### 5. Test the Deployment

```bash
# Check health endpoint
curl https://[your-username]--recipe-chat-assistant-fastapi-app.modal.run/health

# View API docs
# Visit: https://[your-username]--recipe-chat-assistant-fastapi-app.modal.run/docs
```

## Frontend Deployment

The frontend needs to be deployed separately (e.g., on Vercel, Netlify, or GitHub Pages).

### Update Frontend API URL

Edit `frontend_app/src/stores/authStore.js` and other files to use your Modal backend URL:

```javascript
const API_URL = 'https://[your-username]--recipe-chat-assistant-fastapi-app.modal.run'
```

### Deploy to Vercel

```bash
cd frontend_app
npm install -g vercel
vercel
```

## Monitoring

- View logs: `modal logs recipe-chat-assistant`
- Modal dashboard: https://modal.com/dashboard

## Updating

To update the deployment after code changes:
```bash
modal deploy modal_app.py
```