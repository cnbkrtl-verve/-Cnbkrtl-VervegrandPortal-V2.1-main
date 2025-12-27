# pages/2_settings.py (Güncellenmiş Sürüm)

import streamlit as st
import sys
import os

# Projenin ana dizinini Python'un arama yoluna ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()
import json
# YENİ: Modüler yapıya uygun olarak import yolları güncellendi.
from connectors.shopify_api import ShopifyAPI
from connectors.sentos_api import SentosAPI

# CSS'i yükle
def load_css():
    try:
        with open("style.css", encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    except UnicodeDecodeError:
        st.error("CSS dosyası encoding hatası. UTF-8 formatında kaydedildiğinden emin olun.")

# --- Giriş Kontrolü ve Sayfa Kurulumu ---
if not st.session_state.get("authentication_status"):
    st.error("Lütfen bu sayfaya erişmek için giriş yapın.")
    st.stop()

load_css()

# --- AYARLAR SAYFASI ---
st.markdown("""
<div class="main-header">
    <h1>⚙️ Ayarlar & Bağlantı Durumu</h1>
    <p>Mevcut API ayarları aşağıda listelenmiştir. Bu ayarlar Streamlit Cloud üzerinden yönetilmektedir.</p>
</div>
""", unsafe_allow_html=True)

st.info("💡 Buradaki tüm bilgiler, uygulamanızın Streamlit Cloud'daki 'Secrets' bölümünden okunmaktadır. Değişikliklerin kalıcı olması için sırlarınızı oradan yönetmelisiniz.")

# --- Ayar Görüntüleme Bölümü ---
with st.container(border=True):
    st.subheader("🔗 Mevcut API Ayarları")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h5>🏪 Shopify Ayarları</h5>", unsafe_allow_html=True)
        st.text_input("Mağaza URL", value=st.session_state.get('shopify_store', 'Değer Bulunamadı'), disabled=True)
        st.text_input("Erişim Token'ı", value="********" if st.session_state.get('shopify_token') else 'Değer Bulunamadı', type="password", disabled=True)
    
    with col2:
        st.markdown("<h5><img src='https://api.sentos.com.tr/img/favicon.png' width=20> Sentos API Ayarları</h5>", unsafe_allow_html=True)
        st.text_input("Sentos API URL", value=st.session_state.get('sentos_api_url', 'Değer Bulunamadı'), disabled=True)
        st.text_input("Sentos API Key", value=st.session_state.get('sentos_api_key', 'Değer Bulunamadı'), disabled=True)
        st.text_input("Sentos API Secret", value="********" if st.session_state.get('sentos_api_secret') else 'Değer Bulunamadı', type="password", disabled=True)
        st.text_input("Sentos API Cookie", value="********" if st.session_state.get('sentos_cookie') else 'Değer Bulunamadı', type="password", disabled=True)

with st.container(border=True):
    st.subheader("📊 Google E-Tablolar Entegrasyonu")
    gcp_json = st.session_state.get('gcp_service_account_json', '')
    if gcp_json:
        try:
            client_email = json.loads(gcp_json).get('client_email', 'JSON formatı hatalı')
            st.success(f"✅ Google Service Account anahtarı yüklendi. (Hesap: {client_email})")
        except json.JSONDecodeError:
            st.error("❌ Yüklenen Google Service Account anahtarı geçerli bir JSON formatında değil.")
    else:
        st.warning("⚠️ Google Service Account anahtarı Streamlit Secrets'ta bulunamadı.")

st.markdown("---")

# --- Bağlantı Testi Bölümü ---
st.subheader("🧪 Bağlantı Testleri")
if st.button("🔄 Tüm Bağlantıları Yeniden Test Et", use_container_width=True, type="primary"):
    with st.status("Bağlantılar test ediliyor...", expanded=True) as status:
        # Shopify Testi
        st.write("Shopify mağazasına bağlanılıyor...")
        shopify_store = st.session_state.get('shopify_store')
        shopify_token = st.session_state.get('shopify_token')

        shopify_ok = False
        if shopify_store and shopify_token:
            try:
                api = ShopifyAPI(shopify_store, shopify_token)
                result = api.test_connection()
                st.session_state.shopify_status = 'connected' if result.get('success') else 'failed'
                st.session_state.shopify_data = result
                if result.get('success'):
                    st.success(f"✅ Shopify bağlantısı başarılı! Mağaza: {result.get('name', 'N/A')}")
                    shopify_ok = True
                else:
                    st.error(f"❌ Shopify bağlantı hatası: {result.get('error', 'Bilinmeyen hata')}")
            except Exception as e:
                st.session_state.shopify_status = 'failed'
                st.error(f"❌ Shopify Bağlantısı kurulamadı: {e}")
        else:
            st.warning("Shopify bilgileri eksik, test edilemedi.")

        # Sentos Testi
        st.write("Sentos API'ye bağlanılıyor...")
        sentos_url = st.session_state.get('sentos_api_url')
        sentos_key = st.session_state.get('sentos_api_key')
        sentos_secret = st.session_state.get('sentos_api_secret')
        sentos_cookie = st.session_state.get('sentos_cookie')

        sentos_ok = False
        if sentos_url and sentos_key:
            try:
                api = SentosAPI(sentos_url, sentos_key, sentos_secret, sentos_cookie)
                result = api.test_connection()
                st.session_state.sentos_status = 'connected' if result.get('success') else 'failed'
                st.session_state.sentos_data = result
                if result.get('success'):
                    st.success(f"✅ Sentos bağlantısı başarılı! Toplam ürün: {result.get('total_products', 0)}")
                    sentos_ok = True
                else:
                    st.error(f"❌ Sentos bağlantı hatası: {result.get('error', 'Bilinmeyen hata')}")
            except Exception as e:
                st.session_state.sentos_status = 'failed'
                st.error(f"❌ Sentos Bağlantısı kurulamadı: {e}")
        else:
            st.warning("Sentos bilgileri eksik, test edilemedi.")

        # Durum güncelleme
        if shopify_ok and sentos_ok:
            status.update(label="✅ Tüm bağlantılar başarıyla doğrulandı!", state="complete", expanded=False)
        else:
            status.update(label="⚠️ Bazı bağlantılarda sorun tespit edildi.", state="error", expanded=True)