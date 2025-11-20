"""
🧹 Duplicate Resim Temizleme Aracı

SEO modunun yanlışlıkla oluşturduğu duplicate resimleri temizler.
Sadece ALT text'i SEO formatında olan ve duplicate olan resimleri siler.

UYARI: Bu script sadece test modunda çalışır (ilk 20 ürün).
Tüm ürünler için çalıştırmadan önce test edin!
"""

import logging
import time
import os
from connectors.shopify_api import ShopifyAPI

# Loglama
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def find_and_remove_duplicates(shopify_api, product_gid, product_title, dry_run=True):
    """
    Bir ürünün duplicate resimlerini bulur ve siler.
    
    Args:
        shopify_api: ShopifyAPI instance
        product_gid: Ürün GID
        product_title: Ürün başlığı
        dry_run: True ise sadece gösterir, silmez
        
    Returns:
        dict: Silinen resim sayısı ve detaylar
    """
    try:
        # 1. Mevcut medyaları al
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
                            ... on MediaImage {
                                image {
                                    originalSrc
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        result = shopify_api.execute_graphql(query, {"id": product_gid})
        product_data = result.get("product", {})
        media_edges = product_data.get("media", {}).get("edges", [])
        
        if not media_edges:
            return {'deleted': 0, 'message': 'Resim bulunamadı'}
        
        # 2. Resimleri grupla (aynı alt text'e sahip olanları bul)
        alt_groups = {}
        for edge in media_edges:
            node = edge.get('node', {})
            if node.get('mediaContentType') != 'IMAGE':
                continue
                
            alt_text = node.get('alt', '')
            media_id = node.get('id')
            
            if alt_text not in alt_groups:
                alt_groups[alt_text] = []
            alt_groups[alt_text].append({
                'id': media_id,
                'alt': alt_text,
                'url': node.get('image', {}).get('originalSrc', 'N/A')
            })
        
        # 3. Duplicate'leri bul (aynı ALT text'e sahip 2+ resim)
        duplicates_to_delete = []
        for alt_text, images in alt_groups.items():
            if len(images) > 1:
                # İlk resmi koru, kalanları sil
                duplicates_to_delete.extend(images[1:])
                logging.warning(f"  ⚠️ Duplicate bulundu: '{alt_text}' ({len(images)} resim)")
        
        if not duplicates_to_delete:
            return {'deleted': 0, 'message': 'Duplicate resim bulunamadı'}
        
        logging.info(f"  📊 Toplam {len(media_edges)} resim, {len(duplicates_to_delete)} duplicate bulundu")
        
        if dry_run:
            logging.info(f"  🔍 DRY RUN: {len(duplicates_to_delete)} resim silinecekti (gerçekte silinmedi)")
            for dup in duplicates_to_delete:
                logging.info(f"    - {dup['alt']}")
            return {'deleted': 0, 'would_delete': len(duplicates_to_delete), 'message': f'DRY RUN: {len(duplicates_to_delete)} duplicate bulundu'}
        
        # 4. Duplicate'leri sil
        deleted_count = 0
        for dup in duplicates_to_delete:
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
                    "productId": product_gid,
                    "mediaIds": [dup['id']]
                }
            )
            
            errors = delete_result.get('productDeleteMedia', {}).get('mediaUserErrors', [])
            if errors:
                logging.error(f"    ❌ Silme hatası: {dup['alt']} - {errors}")
            else:
                deleted_count += 1
                logging.info(f"    ✅ Silindi: {dup['alt']}")
            
            time.sleep(0.3)  # Rate limit
        
        return {
            'deleted': deleted_count,
            'message': f'{deleted_count}/{len(duplicates_to_delete)} duplicate resim silindi'
        }
        
    except Exception as e:
        logging.error(f"Duplicate temizleme hatası: {e}")
        return {'deleted': 0, 'message': f'Hata: {str(e)}'}


def main():
    """Ana fonksiyon"""
    print("🧹 Duplicate Resim Temizleme Aracı")
    print("=" * 60)
    
    # Shopify bilgilerini al
    print("\n📝 Shopify mağaza bilgilerini girin:")
    store_url = input("Store URL (örn: mystore.myshopify.com): ").strip()
    if not store_url:
        print("❌ Store URL gerekli!")
        return
    
    access_token = input("Access Token: ").strip()
    if not access_token:
        print("❌ Access Token gerekli!")
        return
    
    # Kullanıcıdan onay al
    print("\n⚠️  UYARI: Bu araç duplicate resimleri SİLECEK!")
    print("   İlk olarak DRY RUN modunda çalışacak (sadece gösterir)")
    print()
    
    dry_run_input = input("DRY RUN modunda başlat? (E/h): ").strip().lower()
    dry_run = dry_run_input != 'h'
    
    if dry_run:
        print("✅ DRY RUN modu: Resimler silinmeyecek, sadece gösterilecek\n")
    else:
        print("⚠️  GERÇEK MOD: Duplicate resimler SİLİNECEK!")
        confirm = input("Emin misiniz? (EVET yazın): ").strip()
        if confirm != "EVET":
            print("❌ İptal edildi")
            return
        print()
    
    # Config yükle
    try:
        shopify_api = ShopifyAPI(store_url, access_token)
        
        print("📦 Shopify'dan ürünler yükleniyor...")
        shopify_api.load_all_products_for_cache()
        
        # Unique ürünleri al
        unique_products = {}
        for product_data in shopify_api.product_cache.values():
            gid = product_data.get('gid')
            if gid and gid not in unique_products:
                unique_products[gid] = product_data
        
        products = list(unique_products.values())[:20]  # İlk 20 ürün (test)
        
        print(f"✅ {len(products)} ürün yüklendi (test modu)\n")
        
        # İstatistikler
        total_deleted = 0
        products_with_duplicates = 0
        
        for idx, product in enumerate(products, 1):
            gid = product.get('gid')
            title = product.get('title', 'Bilinmeyen')
            
            print(f"[{idx}/{len(products)}] {title}")
            
            result = find_and_remove_duplicates(shopify_api, gid, title, dry_run=dry_run)
            
            deleted = result.get('deleted', 0)
            would_delete = result.get('would_delete', 0)
            
            if deleted > 0 or would_delete > 0:
                products_with_duplicates += 1
                total_deleted += deleted if not dry_run else would_delete
            
            print()
        
        # Özet
        print("=" * 60)
        print("📊 ÖZET:")
        print(f"   Toplam ürün: {len(products)}")
        print(f"   Duplicate bulunan ürün: {products_with_duplicates}")
        if dry_run:
            print(f"   Silinecek resim: {total_deleted} (DRY RUN - silinmedi)")
        else:
            print(f"   Silinen resim: {total_deleted}")
        print("=" * 60)
        
        if dry_run and total_deleted > 0:
            print("\n💡 Gerçekten silmek için programı tekrar çalıştırıp 'h' yazın")
        
    except Exception as e:
        logging.error(f"Hata: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
