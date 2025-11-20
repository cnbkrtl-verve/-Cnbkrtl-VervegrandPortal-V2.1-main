"""
Shopify sitesinden koleksiyon ve ürün verilerini analiz ederek
kategori ve meta alan yapısını çıkarır.
"""

import sys
import os
from collections import defaultdict, Counter
import json
import re

# Proje ana dizinini ekle
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from connectors.shopify_api import ShopifyAPI
import config_manager

def analyze_product_titles(products):
    """Ürün başlıklarından kategori pattern'lerini analiz et"""
    
    # Olası kategori kelimeleri
    patterns = defaultdict(list)
    word_frequency = Counter()
    
    for product in products:
        title = product.get('title', '').lower()
        
        # Kelimeleri çıkar
        words = re.findall(r'\w+', title)
        for word in words:
            if len(word) > 3:  # Kısa kelimeleri atla
                word_frequency[word] += 1
        
        patterns['titles'].append(title)
    
    return patterns, word_frequency

def analyze_collections(collections):
    """Koleksiyonları analiz et"""
    
    collection_info = []
    
    for collection in collections:
        info = {
            'title': collection.get('title', ''),
            'handle': collection.get('handle', ''),
            'product_count': collection.get('products_count', 0),
            'description': collection.get('body_html', '')[:100] if collection.get('body_html') else ''
        }
        collection_info.append(info)
    
    return collection_info

def extract_category_keywords(titles, min_frequency=3):
    """Başlıklardan kategori anahtar kelimelerini çıkar"""
    
    # Türkçe giyim kategorileri için potansiyel kelimeler
    clothing_keywords = [
        'elbise', 'dress', 'bluz', 'gömlek', 'shirt', 'tshirt', 'tişört',
        'pantolon', 'pants', 'jean', 'kot', 'şort', 'short', 'etek', 'skirt',
        'ceket', 'jacket', 'mont', 'coat', 'kaban', 'kazak', 'sweater',
        'hırka', 'cardigan', 'tunik', 'tunic', 'yelek', 'vest',
        'takım', 'suit', 'set', 'mayo', 'bikini', 'swim',
        'gecelik', 'pijama', 'nightgown', 'tulum', 'jumpsuit',
        'çanta', 'bag', 'ayakkabı', 'shoe', 'bot', 'boot',
        'sandalet', 'sandal', 'terlik', 'slipper'
    ]
    
    found_categories = Counter()
    
    for title in titles:
        title_lower = title.lower()
        for keyword in clothing_keywords:
            if keyword in title_lower:
                found_categories[keyword] += 1
    
    # Minimum frekansın üzerinde olanları filtrele
    return {k: v for k, v in found_categories.items() if v >= min_frequency}

def main():
    print("=" * 80)
    print("SHOPIFY SİTE ANALİZİ - Kategori ve Meta Alan Keşfi")
    print("=" * 80)
    
    # Kullanıcı bilgilerini yükle
    try:
        user_keys = config_manager.load_all_user_keys('admin')
        
        if not user_keys.get('shopify_store') or not user_keys.get('shopify_token'):
            print("❌ Shopify API bilgileri bulunamadı!")
            print("Lütfen önce settings sayfasından Shopify bilgilerinizi kaydedin.")
            return
        
        # Shopify API bağlantısı
        shopify = ShopifyAPI(
            store_url=user_keys['shopify_store'],
            access_token=user_keys['shopify_token']
        )
        
        print(f"\n✓ Shopify Store: {user_keys['shopify_store']}")
        print("\n" + "=" * 80)
        
        # Koleksiyonları çek
        print("\n📚 KOLEKSİYONLAR ANALİZ EDİLİYOR...")
        print("-" * 80)
        
        collections = shopify.get_all_collections()
        print(f"✓ Toplam {len(collections)} koleksiyon bulundu\n")
        
        collection_info = analyze_collections(collections)
        
        print("Koleksiyon Listesi:")
        for idx, coll in enumerate(collection_info, 1):
            print(f"{idx:2}. {coll['title']:40} | Ürün Sayısı: {coll['product_count']:3} | Handle: {coll['handle']}")
        
        # Ürünleri çek
        print("\n" + "=" * 80)
        print("\n📦 ÜRÜNLER ANALİZ EDİLİYOR...")
        print("-" * 80)
        
        products = shopify.get_all_products_for_export()
        print(f"✓ Toplam {len(products)} ürün bulundu\n")
        
        # Ürün başlıklarını analiz et
        patterns, word_freq = analyze_product_titles(products)
        
        # En sık kullanılan kelimeleri göster
        print("\nEn Sık Kullanılan Kelimeler (Top 30):")
        print("-" * 80)
        for word, count in word_freq.most_common(30):
            print(f"{word:20} : {count:3} kez")
        
        # Kategori anahtar kelimelerini çıkar
        print("\n" + "=" * 80)
        print("\n🏷️ TESPİT EDİLEN KATEGORİLER:")
        print("-" * 80)
        
        category_keywords = extract_category_keywords(patterns['titles'])
        
        for keyword, count in sorted(category_keywords.items(), key=lambda x: x[1], reverse=True):
            print(f"{keyword:20} : {count:3} üründe bulundu")
        
        # Örnek ürün başlıkları
        print("\n" + "=" * 80)
        print("\nÖRNEK ÜRÜN BAŞLIKLARI (İlk 20):")
        print("-" * 80)
        for idx, title in enumerate(patterns['titles'][:20], 1):
            print(f"{idx:2}. {title}")
        
        # Sonuçları JSON dosyasına kaydet
        output_data = {
            'collections': collection_info,
            'category_keywords': category_keywords,
            'word_frequency': dict(word_freq.most_common(50)),
            'sample_titles': patterns['titles'][:100],
            'total_products': len(products),
            'total_collections': len(collections)
        }
        
        output_file = 'site_category_analysis.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 80)
        print(f"\n✅ Analiz tamamlandı! Sonuçlar '{output_file}' dosyasına kaydedildi.")
        print("\nBu verileri kullanarak category_metafield_manager.py dosyasını güncelleyebilirsiniz.")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
