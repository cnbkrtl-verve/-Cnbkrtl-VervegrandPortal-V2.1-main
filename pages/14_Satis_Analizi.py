# pages/14_Satis_Analizi.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Proje root'unu path'e ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from connectors.sentos_api import SentosAPI
from operations.sales_analytics import SalesAnalytics
from config_manager import load_all_user_keys

# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()

st.set_page_config(page_title="Satış Analizi", page_icon="📊", layout="wide")
st.title("📊 Satış Analizi ve Karlılık Raporu")

# --- Oturum Kontrolü ---
if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    st.warning("⚠️ Lütfen devam etmek için giriş yapın.")
    st.stop()

# --- API Bilgilerini Yükle ---
try:
    user_keys = load_all_user_keys(st.session_state.get('username', 'admin'))
    sentos_url = user_keys.get('sentos_api_url')
    sentos_key = user_keys.get('sentos_api_key')
    sentos_secret = user_keys.get('sentos_api_secret')
    sentos_cookie = user_keys.get('sentos_cookie')
    
    if not all([sentos_url, sentos_key, sentos_secret]):
        st.error("❌ Sentos API bilgileri eksik. Lütfen ayarlar sayfasından yapılandırın.")
        
        # Debug bilgisi
        with st.expander("🔍 Debug Bilgisi"):
            st.write("API Bilgileri Durumu:")
            st.write(f"- SENTOS_API_URL: {'✅ Tanımlı' if sentos_url else '❌ Eksik'}")
            st.write(f"- SENTOS_API_KEY: {'✅ Tanımlı' if sentos_key else '❌ Eksik'}")
            st.write(f"- SENTOS_API_SECRET: {'✅ Tanımlı' if sentos_secret else '❌ Eksik'}")
            st.write(f"- SENTOS_COOKIE: {'✅ Tanımlı' if sentos_cookie else '⚠️ Opsiyonel'}")
            
            st.info("""
            **Ayarlar Sayfasına Gitmek İçin:**
            1. Sol menüden "Settings" (⚙️) sayfasını açın
            2. Sentos API bilgilerini girin
            3. "Kaydet" butonuna tıklayın
            4. Bu sayfaya geri dönün
            """)
        st.stop()
    
    sentos_api = SentosAPI(sentos_url, sentos_key, sentos_secret, sentos_cookie)
    analytics = SalesAnalytics(sentos_api)
    
    # API bağlantı durumu göstergesi
    st.sidebar.success("✅ Sentos API Bağlantısı Aktif")
    
    # Debug modu
    if st.sidebar.checkbox("🔧 Debug Modu (Geliştirici)", value=False):
        st.session_state['debug_mode'] = True
    else:
        st.session_state['debug_mode'] = False
    
except Exception as e:
    st.error(f"❌ API bağlantısı kurulamadı: {e}")
    import traceback
    with st.expander("🔍 Detaylı Hata Bilgisi"):
        st.code(traceback.format_exc())
    st.stop()

# --- Filtreler ---
st.sidebar.header("🔍 Filtreler")

# Tarih aralığı
date_option = st.sidebar.selectbox(
    "Tarih Aralığı",
    ["Son 7 Gün", "Son 30 Gün", "Son 90 Gün", "Bu Ay", "Geçen Ay", "Özel Aralık"]
)

today = datetime.now().date()
if date_option == "Son 7 Gün":
    start_date = today - timedelta(days=7)
    end_date = today
elif date_option == "Son 30 Gün":
    start_date = today - timedelta(days=30)
    end_date = today
elif date_option == "Son 90 Gün":
    start_date = today - timedelta(days=90)
    end_date = today
elif date_option == "Bu Ay":
    start_date = today.replace(day=1)
    end_date = today
elif date_option == "Geçen Ay":
    last_month = today.replace(day=1) - timedelta(days=1)
    start_date = last_month.replace(day=1)
    end_date = last_month
else:  # Özel Aralık
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Başlangıç", today - timedelta(days=30))
    with col2:
        end_date = st.date_input("Bitiş", today)

# Pazar yeri filtresi
marketplace_options = ["Tümü", "Trendyol", "Hepsiburada", "N11", "Amazon", "Çiçeksepeti", "Diğer"]
selected_marketplace = st.sidebar.selectbox("Pazar Yeri", marketplace_options)
marketplace_filter = None if selected_marketplace == "Tümü" else selected_marketplace.lower()

# Analiz butonu
if st.sidebar.button("📊 Analizi Başlat", type="primary", use_container_width=True):
    st.session_state['run_analysis'] = True
    st.session_state['analysis_params'] = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'marketplace': marketplace_filter
    }

# --- Yardım Bölümü ---
with st.sidebar.expander("ℹ️ Yardım"):
    st.markdown("""
    ### Satış Analizi
    
    Bu modül Sentos'tan e-ticaret satış verilerini çeker ve detaylı analiz yapar.
    
    **Özellikler:**
    - 📦 Brüt ve net adet analizi
    - 💰 Brüt ve net ciro hesaplaması
    - 🔄 İade analizi
    - 📊 Pazar yeri bazında raporlama
    - 📈 Karlılık analizi
    - 💵 Maliyet ve kar marjı hesaplama
    
    **Not:** Sadece e-ticaret kanalı verileri kullanılır (retail hariç).
    """)

# --- Ana İçerik ---
if st.session_state.get('run_analysis', False):
    params = st.session_state['analysis_params']
    
    # İlerleme göstergesi
    progress_container = st.empty()
    status_text = st.empty()
    
    def progress_callback(data):
        progress_container.progress(data['progress'] / 100)
        status_text.info(data['message'])
    
    try:
        # Analizi çalıştır
        with st.spinner("Veriler çekiliyor ve analiz ediliyor..."):
            analysis_result = analytics.analyze_sales_data(
                start_date=params['start_date'],
                end_date=params['end_date'],
                marketplace=params['marketplace'],
                progress_callback=progress_callback
            )
        
        progress_container.empty()
        status_text.empty()
        
        # Sonuçları session'a kaydet
        st.session_state['analysis_result'] = analysis_result
        st.session_state['analysis_params'] = params  # Parametreleri de kaydet
        st.session_state['run_analysis'] = False
        
        st.success("✅ Analiz tamamlandı!")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Analiz sırasında hata oluştu: {str(e)}")
        
        # Detaylı hata bilgisi
        import traceback
        with st.expander("🔍 Detaylı Hata Bilgisi"):
            st.code(traceback.format_exc())
            st.write("**API Parametreleri:**")
            st.json({
                'start_date': params['start_date'],
                'end_date': params['end_date'],
                'marketplace': params['marketplace']
            })
        
        progress_container.empty()
        status_text.empty()
        st.session_state['run_analysis'] = False

# --- Sonuçları Göster ---
if 'analysis_result' in st.session_state:
    result = st.session_state['analysis_result']
    params = st.session_state.get('analysis_params', {})
    summary = result['summary']
    by_marketplace = result['by_marketplace']
    by_date = result['by_date']
    by_product = result['by_product']
    returns = result['returns']
    profitability = result['profitability']
    
    # Debug modu - Ham veri göster
    if st.session_state.get('debug_mode', False):
        with st.expander("🔍 DEBUG: Ham Analiz Sonuçları", expanded=True):
            st.warning("⚠️ Eğer tüm değerler 0 ise, lütfen terminal/konsol çıktısını kontrol edin!")
            st.info("Terminal'de `Sentos API Response Yapısı` ve `İlk sipariş örneği` loglarını arayın.")
            
            st.subheader("Pazar Yeri Verileri")
            st.json(by_marketplace)
            
            st.subheader("İlk 3 Ürün")
            st.json(dict(list(by_product.items())[:3]) if by_product else {})
            
            st.subheader("Özet")
            st.json(summary)
            
            # Terminal log talimatları
            st.divider()
            st.markdown("""
            ### 📋 Terminal Loglarını Nasıl Bulursunuz?
            
            1. Streamlit'in çalıştığı terminal/konsol penceresine gidin
            2. Şu satırları arayın:
               - `Sentos API Response Yapısı:`
               - `İlk sipariş keys:`
               - `İlk sipariş örneği:`
            3. Bu bilgileri kopyalayıp paylaşın
            
            **Örnek log çıktısı:**
            ```
            INFO - Sentos API Response Yapısı: ['data', 'total', 'page']
            INFO - İlk sipariş keys: ['id', 'orderNumber', 'marketplace', 'items', ...]
            INFO - İlk sipariş örneği: {'id': 123, 'marketplace': 'trendyol', ...}
            ```
            """)
            st.json(summary)
    
    # --- ÖZET KARTLARı ---
    st.header("📋 Genel Özet")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Toplam Sipariş",
            f"{summary['total_orders']:,}",
            help="Toplam sipariş sayısı"
        )
    
    with col2:
        st.metric(
            "Brüt Adet",
            f"{int(summary['gross_quantity']):,}",
            help="İadeler dahil toplam satılan adet"
        )
    
    with col3:
        st.metric(
            "Net Adet",
            f"{int(summary['net_quantity']):,}",
            delta=f"-{int(summary['return_quantity'])} iade",
            delta_color="inverse",
            help="İadeler düşüldükten sonraki net adet"
        )
    
    with col4:
        st.metric(
            "Brüt Ciro",
            f"₺{summary['gross_revenue']:,.2f}",
            help="İadeler dahil toplam ciro"
        )
    
    with col5:
        st.metric(
            "Net Ciro",
            f"₺{summary['net_revenue']:,.2f}",
            delta=f"-₺{summary['return_amount']:,.2f} iade",
            delta_color="inverse",
            help="İadeler düşüldükten sonraki net ciro"
        )
    
    st.divider()
    
    # --- KARLILIK KARTLARI ---
    st.header("💰 Karlılık Analizi")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Toplam Maliyet",
            f"₺{summary['total_cost']:,.2f}",
            help="Satılan ürünlerin toplam maliyeti"
        )
    
    with col2:
        st.metric(
            "Brüt Kar",
            f"₺{summary['gross_profit']:,.2f}",
            help="Net Ciro - Toplam Maliyet"
        )
    
    with col3:
        profit_color = "normal" if summary['profit_margin'] >= 20 else "inverse"
        st.metric(
            "Kar Marjı",
            f"%{summary['profit_margin']:.2f}",
            help="(Brüt Kar / Net Ciro) × 100"
        )
    
    with col4:
        st.metric(
            "İade Oranı",
            f"%{returns['return_rate']:.2f}",
            delta=f"{int(summary['return_quantity'])} adet",
            delta_color="inverse",
            help="İade edilen ürün oranı"
        )
    
    st.divider()
    
    # --- GRAFIKLER ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Pazar Yeri Analizi",
        "📈 Tarihsel Analiz", 
        "🏆 Ürün Analizi",
        "🔄 İade Analizi",
        "💵 Karlılık Detayları"
    ])
    
    # TAB 1: Pazar Yeri Analizi
    with tab1:
        if by_marketplace:
            st.subheader("Pazar Yeri Bazında Performans")
            
            # DataFrame oluştur
            mp_df = pd.DataFrame([
                {
                    'Pazar Yeri': mp.title(),
                    'Sipariş': data['order_count'],
                    'Brüt Adet': int(data['gross_quantity']),
                    'Net Adet': int(data['net_quantity']),
                    'İade Adet': int(data['return_quantity']),
                    'Brüt Ciro': data['gross_revenue'],
                    'Net Ciro': data['net_revenue'],
                    'İade Tutarı': data['return_amount'],
                    'Maliyet': data['total_cost'],
                    'Brüt Kar': data['gross_profit'],
                    'Kar Marjı (%)': data.get('profit_margin', 0)
                }
                for mp, data in by_marketplace.items()
            ])
            
            # Pasta grafik - Ciro dağılımı
            col1, col2 = st.columns(2)
            
            with col1:
                fig_revenue = px.pie(
                    mp_df, 
                    values='Net Ciro', 
                    names='Pazar Yeri',
                    title='Ciro Dağılımı (Net)',
                    hole=0.4
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
            
            with col2:
                fig_orders = px.pie(
                    mp_df, 
                    values='Sipariş', 
                    names='Pazar Yeri',
                    title='Sipariş Dağılımı',
                    hole=0.4
                )
                st.plotly_chart(fig_orders, use_container_width=True)
            
            # Bar chart - Karlılık
            fig_profit = px.bar(
                mp_df.sort_values('Brüt Kar', ascending=False),
                x='Pazar Yeri',
                y=['Net Ciro', 'Maliyet', 'Brüt Kar'],
                title='Pazar Yeri Karlılık Analizi',
                barmode='group'
            )
            st.plotly_chart(fig_profit, use_container_width=True)
            
            # Detaylı tablo
            st.subheader("Detaylı Veriler")
            
            # Para formatı
            mp_df_display = mp_df.copy()
            mp_df_display['Brüt Ciro'] = mp_df_display['Brüt Ciro'].apply(lambda x: f"₺{x:,.2f}")
            mp_df_display['Net Ciro'] = mp_df_display['Net Ciro'].apply(lambda x: f"₺{x:,.2f}")
            mp_df_display['İade Tutarı'] = mp_df_display['İade Tutarı'].apply(lambda x: f"₺{x:,.2f}")
            mp_df_display['Maliyet'] = mp_df_display['Maliyet'].apply(lambda x: f"₺{x:,.2f}")
            mp_df_display['Brüt Kar'] = mp_df_display['Brüt Kar'].apply(lambda x: f"₺{x:,.2f}")
            mp_df_display['Kar Marjı (%)'] = mp_df_display['Kar Marjı (%)'].apply(lambda x: f"%{x:.2f}")
            
            st.dataframe(mp_df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Seçilen filtrelere uygun veri bulunamadı.")
    
    # TAB 2: Tarihsel Analiz
    with tab2:
        if by_date:
            st.subheader("Günlük Satış Trendi")
            
            # DataFrame oluştur
            date_df = pd.DataFrame([
                {
                    'Tarih': date,
                    'Sipariş': data['order_count'],
                    'Brüt Adet': int(data['gross_quantity']),
                    'Net Adet': int(data['net_quantity']),
                    'Brüt Ciro': data['gross_revenue'],
                    'Net Ciro': data['net_revenue'],
                    'İade Adet': int(data['return_quantity']),
                    'İade Tutarı': data['return_amount']
                }
                for date, data in by_date.items()
            ]).sort_values('Tarih')
            
            # Çizgi grafik - Ciro trendi
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=date_df['Tarih'], 
                y=date_df['Brüt Ciro'],
                name='Brüt Ciro',
                line=dict(color='#1f77b4', width=2)
            ))
            fig_trend.add_trace(go.Scatter(
                x=date_df['Tarih'], 
                y=date_df['Net Ciro'],
                name='Net Ciro',
                line=dict(color='#2ca02c', width=2)
            ))
            fig_trend.update_layout(
                title='Günlük Ciro Trendi',
                xaxis_title='Tarih',
                yaxis_title='Ciro (₺)',
                hovermode='x unified'
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Bar chart - Adet trendi
            fig_quantity = go.Figure()
            fig_quantity.add_trace(go.Bar(
                x=date_df['Tarih'], 
                y=date_df['Net Adet'],
                name='Net Adet',
                marker_color='#2ca02c'
            ))
            fig_quantity.add_trace(go.Bar(
                x=date_df['Tarih'], 
                y=date_df['İade Adet'],
                name='İade Adet',
                marker_color='#d62728'
            ))
            fig_quantity.update_layout(
                title='Günlük Satış ve İade Adedi',
                xaxis_title='Tarih',
                yaxis_title='Adet',
                barmode='stack'
            )
            st.plotly_chart(fig_quantity, use_container_width=True)
            
            # Detaylı tablo
            st.subheader("Günlük Detay")
            date_df_display = date_df.copy()
            date_df_display['Brüt Ciro'] = date_df_display['Brüt Ciro'].apply(lambda x: f"₺{x:,.2f}")
            date_df_display['Net Ciro'] = date_df_display['Net Ciro'].apply(lambda x: f"₺{x:,.2f}")
            date_df_display['İade Tutarı'] = date_df_display['İade Tutarı'].apply(lambda x: f"₺{x:,.2f}")
            st.dataframe(date_df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Seçilen filtrelere uygun veri bulunamadı.")
    
    # TAB 3: Ürün Analizi
    with tab3:
        if by_product:
            st.subheader("En Çok Satan Ürünler")
            
            # Top 20 ürün
            product_df = pd.DataFrame([
                {
                    'Ürün': data['product_name'],
                    'SKU': data['sku'],
                    'Satılan': int(data['quantity_sold']),
                    'İade': int(data['quantity_returned']),
                    'Net': int(data['net_quantity']),
                    'Brüt Ciro': data['gross_revenue'],
                    'Net Ciro': data['net_revenue'],
                    'Maliyet': data['total_cost'],
                    'Kar': data['gross_profit'],
                    'Marj (%)': data.get('profit_margin', 0)
                }
                for data in by_product.values()
                if data['quantity_sold'] > 0
            ]).sort_values('Net Ciro', ascending=False).head(20)
            
            # Bar chart - Top ürünler
            fig_products = px.bar(
                product_df.head(10),
                x='Net Ciro',
                y='Ürün',
                title='En Çok Ciro Yapan 10 Ürün',
                orientation='h',
                color='Marj (%)',
                color_continuous_scale='RdYlGn'
            )
            fig_products.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_products, use_container_width=True)
            
            # Detaylı tablo
            st.subheader("Ürün Detayları (Top 20)")
            product_df_display = product_df.copy()
            product_df_display['Brüt Ciro'] = product_df_display['Brüt Ciro'].apply(lambda x: f"₺{x:,.2f}")
            product_df_display['Net Ciro'] = product_df_display['Net Ciro'].apply(lambda x: f"₺{x:,.2f}")
            product_df_display['Maliyet'] = product_df_display['Maliyet'].apply(lambda x: f"₺{x:,.2f}")
            product_df_display['Kar'] = product_df_display['Kar'].apply(lambda x: f"₺{x:,.2f}")
            product_df_display['Marj (%)'] = product_df_display['Marj (%)'].apply(lambda x: f"%{x:.2f}")
            st.dataframe(product_df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Seçilen filtrelere uygun veri bulunamadı.")
    
    # TAB 4: İade Analizi
    with tab4:
        st.subheader("İade İstatistikleri")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam İade", f"{int(summary['return_quantity']):,} adet")
        with col2:
            st.metric("İade Tutarı", f"₺{summary['return_amount']:,.2f}")
        with col3:
            st.metric("İade Oranı", f"%{returns['return_rate']:.2f}")
        
        # En çok iade alan ürünler
        if returns['top_returned_products']:
            st.subheader("En Çok İade Alan Ürünler")
            
            returns_df = pd.DataFrame(returns['top_returned_products'])
            
            # Bar chart
            fig_returns = px.bar(
                returns_df.head(10),
                x='return_quantity',
                y='product_name',
                title='En Çok İade Alan 10 Ürün',
                orientation='h',
                color='return_rate',
                color_continuous_scale='Reds'
            )
            fig_returns.update_layout(
                yaxis={'categoryorder':'total ascending'},
                xaxis_title='İade Adedi',
                yaxis_title='Ürün'
            )
            st.plotly_chart(fig_returns, use_container_width=True)
            
            # Detaylı tablo
            returns_df_display = returns_df.copy()
            returns_df_display['return_rate'] = returns_df_display['return_rate'].apply(lambda x: f"%{x:.2f}")
            returns_df_display.columns = ['Ürün', 'SKU', 'İade Adet', 'İade Oranı']
            st.dataframe(returns_df_display, use_container_width=True, hide_index=True)
        else:
            st.success("✅ İade yok!")
    
    # TAB 5: Karlılık Detayları
    with tab5:
        st.subheader("Karlılık Analizi")
        
        # Özet metrikler
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Net Ciro", f"₺{summary['net_revenue']:,.2f}")
        with col2:
            st.metric("Toplam Maliyet", f"₺{summary['total_cost']:,.2f}")
        with col3:
            st.metric("Brüt Kar", f"₺{summary['gross_profit']:,.2f}")
        
        # En karlı ürünler
        if profitability['top_profitable_products']:
            st.subheader("En Karlı Ürünler (Top 20)")
            
            profit_df = pd.DataFrame(profitability['top_profitable_products'])
            
            # Bar chart
            fig_profit = px.bar(
                profit_df.head(10),
                x='gross_profit',
                y='product_name',
                title='En Karlı 10 Ürün',
                orientation='h',
                color='profit_margin',
                color_continuous_scale='Greens'
            )
            fig_profit.update_layout(
                yaxis={'categoryorder':'total ascending'},
                xaxis_title='Brüt Kar (₺)',
                yaxis_title='Ürün'
            )
            st.plotly_chart(fig_profit, use_container_width=True)
            
            # Detaylı tablo
            profit_df_display = profit_df.copy()
            profit_df_display['net_revenue'] = profit_df_display['net_revenue'].apply(lambda x: f"₺{x:,.2f}")
            profit_df_display['total_cost'] = profit_df_display['total_cost'].apply(lambda x: f"₺{x:,.2f}")
            profit_df_display['gross_profit'] = profit_df_display['gross_profit'].apply(lambda x: f"₺{x:,.2f}")
            profit_df_display['profit_margin'] = profit_df_display['profit_margin'].apply(lambda x: f"%{x:.2f}")
            profit_df_display.columns = ['Ürün', 'SKU', 'Net Adet', 'Net Ciro', 'Maliyet', 'Brüt Kar', 'Kar Marjı']
            st.dataframe(profit_df_display, use_container_width=True, hide_index=True)
        
        # Düşük marjlı ürünler
        if profitability['low_margin_products']:
            st.subheader("⚠️ Düşük Kar Marjlı Ürünler (<10%)")
            
            low_margin_df = pd.DataFrame(profitability['low_margin_products'])
            
            # Detaylı tablo
            low_margin_display = low_margin_df.copy()
            low_margin_display['net_revenue'] = low_margin_display['net_revenue'].apply(lambda x: f"₺{x:,.2f}")
            low_margin_display['total_cost'] = low_margin_display['total_cost'].apply(lambda x: f"₺{x:,.2f}")
            low_margin_display['gross_profit'] = low_margin_display['gross_profit'].apply(lambda x: f"₺{x:,.2f}")
            low_margin_display['profit_margin'] = low_margin_display['profit_margin'].apply(lambda x: f"%{x:.2f}")
            low_margin_display.columns = ['Ürün', 'SKU', 'Net Adet', 'Net Ciro', 'Maliyet', 'Brüt Kar', 'Kar Marjı']
            
            st.dataframe(
                low_margin_display,
                use_container_width=True,
                hide_index=True
            )
            
            st.warning(f"⚠️ {len(low_margin_df)} ürünün kar marjı %10'un altında. Bu ürünlerin fiyatlandırmasını gözden geçirmeniz önerilir.")
    
    # --- EXPORT BÖLÜMÜ ---
    st.divider()
    st.subheader("📥 Rapor İndirme")
    
    # Dosya adı için tarih bilgisi
    start_date_str = params.get('start_date', 'baslangic')
    end_date_str = params.get('end_date', 'bitis')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Özet rapor CSV
        summary_csv = pd.DataFrame([summary]).to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📊 Özet Rapor (CSV)",
            data=summary_csv,
            file_name=f"satis_ozet_{start_date_str}_{end_date_str}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Detaylı ürün raporu
        if by_product:
            product_detail_df = pd.DataFrame([
                {
                    'Ürün': data['product_name'],
                    'SKU': data['sku'],
                    'Satılan Adet': int(data['quantity_sold']),
                    'İade Adet': int(data['quantity_returned']),
                    'Net Adet': int(data['net_quantity']),
                    'Brüt Ciro': data['gross_revenue'],
                    'İade Tutarı': data['return_amount'],
                    'Net Ciro': data['net_revenue'],
                    'Birim Maliyet': data['unit_cost'],
                    'Toplam Maliyet': data['total_cost'],
                    'Brüt Kar': data['gross_profit'],
                    'Kar Marjı (%)': data.get('profit_margin', 0)
                }
                for data in by_product.values()
            ])
            product_csv = product_detail_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📦 Ürün Detay Raporu (CSV)",
                data=product_csv,
                file_name=f"satis_urun_detay_{start_date_str}_{end_date_str}.csv",
                mime="text/csv"
            )

else:
    st.info("👈 Lütfen sol menüden filtreleri seçip 'Analizi Başlat' butonuna tıklayın.")
    
    # Örnek kullanım
    st.markdown("""
    ### 📊 Satış Analizi Hakkında
    
    Bu modül Sentos'tan e-ticaret satış verilerini çekerek detaylı analiz yapar:
    
    **Özellikler:**
    - 📦 **Brüt & Net Adet:** İadeler dahil ve hariç toplam satış adedi
    - 💰 **Brüt & Net Ciro:** İadeler dahil ve hariç toplam gelir
    - 🔄 **İade Analizi:** İade oranları ve en çok iade alan ürünler
    - 📊 **Pazar Yeri Analizi:** Her pazar yerinin performansı
    - 📈 **Tarihsel Analiz:** Günlük satış trendleri
    - 💵 **Karlılık:** Maliyet, kar ve kar marjı hesaplamaları
    
    **Maliyet Hesaplama:**
    Sentos'ta tanımlı ürün maliyetleri kullanılarak her ürün için kar marjı otomatik hesaplanır.
    
    **Veri Kaynağı:**
    Sadece **e-ticaret kanalı** verileri kullanılır (retail siparişleri hariç).
    """)
