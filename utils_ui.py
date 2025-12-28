"""
Shopify Polaris-Style UI Components for Streamlit
Injects custom CSS to make Streamlit look like a native Shopify app
"""

import streamlit as st


def inject_shopify_style():
    """
    Injects custom CSS to transform Streamlit into a Shopify Polaris-like interface.
    This function should be called at the top of every Streamlit page.
    
    Key transformations:
    - Shopify color palette (greens, grays)
    - Shopify typography (SF Pro, Segoe UI stack)
    - Polaris-style buttons, cards, and form elements
    - Removes Streamlit branding
    - Adds proper spacing and shadows
    """
    
    shopify_css = """
    <style>
    /* ============================================
       SHOPIFY POLARIS DESIGN SYSTEM OVERRIDE
       ============================================ */
    
    /* Import Shopify-like fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Root Variables - Shopify Color Palette */
    :root {
        --shopify-green: #008060;
        --shopify-green-dark: #004c3f;
        --shopify-green-light: #50b83c;
        --shopify-surface: #f6f6f7;
        --shopify-surface-dark: #f1f1f1;
        --shopify-border: #c4cdd5;
        --shopify-text: #202223;
        --shopify-text-secondary: #6d7175;
        --shopify-critical: #d72c0d;
        --shopify-warning: #ffc453;
        --shopify-highlight: #5c6ac4;
        --shopify-interactive: #2c6ecb;
        --shopify-shadow: rgba(23, 24, 24, 0.05);
    }
    
    /* ============================================
       GLOBAL RESETS & BASE STYLES
       ============================================ */
    
    /* Override Streamlit's default font stack */
    html, body, [class*="css"], .stApp {
        font-family: -apple-system, BlinkMacSystemFont, 'San Francisco', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif !important;
        background-color: var(--shopify-surface) !important;
        color: var(--shopify-text) !important;
    }
    
    /* Main app container */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1200px !important;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Hide hamburger menu */
    .css-1dp5vir {
        display: none;
    }
    
    /* ============================================
       TYPOGRAPHY
       ============================================ */
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--shopify-text) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }
    
    h1 {
        font-size: 28px !important;
        line-height: 32px !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-size: 20px !important;
        line-height: 24px !important;
        margin-bottom: 0.75rem !important;
    }
    
    h3 {
        font-size: 16px !important;
        line-height: 20px !important;
        font-weight: 600 !important;
    }
    
    p, div, span, label {
        color: var(--shopify-text) !important;
        font-size: 14px !important;
        line-height: 20px !important;
    }
    
    /* ============================================
       BUTTONS - SHOPIFY POLARIS STYLE
       ============================================ */
    
    /* Primary Button */
    .stButton > button {
        background-color: var(--shopify-green) !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 10px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        line-height: 20px !important;
        cursor: pointer !important;
        transition: background-color 0.2s ease !important;
        box-shadow: 0 1px 0 0 rgba(0, 0, 0, 0.05) !important;
        min-height: 36px !important;
    }
    
    .stButton > button:hover {
        background-color: var(--shopify-green-dark) !important;
        box-shadow: 0 1px 0 0 rgba(0, 0, 0, 0.1) !important;
    }
    
    .stButton > button:active {
        background-color: #003d2e !important;
        box-shadow: inset 0 1px 0 0 rgba(0, 0, 0, 0.15) !important;
    }
    
    .stButton > button:focus {
        outline: 2px solid var(--shopify-interactive) !important;
        outline-offset: 2px !important;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background-color: white !important;
        color: var(--shopify-text) !important;
        border: 1px solid var(--shopify-border) !important;
        border-radius: 4px !important;
        padding: 10px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    .stDownloadButton > button:hover {
        border-color: var(--shopify-text-secondary) !important;
        background-color: var(--shopify-surface) !important;
    }
    
    /* ============================================
       FORM ELEMENTS
       ============================================ */
    
    /* Text Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        border: 1px solid var(--shopify-border) !important;
        border-radius: 4px !important;
        padding: 8px 12px !important;
        font-size: 14px !important;
        color: var(--shopify-text) !important;
        background-color: white !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--shopify-interactive) !important;
        outline: 2px solid var(--shopify-interactive) !important;
        outline-offset: 0px !important;
    }
    
    /* Select Boxes */
    .stSelectbox > div > div > div {
        border: 1px solid var(--shopify-border) !important;
        border-radius: 4px !important;
        background-color: white !important;
    }
    
    /* Multiselect */
    .stMultiSelect > div > div > div {
        border: 1px solid var(--shopify-border) !important;
        border-radius: 4px !important;
        background-color: white !important;
    }
    
    /* Checkboxes & Radio */
    .stCheckbox, .stRadio {
        font-size: 14px !important;
    }
    
    /* Sliders */
    .stSlider > div > div > div {
        background-color: var(--shopify-green) !important;
    }
    
    /* ============================================
       CARDS & CONTAINERS
       ============================================ */
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: white !important;
        padding: 16px !important;
        border-radius: 8px !important;
        border: 1px solid var(--shopify-border) !important;
        box-shadow: 0 1px 0 0 var(--shopify-shadow) !important;
    }
    
    [data-testid="stMetric"] label {
        font-size: 13px !important;
        color: var(--shopify-text-secondary) !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 600 !important;
        color: var(--shopify-text) !important;
    }
    
    /* Expander (Collapsible) */
    .streamlit-expanderHeader {
        background-color: white !important;
        border: 1px solid var(--shopify-border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-weight: 500 !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: var(--shopify-text-secondary) !important;
        background-color: var(--shopify-surface) !important;
    }
    
    /* Columns */
    [data-testid="column"] {
        background-color: white !important;
        padding: 16px !important;
        border-radius: 8px !important;
        border: 1px solid var(--shopify-border) !important;
    }
    
    /* ============================================
       DATAFRAMES & TABLES
       ============================================ */
    
    .dataframe {
        border: 1px solid var(--shopify-border) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        font-size: 13px !important;
    }
    
    .dataframe thead tr th {
        background-color: var(--shopify-surface) !important;
        color: var(--shopify-text-secondary) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        letter-spacing: 0.05em !important;
        padding: 12px !important;
        border-bottom: 1px solid var(--shopify-border) !important;
    }
    
    .dataframe tbody tr {
        border-bottom: 1px solid var(--shopify-surface-dark) !important;
    }
    
    .dataframe tbody tr:hover {
        background-color: var(--shopify-surface) !important;
    }
    
    .dataframe tbody tr td {
        padding: 12px !important;
        color: var(--shopify-text) !important;
    }
    
    /* ============================================
       ALERTS & MESSAGES
       ============================================ */
    
    /* Success Message */
    .stSuccess {
        background-color: #e3f5ee !important;
        border-left: 4px solid var(--shopify-green) !important;
        padding: 12px 16px !important;
        border-radius: 4px !important;
        color: #004c3f !important;
    }
    
    /* Error Message */
    .stError {
        background-color: #fef5f1 !important;
        border-left: 4px solid var(--shopify-critical) !important;
        padding: 12px 16px !important;
        border-radius: 4px !important;
        color: #8b1e0c !important;
    }
    
    /* Warning Message */
    .stWarning {
        background-color: #fff8e1 !important;
        border-left: 4px solid var(--shopify-warning) !important;
        padding: 12px 16px !important;
        border-radius: 4px !important;
        color: #5c4813 !important;
    }
    
    /* Info Message */
    .stInfo {
        background-color: #e8f5fa !important;
        border-left: 4px solid var(--shopify-interactive) !important;
        padding: 12px 16px !important;
        border-radius: 4px !important;
        color: #1e4e79 !important;
    }
    
    /* ============================================
       SIDEBAR
       ============================================ */
    
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid var(--shopify-border) !important;
        padding: 1.5rem 1rem !important;
    }
    
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        justify-content: flex-start !important;
        background-color: transparent !important;
        color: var(--shopify-text) !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: var(--shopify-surface) !important;
    }
    
    /* ============================================
       PROGRESS INDICATORS
       ============================================ */
    
    .stProgress > div > div > div {
        background-color: var(--shopify-green) !important;
    }
    
    .stSpinner > div {
        border-top-color: var(--shopify-green) !important;
    }
    
    /* ============================================
       TABS
       ============================================ */
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 8px;
        border-radius: 8px;
        border: 1px solid var(--shopify-border);
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        background-color: transparent;
        border-radius: 4px;
        color: var(--shopify-text-secondary);
        font-weight: 500;
        font-size: 14px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--shopify-surface) !important;
        color: var(--shopify-text) !important;
    }
    
    /* ============================================
       FILE UPLOADER
       ============================================ */
    
    [data-testid="stFileUploader"] {
        background-color: white !important;
        border: 2px dashed var(--shopify-border) !important;
        border-radius: 8px !important;
        padding: 24px !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: var(--shopify-text-secondary) !important;
        background-color: var(--shopify-surface) !important;
    }
    
    /* ============================================
       CUSTOM POLARIS CARD CLASS
       ============================================ */
    
    .polaris-card {
        background-color: white;
        border: 1px solid var(--shopify-border);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 0 0 var(--shopify-shadow);
    }
    
    .polaris-card h3 {
        margin-top: 0 !important;
        margin-bottom: 12px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    
    .polaris-card p {
        color: var(--shopify-text-secondary) !important;
        margin-bottom: 8px !important;
    }
    
    /* ============================================
       BADGE COMPONENT
       ============================================ */
    
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        line-height: 16px;
    }
    
    .badge-success {
        background-color: #e3f5ee;
        color: #004c3f;
    }
    
    .badge-warning {
        background-color: #fff8e1;
        color: #5c4813;
    }
    
    .badge-error {
        background-color: #fef5f1;
        color: #8b1e0c;
    }
    
    .badge-info {
        background-color: #e8f5fa;
        color: #1e4e79;
    }

    .badge-subdued, .badge-gray {
        background-color: #f1f2f3;
        color: #6d7175;
    }
    
    /* ============================================
       RESPONSIVE DESIGN
       ============================================ */
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        h1 {
            font-size: 24px !important;
        }
        
        [data-testid="column"] {
            padding: 12px !important;
        }
    }
    
    /* ============================================
       SHOPIFY APP BRIDGE INTEGRATION
       ============================================ */
    
    /* Ensure proper iframe embedding */
    body {
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    /* Hide elements that shouldn't appear in embedded context */
    .embedded-mode .stDeployButton {
        display: none !important;
    }
    
    </style>
    """
    
    st.markdown(shopify_css, unsafe_allow_html=True)


def create_polaris_card(title: str, content: str, status: str = None):
    """
    Creates a Shopify Polaris-style card component
    
    Args:
        title: Card title
        content: Card content (can be HTML)
        status: Optional status badge ('success', 'warning', 'error', 'info')
    """
    badge_html = ""
    if status:
        badge_class = f"badge badge-{status}"
        badge_html = f'<span class="{badge_class}">{status.upper()}</span>'
    
    card_html = f"""
    <div class="polaris-card">
        <h3>{title} {badge_html}</h3>
        <div>{content}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def inject_app_bridge_js():
    """
    Injects Shopify App Bridge JavaScript for communication with Shopify admin
    This enables features like Toast notifications, navigation, and modal dialogs
    """
    
    app_bridge_js = """
    <script>
    // Check if we're running inside Shopify admin
    const isEmbedded = window.top !== window.self;
    
    if (isEmbedded && window.parent.shopifyApp) {
        console.log('Shopify App Bridge detected');
        
        // Function to show toast from Streamlit
        window.showShopifyToast = function(message, isError = false) {
            window.parent.postMessage({
                type: 'SHOW_TOAST',
                message: message,
                isError: isError,
                duration: 3000
            }, '*');
        };
        
        // Function to trigger navigation
        window.navigateShopify = function(path) {
            window.parent.postMessage({
                type: 'NAVIGATE',
                path: path
            }, '*');
        };
        
        console.log('Shopify helper functions initialized');
    } else {
        console.log('Running in standalone mode (not embedded)');
        
        // Fallback functions for standalone mode
        window.showShopifyToast = function(message, isError = false) {
            console.log('Toast:', message, isError ? '(error)' : '(success)');
        };
        
        window.navigateShopify = function(path) {
            console.log('Navigate to:', path);
        };
    }
    
    // Make functions available to Streamlit components
    window.addEventListener('load', function() {
        console.log('Shopify integration ready');
    });
    </script>
    """
    
    st.components.v1.html(app_bridge_js, height=0)


def show_shopify_toast(message: str, is_error: bool = False):
    """
    Shows a toast notification using Shopify App Bridge
    
    Args:
        message: Toast message text
        is_error: Whether this is an error toast (red) or success toast (green)
    """
    toast_js = f"""
    <script>
    if (window.showShopifyToast) {{
        window.showShopifyToast("{message}", {str(is_error).lower()});
    }}
    </script>
    """
    st.components.v1.html(toast_js, height=0)


def badge(text, icon=None, color="gray"):
    """
    Renders a badge component.
    Args:
        text: The text to display.
        icon: An optional icon (emoji or text).
        color: The color of the badge (green, red, yellow, blue, gray).
    """
    color_map = {
        "green": "success",
        "red": "error",
        "yellow": "warning",
        "blue": "info",
        "gray": "subdued"
    }

    status_class = color_map.get(color, "subdued")
    icon_html = f'<span style="margin-right: 4px;">{icon}</span>' if icon else ""

    html = f'<span class="badge badge-{status_class}">{icon_html}{text}</span>'
    st.markdown(html, unsafe_allow_html=True)


# Monkey patch st.badge
if not hasattr(st, 'badge'):
    st.badge = badge


# Example usage in a Streamlit page
if __name__ == "__main__":
    # This is how you would use it in your pages
    inject_shopify_style()
    inject_app_bridge_js()
    
    st.title("🛍️ Shopify Polaris Demo")
    
    create_polaris_card(
        title="Welcome to Vervegrand Portal",
        content="This is a demo of Shopify Polaris-styled components in Streamlit.",
        status="success"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Products", "1,234", "+12%")
    with col2:
        st.metric("Orders", "567", "+23%")
    with col3:
        st.metric("Revenue", "$12,345", "+8%")
    
    if st.button("Show Toast Notification"):
        show_shopify_toast("This is a test notification!")
