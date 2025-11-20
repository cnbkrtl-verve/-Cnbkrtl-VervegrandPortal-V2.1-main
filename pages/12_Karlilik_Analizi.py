import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import numpy as np

# Proje kök dizinini ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.style_loader import load_global_css
from connectors.shopify_api import ShopifyAPI
from connectors.sentos_api import SentosAPI
from gsheets_manager import load_pricing_data_from_gsheets
from config_manager import load_all_user_keys
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Sayfa Ayarları
st.set_page_config(page_title="Kârlılık Analizi", page_icon="💰", layout="wide")
load_global_css()

# --- Yardımcı Fonksiyonlar ---

def process_cost_data(product_list):
    """Sentos verisini maliyet sözlüğüne çevirir: SKU -> Alış Fiyatı"""
    cost_map = {}
    for p in product_list:
        # Ana ürün
        main_sku = str(p.get('sku', '')).strip()
        try:
            price = float(str(p.get('purchase_price') or p.get('AlisFiyati') or '0').replace(',', '.'))
        except:
            price = 0.0
        
        if main_sku:
            cost_map[main_sku] = price
            
        # Varyantlar
        for v in p.get('variants', []):
            v_sku = str(v.get('sku', '')).strip()
            try:
                v_price = float(str(v.get('purchase_price') or v.get('AlisFiyati') or '0').replace(',', '.'))
            except:
                v_price = 0.0
            
            # Varyant fiyatı 0 ise ana ürün fiyatını kullan
            final_price = v_price if v_price > 0 else price
            if v_sku:
                cost_map[v_sku] = final_price
                
    return cost_map

def calculate_profitability(orders, cost_map, shipping_cost, vat_rate_purchase=10):
    """Siparişleri analiz eder ve kârlılık verilerini hesaplar."""
    analysis_data = []
    
    for order in orders:
        order_name = order.get('name')
        created_at = order.get('createdAt', '')[:10] # YYYY-MM-DD
        
        # Gelirler
        total_price = float(order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
        subtotal_price = float(order.get('currentSubtotalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
        total_discounts = float(order.get('totalDiscountsSet', {}).get('shopMoney', {}).get('amount', 0))
        
        # Maliyetler
        total_product_cost = 0
        items_details = []
        
        for item in order.get('lineItems', {}).get('nodes', []):
            sku = str(item.get('variant', {}).get('sku', '')).strip()
            quantity = int(item.get('quantity', 0))
            
            # Maliyet Bulma
            unit_cost = cost_map.get(sku, 0.0)
            
            # Alış KDV Ekleme (+%10)
            unit_cost_with_vat = unit_cost * (1 + vat_rate_purchase / 100)
            
            line_cost = unit_cost_with_vat * quantity
            total_product_cost += line_cost
            
            items_details.append(f"{sku} (x{quantity})")
            
        # Kârlılık Hesaplama
        # Brüt Kâr = Satış Cirosu (Subtotal) - Ürün Maliyeti (KDV'li)
        # Not: Subtotal genellikle indirimler düşüldükten sonraki tutardır, ama vergi hariç olabilir.
        # Shopify'da 'currentSubtotalPriceSet' genellikle vergi öncesi, indirim sonrası tutardır.
        # Kullanıcı "satıştan çıkacağız" dediği için Total Price (KDV dahil, kargo dahil) mi yoksa Subtotal mi kullanmalı?
        # Genellikle Brüt Kâr = Net Satışlar - SMM.
        # Basitlik için: Total Price (Müşterinin ödediği) üzerinden gidelim, kargoyu gider düşelim.
        
        gross_profit = total_price - total_product_cost
        net_profit = gross_profit - shipping_cost
        
        # Margin
        margin_percent = (net_profit / total_price * 100) if total_price > 0 else 0
        
        analysis_data.append({
            "Sipariş No": order_name,
            "Tarih": created_at,
            "Toplam Tutar": total_price,
            "Ürün Maliyeti (KDV'li)": total_product_cost,
            "Kargo Gideri": shipping_cost,
            "Brüt Kâr": gross_profit,
            "Net Kâr": net_profit,
            "Kâr Marjı (%)": margin_percent,
            "Ürünler": ", ".join(items_details),
            "SKU Sayısı": len(items_details)
        })
        
    return pd.DataFrame(analysis_data)

# --- Ana Uygulama ---

st.title("📈 Sipariş Kârlılık Analizi")
st.markdown("Sipariş bazlı net kârlılık analizi. Ürün maliyetleri, kargo giderleri ve vergiler dahil.")

if 'authentication_status' not in st.session_state or not st.session_state.authentication_status:
    st.warning("Lütfen önce giriş yapın.")
    st.stop()

# Session State Başlatma
if 'cost_map' not in st.session_state:
    st.session_state.cost_map = {}
if 'profit_df' not in st.session_state:
    st.session_state.profit_df = None

# 1. Maliyet Verisi Yükleme
with st.expander("1️⃣ Maliyet Verileri (Sentos/G-Sheets)", expanded=not bool(st.session_state.cost_map)):
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button("🔄 Sentos'tan Maliyetleri Çek", use_container_width=True):
            with st.spinner("Sentos'tan güncel alış fiyatları çekiliyor..."):
                try:
                    user_keys = load_all_user_keys(st.session_state.username)
                    sentos = SentosAPI(
                        user_keys['sentos_api_url'],
                        user_keys['sentos_api_key'],
                        user_keys['sentos_api_secret'],
                        user_keys['sentos_cookie']
                    )
                    products = sentos.get_all_products()
                    if products:
                        st.session_state.cost_map = process_cost_data(products)
                        st.success(f"✅ {len(st.session_state.cost_map)} adet ürün maliyeti yüklendi.")
                    else:
                        st.error("Sentos'tan veri alınamadı.")
                except Exception as e:
                    st.error(f"Hata: {e}")

    with c2:
        if st.button("📄 G-Sheets'ten Maliyetleri Yükle", use_container_width=True):
            with st.spinner("Google Sheets'ten yükleniyor..."):
                try:
                    main_df, variants_df = load_pricing_data_from_gsheets()
                    cost_map = {}
                    # Main DF
                    if main_df is not None:
                        for _, row in main_df.iterrows():
                            cost_map[str(row['MODEL KODU']).strip()] = float(row.get('ALIŞ FİYATI', 0))
                    # Variants DF
                    if variants_df is not None:
                        for _, row in variants_df.iterrows():
                            cost_map[str(row['sku']).strip()] = float(row.get('purchase_price', 0))
                    
                    st.session_state.cost_map = cost_map
                    st.success(f"✅ {len(cost_map)} adet ürün maliyeti yüklendi.")
                except Exception as e:
                    st.error(f"Hata: {e}")

    if st.session_state.cost_map:
        st.info(f"Hafızada {len(st.session_state.cost_map)} ürün için maliyet bilgisi mevcut.")

# 2. Sipariş Analizi
st.markdown("---")
st.subheader("2️⃣ Sipariş Analizi")

col_date1, col_date2, col_ship = st.columns(3)
start_date = col_date1.date_input("Başlangıç Tarihi", datetime.now() - timedelta(days=7))
end_date = col_date2.date_input("Bitiş Tarihi", datetime.now())
shipping_cost_input = col_ship.number_input("Sipariş Başı Kargo Gideri (TL)", value=85.0, step=5.0)

if st.button("🚀 Analizi Başlat", type="primary", use_container_width=True):
    if not st.session_state.cost_map:
        st.error("⚠️ Lütfen önce maliyet verilerini yükleyin (Adım 1).")
    else:
        with st.spinner("Shopify'dan siparişler çekiliyor ve analiz ediliyor..."):
            try:
                user_keys = load_all_user_keys(st.session_state.username)
                shopify = ShopifyAPI(user_keys['shopify_store'], user_keys['shopify_token'])
                
                # Tarihleri ISO formatına çevir
                start_iso = datetime.combine(start_date, datetime.min.time()).isoformat()
                end_iso = datetime.combine(end_date, datetime.max.time()).isoformat()
                
                orders = shopify.get_orders_by_date_range(start_iso, end_iso)
                
                if not orders:
                    st.warning("Seçilen tarih aralığında sipariş bulunamadı.")
                else:
                    df_profit = calculate_profitability(orders, st.session_state.cost_map, shipping_cost_input)
                    st.session_state.profit_df = df_profit
                    st.success(f"✅ {len(orders)} sipariş analiz edildi.")
                    
            except Exception as e:
                st.error(f"Analiz sırasında hata: {e}")

# 3. Sonuçlar ve Görselleştirme
if st.session_state.profit_df is not None and not st.session_state.profit_df.empty:
    df = st.session_state.profit_df
    
    # Özet Metrikler
    total_revenue = df['Toplam Tutar'].sum()
    total_cost = df["Ürün Maliyeti (KDV'li)"].sum()
    total_shipping = df['Kargo Gideri'].sum()
    total_net_profit = df['Net Kâr'].sum()
    avg_margin = df['Kâr Marjı (%)'].mean()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Ciro", f"{total_revenue:,.2f} ₺")
    m2.metric("Toplam Maliyet (KDV'li)", f"{total_cost:,.2f} ₺", delta_color="inverse")
    m3.metric("Toplam Kargo", f"{total_shipping:,.2f} ₺", delta_color="inverse")
    m4.metric("Toplam Net Kâr", f"{total_net_profit:,.2f} ₺", f"%{avg_margin:.1f}", delta_color="normal")
    
    # Grafikler
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        # Günlük Kâr Grafiği
        daily_profit = df.groupby('Tarih')['Net Kâr'].sum().reset_index()
        fig_daily = px.bar(daily_profit, x='Tarih', y='Net Kâr', title="Günlük Net Kâr Dağılımı", color='Net Kâr', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_daily, use_container_width=True)
        
    with c_chart2:
        # Kâr Marjı Histogramı
        fig_hist = px.histogram(df, x="Kâr Marjı (%)", nbins=20, title="Sipariş Kâr Marjı Dağılımı", color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_hist, use_container_width=True)
        
    # Detaylı Tablo (Ag-Grid)
    st.subheader("📋 Sipariş Detayları")
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_side_bar()
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
    
    # Para formatları
    currency_cols = ['Toplam Tutar', "Ürün Maliyeti (KDV'li)", 'Kargo Gideri', 'Brüt Kâr', 'Net Kâr']
    for col in currency_cols:
        gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=2)
        
    gb.configure_column("Kâr Marjı (%)", type=["numericColumn", "numberColumnFilter"], precision=2)
    
    # Koşullu Biçimlendirme (Negatif kâr kırmızı)
    js_code = """
    function(params) {
        if (params.value < 0) {
            return {'color': 'red', 'fontWeight': 'bold'};
        } else {
            return {'color': 'green', 'fontWeight': 'bold'};
        }
    }
    """
    gb.configure_column("Net Kâr", cellStyle=js_code)
    
    gridOptions = gb.build()
    
    AgGrid(
        df,
        gridOptions=gridOptions,
        enable_enterprise_modules=False,
        allow_unsafe_jscode=True,
        columns_auto_size_mode=2,
        theme='streamlit'
    )
    
    # İndirme Butonu
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Raporu İndir (CSV)",
        csv,
        "karlilik_raporu.csv",
        "text/csv",
        key='download-csv'
    )
