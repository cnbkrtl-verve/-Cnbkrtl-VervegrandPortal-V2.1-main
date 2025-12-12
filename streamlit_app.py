# streamlit_app.py (Düzeltilmiş Sürüm)

import streamlit as st
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
import pandas as pd
from io import StringIO
import threading
import queue
import os
import time

# Gerekli modülleri import ediyoruz
from config_manager import load_all_user_keys
from data_manager import load_user_data
# YENİ: Import ifadeleri yeni modüler yapıya göre güncellendi.
from connectors.shopify_api import ShopifyAPI
from connectors.sentos_api import SentosAPI

st.set_page_config(page_title="Vervegrand Sync", page_icon="🔄", layout="wide", initial_sidebar_state="expanded")

# 🎨 GLOBAL CSS YÜKLEME - Tüm sayfalarda geçerli
def load_css():
    """Global CSS dosyasını yükler - Tüm uygulamada geçerli olur"""
    css_file_path = os.path.join(os.path.dirname(__file__), 'style.css')
    
    if os.path.exists(css_file_path):
        with open(css_file_path, encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        # CSS dosyası bulunamazsa temel stiller
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        </style>
        """, unsafe_allow_html=True)

# CSS'i yükle
load_css()

# YENİ: Oturum durumu için başlangıç değerlerini ayarlayan fonksiyon
def initialize_session_state_defaults():
    """Oturum durumu için başlangıç değerlerini ayarlar."""
    defaults = {
        'authentication_status': None,
        'shopify_status': 'pending', 'sentos_status': 'pending',
        'shopify_data': {}, 'sentos_data': {}, 'user_data_loaded_for': None,
        'price_df': None, 'calculated_df': None,
        'shopify_store': None, 'shopify_token': None,
        'sentos_api_url': None, 'sentos_api_key': None, 'sentos_api_secret': None, 'sentos_cookie': None,
        'update_in_progress': False,
        'sync_progress_queue': queue.Queue(),
        'dashboard_stats': None,
        'last_stats_update': 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def load_and_verify_user_data(username):
    """Kullanıcıya özel sırları ve verileri yükler, bağlantıları test eder."""
    # YENİ: Oturum durumu önceden yüklenmişse tekrar yüklemeye gerek yok
    if st.session_state.get('user_data_loaded_for') == username:
        return

    # API anahtarlarını Streamlit Secrets'tan yükle
    user_keys = load_all_user_keys(username)
    st.session_state.update(user_keys)
    
    # Kalıcı fiyat verilerini data_manager'dan yükle
    user_price_data = load_user_data(username)
    try:
        price_df_json = user_price_data.get('price_df_json')
        if price_df_json: st.session_state.price_df = pd.read_json(StringIO(price_df_json), orient='split')
        calculated_df_json = user_price_data.get('calculated_df_json')
        if calculated_df_json: st.session_state.calculated_df = pd.read_json(StringIO(calculated_df_json), orient='split')
    except Exception as e:
        st.session_state.price_df, st.session_state.calculated_df = None, None

    # API Bağlantı Testleri
    if st.session_state.get('shopify_store') and st.session_state.get('shopify_token'):
        try:
            api = ShopifyAPI(st.session_state.shopify_store, st.session_state.shopify_token)
            # test_connection metodu ShopifyAPI sınıfına eklenmelidir.
            # st.session_state.shopify_data = api.test_connection()
            st.session_state.shopify_status = 'connected'
        except: st.session_state.shopify_status = 'failed'

    if st.session_state.get('sentos_api_url') and st.session_state.get('sentos_api_key'):
        try:
            api = SentosAPI(st.session_state.sentos_api_url, st.session_state.sentos_api_key, st.session_state.sentos_api_secret, st.session_state.sentos_cookie)
            # test_connection metodu SentosAPI sınıfına eklenmelidir.
            # st.session_state.sentos_data = api.test_connection()
            st.session_state.sentos_status = 'connected' # if st.session_state.sentos_data.get('success') else 'failed'
        except: st.session_state.sentos_status = 'failed'
            
    st.session_state['user_data_loaded_for'] = username

# --- Ana Uygulama Mantığı ---
initialize_session_state_defaults() # Sayfa yüklenirken varsayılan değerleri ayarla

# YENİ: config.yaml yerine Streamlit Secrets kullanarak authenticator yapılandırması
# Eğer config.yaml dosyası yoksa, varsayılan yapılandırma oluştur
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

if os.path.exists(config_path):
    # Eğer config.yaml varsa onu kullan
    with open(config_path, encoding='utf-8') as file:
        config = yaml.load(file, Loader=SafeLoader)
else:
    # Yoksa varsayılan yapılandırma oluştur (Streamlit Cloud için)
    # Not: Şifre hash'leri önceden oluşturulmuş olmalı
    config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@vervegrand.com',
                    'name': 'Admin',
                    'password': '$2b$12$HjMUzQ7yUbJn9vLfhez.reHQ4hCcKVc0b6djMWelYmHf2PFnigedu'  # 19519
                },
                'cnbkrtl': {
                    'email': 'cnbkrtl@vervegrand.com',
                    'name': 'Cnbkrtl',
                    'password': '$2b$12$AaeMp3GP7arq/0zLO9RBReFAfPq8.ICRLqct8VYlg.6L0UzI6iB0y'  # Cn1Bkrtl
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'vervegrand_secret_key_change_this_in_production',
            'name': 'vervegrand_auth_cookie'
        }
    }

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state.get("authentication_status"):
    load_and_verify_user_data(st.session_state.get("username"))

    # Sidebar
    with st.sidebar:
        st.title(f"Hoş geldiniz, *{st.session_state.get('name')}*!")
        authenticator.logout(use_container_width=True)

    # --- LANDING PAGE (DASHBOARD) ---
    st.markdown(f"""
    <div class="main-header" style="text-align: center; margin-bottom: 2rem;">
        <h1>👋 Hoş Geldiniz, {st.session_state.get('name')}</h1>
        <p style="font-size: 1.2rem; opacity: 0.8;">Vervegrand Operasyon Merkezi</p>
    </div>
    """, unsafe_allow_html=True)

    # KPI Stats Loader
    @st.cache_data(ttl=300)
    def load_dashboard_stats():
        stats = {}
        if st.session_state.get('shopify_status') == 'connected':
            try:
                api = ShopifyAPI(st.session_state.shopify_store, st.session_state.shopify_token)
                stats['shopify'] = api.get_dashboard_stats()
            except:
                stats['shopify'] = None
        return stats

    # Dashboard Metrics
    stats = load_dashboard_stats()

    col1, col2, col3, col4 = st.columns(4)

    # Varsayılan değerler
    s_stats = stats.get('shopify', {}) or {}

    with col1:
        st.metric(
            "Bugünkü Sipariş",
            s_stats.get('orders_today', '-'),
            delta=f"{s_stats.get('revenue_today', 0):.2f} {s_stats.get('shop_info', {}).get('currencyCode', 'TL')}"
        )

    with col2:
        st.metric(
            "Bu Ay Sipariş",
            s_stats.get('orders_this_month', '-'),
             delta=f"{s_stats.get('revenue_this_month', 0):.2f} {s_stats.get('shop_info', {}).get('currencyCode', 'TL')}"
        )

    with col3:
        st.metric(
            "Toplam Ürün",
            s_stats.get('products_count', '-'),
            help="Shopify Mağazasındaki Toplam Ürün Sayısı"
        )

    with col4:
         status_color = "🟢" if st.session_state.get('shopify_status') == 'connected' else "🔴"
         st.metric("Sistem Durumu", "Aktif", delta=f"{status_color} Shopify Bağlı")

    st.markdown("---")

    # Quick Actions Grid
    st.subheader("🚀 Hızlı İşlemler")

    row1_1, row1_2, row1_3, row1_4 = st.columns(4)

    with row1_1:
        st.info("**📦 Ürün Transferi**")
        st.caption("Shopify mağazalar arası ürün aktarımı yapın.")
        if st.button("Transfer Başlat", key="btn_transfer", use_container_width=True):
             st.switch_page("pages/13_Shopify_Magaza_Transferi.py")

    with row1_2:
        st.success("**📊 Satış Analizi**")
        st.caption("Detaylı satış ve karlılık raporlarını inceleyin.")
        if st.button("Raporları Gör", key="btn_reports", use_container_width=True):
             st.switch_page("pages/14_Satis_Analizi.py")

    with row1_3:
        st.warning("**🏷️ Metafield Yönetimi**")
        st.caption("Ürünler için özel alanları ve filtreleri düzenleyin.")
        if st.button("Metafield Düzenle", key="btn_metafield", use_container_width=True):
             st.switch_page("pages/8_Metafield_Yonetimi.py")

    with row1_4:
        st.error("**🖥️ Sistem İzleme**")
        st.caption("Logları, API durumunu ve hataları kontrol edin.")
        if st.button("Monitörü Aç", key="btn_monitor", use_container_width=True):
             st.switch_page("pages/99_Sistem_Durumu.py")

    # Categories View
    st.markdown("### 📂 Modüller")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analiz & Rapor", "🛠️ Operasyonlar", "📦 Ürün Yönetimi", "⚙️ Sistem"])

    with tab1:
        c1, c2 = st.columns(2)
        c1.page_link("pages/1_dashboard.py", label="Genel Dashboard", icon="📈")
        c1.page_link("pages/11_Siparis_Izleme.py", label="Sipariş İzleme", icon="🛒")
        c2.page_link("pages/12_Karlilik_Analizi.py", label="Karlılık Analizi", icon="💰")
        c2.page_link("pages/14_Satis_Analizi.py", label="Satış Analizi", icon="📉")

    with tab2:
        c1, c2 = st.columns(2)
        c1.page_link("pages/13_Shopify_Magaza_Transferi.py", label="Mağaza Transferi", icon="🔄")
        c1.page_link("pages/18_Shopify_Urun_Transferi.py", label="Ürün Transferi", icon="📦")
        c2.page_link("pages/3_sync.py", label="Senkronizasyon", icon="🔃")
        c2.page_link("pages/16_Toplu_Urun_Islemleri.py", label="Toplu İşlemler", icon="⚡")

    with tab3:
        c1, c2 = st.columns(2)
        c1.page_link("pages/8_Metafield_Yonetimi.py", label="Metafield Yönetimi", icon="🏷️")
        c1.page_link("pages/15_Otomatik_Kategori_Meta_Alan.py", label="Oto. Kategori & Meta", icon="🤖")
        c2.page_link("pages/6_Fiyat_Hesaplayıcı.py", label="Fiyat Hesaplayıcı", icon="🧮")
        c2.page_link("pages/17_SEO_Icerik_Yonetimi.py", label="SEO Yönetimi", icon="🔍")

    with tab4:
        c1, c2 = st.columns(2)
        c1.page_link("pages/2_settings.py", label="Ayarlar", icon="⚙️")
        c1.page_link("pages/4_logs.py", label="Log Kayıtları", icon="📝")
        c2.page_link("pages/99_Sistem_Durumu.py", label="Sistem Monitörü", icon="🖥️")
        c2.page_link("pages/10_Gelistirici_Test_Araclari.py", label="Test Araçları", icon="🧪")

elif st.session_state.get("authentication_status") is False:
    st.error('Kullanıcı adı/şifre hatalı')

elif st.session_state.get("authentication_status") is None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi girin')
