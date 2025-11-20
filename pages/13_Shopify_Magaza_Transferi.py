# pages/13_Shopify_Magaza_Transferi.py

import streamlit as st
from datetime import datetime, timedelta
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from connectors.shopify_api import ShopifyAPI
from operations.shopify_to_shopify import transfer_order
from config_manager import load_all_user_keys

# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()
st.set_page_config(layout="wide")
st.title("🚚 Shopify Mağazaları Arası Sipariş Transferi")

# --- Oturum ve API Kontrolleri ---
if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
    st.warning("Lütfen devam etmek için giriş yapın.")
    st.stop()

# --- API Bilgilerini Yükle ---
try:
    user_keys = load_all_user_keys(st.session_state.get('username', 'admin'))
except Exception as e:
    st.error(f"⚠️ API bilgileri yüklenirken hata oluştu: {e}")
    st.info("""
    **Çözüm Adımları:**
    
    1. Projenizin ana dizininde `.streamlit` klasörü oluşturun (eğer yoksa)
    2. `.streamlit` klasörü içinde `secrets.toml` dosyası oluşturun
    3. Aşağıdaki bilgileri `secrets.toml` dosyasına ekleyin:
    
    ```toml
    SHOPIFY_STORE = "kaynak-magazaniz.myshopify.com"
    SHOPIFY_TOKEN = "kaynak-magaza-api-token"
    SHOPIFY_DESTINATION_STORE = "hedef-magazaniz.myshopify.com"
    SHOPIFY_DESTINATION_TOKEN = "hedef-magaza-api-token"
    ```
    
    4. Streamlit uygulamasını yeniden başlatın
    """)
    st.stop()

# --- API Istemcilerini Başlat ---
try:
    # Kaynak Mağaza
    source_store = user_keys.get('shopify_store')
    source_token = user_keys.get('shopify_token')
    if not source_store or not source_token:
        st.error("❌ Kaynak Shopify mağazası için 'SHOPIFY_STORE' ve 'SHOPIFY_TOKEN' bilgileri secrets dosyasında eksik.")
        st.info("""
        **secrets.toml dosyasına şu bilgileri ekleyin:**
        ```toml
        SHOPIFY_STORE = "kaynak-magazaniz.myshopify.com"
        SHOPIFY_TOKEN = "shpat_xxxxxxxxxxxxx"
        ```
        """)
        st.stop()
    source_api = ShopifyAPI(source_store, source_token)

    # Hedef Mağaza
    dest_store = user_keys.get('shopify_destination_store')
    dest_token = user_keys.get('shopify_destination_token')
    if not dest_store or not dest_token:
        st.error("❌ Hedef Shopify mağazası için 'SHOPIFY_DESTINATION_STORE' ve 'SHOPIFY_DESTINATION_TOKEN' bilgileri secrets dosyasında eksik.")
        st.info("""
        **secrets.toml dosyasına şu bilgileri ekleyin:**
        ```toml
        SHOPIFY_DESTINATION_STORE = "hedef-magazaniz.myshopify.com"
        SHOPIFY_DESTINATION_TOKEN = "shpat_xxxxxxxxxxxxx"
        ```
        """)
        st.stop()
    destination_api = ShopifyAPI(dest_store, dest_token)
    
    st.success(f"Kaynak Mağaza: `{source_store}` | Hedef Mağaza: `{dest_store}` - Bağlantılar hazır.")

except Exception as e:
    st.error(f"API istemcileri başlatılırken bir hata oluştu: {e}")
    st.stop()

# --- ADIM 1: Siparişleri Getir ---
st.header("📋 Adım 1: Siparişleri Listele")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Başlangıç Tarihi", datetime.now().date() - timedelta(days=1))
with col2:
    end_date = st.date_input("Bitiş Tarihi", datetime.now().date())

# Siparişleri getir butonu
if st.button("📥 Siparişleri Getir", type="primary", use_container_width=True):
    start_datetime = datetime.combine(start_date, datetime.min.time()).isoformat()
    end_datetime = datetime.combine(end_date, datetime.max.time()).isoformat()
    
    with st.spinner("Kaynak mağazadan siparişler yükleniyor..."):
        try:
            orders = source_api.get_orders_by_date_range(start_datetime, end_datetime)
            st.session_state['fetched_orders'] = orders
            st.session_state['start_datetime'] = start_datetime
            st.session_state['end_datetime'] = end_datetime
            st.success(f"✅ {len(orders)} adet sipariş bulundu!")
        except Exception as e:
            st.error(f"❌ Siparişler yüklenirken hata: {e}")
            st.session_state['fetched_orders'] = []

# --- ADIM 2: Siparişleri Seç ---
if 'fetched_orders' in st.session_state and st.session_state['fetched_orders']:
    st.markdown("---")
    st.header("📦 Adım 2: Transfer Edilecek Siparişleri Seçin")
    
    orders = st.session_state['fetched_orders']
    
    # Tümünü seç/kaldır
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("✅ Tümünü Seç", use_container_width=True):
            st.session_state['select_all'] = True
    with col2:
        if st.button("❌ Tümünü Kaldır", use_container_width=True):
            st.session_state['select_all'] = False
    
    # Session state'de seçimleri sakla
    if 'selected_order_ids' not in st.session_state:
        st.session_state['selected_order_ids'] = set()
    
    # Tümünü seç/kaldır işlemi
    if 'select_all' in st.session_state:
        if st.session_state['select_all']:
            st.session_state['selected_order_ids'] = {order['id'] for order in orders}
        else:
            st.session_state['selected_order_ids'] = set()
        del st.session_state['select_all']
    
    # Tablo başlıkları
    st.markdown("### 📋 Sipariş Listesi")
    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([0.5, 1.5, 2, 1.5, 1.5, 1.5])
    with header_col1:
        st.markdown("**Seç**")
    with header_col2:
        st.markdown("**Sipariş No**")
    with header_col3:
        st.markdown("**Müşteri**")
    with header_col4:
        st.markdown("**Tarih**")
    with header_col5:
        st.markdown("**Tutar**")
    with header_col6:
        st.markdown("**Ödeme Durumu**")
    
    st.markdown("---")
    
    # Siparişleri göster
    for idx, order in enumerate(orders):
        order_id = order['id']
        order_name = order.get('name', 'N/A')
        order_date = order.get('createdAt', 'N/A')
        customer = order.get('customer', {})
        
        # Müşteri adını akıllıca belirle
        if customer:
            first_name = customer.get('firstName', '').strip()
            last_name = customer.get('lastName', '').strip()
            email = customer.get('email', '').strip()
            
            if first_name or last_name:
                customer_name = f"{first_name} {last_name}".strip()
            elif email:
                customer_name = email
            else:
                customer_name = 'Misafir'
        else:
            customer_name = 'Misafir'
        
        total_price = order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', '0.00')
        currency = order.get('totalPriceSet', {}).get('shopMoney', {}).get('currencyCode', 'TRY')
        financial_status = order.get('displayFinancialStatus', 'N/A')
        
        # Sipariş satırı
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 1.5, 2, 1.5, 1.5, 1.5])
        
        with col1:
            # Checkbox durumu
            is_selected = order_id in st.session_state['selected_order_ids']
            
            if st.checkbox(
                "✓", 
                value=is_selected,
                key=f"order_select_{order_id}",
                label_visibility="collapsed"
            ):
                st.session_state['selected_order_ids'].add(order_id)
            else:
                st.session_state['selected_order_ids'].discard(order_id)
        
        with col2:
            st.markdown(f"**{order_name}**")
        
        with col3:
            st.text(customer_name)
        
        with col4:
            # Tarih formatla
            try:
                date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = order_date[:16] if len(order_date) > 16 else order_date
            st.text(formatted_date)
        
        with col5:
            st.text(f"{float(total_price):.2f} {currency}")
        
        with col6:
            # Durum badge'leri
            if financial_status == "PAID":
                st.success("💳 Ödendi")
            elif financial_status == "PENDING":
                st.warning("💳 Beklemede")
            elif financial_status == "REFUNDED":
                st.error("💳 İade")
            else:
                st.info(f"💳 {financial_status}")
    
    # Seçilen siparişleri topla
    selected_orders = [order for order in orders if order['id'] in st.session_state['selected_order_ids']]
    
    st.markdown("---")
    st.info(f"**✅ Seçilen Sipariş:** {len(selected_orders)} / {len(orders)}")
    
    # Transfer butonu
    if len(selected_orders) > 0:
        if st.button(
            f"🚀 {len(selected_orders)} Siparişi Transfer Et", 
            type="primary", 
            use_container_width=True
        ):
            st.session_state['confirm_transfer'] = True
    else:
        st.warning("⚠️ Lütfen en az bir sipariş seçin.")

# --- ADIM 3: Transfer Onayı ---
if 'confirm_transfer' in st.session_state and st.session_state['confirm_transfer']:
    st.markdown("---")
    st.header("⚠️ Adım 3: Transfer Onayı")
    
    selected_orders = [
        order for order in st.session_state['fetched_orders'] 
        if order['id'] in st.session_state['selected_order_ids']
    ]
    
    st.warning(f"**{len(selected_orders)} sipariş** hedef mağazaya transfer edilecek. Devam etmek istiyor musunuz?")
    
    # Seçilen siparişlerin özeti
    with st.expander("📋 Transfer Edilecek Siparişler", expanded=True):
        for order in selected_orders:
            customer = order.get('customer', {})
            if customer:
                first_name = customer.get('firstName', '').strip()
                last_name = customer.get('lastName', '').strip()
                email = customer.get('email', '').strip()
                
                if first_name or last_name:
                    customer_name = f"{first_name} {last_name}".strip()
                elif email:
                    customer_name = email
                else:
                    customer_name = 'Misafir'
            else:
                customer_name = 'Misafir'
            
            st.markdown(f"- **{order.get('name')}** - {customer_name}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Evet, Transfer Et", type="primary", use_container_width=True):
            st.session_state['start_transfer'] = True
            st.session_state['confirm_transfer'] = False
            # Transfer için seçili siparişleri KALICI kaydet
            st.session_state['orders_to_transfer'] = [
                order for order in st.session_state['fetched_orders'] 
                if order['id'] in st.session_state['selected_order_ids']
            ]
            # Seçimleri temizle (yeni seçim yapılmasını önle)
            st.session_state['selected_order_ids'] = set()
            st.rerun()
    with col2:
        if st.button("❌ İptal", use_container_width=True):
            st.session_state['confirm_transfer'] = False
            st.rerun()

# --- ADIM 4: Transfer İşlemi ---
if 'start_transfer' in st.session_state and st.session_state['start_transfer']:
    st.markdown("---")
    st.header("📊 Adım 4: Transfer Sonuçları")
    
    # Transfer edilecek siparişleri AL (onay anında kaydedilmiş)
    selected_orders = st.session_state.get('orders_to_transfer', [])
    
    if not selected_orders:
        st.error("❌ Transfer edilecek sipariş bulunamadı!")
        st.session_state['start_transfer'] = False
        st.rerun()
    
    progress_bar = st.progress(0)
    total_orders = len(selected_orders)
    
    success_count = 0
    failed_count = 0
    
    for i, order in enumerate(selected_orders):
        with st.expander(f"İşleniyor: Sipariş {order['name']}", expanded=(i < 3)):  # İlk 3'ü açık göster
            status_placeholder = st.empty()
            with st.spinner(f"Sipariş {order['name']} hedef mağazaya aktarılıyor..."):
                result = transfer_order(source_api, destination_api, order)
            
            status_placeholder.container().write(f"**Sipariş {order['name']} Aktarım Logları:**")
            
            has_error = False
            has_warning = False
            transfer_quality = result.get('transfer_quality', 100)
            
            for log in result.get('logs', []):
                if "✅" in log or "BAŞARILI" in log or "MÜKEMMEL" in log:
                    st.success(log)
                elif "❌" in log or "HATA" in log or "KRİTİK" in log:
                    st.error(log)
                    has_error = True
                elif "⚠️" in log or "UYARI" in log or "DİKKAT" in log:
                    st.warning(log)
                    has_warning = True
                elif "═" in log:
                    st.markdown(f"`{log}`")
                else:
                    st.info(log)
            
            # Transfer kalitesi göstergesi
            if transfer_quality < 100:
                st.warning(f"⚠️ Transfer Kalitesi: %{transfer_quality:.1f} - Bazı ürünler eksik!")
            
            if has_error:
                failed_count += 1
            else:
                success_count += 1
        
        progress_bar.progress((i + 1) / total_orders)
    
    # ✅ Transfer tamamlandı - flag'i TEMİZLE
    st.session_state['start_transfer'] = False
    st.session_state['transfer_completed'] = True
    
    # Özet
    st.markdown("---")
    st.markdown("### 📊 Transfer Özeti")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam", total_orders)
    with col2:
        st.metric("✅ Başarılı", success_count, delta=success_count)
    with col3:
        st.metric("❌ Başarısız", failed_count, delta=-failed_count if failed_count > 0 else 0)
    
    if failed_count == 0:
        st.balloons()
        st.success("✅ Tüm siparişler başarıyla transfer edildi!")
    else:
        st.warning(f"⚠️ {success_count} sipariş başarılı, {failed_count} sipariş başarısız")
    
    # Yeni transfer butonu
    st.markdown("---")
    if st.button("🔄 Yeni Transfer İşlemi", use_container_width=True, type="primary"):
        # Session state'i TEMİZLE
        for key in ['fetched_orders', 'selected_order_ids', 'confirm_transfer', 'start_transfer', 'transfer_completed', 'orders_to_transfer']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Yardım Bölümü
with st.expander("❓ Nasıl Kullanılır?"):
    st.markdown("""
    ### 📚 Kullanım Kılavuzu
    
    **Adım 1: Siparişleri Getir**
    - Başlangıç ve bitiş tarihlerini seçin
    - "Siparişleri Getir" butonuna tıklayın
    
    **Adım 2: Transfer Edilecek Siparişleri Seçin**
    - Listeden transfer etmek istediğiniz siparişleri seçin
    - "Tümünü Seç" ile hepsini seçebilirsiniz
    - "Tümünü Kaldır" ile seçimleri temizleyebilirsiniz
    
    **Adım 3: Transfer İşlemi**
    - Seçtiğiniz siparişleri transfer etmek için "Siparişi Transfer Et" butonuna tıklayın
    - Onay ekranında "Evet, Transfer Et" ile işlemi başlatın
    
    **⚠️ ÖNEMLİ NOTLAR:**
    
    **1. Ürün Eşleştirme Problemi:**
    - Siparişteki ürünler **SKU** ile eşleştirilir
    - Eğer hedef mağazada ürün yoksa, o ürün **atlanır**
    - Bu durumda sipariş **eksik** oluşturulur!
    
    **2. Eksik Transfer Önleme:**
    - ✅ Transfer öncesi tüm ürünlerin hedef mağazada olduğundan emin olun
    - ✅ SKU'ların her iki mağazada da **aynı** olduğunu kontrol edin
    - ✅ Transfer loglarında "❌ HATA: SKU bulunamadı" uyarılarını kontrol edin
    
    **3. Transfer Kalitesi:**
    - Her sipariş için **Transfer Kalitesi** gösterilir
    - %100 = Tüm ürünler başarıyla transfer edildi ✅
    - %80-99 = Bazı ürünler eksik ⚠️
    - %0-79 = Çok fazla ürün eksik ❌
    
    **4. Sorun Giderme:**
    - Eğer ürünler eksik transfer edildiyse:
      1. Transfer loglarını kontrol edin
      2. Eksik SKU'ları not alın
      3. Bu ürünleri hedef mağazada oluşturun
      4. Siparişi tekrar transfer edin
    
    **İpuçları:**
    - ✅ İlk transferden sonra, aynı gün içinde gelen yeni siparişleri seçerek transfer edebilirsiniz
    - ✅ Her sipariş için detaylı transfer logları görüntülenir
    - ✅ Başarılı ve başarısız transferlerin özeti gösterilir
    - ✅ Transfer kalitesi %100'den düşükse mutlaka logları kontrol edin!
    """)