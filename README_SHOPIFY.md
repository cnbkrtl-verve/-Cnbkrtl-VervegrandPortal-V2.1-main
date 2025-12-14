# 🔄 Vervegrand Portal - Shopify Embedded App

A production-ready Shopify embedded application built with Python, Streamlit, and FastAPI. Designed for deployment on Render's free tier with a single exposed port.

## 🎯 Features

- ✅ **Shopify OAuth Integration** - Secure app installation and authentication
- ✅ **Polaris Design System** - Native Shopify look and feel
- ✅ **App Bridge Integration** - Toast notifications and native Shopify features
- ✅ **Single Port Deployment** - Optimized for Render free tier
- ✅ **Docker Support** - Containerized deployment with health checks
- ✅ **Production Ready** - Security headers, HMAC verification, session management

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Shopify Admin                   │
│  ┌───────────────────────────────────┐ │
│  │   Embedded App (iframe)           │ │
│  │   ┌─────────────────────────┐    │ │
│  │   │   Streamlit Interface   │    │ │
│  │   └─────────────────────────┘    │ │
│  └───────────────────────────────────┘ │
└────────────────┬────────────────────────┘
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────┐
│   Render (Port 8000)                    │
│  ┌─────────────────────────────────┐   │
│  │  FastAPI Gateway                │   │
│  │  • OAuth (/auth/*)              │   │
│  │  • Proxy to Streamlit           │   │
│  │  • CSP Headers                  │   │
│  └──────────────┬──────────────────┘   │
│                 │ Internal              │
│  ┌──────────────▼──────────────────┐   │
│  │  Streamlit App (Port 8501)      │   │
│  │  • Product Management           │   │
│  │  • Polaris Styled UI            │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Why This Architecture?

**Problem**: Render's free tier exposes only ONE port, but we need:
1. OAuth endpoints for Shopify authentication
2. Streamlit UI for the application interface

**Solution**: FastAPI acts as a gateway on the exposed port (8000), handling OAuth and proxying requests to Streamlit running internally on port 8501.

**Benefits**:
- ✅ Works on Render free tier
- ✅ No complex Nginx configuration
- ✅ Python-native solution
- ✅ Full control over routing and security
- ✅ Easy to debug and maintain

## 📋 Quick Start

### Prerequisites

1. **Shopify Partner Account** - [Create one](https://partners.shopify.com/)
2. **Render Account** - [Sign up](https://render.com/)
3. **Docker** (for local testing) - [Install](https://www.docker.com/)

### 1. Create Shopify App

1. Go to [Shopify Partners Dashboard](https://partners.shopify.com/)
2. Create a new app
3. Note your **API Key** and **API Secret**
4. Configure URLs (update after deployment):
   - App URL: `https://your-app.onrender.com/app`
   - Redirect URL: `https://your-app.onrender.com/auth/callback`

### 2. Local Testing

```bash
# Clone repository
git clone <your-repo-url>
cd vervegrand-portal

# Create environment file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Test locally with Docker
./test-local.sh

# Access at http://localhost:8000
```

### 3. Deploy to Render

#### Option A: Dashboard (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `vervegrand-shopify-app`
   - **Environment**: `Docker`
   - **Plan**: `Free`
   - **Health Check Path**: `/health`
5. Add environment variables:
   ```
   SHOPIFY_API_KEY=your_api_key
   SHOPIFY_API_SECRET=your_api_secret
   APP_URL=https://vervegrand-shopify-app.onrender.com
   SHOPIFY_SCOPES=read_products,write_products,read_orders
   SESSION_SECRET=<generate-random-32-chars>
   ```
6. Click **Create Web Service**

#### Option B: Blueprint (Automated)

```bash
# Push code with render.yaml
git push origin main

# In Render Dashboard:
# New → Blueprint → Connect repository → Deploy
```

### 4. Update Shopify App Settings

After deployment, update your Shopify app:
- **App URL**: `https://your-app.onrender.com/app`
- **Redirect URL**: `https://your-app.onrender.com/auth/callback`

### 5. Install & Test

Visit: `https://your-app.onrender.com/auth/shopify?shop=your-store.myshopify.com`

## 📁 Project Structure

```
├── main.py                      # FastAPI OAuth gateway
├── utils_ui.py                  # Shopify Polaris UI components
├── streamlit_app.py             # Original Streamlit app
├── streamlit_app_shopify.py     # Shopify-integrated version
├── app_example.py               # Full example with all features
├── Dockerfile                   # Container definition
├── start.sh                     # Startup script (runs both services)
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render configuration
├── .env.example                 # Environment variables template
├── .dockerignore                # Docker build exclusions
├── test-local.sh                # Local testing script
├── DEPLOYMENT_GUIDE.md          # Comprehensive deployment guide
└── README.md                    # This file
```

## 🎨 Using Shopify Polaris Styling

### Basic Integration

Add to the top of every Streamlit page:

```python
from utils_ui import inject_shopify_style, inject_app_bridge_js

# Apply Shopify Polaris styling
inject_shopify_style()
inject_app_bridge_js()

st.title("My Page")
# Rest of your page...
```

### Polaris Cards

```python
from utils_ui import create_polaris_card

create_polaris_card(
    title="Sales Overview",
    content="<p>Total: <strong>$12,345</strong></p>",
    status="success"  # success | warning | error | info
)
```

### Toast Notifications

```python
from utils_ui import show_shopify_toast

if st.button("Save"):
    # Your save logic
    show_shopify_toast("Saved successfully!", is_error=False)
```

### Complete Example

See [app_example.py](./app_example.py) for a full working implementation.

## 🔒 Security Features

### 1. Content Security Policy (CSP)
Properly configured CSP headers allow embedding in Shopify admin:
```python
Content-Security-Policy: frame-ancestors https://{shop} https://admin.shopify.com;
```

### 2. HMAC Verification
All OAuth callbacks verify Shopify's HMAC signature:
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
- Secure session middleware with encryption
- Access token storage (use database in production)
- CSRF protection via state parameter

### 4. HTTPS Enforcement
- Shopify requires HTTPS for embedded apps
- Render provides free SSL certificates
- All OAuth redirects use HTTPS

## 🐛 Troubleshooting

### App won't load in iframe

**Issue**: Browser blocks due to CSP

**Fix**: Check CSP headers in `main.py`:
```python
response.headers["Content-Security-Policy"] = (
    f"frame-ancestors https://{shop} https://admin.shopify.com;"
)
```

### OAuth fails

**Issue**: HMAC verification error

**Fix**: 
1. Verify `SHOPIFY_API_SECRET` is correct
2. Check callback URL matches Shopify settings exactly
3. View logs: Render Dashboard → Your Service → Logs

### Streamlit won't start

**Issue**: Port conflict or timeout

**Fix**:
```bash
# Check logs
cat /app/logs/streamlit.log

# Verify environment
echo $STREAMLIT_PORT

# Test locally
./test-local.sh
```

### Cold start is slow (Free tier)

**Issue**: Render spins down after 15 minutes

**Solution**: Use [UptimeRobot](https://uptimerobot.com/) to ping `/health` every 5 minutes

## 📊 Monitoring

### Health Check
```bash
curl https://your-app.onrender.com/health
# {"status":"healthy","service":"shopify-app-gateway"}
```

### View Logs
- **Render Dashboard** → Your Service → Logs
- **In container**: 
  - FastAPI: `/app/logs/fastapi.log`
  - Streamlit: `/app/logs/streamlit.log`

## 🚀 Performance Tips

### 1. Cache Data
```python
@st.cache_data(ttl=3600)
def load_products():
    return fetch_products()
```

### 2. Use Session State
```python
if 'products' not in st.session_state:
    st.session_state.products = load_products()
```

### 3. Database for Production
Replace session-based storage with:
- **PostgreSQL** (Render free 90-day instance)
- **SQLite** (simple, file-based)
- **Redis** (caching & sessions)

## 📚 Documentation

- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[Shopify App Bridge](https://shopify.dev/docs/api/app-bridge)** - Shopify integration docs
- **[Polaris Design System](https://polaris.shopify.com/)** - UI component library
- **[FastAPI Docs](https://fastapi.tiangolo.com/)** - API framework
- **[Streamlit Docs](https://docs.streamlit.io/)** - UI framework

## 🔄 Updating

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Render auto-deploys
# Or manual deploy in Dashboard → Manual Deploy
```

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SHOPIFY_API_KEY` | ✅ | Your Shopify app's API key |
| `SHOPIFY_API_SECRET` | ✅ | Your Shopify app's API secret |
| `APP_URL` | ✅ | Your app's public URL |
| `SHOPIFY_SCOPES` | ❌ | OAuth scopes (default: read_products,write_products) |
| `SESSION_SECRET` | ❌ | Session encryption key (auto-generated if not set) |
| `PORT` | ❌ | Main port (Render sets automatically) |
| `STREAMLIT_PORT` | ❌ | Internal Streamlit port (default: 8501) |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: See `DEPLOYMENT_GUIDE.md`
- **Shopify Help**: [Shopify Community](https://community.shopify.com/)

---

**Built with ❤️ for Shopify merchants**

🔗 [Shopify App Store](#) | 📧 [Support Email](#) | 📖 [Documentation](./DEPLOYMENT_GUIDE.md)
