"""
Example Streamlit Page with Shopify Polaris Styling
This demonstrates how to use the UI utilities in your Streamlit pages
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path to import utils_ui
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Shopify styling utilities
from utils_ui import (
    inject_shopify_style,
    inject_app_bridge_js,
    create_polaris_card,
    show_shopify_toast
)

# ============================================
# APPLY SHOPIFY POLARIS STYLING
# ============================================
# IMPORTANT: Call this at the top of EVERY page
inject_shopify_style()
inject_app_bridge_js()

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Dashboard - Vervegrand Portal",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# PAGE HEADER
# ============================================
st.title("🛍️ Vervegrand Portal Dashboard")
st.markdown("Welcome to your Shopify product management dashboard")

# ============================================
# METRICS SECTION (POLARIS CARDS)
# ============================================
st.subheader("📊 Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Products",
        value="1,234",
        delta="12 new today",
        delta_color="normal"
    )

with col2:
    st.metric(
        label="Active Orders",
        value="567",
        delta="23 pending",
        delta_color="normal"
    )

with col3:
    st.metric(
        label="Inventory Value",
        value="$45,678",
        delta="+8.2%",
        delta_color="normal"
    )

with col4:
    st.metric(
        label="Low Stock Items",
        value="34",
        delta="-5 from yesterday",
        delta_color="inverse"
    )

# ============================================
# POLARIS CARD EXAMPLES
# ============================================
st.subheader("📦 Recent Activity")

col1, col2 = st.columns(2)

with col1:
    create_polaris_card(
        title="Sync Status",
        content="""
        <p>Last sync: <strong>2 minutes ago</strong></p>
        <p>Next scheduled sync: <strong>In 58 minutes</strong></p>
        <p>Products synced today: <strong>1,234</strong></p>
        """,
        status="success"
    )
    
    create_polaris_card(
        title="API Health",
        content="""
        <p>Shopify API: <span class="badge badge-success">Connected</span></p>
        <p>Sentos API: <span class="badge badge-success">Connected</span></p>
        <p>Response time: <strong>124ms</strong></p>
        """,
        status="success"
    )

with col2:
    create_polaris_card(
        title="Pending Actions",
        content="""
        <p>📋 5 products awaiting review</p>
        <p>⚠️ 3 inventory discrepancies</p>
        <p>📦 2 failed uploads need retry</p>
        """,
        status="warning"
    )
    
    create_polaris_card(
        title="System Notifications",
        content="""
        <p>✅ Backup completed successfully</p>
        <p>🔄 Auto-sync enabled for 15 collections</p>
        <p>📊 Weekly report generated</p>
        """,
        status="info"
    )

# ============================================
# DATA TABLE WITH POLARIS STYLING
# ============================================
st.subheader("📋 Recent Products")

# Sample data
products_data = {
    "Product": ["Product A", "Product B", "Product C", "Product D", "Product E"],
    "SKU": ["SKU001", "SKU002", "SKU003", "SKU004", "SKU005"],
    "Stock": [125, 34, 0, 567, 89],
    "Price": ["$29.99", "$49.99", "$19.99", "$99.99", "$39.99"],
    "Status": ["Active", "Active", "Out of Stock", "Active", "Active"]
}

df = pd.DataFrame(products_data)

# Display with custom styling (already styled by CSS)
st.dataframe(
    df,
    use_container_width=True,
    height=250
)

# ============================================
# ACTION BUTTONS
# ============================================
st.subheader("🎯 Quick Actions")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔄 Sync Now", use_container_width=True):
        show_shopify_toast("Sync started successfully!", is_error=False)
        st.success("Sync initiated! This will take a few minutes.")

with col2:
    if st.button("📤 Export Data", use_container_width=True):
        show_shopify_toast("Export queued for processing", is_error=False)
        st.info("Your export will be ready in a few moments.")

with col3:
    if st.button("📊 Generate Report", use_container_width=True):
        show_shopify_toast("Report generation started", is_error=False)
        st.info("Report will be available in Reports section.")

with col4:
    if st.button("⚙️ Settings", use_container_width=True):
        st.info("Opening settings...")

# ============================================
# FORM EXAMPLE WITH POLARIS STYLING
# ============================================
st.subheader("🔍 Product Search")

with st.form("product_search_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        search_query = st.text_input(
            "Product Name or SKU",
            placeholder="Search products..."
        )
    
    with col2:
        category = st.selectbox(
            "Category",
            ["All Categories", "Electronics", "Clothing", "Home & Garden", "Sports"]
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        min_price = st.number_input("Min Price", min_value=0.0, value=0.0, step=5.0)
    
    with col4:
        max_price = st.number_input("Max Price", min_value=0.0, value=1000.0, step=5.0)
    
    stock_status = st.multiselect(
        "Stock Status",
        ["In Stock", "Low Stock", "Out of Stock", "Backorder"]
    )
    
    submitted = st.form_submit_button("🔍 Search Products", use_container_width=False)
    
    if submitted:
        show_shopify_toast("Searching products...", is_error=False)
        st.success(f"Searching for: {search_query} in {category}")

# ============================================
# TABS EXAMPLE
# ============================================
st.subheader("📑 Detailed Information")

tab1, tab2, tab3 = st.tabs(["Analytics", "Logs", "Settings"])

with tab1:
    st.write("**Sales Analytics**")
    st.line_chart(data=[10, 20, 30, 25, 35, 45, 40], height=200)

with tab2:
    st.write("**Recent Logs**")
    logs = [
        "[2024-01-15 10:30] ✅ Product sync completed",
        "[2024-01-15 10:25] 🔄 Starting product sync",
        "[2024-01-15 10:20] ✅ API connection established",
        "[2024-01-15 10:15] 📊 Daily report generated"
    ]
    for log in logs:
        st.text(log)

with tab3:
    st.write("**Application Settings**")
    st.checkbox("Enable automatic sync", value=True)
    st.slider("Sync interval (minutes)", 5, 60, 15)
    st.checkbox("Send email notifications", value=False)

# ============================================
# SIDEBAR NAVIGATION
# ============================================
with st.sidebar:
    st.title("Navigation")
    
    st.markdown("### 📊 Main")
    st.button("Dashboard", use_container_width=True)
    st.button("Products", use_container_width=True)
    st.button("Orders", use_container_width=True)
    
    st.markdown("### 🔄 Sync")
    st.button("Sync Manager", use_container_width=True)
    st.button("Logs", use_container_width=True)
    
    st.markdown("### ⚙️ Settings")
    st.button("Configuration", use_container_width=True)
    st.button("API Keys", use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Status:** 🟢 Connected")
    st.markdown(f"**Last sync:** {datetime.now().strftime('%H:%M:%S')}")

# ============================================
# EXPANDER EXAMPLE
# ============================================
st.subheader("💡 Tips & Documentation")

with st.expander("🚀 Quick Start Guide"):
    st.markdown("""
    **Getting Started with Vervegrand Portal:**
    
    1. **Connect your APIs** - Add your Shopify and Sentos API credentials in Settings
    2. **Configure sync** - Set up automatic sync schedules in Sync Manager
    3. **Monitor products** - Use the dashboard to track inventory and sales
    4. **Run reports** - Generate detailed analytics and export data
    """)

with st.expander("📖 API Documentation"):
    st.markdown("""
    **Available API Endpoints:**
    
    - `GET /api/products` - Fetch all products
    - `POST /api/products` - Create new product
    - `PUT /api/products/{id}` - Update existing product
    - `DELETE /api/products/{id}` - Delete product
    """)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #637381; font-size: 12px;">
        Vervegrand Portal v2.1 | Built with ❤️ for Shopify | 
        <a href="https://github.com/your-repo" target="_blank">Documentation</a>
    </div>
    """,
    unsafe_allow_html=True
)
