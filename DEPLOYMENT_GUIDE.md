# Shopify Embedded App - Deployment Guide

## 🎯 Overview

This guide explains how to deploy your Streamlit application as a Shopify Embedded App on Render's free tier.

### Architecture

```
┌─────────────────────────────────────────┐
│         Shopify Admin                   │
│  ┌───────────────────────────────────┐ │
│  │   Embedded App (iframe)           │ │
│  │                                   │ │
│  │   ┌─────────────────────────┐    │ │
│  │   │   Your Streamlit App    │    │ │
│  │   └─────────────────────────┘    │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
           │
           │ HTTPS
           ▼
┌─────────────────────────────────────────┐
│   Render (Single Port: 8000)            │
│  ┌─────────────────────────────────┐   │
│  │  FastAPI Gateway (Port 8000)    │   │
│  │  - OAuth Flow (/auth/*)         │   │
│  │  - Proxy to Streamlit           │   │
│  │  - Security Headers (CSP)       │   │
│  └──────────────┬──────────────────┘   │
│                 │                        │
│  ┌──────────────▼──────────────────┐   │
│  │  Streamlit App (Port 8501)      │   │
│  │  - Internal only                │   │
│  │  - UI Components                │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Why This Architecture?

**Single Port Constraint**: Render's free tier exposes only ONE port. We solve this by:
1. **FastAPI on exposed port (8000)**: Handles OAuth and acts as a gateway
2. **Streamlit on internal port (8501)**: Runs the UI, accessed via FastAPI proxy
3. **Both start simultaneously**: Managed by `start.sh` script

This is superior to alternatives like:
- ❌ **Nginx**: Adds complexity, larger container size
- ❌ **Port forwarding tricks**: Unreliable on free tier
- ✅ **FastAPI proxy**: Lightweight, Python-native, full control

---

## 📋 Prerequisites

### 1. Create a Shopify App

1. Go to [Shopify Partners](https://partners.shopify.com/)
2. Create a new app
3. Note your:
   - **API Key** (Client ID)
   - **API Secret** (Client Secret)
4. Set **App URL** to: `https://your-app-name.onrender.com`
5. Set **Allowed redirection URL(s)** to: `https://your-app-name.onrender.com/auth/callback`

### 2. Required Environment Variables

You'll need these values:
- `SHOPIFY_API_KEY`: Your app's API key
- `SHOPIFY_API_SECRET`: Your app's API secret
- `APP_URL`: Your Render app URL
- `SHOPIFY_SCOPES`: OAuth scopes (e.g., `read_products,write_products`)

---

## 🚀 Deployment Steps

### Step 1: Prepare Your Repository

Ensure these files are in your repo:
```
├── Dockerfile              ← Container definition
├── start.sh               ← Startup script
├── main.py                ← FastAPI OAuth gateway
├── utils_ui.py            ← Shopify Polaris styling
├── streamlit_app.py       ← Your main Streamlit app
├── requirements.txt       ← Python dependencies
└── render.yaml            ← (Optional) Render configuration
```

### Step 2: Deploy to Render

#### Option A: Using Render Dashboard (Recommended)

1. **Create New Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Name**: `vervegrand-shopify-app`
   - **Environment**: `Docker`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Plan**: `Free`

3. **Add Environment Variables**
   ```
   SHOPIFY_API_KEY=your_api_key_here
   SHOPIFY_API_SECRET=your_api_secret_here
   APP_URL=https://vervegrand-shopify-app.onrender.com
   SHOPIFY_SCOPES=read_products,write_products,read_orders,write_orders
   SESSION_SECRET=generate_random_32_char_string
   ```

4. **Advanced Settings**
   - **Docker Command**: Leave empty (uses CMD from Dockerfile)
   - **Health Check Path**: `/health`

5. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete (~5-10 minutes)

#### Option B: Using Render Blueprint (render.yaml)

1. Push code with `render.yaml` to your repo
2. In Render Dashboard:
   - Click "New" → "Blueprint"
   - Connect repository
   - Set environment variables in dashboard
3. Deploy automatically

### Step 3: Configure Shopify App

Once deployed, update your Shopify app settings:

1. **App URL**: `https://your-app-name.onrender.com/app`
2. **Allowed redirection URL(s)**: `https://your-app-name.onrender.com/auth/callback`
3. **Embedded app**: Enable
4. **App bridge version**: 3.0

### Step 4: Test Installation

1. Go to your app's installation URL:
   ```
   https://your-app-name.onrender.com/auth/shopify?shop=your-test-store.myshopify.com
   ```
2. Authorize the app
3. You should see your Streamlit app embedded in Shopify admin

---

## 🎨 Adapting Your Streamlit Pages

### Basic Integration

Add these lines to the **top of every page**:

```python
from utils_ui import inject_shopify_style, inject_app_bridge_js

# Apply Shopify Polaris styling
inject_shopify_style()
inject_app_bridge_js()

# Rest of your page code...
st.title("My Page")
```

### Using Polaris Cards

```python
from utils_ui import create_polaris_card

create_polaris_card(
    title="Sales Overview",
    content="<p>Total sales: <strong>$12,345</strong></p>",
    status="success"  # success, warning, error, info
)
```

### Showing Toast Notifications

```python
from utils_ui import show_shopify_toast

if st.button("Save"):
    # Your save logic
    show_shopify_toast("Saved successfully!", is_error=False)
```

### Complete Example

See [app_example.py](./app_example.py) for a full working example.

---

## 🔒 Security Considerations

### 1. Content Security Policy (CSP)

The FastAPI gateway sets CSP headers to allow embedding:
```python
Content-Security-Policy: frame-ancestors https://{shop} https://admin.shopify.com;
```

### 2. HMAC Verification

All OAuth callbacks are verified using HMAC signatures:
```python
def verify_shopify_hmac(query_string: str, hmac_to_verify: str) -> bool:
    computed_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_hmac, hmac_to_verify)
```

### 3. Session Management

- Uses `SessionMiddleware` with secure secret
- Store access tokens securely (use database in production)
- Implement token refresh logic

### 4. HTTPS Only

- Shopify requires HTTPS for embedded apps
- Render provides free SSL certificates
- Never use HTTP in production

---

## 🐛 Troubleshooting

### App doesn't load in iframe

**Issue**: Browser blocks iframe due to CSP

**Solution**: Ensure CSP headers are correct in `main.py`:
```python
response.headers["Content-Security-Policy"] = (
    f"frame-ancestors https://{shop} https://admin.shopify.com;"
)
```

### OAuth callback fails

**Issue**: HMAC verification fails

**Solution**: 
1. Check `SHOPIFY_API_SECRET` is correct
2. Ensure callback URL matches exactly in Shopify settings
3. Check logs: `cat /app/logs/fastapi.log`

### Streamlit not starting

**Issue**: Port conflict or startup timeout

**Solution**:
1. Check logs: `cat /app/logs/streamlit.log`
2. Verify `STREAMLIT_PORT` environment variable
3. Ensure no other process is using port 8501

### Render service won't start

**Issue**: Build fails or health check fails

**Solution**:
1. Check Render logs in dashboard
2. Verify all environment variables are set
3. Test Dockerfile locally:
   ```bash
   docker build -t shopify-app .
   docker run -p 8000:8000 \
     -e SHOPIFY_API_KEY=your_key \
     -e SHOPIFY_API_SECRET=your_secret \
     -e APP_URL=http://localhost:8000 \
     shopify-app
   ```

### Styling looks wrong

**Issue**: CSS not applied or conflicts

**Solution**:
1. Ensure `inject_shopify_style()` is called at page top
2. Check for custom CSS conflicts in `style.css`
3. Clear browser cache

---

## 📊 Monitoring & Logs

### Access Logs on Render

1. Go to Render Dashboard
2. Select your service
3. Click "Logs" tab
4. Filter by service:
   - **FastAPI**: OAuth and routing logs
   - **Streamlit**: Application logs

### Log Files in Container

```bash
# SSH into container (Render Dashboard → Shell)
cat /app/logs/fastapi.log    # Gateway logs
cat /app/logs/streamlit.log  # Streamlit logs
```

### Health Check Endpoint

```bash
curl https://your-app.onrender.com/health
# Response: {"status":"healthy","service":"shopify-app-gateway"}
```

---

## 🚀 Performance Optimization

### 1. Cold Start Issue (Render Free Tier)

**Problem**: Free tier spins down after 15 minutes of inactivity

**Solutions**:
- Use [UptimeRobot](https://uptimerobot.com/) to ping `/health` every 5 minutes
- Upgrade to paid tier for always-on service
- Show loading message in Shopify App Bridge

### 2. Streamlit Performance

```python
# Cache expensive operations
@st.cache_data(ttl=3600)
def load_products():
    # Expensive API call
    return fetch_products()

# Use session state for data
if 'products' not in st.session_state:
    st.session_state.products = load_products()
```

### 3. Database Considerations

For production, replace session-based storage:
- **SQLite**: Simple, file-based (works on Render)
- **PostgreSQL**: Render provides free 90-day instances
- **Redis**: For caching and sessions

---

## 🔄 Updating Your App

### Push Updates

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Render will automatically rebuild and deploy.

### Manual Deploy

In Render Dashboard:
1. Go to your service
2. Click "Manual Deploy" → "Deploy latest commit"

### Rollback

In Render Dashboard:
1. Go to "Events" tab
2. Find previous successful deploy
3. Click "Rollback to this deploy"

---

## 📚 Additional Resources

- [Shopify App Bridge Documentation](https://shopify.dev/docs/api/app-bridge)
- [Shopify Polaris Design System](https://polaris.shopify.com/)
- [Render Documentation](https://render.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

## 🆘 Getting Help

1. **Check logs** first (both FastAPI and Streamlit)
2. **Verify environment variables** are set correctly
3. **Test locally** using Docker before deploying
4. **Review Shopify App settings** for correct URLs

---

## 📝 License

MIT License - See LICENSE file for details
