# Frontend Deployment Options

## Option 1: Modal (Serverless Functions)
**Pros:**
- Same platform as backend
- Single deployment workflow
- No additional accounts needed

**Cons:**
- Overkill for static files
- Higher cost than static hosting
- Function cold starts

**Deploy:**
```bash
./deploy_frontend.sh
```

## Option 2: Vercel (Recommended for React)
**Pros:**
- Free tier generous
- Optimized for React/Next.js
- Automatic deployments from Git
- Global CDN
- Zero configuration

**Deploy:**
```bash
cd frontend_app
npx vercel --prod
```

## Option 3: Netlify
**Pros:**
- Free tier available
- Great developer experience
- Form handling, functions
- Easy rollbacks

**Deploy:**
```bash
cd frontend_app
npm run build
npx netlify deploy --prod --dir=dist
```

## Option 4: Cloudflare Pages
**Pros:**
- Unlimited bandwidth on free tier
- Fast global CDN
- Automatic deployments

**Deploy:**
```bash
cd frontend_app
npm run build
npx wrangler pages deploy dist --project-name=recipe-chat
```

## Option 5: GitHub Pages
**Pros:**
- Free for public repos
- Integrated with GitHub

**Cons:**
- Requires routing workaround for SPAs
- Public repos only (free tier)

**Deploy:**
```bash
cd frontend_app
npm install --save-dev gh-pages
# Add to package.json: "homepage": "https://username.github.io/recipe-chat"
npm run build
npx gh-pages -d dist
```

## Recommendation

For a production React app, I recommend **Vercel** or **Netlify**:
1. They're designed for frontend hosting
2. Free tiers are generous
3. Automatic HTTPS
4. Global CDN included
5. Much simpler than Modal for static files

If you want everything on Modal for simplicity, use the provided Modal deployment. Otherwise, Vercel will give you the best performance and developer experience for a React SPA.