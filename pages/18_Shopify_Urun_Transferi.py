# pages/18_Shopify_Urun_Transferi.py

import streamlit as st
import pandas as pd
import threading
import queue
import time
import sys
import os

# Proje kök dizinini Python path'ine ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from connectors.shopify_api import ShopifyAPI
from operations.shopify_product_transfer import transfer_products_manual, sync_stock_only_shopify_to_shopify
from config_manager import load_all_user_keys

# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()

st.set_page_config(page_title="Shopify Ürün Transferi", layout="wide")
st.title("🔄 Shopify'dan Shopify'a Ürün & Stok Transferi")

# --- Authentication ---
if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    st.warning("Lütfen devam etmek için giriş yapın.")
    st.stop()

# --- Initialize Session State ---
if 'pt_source_products' not in st.session_state: st.session_state.pt_source_products = []
if 'pt_selected_products' not in st.session_state: st.session_state.pt_selected_products = set()
if 'pt_log' not in st.session_state: st.session_state.pt_log = []
if 'pt_progress' not in st.session_state: st.session_state.pt_progress = queue.Queue()
if 'pt_running' not in st.session_state: st.session_state.pt_running = False

# --- API Connection Setup ---
with st.expander("🔌 Mağaza Bağlantı Ayarları", expanded=True):
    col1, col2 = st.columns(2)

    # Load default keys
    user_keys = {}
    try:
        user_keys = load_all_user_keys(st.session_state.get('username', 'admin'))
    except: pass

    with col1:
        st.subheader("Kaynak Mağaza (Veri Alınacak)")
        source_store = st.text_input("Mağaza URL", value=user_keys.get('shopify_store', ''), placeholder="shop.myshopify.com", key="src_store")
        source_token = st.text_input("Access Token", value=user_keys.get('shopify_token', ''), type="password", key="src_token")

    with col2:
        st.subheader("Hedef Mağaza (Veri Gönderilecek)")
        dest_store = st.text_input("Mağaza URL", value=user_keys.get('shopify_destination_store', ''), placeholder="dest-shop.myshopify.com", key="dest_store")
        dest_token = st.text_input("Access Token", value=user_keys.get('shopify_destination_token', ''), type="password", key="dest_token")

    if not source_store or not source_token or not dest_store or not dest_token:
        st.warning("⚠️ Lütfen her iki mağaza için de bağlantı bilgilerini girin.")
        st.stop()

    # Initialize APIs
    try:
        source_api = ShopifyAPI(source_store, source_token)
        dest_api = ShopifyAPI(dest_store, dest_token)
    except Exception as e:
        st.error(f"API başlatma hatası: {e}")
        st.stop()

# --- Tabs ---
tab1, tab2 = st.tabs(["📋 Manuel Ürün Transferi", "📦 Sadece Stok Eşitleme"])

# === TAB 1: MANUEL TRANSFER ===
with tab1:
    st.header("Manuel Ürün Transferi")
    st.info("Kaynak mağazadan ürünleri seçip hedef mağazaya 'Taslak' veya 'Aktif' olarak eksiksiz aktarabilirsiniz.")

    # Search & Fetch
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("Ürün Ara (Başlık)", placeholder="Örn: T-Shirt")
    with col_btn:
        if st.button("🔍 Ürünleri Getir", use_container_width=True):
            with st.spinner("Ürünler aranıyor..."):
                query = f"title:{search_query}*" if search_query else None
                result = source_api.get_products_page(limit=50, query=query)
                st.session_state.pt_source_products = result.get('products', [])
                st.session_state.pt_selected_products = set() # Reset selection

    # Product Table
    products = st.session_state.pt_source_products
    if products:
        st.markdown(f"**{len(products)}** ürün bulundu.")

        # Select All
        if st.checkbox("Tümünü Seç"):
            st.session_state.pt_selected_products = {p['id'] for p in products}
        else:
            if len(st.session_state.pt_selected_products) == len(products): # Only deselect if all were selected
                 st.session_state.pt_selected_products = set()

        # Table Header
        cols = st.columns([0.5, 1, 3, 2, 2, 1.5])
        cols[0].write("✅")
        cols[1].write("Resim")
        cols[2].write("Ürün Adı")
        cols[3].write("SKU (Varyant)")
        cols[4].write("Stok")
        cols[5].write("Durum")

        for p in products:
            cols = st.columns([0.5, 1, 3, 2, 2, 1.5])
            is_selected = p['id'] in st.session_state.pt_selected_products

            if cols[0].checkbox("Seç", value=is_selected, key=f"sel_{p['id']}", label_visibility="collapsed"):
                st.session_state.pt_selected_products.add(p['id'])
            else:
                st.session_state.pt_selected_products.discard(p['id'])

            if p.get('image'):
                cols[1].image(p['image'], width=50)
            else:
                cols[1].text("Yok")

            cols[2].write(p['title'])
            cols[3].write(p['sku'])
            cols[4].write(p['inventory'])
            cols[5].write(p['status'])
            st.divider()

        # Action Bar
        selected_count = len(st.session_state.pt_selected_products)
        st.markdown(f"### Seçili Ürünler: {selected_count}")

        if selected_count > 0:
            status_option = st.radio("Hedef Durum", ["Taslak (DRAFT)", "Aktif (ACTIVE)"], horizontal=True)
            status_val = "DRAFT" if "Taslak" in status_option else "ACTIVE"

            if st.button(f"🚀 {selected_count} Ürünü Transfer Et", type="primary"):
                st.session_state.pt_running = True
                st.session_state.pt_log = []

                def run_transfer():
                    selected_ids = list(st.session_state.pt_selected_products)

                    def callback(msg):
                        st.session_state.pt_progress.put({'log': msg})

                    results = transfer_products_manual(source_api, dest_api, selected_ids, status_val, callback)
                    st.session_state.pt_progress.put({'done': True, 'results': results})

                thread = threading.Thread(target=run_transfer)
                thread.start()
                st.rerun()

# === TAB 2: STOCK SYNC ===
with tab2:
    st.header("Stok Eşitleme (SKU Bazlı)")
    st.warning("⚠️ DİKKAT: Bu işlem, Kaynak mağazadaki stok miktarlarını Hedef mağazaya birebir kopyalar (SKU eşleşmesi üzerinden). Diğer ürün bilgileri (fiyat, açıklama vs.) değişmez.")

    if st.button("🔄 Stok Eşitlemeyi Başlat", type="primary"):
         st.session_state.pt_running = True
         st.session_state.pt_log = []

         def run_stock_sync():
             def callback(msg):
                 st.session_state.pt_progress.put({'log': msg})

             results = sync_stock_only_shopify_to_shopify(source_api, dest_api, callback)
             st.session_state.pt_progress.put({'done': True, 'results': results, 'type': 'stock'})

         thread = threading.Thread(target=run_stock_sync)
         thread.start()
         st.rerun()

# === PROGRESS & LOGS ===
if st.session_state.pt_running:
    st.divider()
    st.subheader("⏳ İşlem Durumu")

    log_placeholder = st.empty()
    status_placeholder = st.empty()

    while True:
        try:
            msg = st.session_state.pt_progress.get(timeout=1)

            if 'log' in msg:
                st.session_state.pt_log.append(msg['log'])
                log_placeholder.code("\n".join(st.session_state.pt_log[-10:])) # Show last 10 lines

            if 'done' in msg:
                st.session_state.pt_running = False
                results = msg['results']

                if msg.get('type') == 'stock':
                    st.success(f"✅ Stok Eşitleme Tamamlandı!")
                    st.json(results)
                else:
                    st.success(f"✅ Transfer Tamamlandı!")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Başarılı", len(results['success']))
                    c2.metric("Başarısız", len(results['failed']))
                    c3.metric("Atlanan", len(results['skipped']))

                    if results['failed']:
                        st.error("Hatalar:")
                        st.dataframe(pd.DataFrame(results['failed']))
                break

        except queue.Empty:
            time.sleep(0.1)

    if st.button("Kapat ve Yenile"):
        st.session_state.pt_running = False
        st.rerun()
