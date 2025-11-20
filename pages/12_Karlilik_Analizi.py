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
from operations.sales_analytics import SalesAnalytics
from config_manager import load_all_user_keys
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Sayfa Ayarları
st.set_page_config(page_title="Kârlılık Analizi", page_icon="💰", layout="wide")
load_global_css()

# --- Yardımcı Fonksiyonlar ---

def calculate_profitability(orders, cost_map, shipping_cost, vat_rate_purchase=10):
    """Siparişleri analiz eder ve kârlılık verilerini hesaplar."""
    analysis_data = []
    
    for order in orders:
        order_name = order.get('name')
        created_at = order.get('createdAt', '')[:10] # YYYY-MM-DD
        
        # Gelirler
        total_price = float(order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
        
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
if 'profit_df' not in st.session_state:
    st.session_state.profit_df = None
if 'orders' not in st.session_state:
    st.session_state.orders = []
if 'cost_map' not in st.session_state:
    st.session_state.cost_map = {}

# Analiz Parametreleri
st.subheader("⚙️ Analiz Ayarları")

col_date1, col_date2, col_ship = st.columns(3)
start_date = col_date1.date_input("Başlangıç Tarihi", datetime.now() - timedelta(days=7))
end_date = col_date2.date_input("Bitiş Tarihi", datetime.now())
shipping_cost_input = col_ship.number_input("Sipariş Başı Kargo Gideri (TL)", value=85.0, step=5.0)

if st.button("🚀 Analizi Başlat", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(data):
        if isinstance(data, dict):
            msg = data.get('message', '')
            prog = data.get('progress', 0)
            status_text.text(msg)
            progress_bar.progress(min(prog, 100))
            
    try:
        user_keys = load_all_user_keys(st.session_state.username)
        
        # 1. API Bağlantıları
        status_text.text("🔌 API bağlantıları kuruluyor...")
        shopify = ShopifyAPI(user_keys['shopify_store'], user_keys['shopify_token'])
        sentos = SentosAPI(
            user_keys['sentos_api_url'],
            user_keys['sentos_api_key'],
            user_keys['sentos_api_secret'],
            user_keys['sentos_cookie']
        )
        sales_analytics = SalesAnalytics(sentos)
        progress_bar.progress(10)
        
        # 2. Siparişleri Çek
        status_text.text("📦 Shopify'dan siparişler çekiliyor...")
        start_iso = datetime.combine(start_date, datetime.min.time()).isoformat()
        end_iso = datetime.combine(end_date, datetime.max.time()).isoformat()
        
        orders = shopify.get_orders_by_date_range(start_iso, end_iso)
        st.session_state.orders = orders
        
        if not orders:
            status_text.text("⚠️ Seçilen tarih aralığında sipariş bulunamadı.")
            st.warning("Seçilen tarih aralığında sipariş bulunamadı.")
            progress_bar.progress(100)
        else:
            progress_bar.progress(30)
            status_text.text(f"✅ {len(orders)} sipariş çekildi. SKU'lar analiz ediliyor...")
            
            # 3. SKU'ları Belirle
            unique_skus = set()
            for order in orders:
                for item in order.get('lineItems', {}).get('nodes', []):
                    sku = str(item.get('variant', {}).get('sku', '')).strip()
                    if sku:
                        unique_skus.add(sku)
            
            # 4. Maliyetleri Çek (Optimize Edilmiş)
            status_text.text(f"🔍 {len(unique_skus)} farklı ürün için maliyetler Sentos'tan çekiliyor...")
            
            # Progress callback adaptörü
            def cost_progress_callback(data):
                # 30 ile 80 arası progress
                base_progress = 30
                range_progress = 50
                
                if isinstance(data, dict):
                    sub_progress = data.get('progress', 0)
                    total_progress = base_progress + int((sub_progress / 100) * range_progress)
                    update_progress({'message': data.get('message'), 'progress': total_progress})

            cost_map = sales_analytics._fetch_costs_for_skus(unique_skus, progress_callback=cost_progress_callback)
            st.session_state.cost_map = cost_map
            
            progress_bar.progress(80)
            status_text.text("💰 Kârlılık hesaplanıyor...")
            
            # 5. Hesaplama
            df_profit = calculate_profitability(orders, cost_map, shipping_cost_input)
            st.session_state.profit_df = df_profit
            
            progress_bar.progress(100)
            status_text.text("✅ Analiz tamamlandı!")
            st.success(f"✅ {len(orders)} sipariş başarıyla analiz edildi.")
            
            # DEBUG: Maliyet Kontrolü
            with st.expander("🛠️ Geliştirici Detayları (Maliyet Kontrolü)"):
                st.info("ℹ️ Sistem artık SKU ile bulamazsa Barkod ile de arama yapmaktadır.")
                st.write(f"Toplam {len(unique_skus)} adet benzersiz SKU tarandı.")
                st.write(f"Bulunan Maliyet Sayısı: {len(cost_map)}")
                
                # Maliyeti 0 olanları ve olmayanları ayır
                found_costs = {k: v for k, v in cost_map.items() if v > 0}
                missing_costs = [sku for sku in unique_skus if sku not in cost_map or cost_map[sku] == 0]
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("✅ Maliyeti Bulunanlar (Örnek 20):")
                    st.json(dict(list(found_costs.items())[:20]))
                with c2:
                    st.write("⚠️ Maliyeti Bulunamayanlar/Sıfır Olanlar (Örnek 20):")
                    st.write(missing_costs[:20])

    except Exception as e:
        st.error(f"Analiz sırasında hata: {e}")
        status_text.text("❌ Hata oluştu.")
        import traceback
        st.code(traceback.format_exc())

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
    
    if total_cost == 0 and total_revenue > 0:
        st.warning("⚠️ Toplam maliyet 0.00 ₺ görünüyor. Bu durum şunlardan kaynaklanabilir:")
        st.markdown("""
        - Ürünlerin Sentos'ta **alış fiyatı** girilmemiş olabilir.
        - Shopify'daki **SKU**'lar ile Sentos'taki **SKU** veya **Barkod**'lar eşleşmiyor olabilir.
        - "Geliştirici Detayları" kısmından hangi ürünlerin maliyetinin bulunamadığını kontrol edebilirsiniz.
        """)
    
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
    js_code = JsCode("""
    function(params) {
        if (params.value < 0) {
            return {'color': 'red', 'fontWeight': 'bold'};
        } else {
            return {'color': 'green', 'fontWeight': 'bold'};
        }
    }
    """)
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

    # --- YENİ: Detaylı Sipariş Analizi (Button Dışında) ---
    if st.session_state.orders:
        st.divider()
        st.subheader("🔍 Detaylı Sipariş İnceleme")
        
        orders = st.session_state.orders
        cost_map = st.session_state.cost_map
        
        selected_order_name = st.selectbox(
            "İncelemek istediğiniz siparişi seçin:",
            options=[o.get('name') for o in orders],
            index=0
        )
        
        if selected_order_name:
            selected_order = next((o for o in orders if o.get('name') == selected_order_name), None)
            if selected_order:
                st.write(f"**Sipariş:** {selected_order_name}")
                
                # Gelir
                total_price = float(selected_order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
                st.write(f"**Toplam Tutar (Ciro):** {total_price:,.2f} ₺")
                
                # Kalemler
                items_data = []
                total_calc_cost = 0
                
                for item in selected_order.get('lineItems', {}).get('nodes', []):
                    sku = str(item.get('variant', {}).get('sku', '')).strip()
                    quantity = int(item.get('quantity', 0))
                    title = item.get('title', '')
                    
                    unit_cost_raw = cost_map.get(sku, 0.0)
                    unit_cost_vat = unit_cost_raw * 1.10
                    line_cost = unit_cost_vat * quantity
                    total_calc_cost += line_cost
                    
                    items_data.append({
                        "Ürün": title,
                        "SKU": sku,
                        "Adet": quantity,
                        "Birim Maliyet (Ham)": f"{unit_cost_raw:,.2f} ₺",
                        "Birim Maliyet (+KDV)": f"{unit_cost_vat:,.2f} ₺",
                        "Toplam Maliyet": f"{line_cost:,.2f} ₺"
                    })
                
                st.table(items_data)
                
                st.write(f"**Hesaplanan Toplam Ürün Maliyeti:** {total_calc_cost:,.2f} ₺")
                st.write(f"**Kargo Gideri:** {shipping_cost_input:,.2f} ₺")
                
                net_profit = total_price - total_calc_cost - shipping_cost_input
                st.metric("Bu Sipariş İçin Net Kâr", f"{net_profit:,.2f} ₺", delta_color="normal" if net_profit > 0 else "inverse")
                
                if net_profit < 0:
                    st.error(f"⚠️ Bu siparişte {abs(net_profit):,.2f} ₺ zarar görünüyor. Lütfen yukarıdaki tablodan birim maliyetleri kontrol edin.")
                    st.info("Eğer 'Birim Maliyet (Ham)' beklediğinizden yüksekse, Sentos'taki alış fiyatını kontrol edin.")
                    st.info("Eğer 'Birim Maliyet (Ham)' 0.00 ₺ ise, ürün Sentos'ta bulunamamış veya maliyeti girilmemiştir.")
                
                # --- CANLI KONTROL BUTONU ---
                st.divider()
                if st.button("🔍 Bu Sipariş İçin Canlı Sentos Kontrolü Yap (Debug)", type="secondary"):
                    st.info("Sentos API'ye canlı sorgu atılıyor... Lütfen bekleyin.")
                    
                    # API Bağlantısı (Tekrar kuruyoruz çünkü session state'de obje saklanamaz)
                    try:
                        user_keys = load_all_user_keys(st.session_state.username)
                        sentos_debug = SentosAPI(
                            user_keys['sentos_api_url'],
                            user_keys['sentos_api_key'],
                            user_keys['sentos_api_secret'],
                            user_keys['sentos_cookie']
                        )
                        
                        debug_results = []
                        
                        for item in selected_order.get('lineItems', {}).get('nodes', []):
                            sku = str(item.get('variant', {}).get('sku', '')).strip()
                            
                            # 1. SKU ile Ara
                            found_product = sentos_debug.get_product_by_sku(sku)
                            method = "SKU"
                            
                            # 2. Bulunamazsa Barkod ile Ara
                            if not found_product:
                                found_product = sentos_debug.get_product_by_barcode(sku)
                                method = "BARKOD"
                            
                            if found_product:
                                p_name = found_product.get('name', 'İsimsiz')
                                p_sku = found_product.get('sku', '')
                                p_price = found_product.get('purchase_price') or found_product.get('AlisFiyati')
                                
                                # Varyant kontrolü
                                variant_match = "Hayır"
                                variant_sku = "-"
                                
                                # Varyantlarda ara
                                for v in found_product.get('variants', []):
                                    v_s = str(v.get('sku', '')).strip().lower()
                                    v_b = str(v.get('barcode', '')).strip().lower()
                                    target = sku.lower()
                                    
                                    if v_s == target or v_b == target:
                                        variant_match = "Evet"
                                        variant_sku = v.get('sku', '')
                                        # Varyant fiyatı varsa onu al
                                        v_p = v.get('purchase_price') or v.get('AlisFiyati')
                                        if v_p:
                                            p_price = v_p
                                        break
                                
                                debug_results.append({
                                    "Aranan SKU": sku,
                                    "Bulunan Yöntem": method,
                                    "Sentos Ürün Adı": p_name,
                                    "Sentos Ana SKU": p_sku,
                                    "Varyant Eşleşmesi": variant_match,
                                    "Varyant SKU": variant_sku,
                                    "Sentos Fiyat (Ham)": p_price
                                })
                            else:
                                debug_results.append({
                                    "Aranan SKU": sku,
                                    "Bulunan Yöntem": "-",
                                    "Sentos Ürün Adı": "BULUNAMADI",
                                    "Sentos Ana SKU": "-",
                                    "Varyant Eşleşmesi": "-",
                                    "Varyant SKU": "-",
                                    "Sentos Fiyat (Ham)": "0"
                                })
                        
                        st.write("### Canlı Sorgu Sonuçları")
                        st.dataframe(pd.DataFrame(debug_results))
                        st.warning("Not: Eğer 'Sentos Ürün Adı' tüm satırlarda aynıysa, API yanlış ürünü döndürüyor demektir.")
                        
                    except Exception as e:
                        st.error(f"Canlı kontrol sırasında hata: {e}")

