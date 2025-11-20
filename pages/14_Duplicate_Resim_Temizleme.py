"""
🧹 Duplicate Resim Temizleme Sayfası

SEO modunun oluşturduğu duplicate resimleri temizler.
"""

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
import logging
from connectors.shopify_api import ShopifyAPI
import config_manager
import time

st.set_page_config(page_title="Duplicate Resim Temizleme", page_icon="🧹", layout="wide")

st.title("🧹 Duplicate Resim Temizleme")
st.markdown("---")

# Kullanıcı giriş kontrolü
if "authentication_status" not in st.session_state or not st.session_state.get("authentication_status"):
    st.warning("⚠️ Lütfen önce giriş yapın.")
    st.stop()

username = st.session_state.get("username", "guest")

# API anahtarlarını yükle
user_keys = config_manager.load_all_user_keys(username)

if not user_keys.get("shopify_store") or not user_keys.get("shopify_token"):
    st.error("❌ Shopify API bilgileri eksik! Lütfen Settings sayfasından ekleyin.")
    st.stop()

st.info("""
⚠️ **UYARI:** Bu araç duplicate resimleri tespit edip siler.

**Duplicate Nasıl Tespit Edilir?**
- Aynı ALT text'e sahip birden fazla resim varsa, ilki korunur, diğerleri silinir.

**Güvenlik:**
- İlk 20 ürün ile test edilir
- DRY RUN modu mevcuttur (sadece gösterir, silmez)
""")

# Ayarlar
col1, col2 = st.columns(2)

with col1:
    dry_run = st.checkbox("🔍 DRY RUN (Sadece göster, silme)", value=True)

with col2:
    test_limit = st.number_input("Test Ürün Sayısı", min_value=1, max_value=100, value=20)

st.markdown("---")

if st.button("🚀 Temizlemeyi Başlat", type="primary"):
    try:
        # ShopifyAPI oluştur
        shopify_api = ShopifyAPI(
            user_keys["shopify_store"],
            user_keys["shopify_token"]
        )
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Ürünleri yükle
        status_text.text("📦 Shopify'dan ürünler yükleniyor...")
        shopify_api.load_all_products_for_cache()
        
        # Unique ürünleri al
        unique_products = {}
        for product_data in shopify_api.product_cache.values():
            gid = product_data.get('gid')
            if gid and gid not in unique_products:
                unique_products[gid] = product_data
        
        products = list(unique_products.values())[:test_limit]
        
        status_text.text(f"✅ {len(products)} ürün yüklendi")
        
        # Sonuçlar
        total_duplicates = 0
        products_with_duplicates = 0
        results_container = st.container()
        
        with results_container:
            st.markdown("### 📊 Temizleme Sonuçları:")
            results_placeholder = st.empty()
            
            results_html = ""
            
            for idx, product in enumerate(products):
                gid = product.get('gid')
                title = product.get('title', 'Bilinmeyen')
                
                progress = (idx + 1) / len(products)
                progress_bar.progress(progress)
                status_text.text(f"[{idx + 1}/{len(products)}] {title}")
                
                # Medyaları al
                query = """
                query getProductMedia($id: ID!) {
                    product(id: $id) {
                        title
                        media(first: 250) {
                            edges {
                                node {
                                    id
                                    alt
                                    mediaContentType
                                }
                            }
                        }
                    }
                }
                """
                
                result = shopify_api.execute_graphql(query, {"id": gid})
                media_edges = result.get("product", {}).get("media", {}).get("edges", [])
                
                if not media_edges:
                    continue
                
                # Aynı ALT text'e sahip resimleri grupla
                alt_groups = {}
                for edge in media_edges:
                    node = edge.get('node', {})
                    if node.get('mediaContentType') != 'IMAGE':
                        continue
                    
                    alt_text = node.get('alt', '')
                    media_id = node.get('id')
                    
                    if alt_text not in alt_groups:
                        alt_groups[alt_text] = []
                    alt_groups[alt_text].append(media_id)
                
                # Duplicate'leri bul
                duplicates_to_delete = []
                for alt_text, media_ids in alt_groups.items():
                    if len(media_ids) > 1:
                        # İlk resmi koru, kalanları sil
                        duplicates_to_delete.extend(media_ids[1:])
                
                if duplicates_to_delete:
                    products_with_duplicates += 1
                    total_duplicates += len(duplicates_to_delete)
                    
                    results_html += f"""
                    <div style='padding: 10px; margin: 5px 0; border-left: 3px solid #ff6b6b; background: #fff3f3;'>
                        <strong>⚠️ {title}</strong><br>
                        <small>Duplicate resim: {len(duplicates_to_delete)}</small>
                    </div>
                    """
                    
                    if not dry_run:
                        # Gerçekten sil
                        for media_id in duplicates_to_delete:
                            mutation = """
                            mutation deleteMedia($productId: ID!, $mediaIds: [ID!]!) {
                                productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
                                    deletedMediaIds
                                    mediaUserErrors {
                                        field
                                        message
                                    }
                                }
                            }
                            """
                            
                            delete_result = shopify_api.execute_graphql(
                                mutation,
                                {
                                    "productId": gid,
                                    "mediaIds": [media_id]
                                }
                            )
                            
                            time.sleep(0.3)  # Rate limit
                
                results_placeholder.markdown(results_html, unsafe_allow_html=True)
        
        # Özet
        st.markdown("---")
        st.markdown("### 📊 Özet:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Ürün", len(products))
        with col2:
            st.metric("Duplicate Bulunan", products_with_duplicates)
        with col3:
            if dry_run:
                st.metric("Silinecek Resim", total_duplicates, help="DRY RUN - Silinmedi")
            else:
                st.metric("Silinen Resim", total_duplicates)
        
        if dry_run and total_duplicates > 0:
            st.warning("💡 Gerçekten silmek için DRY RUN'ı kapatıp tekrar çalıştırın.")
        elif total_duplicates == 0:
            st.success("✅ Duplicate resim bulunamadı!")
        else:
            st.success(f"✅ {total_duplicates} duplicate resim başarıyla silindi!")
        
        progress_bar.progress(1.0)
        status_text.text("✅ Tamamlandı!")
        
    except Exception as e:
        st.error(f"❌ Hata: {str(e)}")
        import traceback
        with st.expander("Detaylı Hata"):
            st.code(traceback.format_exc())
