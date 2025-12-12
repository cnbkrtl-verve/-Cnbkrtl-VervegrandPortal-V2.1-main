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

st.set_page_config(page_title="Shopify Ürün Transferi", layout="wide", page_icon="🔄")

# --- UI Header ---
# Using native Streamlit components for better compatibility with the new theme
st.title("🔄 Shopify'dan Shopify'a Transfer")
st.markdown("Mağazalar arası hızlı ve güvenli ürün kopyalama aracı.")

# --- Authentication ---
if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    st.warning("Lütfen devam etmek için giriş yapın.")
    st.stop()

# --- Initialize Session State ---
if 'pt_source_products' not in st.session_state: st.session_state.pt_source_products = []
if 'pt_selected_products' not in st.session_state: st.session_state.pt_selected_products = set()
if 'pt_progress' not in st.session_state: st.session_state.pt_progress = queue.Queue()
if 'pt_running' not in st.session_state: st.session_state.pt_running = False
if 'pt_latest_results' not in st.session_state: st.session_state.pt_latest_results = None

# --- API Connection Setup ---
with st.expander("🔌 Mağaza Bağlantı Ayarları", expanded=True):
    col1, col2 = st.columns(2)

    # Load default keys
    user_keys = {}
    try:
        user_keys = load_all_user_keys(st.session_state.get('username', 'admin'))
    except: pass

    with col1:
        st.subheader("Kaynak Mağaza")
        source_store = st.text_input("Kaynak Mağaza URL", value=user_keys.get('shopify_store', ''), placeholder="shop.myshopify.com", key="src_store")
        source_token = st.text_input("Kaynak Access Token", value=user_keys.get('shopify_token', ''), type="password", key="src_token")

    with col2:
        st.subheader("Hedef Mağaza")
        dest_store = st.text_input("Hedef Mağaza URL", value=user_keys.get('shopify_destination_store', ''), placeholder="dest-shop.myshopify.com", key="dest_store")
        dest_token = st.text_input("Hedef Access Token", value=user_keys.get('shopify_destination_token', ''), type="password", key="dest_token")

    if not source_store or not source_token or not dest_store or not dest_token:
        st.info("ℹ️ İşleme başlamak için bağlantı bilgilerini girin.")
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
    st.info("Kaynak mağazadan ürünleri seçip hedef mağazaya 'Taslak' veya 'Aktif' olarak eksiksiz aktarabilirsiniz.")

    # Search & Fetch
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("Ürün Ara (Başlık)", placeholder="Örn: T-Shirt", label_visibility="collapsed")
    with col_btn:
        if st.button("🔍 Ürünleri Getir", use_container_width=True):
            with st.spinner("Ürünler aranıyor..."):
                query = f"title:{search_query}*" if search_query else None
                result = source_api.get_products_page(limit=50, query=query)
                st.session_state.pt_source_products = result.get('products', [])
                st.session_state.pt_selected_products = set() # Reset selection
                if not st.session_state.pt_source_products:
                    st.toast("Ürün bulunamadı.", icon="⚠️")
                else:
                    st.toast(f"{len(st.session_state.pt_source_products)} ürün bulundu.", icon="✅")

    # Product Table
    products = st.session_state.pt_source_products
    if products:
        # Prepare data for Data Editor
        df_data = []
        for p in products:
            is_selected = p['id'] in st.session_state.pt_selected_products
            img_url = p.get('image', '')
            df_data.append({
                "Seç": is_selected,
                "Resim": img_url,
                "Ürün Adı": p['title'],
                "SKU": p['sku'],
                "Stok": p['inventory'],
                "Durum": p['status'],
                "ID": p['id'] # Hidden column for logic
            })

        df = pd.DataFrame(df_data)

        # Data Editor Configuration
        edited_df = st.data_editor(
            df,
            column_config={
                "Seç": st.column_config.CheckboxColumn(required=True),
                "Resim": st.column_config.ImageColumn(help="Ürün ana görseli"),
                "Ürün Adı": st.column_config.TextColumn(width="large"),
                "ID": None # Hide ID
            },
            hide_index=True,
            use_container_width=True,
            key="product_editor"
        )

        # Sync selection back to session state
        selected_ids = set(edited_df[edited_df["Seç"]]["ID"].tolist())
        st.session_state.pt_selected_products = selected_ids

        # Action Bar
        selected_count = len(selected_ids)
        st.write(f"**{selected_count}** ürün seçildi.")

        if selected_count > 0:
            st.divider()
            col_opt, col_go = st.columns([2, 1])
            with col_opt:
                status_option = st.radio("Hedef Durum", ["Taslak (DRAFT)", "Aktif (ACTIVE)"], horizontal=True)

            with col_go:
                if st.button(f"🚀 Transferi Başlat", type="primary", use_container_width=True):
                    status_val = "DRAFT" if "Taslak" in status_option else "ACTIVE"
                    st.session_state.pt_running = True
                    st.session_state.pt_latest_results = None

                    def run_transfer():
                        ids_to_transfer = list(st.session_state.pt_selected_products)
                        def callback(msg):
                            st.session_state.pt_progress.put({'log': msg})

                        try:
                            results = transfer_products_manual(source_api, dest_api, ids_to_transfer, status_val, callback)
                            st.session_state.pt_progress.put({'done': True, 'results': results, 'type': 'transfer'})
                        except Exception as e:
                            st.session_state.pt_progress.put({'error': str(e)})

                    thread = threading.Thread(target=run_transfer)
                    thread.start()
                    st.rerun()

# === TAB 2: STOCK SYNC ===
with tab2:
    st.warning("⚠️ **DİKKAT:** Bu işlem, Kaynak mağazadaki stok miktarlarını Hedef mağazaya **birebir kopyalar** (SKU eşleşmesi üzerinden).")

    if st.button("🔄 Stok Eşitlemeyi Başlat", type="primary"):
         st.session_state.pt_running = True
         st.session_state.pt_latest_results = None

         def run_stock_sync():
             def callback(msg):
                 st.session_state.pt_progress.put({'log': msg})

             try:
                 results = sync_stock_only_shopify_to_shopify(source_api, dest_api, callback)
                 st.session_state.pt_progress.put({'done': True, 'results': results, 'type': 'stock'})
             except Exception as e:
                 st.session_state.pt_progress.put({'error': str(e)})

         thread = threading.Thread(target=run_stock_sync)
         thread.start()
         st.rerun()

# === PROGRESS & LOGS HANDLING ===
if st.session_state.pt_running:
    with st.status("İşlem Sürüyor...", expanded=True) as status:
        log_placeholder = st.empty()
        logs = []

        while True:
            try:
                msg = st.session_state.pt_progress.get(timeout=0.5)

                if 'log' in msg:
                    logs.append(msg['log'])
                    # Show last 3 logs in the placeholder for immediate feedback
                    log_placeholder.markdown("\n".join([f"- {l}" for l in logs[-3:]]))

                if 'error' in msg:
                    status.update(label="Hata Oluştu!", state="error", expanded=True)
                    st.error(msg['error'])
                    st.session_state.pt_running = False
                    break

                if 'done' in msg:
                    status.update(label="İşlem Tamamlandı!", state="complete", expanded=False)
                    st.session_state.pt_running = False
                    st.session_state.pt_latest_results = msg
                    st.rerun()
                    break

            except queue.Empty:
                pass

# === RESULTS DISPLAY ===
if st.session_state.pt_latest_results:
    res = st.session_state.pt_latest_results

    if res.get('type') == 'stock':
        st.success("✅ Stok Eşitleme Başarılı!")
        with st.expander("Detaylı Rapor"):
            st.json(res['results'])

    elif res.get('type') == 'transfer':
        results = res['results']
        st.success("✅ Transfer İşlemi Tamamlandı!")

        c1, c2, c3 = st.columns(3)
        c1.metric("Başarılı", len(results['success']), border=True)
        c2.metric("Başarısız", len(results['failed']), border=True)
        c3.metric("Atlanan", len(results['skipped']), border=True)

        if results['failed']:
            st.error("Hatalı Ürünler")
            st.dataframe(pd.DataFrame(results['failed']))

        if st.button("Sonuçları Temizle"):
            st.session_state.pt_latest_results = None
            st.rerun()
