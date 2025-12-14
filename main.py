"""
FastAPI Main Entry Point for Shopify Embedded App
Handles OAuth flow, session management, and routes traffic to Streamlit
"""

import os
import hmac
import hashlib
import base64
from typing import Optional
from urllib.parse import urlencode, parse_qs

from fastapi import FastAPI, Request, Response, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import httpx

# Shopify configuration from environment variables
SHOPIFY_API_KEY = os.environ.get("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.environ.get("SHOPIFY_API_SECRET", "")
SHOPIFY_SCOPES = os.environ.get(
    "SHOPIFY_SCOPES",
    "read_products,write_products,read_orders,write_orders,read_inventory,write_inventory"
)
APP_URL = os.environ.get("APP_URL", "https://your-app.onrender.com")
STREAMLIT_PORT = int(os.environ.get("STREAMLIT_PORT", "8501"))
SESSION_SECRET = os.environ.get("SESSION_SECRET", "your-secret-key-change-in-production")

app = FastAPI(title="Shopify Embedded App Gateway")

# Add session middleware for OAuth state management
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# CORS configuration for Shopify embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.myshopify.com", "https://admin.shopify.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_shopify_hmac(query_string: str, hmac_to_verify: str) -> bool:
    """
    Verify HMAC signature from Shopify
    """
    encoded_params = query_string.encode('utf-8')
    computed_hmac = hmac.new(
        SHOPIFY_API_SECRET.encode('utf-8'),
        encoded_params,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_hmac, hmac_to_verify)


def verify_shopify_webhook(data: bytes, hmac_header: str) -> bool:
    """
    Verify webhook signature from Shopify
    """
    computed_hmac = base64.b64encode(
        hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
    ).decode()
    return hmac.compare_digest(computed_hmac, hmac_header)


@app.get("/")
async def root():
    """
    Root endpoint - provides installation instructions
    """
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vervegrand Portal - Shopify App</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'San Francisco', 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f6f6f7;
            }}
            .card {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #202223; margin-top: 0; }}
            .install-btn {{
                display: inline-block;
                background: #008060;
                color: white;
                padding: 12px 24px;
                border-radius: 4px;
                text-decoration: none;
                margin-top: 20px;
            }}
            .install-btn:hover {{ background: #006e52; }}
            code {{
                background: #f6f6f7;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔄 Vervegrand Portal</h1>
            <p>This is a Shopify embedded application for product and inventory management.</p>
            <h3>Installation Steps:</h3>
            <ol>
                <li>Click the install button below</li>
                <li>Enter your Shopify store URL (e.g., <code>your-store.myshopify.com</code>)</li>
                <li>Authorize the app permissions</li>
            </ol>
            <a href="/auth/shopify?shop=your-store.myshopify.com" class="install-btn">Install App</a>
            <p style="margin-top: 30px; color: #637381; font-size: 14px;">
                Need help? Check the <a href="https://github.com/your-repo">documentation</a>
            </p>
        </div>
    </body>
    </html>
    """)


@app.get("/auth/shopify")
async def auth_shopify(request: Request, shop: str = Query(...)):
    """
    Step 1: Initiate Shopify OAuth flow
    Redirects merchant to Shopify authorization page
    """
    if not shop:
        raise HTTPException(status_code=400, detail="Shop parameter is required")
    
    # Sanitize shop domain
    shop = shop.strip()
    if not shop.endswith(".myshopify.com"):
        if "." in shop:
            raise HTTPException(status_code=400, detail="Invalid shop domain")
        shop = f"{shop}.myshopify.com"
    
    # Generate state parameter for CSRF protection
    state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    request.session['oauth_state'] = state
    request.session['shop'] = shop
    
    # Build authorization URL
    auth_params = {
        'client_id': SHOPIFY_API_KEY,
        'scope': SHOPIFY_SCOPES,
        'redirect_uri': f"{APP_URL}/auth/callback",
        'state': state,
    }
    
    auth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(auth_params)}"
    
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str = Query(None),
    shop: str = Query(None),
    state: str = Query(None),
    hmac: str = Query(None)
):
    """
    Step 2: Handle OAuth callback from Shopify
    Exchange authorization code for access token
    """
    # Verify state to prevent CSRF
    session_state = request.session.get('oauth_state')
    if not state or state != session_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Verify HMAC signature
    query_dict = dict(request.query_params)
    hmac_value = query_dict.pop('hmac', '')
    
    # Build query string for HMAC verification (sorted keys)
    sorted_params = sorted(query_dict.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    if not verify_shopify_hmac(query_string, hmac_value):
        raise HTTPException(status_code=400, detail="Invalid HMAC signature")
    
    # Exchange code for access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    token_data = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=token_data)
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        token_response = response.json()
        access_token = token_response.get('access_token')
    
    # Store access token securely (in production, use database)
    # For now, we'll store in session
    request.session['access_token'] = access_token
    request.session['shop'] = shop
    
    # Redirect to embedded app interface
    return RedirectResponse(url=f"/app?shop={shop}&session_token=placeholder")


@app.get("/app")
async def app_interface(request: Request, shop: str = Query(None)):
    """
    Serves the embedded app interface with Shopify App Bridge
    This creates an iframe that loads the Streamlit app with proper headers
    """
    if not shop:
        shop = request.session.get('shop', 'your-store.myshopify.com')
    
    # Create the embedding HTML with App Bridge
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vervegrand Portal</title>
        <script src="https://unpkg.com/@shopify/app-bridge@3"></script>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100vh;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, 'San Francisco', 'Segoe UI', Roboto, sans-serif;
            }}
            #app-frame {{
                width: 100%;
                height: 100%;
                border: none;
            }}
            .loading {{
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                background: #f6f6f7;
                flex-direction: column;
            }}
            .spinner {{
                border: 3px solid #f3f3f3;
                border-top: 3px solid #008060;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p style="margin-top: 20px; color: #637381;">Loading Vervegrand Portal...</p>
        </div>
        <iframe id="app-frame" src="/streamlit?embedded=true&shop={shop}" style="display:none;"></iframe>
        
        <script>
            // Initialize Shopify App Bridge
            const AppBridge = window['app-bridge'];
            const createApp = AppBridge.default;
            
            const app = createApp({{
                apiKey: '{SHOPIFY_API_KEY}',
                host: new URLSearchParams(window.location.search).get('host') || '',
                forceRedirect: false
            }});
            
            // Create Toast action for notifications
            const Toast = AppBridge.actions.Toast;
            
            // Make app bridge available globally for Streamlit
            window.shopifyApp = app;
            window.shopifyToast = Toast;
            
            // Handle frame loading
            const iframe = document.getElementById('app-frame');
            const loading = document.getElementById('loading');
            
            iframe.onload = function() {{
                loading.style.display = 'none';
                iframe.style.display = 'block';
                
                // Show success toast
                const toastOptions = {{
                    message: 'Vervegrand Portal loaded successfully',
                    duration: 3000,
                    isError: false
                }};
                Toast.create(app, toastOptions).dispatch(Toast.Action.SHOW);
            }};
            
            // Handle errors
            iframe.onerror = function() {{
                loading.innerHTML = '<p style="color: #d72c0d;">Failed to load application. Please refresh.</p>';
            }};
            
            // Communication between iframe and parent
            window.addEventListener('message', function(event) {{
                if (event.data.type === 'SHOW_TOAST') {{
                    const toastOptions = {{
                        message: event.data.message,
                        duration: event.data.duration || 3000,
                        isError: event.data.isError || false
                    }};
                    Toast.create(app, toastOptions).dispatch(Toast.Action.SHOW);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    response = HTMLResponse(content=html_content)
    
    # Set security headers for embedding
    response.headers["Content-Security-Policy"] = (
        f"frame-ancestors https://{shop} https://admin.shopify.com;"
    )
    response.headers["X-Frame-Options"] = f"ALLOW-FROM https://{shop}"
    
    return response


@app.get("/streamlit")
async def streamlit_proxy(request: Request):
    """
    Proxy requests to Streamlit with proper headers for embedding
    """
    # Get query parameters
    query_params = str(request.url.query)
    streamlit_url = f"http://localhost:{STREAMLIT_PORT}/?{query_params}" if query_params else f"http://localhost:{STREAMLIT_PORT}/"
    
    async with httpx.AsyncClient() as client:
        try:
            # Forward the request to Streamlit
            response = await client.get(
                streamlit_url,
                headers={
                    "Accept": request.headers.get("Accept", "*/*"),
                },
                follow_redirects=True
            )
            
            # Return Streamlit's response with modified headers
            headers = dict(response.headers)
            
            # Remove headers that prevent embedding
            headers.pop("x-frame-options", None)
            
            # Add CSP header to allow embedding
            shop = request.query_params.get('shop', '*.myshopify.com')
            headers["Content-Security-Policy"] = (
                f"frame-ancestors https://{shop} https://admin.shopify.com;"
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type")
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed to connect to Streamlit: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {"status": "healthy", "service": "shopify-app-gateway"}


@app.post("/webhooks/app/uninstalled")
async def webhook_app_uninstalled(request: Request):
    """
    Handle app uninstallation webhook
    """
    # Verify webhook signature
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    body = await request.body()
    
    if not verify_shopify_webhook(body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Process uninstallation (cleanup data, revoke tokens, etc.)
    # In production, implement proper cleanup logic
    
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
