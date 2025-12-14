"""
Updated streamlit_app.py with Shopify Polaris Styling Integration
This is an example of how to integrate the new UI system into your main app
"""

import streamlit as st
import yaml
from yaml.loader import SafeLoader
import pandas as pd
from io import StringIO
import threading
import queue
import os
import time

# Import Shopify UI utilities
from utils_ui import inject_shopify_style, inject_app_bridge_js, show_shopify_toast

# Gerekli modülleri import ediyoruz
from config_manager import load_all_user_keys
from data_manager import load_user_data
from connectors.shopify_api import ShopifyAPI
from connectors.sentos_api import SentosAPI

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Vervegrand Sync", 
    page_icon="🔄", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ============================================
# APPLY SHOPIFY POLARIS STYLING
# ============================================
# CRITICAL: Apply Shopify styling before any other content
inject_shopify_style()
inject_app_bridge_js()

# ============================================
# SESSION STATE INITIALIZATION
# ============================================
def initialize_session_state_defaults():
    """Oturum durumu için başlangıç değerlerini ayarlar."""
    defaults = {
        'authentication_status': None,
        'shopify_status': 'pending',
        'sentos_status': 'pending',
        'logged_in': False,
        'username': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state_defaults()

# ============================================
# AUTHENTICATION
# ============================================
def check_password(password):
    """Direct password check for demo purposes."""
    return password == "195119"

def login_page():
    """Displays the login page with Shopify Polaris styling."""
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 80px;">
            <h1 style="color: #202223; font-size: 32px; font-weight: 600; margin-bottom: 8px;">
                🔄 Vervegrand Portal
            </h1>
            <p style="color: #637381; font-size: 16px; margin-bottom: 40px;">
                Admin Login Required
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create a card-style container for the form
        st.markdown("""
        <style>
        .login-card {
            background-color: white;
            border: 1px solid #c4cdd5;
            border-radius: 8px;
            padding: 32px;
            box-shadow: 0 1px 0 0 rgba(23, 24, 24, 0.05);
        }
        </style>
        <div class="login-card">
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input(
                "Username",
                value="Admin",
                disabled=True,
                help="Default admin username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
            with col_submit2:
                submitted = st.form_submit_button(
                    "🔓 Sign In",
                    use_container_width=True
                )
            
            if submitted:
                if username == "Admin" and check_password(password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    # Try to load all API keys on successful login
                    load_all_keys()
                    show_shopify_toast("Login successful! Welcome back.", is_error=False)
                    st.success("✅ Logged in successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    show_shopify_toast("Invalid credentials. Please try again.", is_error=True)
                    st.error("❌ Incorrect username or password.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Help text below the form
        st.markdown("""
        <div style="text-align: center; margin-top: 24px; color: #637381; font-size: 14px;">
            Need help? Contact your system administrator.
        </div>
        """, unsafe_allow_html=True)
    
    return False

# ============================================
# MAIN APPLICATION
# ============================================
def display_main_app():
    """Main application interface after login."""
    
    # Sidebar Navigation
    with st.sidebar:
        st.title("🔄 Vervegrand Portal")
        st.markdown(f"**Welcome,** {st.session_state.get('username', 'User')}!")
        st.markdown("---")
        
        # Navigation Menu
        st.markdown("### 📊 Main Menu")
        
        # You can add navigation buttons here
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
        
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.page = "settings"
        
        if st.button("🔄 Sync", use_container_width=True):
            st.session_state.page = "sync"
        
        if st.button("📊 Logs", use_container_width=True):
            st.session_state.page = "logs"
        
        st.markdown("---")
        
        # Status indicators
        st.markdown("### 🔌 Connection Status")
        
        shopify_status = st.session_state.get('shopify_status', 'pending')
        sentos_status = st.session_state.get('sentos_status', 'pending')
        
        if shopify_status == 'connected':
            st.markdown("🟢 **Shopify**: Connected")
        elif shopify_status == 'error':
            st.markdown("🔴 **Shopify**: Error")
        else:
            st.markdown("🟡 **Shopify**: Pending")
        
        if sentos_status == 'connected':
            st.markdown("🟢 **Sentos**: Connected")
        elif sentos_status == 'error':
            st.markdown("🔴 **Sentos**: Error")
        else:
            st.markdown("🟡 **Sentos**: Pending")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            show_shopify_toast("Logged out successfully", is_error=False)
            st.rerun()
    
    # Main Content Area
    st.title("🏠 Dashboard")
    st.markdown("Welcome to your Vervegrand Sync Portal")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Active Products",
            value="1,234",
            delta="12 new",
        )
    
    with col2:
        st.metric(
            label="Synced Today",
            value="567",
            delta="23%",
        )
    
    with col3:
        st.metric(
            label="Pending Items",
            value="45",
            delta="-5",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            label="API Calls",
            value="8,901",
            delta="125",
        )
    
    # Quick Actions
    st.subheader("🎯 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Run Sync Now", use_container_width=True):
            show_shopify_toast("Sync started successfully!", is_error=False)
            st.success("Sync process initiated!")
    
    with col2:
        if st.button("📤 Export Data", use_container_width=True):
            show_shopify_toast("Export queued for processing", is_error=False)
            st.info("Export will be ready shortly")
    
    with col3:
        if st.button("🔍 View Reports", use_container_width=True):
            show_shopify_toast("Opening reports...", is_error=False)
            st.info("Reports section coming soon")
    
    # Recent Activity
    st.subheader("📋 Recent Activity")
    
    # Sample data
    recent_activity = pd.DataFrame({
        "Time": ["10:30 AM", "10:15 AM", "09:45 AM", "09:30 AM", "09:00 AM"],
        "Action": ["Product Sync", "Order Update", "Inventory Check", "Price Update", "Product Sync"],
        "Status": ["✅ Success", "✅ Success", "⚠️ Warning", "✅ Success", "✅ Success"],
        "Items": [234, 12, 45, 123, 189]
    })
    
    st.dataframe(
        recent_activity,
        use_container_width=True,
        height=250
    )
    
    # System Information
    st.subheader("ℹ️ System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🔧 System Status**
        - Application: Running
        - Database: Connected
        - Cache: Active
        - Last Backup: 2 hours ago
        """)
    
    with col2:
        st.markdown("""
        **📊 Statistics**
        - Total Products: 12,345
        - Active Users: 5
        - Uptime: 99.9%
        - Response Time: 124ms
        """)

# ============================================
# MAIN ENTRY POINT
# ============================================
def main():
    """Main application entry point."""
    
    # Check if user is logged in
    if not st.session_state.get("logged_in", False):
        login_page()
    else:
        display_main_app()

if __name__ == "__main__":
    main()
