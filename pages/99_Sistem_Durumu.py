
import streamlit as st
import pandas as pd
import json
import os
import sys
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Konfigürasyonu en başa al
st.set_page_config(page_title="Sistem Durumu", page_icon="🖥️", layout="wide")

# Import necessary modules
from connectors.shopify_api import ShopifyAPI
from connectors.sentos_api import SentosAPI
try:
    from operations.log_manager import log_manager
except ImportError:
    st.error("Log Manager module not found.")
    log_manager = None

from utils.style_loader import load_global_css

# Load global styles
load_global_css()

st.markdown("""
<div class="main-header">
    <h1>🖥️ Sistem Durumu ve Sağlık İzleme</h1>
    <p>API bağlantıları, sistem sağlığı ve kritik hataların anlık takibi.</p>
</div>
""", unsafe_allow_html=True)

# Authentication Check
if not st.session_state.get("authentication_status"):
    st.warning("Bu sayfayı görüntülemek için lütfen giriş yapın.")
    st.stop()

# Helper function to check connection status
def check_connection(api_name, check_func):
    try:
        start_time = time.time()
        result = check_func()
        duration = time.time() - start_time
        return result, duration
    except Exception as e:
        return {'success': False, 'message': str(e)}, 0

# --- Live Health Check Section ---
st.subheader("📡 Canlı Bağlantı Durumu")

col1, col2, col3 = st.columns(3)

# 1. Shopify Check
with col1:
    st.markdown("### Shopify API")
    if st.session_state.get('shopify_token') and st.session_state.get('shopify_store'):
        api = ShopifyAPI(st.session_state.shopify_store, st.session_state.shopify_token)
        with st.status("Bağlantı kontrol ediliyor...", expanded=True) as status:
            res, duration = check_connection("Shopify", api.test_connection)
            if res.get('success'):
                status.update(label=f"✅ Bağlı ({duration:.2f}s)", state="complete", expanded=False)
                st.success(f"Mağaza: {res.get('name')}")
                st.info(f"Plan: {res.get('plan')}")
            else:
                status.update(label="❌ Bağlantı Hatası", state="error", expanded=True)
                st.error(f"Hata: {res.get('message')}")
    else:
        st.warning("⚠️ Shopify kimlik bilgileri eksik.")

# 2. Sentos Check
with col2:
    st.markdown("### Sentos API")
    if st.session_state.get('sentos_api_key') and st.session_state.get('sentos_api_url'):
        sentos_api = SentosAPI(
            st.session_state.sentos_api_url,
            st.session_state.sentos_api_key,
            st.session_state.get('sentos_api_secret', ''),
            st.session_state.get('sentos_cookie')
        )
        with st.status("Bağlantı kontrol ediliyor...", expanded=True) as status:
            res, duration = check_connection("Sentos", sentos_api.test_connection)
            if res.get('success'):
                status.update(label=f"✅ Bağlı ({duration:.2f}s)", state="complete", expanded=False)
                st.success(f"Ürün Sayısı: {res.get('total_products', 'N/A')}")
            else:
                status.update(label="❌ Bağlantı Hatası", state="error", expanded=True)
                st.error(f"Hata: {res.get('message')}")
    else:
        st.warning("⚠️ Sentos kimlik bilgileri eksik.")

# 3. Database & System Check
with col3:
    st.markdown("### Sistem Sağlığı")

    # Check Database
    db_path = "logs/sync_logs.db"
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        st.metric("Log DB Boyutu", f"{size_mb:.2f} MB")
        if size_mb > 100:
            st.warning("⚠️ DB Boyutu yüksek. Temizlik önerilir.")
    else:
        st.info("Log veritabanı henüz oluşturulmamış.")

    # Check Last Sync
    if log_manager:
        recent_logs = log_manager.get_recent_logs(limit=1, log_type='sync')
        if recent_logs:
            last_sync = recent_logs[0]
            st.metric("Son Senkronizasyon",
                      datetime.fromisoformat(last_sync['timestamp']).strftime('%H:%M:%S'),
                      delta=last_sync['status'])
        else:
            st.text("Henüz senkronizasyon yok.")

st.markdown("---")

# --- Recent Errors Section ---
st.subheader("🚨 Son Kritik Hatalar")
if log_manager:
    error_logs = log_manager.get_recent_logs(limit=10, log_type='error')

    if error_logs:
        for log in error_logs:
            with st.expander(f"❌ {log['timestamp']} - {log['source']}", expanded=False):
                st.error(log['error_message'])
                if log.get('details'):
                    st.json(log['details'])
    else:
        st.success("Son 24 saatte kritik hata bulunamadı. 🎉")
else:
    st.info("Log yöneticisi aktif değil.")

# --- Quick Actions ---
st.markdown("---")
col_act1, col_act2 = st.columns(2)

with col_act1:
    if st.button("🔄 Tüm Bağlantıları Yeniden Test Et", use_container_width=True):
        st.rerun()

with col_act2:
    if st.button("🗑️ Cache Temizle (Session State)", use_container_width=True):
        st.session_state.clear()
        st.success("Session state temizlendi. Lütfen sayfayı yenileyin.")
