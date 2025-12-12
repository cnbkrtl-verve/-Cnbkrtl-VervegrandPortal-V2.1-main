"""
🏷️ Otomatik Kategori ve Meta Alan Güncelleme

Ürün başlıklarından otomatik kategori tespiti yaparak 
Shopify kategori ve meta alanlarını otomatik doldurur.
"""

import streamlit as st
import sys
import os

# Proje ana dizinini path'e ekle - mutlak yol kullan
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Sys.path'i temizle ve doğru sırayla ekle
# 'streamlit_app.py' gibi dosya isimlerini kaldır, sadece dizinleri tut
sys.path = [p for p in sys.path if (p == '' or (os.path.exists(p) and os.path.isdir(p)))]
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()


# Import işlemleri
try:
    # Standart importlar
    from connectors.shopify_api import ShopifyAPI
    import config_manager
    import logging
    import time
    
    # CategoryMetafieldManager için özel import
    # Eğer normal import çalışmazsa, doğrudan dosya yolundan yükle
    try:
        from utils.category_metafield_manager import CategoryMetafieldManager
    except (ImportError, ModuleNotFoundError):
        # Alternatif: Doğrudan dosyadan import et
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "category_metafield_manager",
            os.path.join(project_root, "utils", "category_metafield_manager.py")
        )
        category_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(category_module)
        CategoryMetafieldManager = category_module.CategoryMetafieldManager
        
except Exception as e:
    st.error(f"❌ Modül import hatası: {str(e)}")
    st.error(f"Python path (ilk 3): {sys.path[:3]}")
    st.error(f"Project root: {project_root}")
    utils_path = os.path.join(project_root, 'utils')
    st.error(f"Utils path exists: {os.path.exists(utils_path)}")
    if os.path.exists(utils_path):
        st.error(f"Utils contents: {os.listdir(utils_path)}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

st.set_page_config(
    page_title="Otomatik Kategori ve Meta Alan",
    page_icon="🏷️",
    layout="wide"
)

st.title("🏷️ Otomatik Kategori ve Meta Alan Güncelleme")
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

# Bilgilendirme
st.info("""
### 🎯 Bu Modül Ne Yapar?

**Sorun:** Shopify'da her ürün için kategori ve meta alanlarını manuel doldurmak çok zaman alıyor.

**Çözüm:** Bu modül ürün başlıklarından otomatik olarak:
1. 📦 **Kategori tespit eder** (T-shirt, Elbise, Bluz, Pantolon, Şort vb.) - *Puanlama Sistemi ile*
2. 🏷️ **Kategoriye uygun meta alanları belirler** (Yaka tipi, Kol tipi, Boy, Desen vb.)
3. ✨ **Tüm verilerden değerleri çıkarır** (Başlık, Varyant, Açıklama, Etiketler)
4. 💾 **Shopify'a otomatik yazar** (GraphQL API ile)
""")

st.markdown("---")

# Kategori istatistikleri göster
st.markdown("### 📊 Desteklenen Kategoriler ve Meta Alanları")

col1, col2 = st.columns([1, 2])

with col1:
    category_summary = CategoryMetafieldManager.get_category_summary()
    
    summary_data = []
    for category, count in category_summary.items():
        summary_data.append({
            'Kategori': category,
            'Meta Alan Sayısı': count
        })
    
    st.dataframe(summary_data, use_container_width=True, hide_index=True)

with col2:
    selected_category = st.selectbox(
        "Kategori Detayları",
        options=list(category_summary.keys())
    )
    
    if selected_category:
        metafields = CategoryMetafieldManager.get_metafields_for_category(selected_category)
        
        st.markdown(f"**{selected_category}** kategorisi için meta alanlar:")
        for field_key, field_info in metafields.items():
            st.markdown(f"- `{field_info['key']}`: {field_info['description']}")

st.markdown("---")

# ⚠️ METAFIELD DEFINITIONS OLUŞTURMA
with st.expander("🔧 Metafield Definitions Oluşturma (Gerekirse)"):
    st.warning("""
    ⚠️ **ÖNEMLİ**: Meta alanların Shopify'da görünmesi için önce **metafield definitions** oluşturulmalı!
    Bu işlem sadece **BİR KERE** yapılır.
    """)

    if st.button("🏗️ Tüm Kategoriler İçin Metafield Definitions Oluştur"):
        with st.spinner("Metafield definitions oluşturuluyor..."):
            try:
                shopify_api = ShopifyAPI(
                    user_keys["shopify_store"],
                    user_keys["shopify_token"]
                )
                
                categories = list(CategoryMetafieldManager.get_category_summary().keys())
                
                total_created = 0
                results_md = ""

                for category in categories:
                    result = shopify_api.create_all_metafield_definitions_for_category(category)
                    total_created += result.get('created', 0)

                    if result.get('success'):
                        results_md += f"✅ **{category}**: {result['created']} definition oluşturuldu/kontrol edildi\n\n"
                    else:
                        results_md += f"❌ **{category}**: Hata - {result.get('errors', [])}\n\n"

                    time.sleep(0.5)  # Rate limit

                st.success(f"✅ Toplam {total_created} metafield definition oluşturuldu/kontrol edildi!")
                st.markdown(results_md)

            except Exception as e:
                st.error(f"❌ Hata: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

st.markdown("---")

# Güncelleme Ayarları
st.markdown("### ⚙️ Tarama ve Güncelleme Ayarları")

col1, col2, col3, col4 = st.columns(4)

with col1:
    scan_mode = st.radio(
        "🔍 Tarama Modu",
        ["Test Modu (İlk 20)", "Tam Tarama (Tüm Mağaza)"],
        index=0,
        help="Tam tarama tüm ürünleri çeker, uzun sürebilir."
    )
    test_mode = scan_mode == "Test Modu (İlk 20)"
    
with col2:
    dry_run = st.checkbox("🧪 DRY RUN (Sadece göster)", value=True, help="Değişiklikleri Shopify'a göndermez, sadece ne olacağını gösterir.")

with col3:
    update_category = st.checkbox("📦 Kategori güncelle", value=True)
    update_metafields = st.checkbox("🏷️ Meta alanları güncelle", value=True)

with col4:
    use_shopify_suggestions = st.checkbox("🎯 Shopify Önerilerini Kullan", value=True, 
                                          help="Shopify'ın önerdiği kategori ve meta alanları otomatik kullanılır")

st.markdown("---")

def process_products(preview_only=True):
    shopify_api = ShopifyAPI(user_keys["shopify_store"], user_keys["shopify_token"])

    # 1. YÜKLEME
    with st.status("📦 Ürünler yükleniyor...", expanded=True) as status:
        shopify_api.load_all_products_for_cache()

        unique_products = {}
        for product_data in shopify_api.product_cache.values():
            gid = product_data.get('gid')
            if gid and gid not in unique_products:
                unique_products[gid] = product_data

        products = list(unique_products.values())
        if test_mode:
            products = products[:20]
            
        status.update(label=f"✅ {len(products)} ürün analiz için hazır!", state="complete", expanded=False)

    # 2. ANALİZ VE GÜNCELLEME
    results_container = st.container()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    stats = {'total': len(products), 'updated': 0, 'skipped': 0, 'failed': 0, 'analyzed': 0}

    with results_container:
        st.markdown("### 📝 İşlem Sonuçları")
        results_placeholder = st.empty()
        results_html = ""

        # Sadece son 50 logu tutalım ki UI donmasın
        log_buffer = []

        for idx, product in enumerate(products):
            progress = (idx + 1) / len(products)
            progress_bar.progress(progress)
            
            gid = product.get('gid')
            title = product.get('title', 'Bilinmeyen')
            description = product.get('description', '')
            
            # Varyantları düzgün formatla (API cache'den gelen yapı biraz farklı olabilir)
            # load_all_products_for_cache zaten standart formata çeviriyor:
            # variants = [{'sku': '...', 'options': [{'name': 'Size', 'value': 'S'}]}]
            variants = product.get('variants', [])
            
            # NOT: Cache'de tags/productType olmayabilir, eğer eksikse detay çekmek gerekebilir
            # Ancak performans için şimdilik cache'deki (sınırlı) veriyi kullanıyoruz.
            # Geliştirme: load_all_products_for_cache fonksiyonu tags/productType da çekmeli.
            # Şu anki versiyon çekmiyor olabilir. API'yi kontrol etmeliyiz.
            # Eğer çekmiyorsa, burada ek bir çağrı yapmak çok yavaşlatır.
            # Varsayım: Cache'de yoksa boş kabul edelim.
            tags = [] # Cache güncellenmeli
            product_type = ""
            
            status_text.text(f"Analiz ediliyor ({idx+1}/{len(products)}): {title[:40]}...")
            
            # Kategori tespit
            category = CategoryMetafieldManager.detect_category(title)
            
            if not category:
                stats['skipped'] += 1
                # Sadece önizlemede başarısızları gösterelim mi? Hayır, log kalabalık olur.
                continue
            
            # Taxonomy ID al
            taxonomy_id = CategoryMetafieldManager.get_taxonomy_id(category)
            
            # Shopify Önerileri (Sadece güncelleme modunda veya detaylı analizde)
            shopify_recommendations = None
            if not preview_only or idx < 5: # Önizlemede sadece ilk 5 için API çağrısı yap (hız için)
                 try:
                    # Bu çağrı her ürün için yapılırsa yavaşlatır.
                    # Test modunda sorun yok, ama Tam Taramada rate limit'e takılabilir.
                    # Eğer çok ürün varsa bunu atlamak mantıklı olabilir veya cache'lemek.
                    if use_shopify_suggestions:
                        recommendations_data = shopify_api.get_product_recommendations(gid)
                        if recommendations_data:
                            shopify_recommendations = recommendations_data
                 except Exception as e:
                     pass

            # Meta alanları hazırla
            metafields = CategoryMetafieldManager.prepare_metafields_for_shopify(
                category=category,
                product_title=title,
                product_description=description,
                variants=variants,
                shopify_recommendations=shopify_recommendations,
                tags=tags,
                product_type=product_type
            )

            stats['analyzed'] += 1

            metafield_str = ", ".join([f"{m['key']}: {m['value']}" for m in metafields])

            log_entry = ""
            if preview_only or dry_run:
                stats['updated'] += 1 # Teorik olarak güncellenecek
                log_entry = f"""
                <div style='padding: 8px; margin: 3px 0; border-left: 3px solid #2196f3; background: #e3f2fd; font-family: monospace; font-size: 0.9em;'>
                    <b>{title[:50]}</b><br>
                    <span style='color: #1565c0'>📂 {category}</span> | <span style='color: #00695c'>🏷️ {metafield_str}</span>
                </div>
                """
            else:
                # GERÇEK GÜNCELLEME
                try:
                    result = shopify_api.update_product_category_and_metafields(
                        gid,
                        category if update_category else None,
                        metafields if update_metafields else [],
                        use_shopify_suggestions=use_shopify_suggestions,
                        taxonomy_id=taxonomy_id if update_category else None
                    )
                    
                    if result.get('success'):
                        stats['updated'] += 1
                        log_entry = f"""
                        <div style='padding: 8px; margin: 3px 0; border-left: 3px solid #4caf50; background: #e8f5e9; font-size: 0.9em;'>
                            ✅ <b>{title[:50]}</b>: Güncellendi ({category})
                        </div>
                        """
                    else:
                        stats['failed'] += 1
                        log_entry = f"""
                        <div style='padding: 8px; margin: 3px 0; border-left: 3px solid #f44336; background: #ffebee; font-size: 0.9em;'>
                            ❌ <b>{title[:50]}</b>: {result.get('message')}
                        </div>
                        """
                    
                    time.sleep(0.3) # Rate limit koruması

                except Exception as e:
                    stats['failed'] += 1
                    log_entry = f"<div style='color:red'>Hata: {str(e)}</div>"

            log_buffer.insert(0, log_entry)
            if len(log_buffer) > 50: log_buffer.pop()
            
            results_html = "".join(log_buffer)
            results_placeholder.markdown(results_html, unsafe_allow_html=True)
            
    return stats

# Butonlar
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("👁️ Analiz Et ve Önizle", type="secondary"):
        stats = process_products(preview_only=True)
        st.success(f"Analiz tamamlandı! {stats['analyzed']} ürün için kategori ve meta alan tespit edildi.")

with col_btn2:
    if st.button("🚀 İşlemi Başlat", type="primary", disabled=(not update_category and not update_metafields)):
        if dry_run:
            st.warning("DRY RUN Modu: Hiçbir değişiklik yapılmayacak.")
        stats = process_products(preview_only=False)
        st.success(f"İşlem tamamlandı! {stats['updated']} ürün işlendi.")

# Yardım
with st.expander("❓ Sıkça Sorulan Sorular"):
    st.markdown("""
    **S: "Tam Tarama" ne kadar sürer?**
    C: Mağazadaki ürün sayısına göre değişir. 1000 ürün yaklaşık 2-3 dakika sürebilir (Shopify önerileri kapalıysa).
    
    **S: Kategori yanlış tespit edilirse ne olur?**
    C: Başlıktaki anahtar kelimeleri düzenleyebilir veya `category_config.json` dosyasını güncelleyebilirsiniz.
    
    **S: Metafield'lar görünmüyor?**
    C: Yukarıdaki "Metafield Definitions Oluştur" butonunu kullandığınızdan emin olun.
    """)
