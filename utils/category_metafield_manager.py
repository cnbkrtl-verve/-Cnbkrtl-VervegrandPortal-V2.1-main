"""
🏷️ Otomatik Kategori ve Meta Alan Yönetim Sistemi

Ürün başlığından otomatik kategori tespiti ve kategori bazlı meta alanlarını doldurur.
Shopify'da manuel işlem yapmadan kategori ve meta alanlarını otomatik günceller.
"""

import re
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Any

# Varyant helper fonksiyonlarını import et
try:
    from .variant_helpers import get_color_list_as_string
except ImportError:
    # Eğer relative import çalışmazsa, absolute import dene
    try:
        from utils.variant_helpers import get_color_list_as_string
    except ImportError:
        # Son çare: fonksiyonu burada tanımla
        def get_color_list_as_string(variants, separator=', '):
            """Fallback: Varyantlardan renk listesi çıkar"""
            if not variants:
                return None
            colors = set()
            for variant in variants:
                for option in variant.get('options', []):
                    if option.get('name', '').lower() in ['color', 'renk', 'colour']:
                        color = option.get('value')
                        if color:
                            colors.add(color)
            return separator.join(sorted(list(colors))) if colors else None

class CategoryMetafieldManager:
    """
    Kategori tespit ve meta alan yönetimi için merkezi sınıf.
    """
    
    _config = None
    
    @classmethod
    def _load_config(cls):
        if cls._config is None:
            try:
                # Proje kök dizinini bul
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                config_path = os.path.join(project_root, 'category_config.json')

                if not os.path.exists(config_path):
                     # Fallback: belki utils içindedir (test ortamı vs)
                     config_path = os.path.join(current_dir, '..', 'category_config.json')

                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._config = json.load(f)
            except Exception as e:
                logging.error(f"Konfigürasyon dosyası yüklenemedi: {e}")
                cls._config = {"categories": {}, "patterns": {}}
        return cls._config

    @classmethod
    def get_category_keywords(cls):
        config = cls._load_config()
        keywords = {}
        for cat, data in config.get('categories', {}).items():
            keywords[cat] = data.get('keywords', [])
        return keywords

    @classmethod
    def get_category_metafields(cls):
        config = cls._load_config()
        metafields = {}
        for cat, data in config.get('categories', {}).items():
            metafields[cat] = data.get('metafields', {})
        return metafields
    
    @staticmethod
    def detect_category(product_title: str) -> Optional[str]:
        """
        Ürün başlığından kategori tespit eder (PUANLAMA SİSTEMİ İLE).
        
        Args:
            product_title: Ürün başlığı
            
        Returns:
            Tespit edilen kategori veya None
        """
        if not product_title:
            return None
        
        title_lower = product_title.lower()
        keywords_map = CategoryMetafieldManager.get_category_keywords()
        scores = {}
        
        # Puanlama sistemi: Her eşleşen anahtar kelime için puan ver
        # Uzun anahtar kelimeler daha spesifiktir, daha yüksek puan alır
        for category, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    # Temel puan: 10
                    # Uzunluk bonusu: Kelime uzunluğu kadar puan
                    score = 10 + len(keyword)

                    # Tam eşleşme bonusu (kelime sınırları ile)
                    # "shirt" kelimesi "t-shirt" içinde geçebilir, bunu ayırt etmek lazım
                    # Ancak basit containment şimdilik yeterli, uzunluk puanı bunu çözer
                    # (T-shirt (7 puan) > Shirt (5 puan))

                    scores[category] = scores.get(category, 0) + score
                    logging.debug(f"Kategori ipucu: '{keyword}' -> {category} (+{score})")

        if not scores:
            logging.warning(f"'{product_title}' için kategori tespit edilemedi")
            return None
        
        # En yüksek puanlı kategoriyi seç
        best_category = max(scores, key=scores.get)
        logging.info(f"Kategori tespit edildi: '{best_category}' (Puan: {scores[best_category]})")
        return best_category

    @staticmethod
    def get_taxonomy_id(category: str) -> Optional[str]:
        """
        Kategori adı için Taxonomy ID (GID) döndürür.
        """
        config = CategoryMetafieldManager._load_config()
        cat_data = config.get('categories', {}).get(category)
        if cat_data:
            return cat_data.get('taxonomy_id')
        return None
    
    @staticmethod
    def extract_metafield_values(
        product_title: str, 
        category: str,
        product_description: str = "",
        variants: List[Dict] = None,
        shopify_recommendations: Dict = None,
        tags: List[str] = None,
        product_type: str = None
    ) -> Dict[str, str]:
        """
        🔍 ÇOK KATMANLI META ALAN ÇIKARMA SİSTEMİ
        
        Veri Kaynakları (Öncelik Sırasına Göre):
        1. Shopify Önerileri (En yüksek öncelik)
        2. Varyant Bilgileri (Renk, Beden, Materyal)
        3. Etiketler (Tags)
        4. Ürün Başlığı (Regex)
        5. Ürün Açıklaması (Regex)
        """
        values = {}
        title_lower = product_title.lower()
        desc_lower = product_description.lower() if product_description else ""
        tags_lower = [t.lower() for t in tags] if tags else []
        
        config = CategoryMetafieldManager._load_config()
        patterns = config.get('patterns', {})
        
        # ============================================
        # 1. SHOPIFY ÖNERİLERİ
        # ============================================
        if shopify_recommendations:
            recommended_attrs = shopify_recommendations.get('recommended_attributes', [])
            if recommended_attrs:
                logging.info(f"✨ Shopify önerilen attribute'ler: {', '.join(recommended_attrs)}")
        
        # ============================================
        # 2. VARYANT BİLGİLERİ
        # ============================================
        if variants:
            # Renk
            color_value = get_color_list_as_string(variants)
            if color_value and 'renk' not in values:
                values['renk'] = color_value
            
            # Beden ve Kumaş
            sizes = set()
            for variant in variants:
                options = variant.get('options', [])
                for option in options:
                    name = option.get('name', '').lower()
                    val = option.get('value', '')
                    
                    if name in ['size', 'beden', 'boyut']:
                        sizes.add(val)
                    
                    if name in ['material', 'kumaş', 'kumaş tipi', 'fabric'] and 'kumaş' not in values:
                        values['kumaş'] = val

            if sizes and 'beden' not in values:
                values['beden'] = ', '.join(sorted(list(sizes)))

        # ============================================
        # 3. TAGS & PRODUCT TYPE
        # ============================================
        # Etiketlerden desen, kumaş vb. yakalama
        for field, pattern_list in patterns.items():
            if field in values: continue

            # Tags içinde ara
            for tag in tags_lower:
                for pattern, value in pattern_list:
                    if re.search(pattern, tag):
                        values[field] = value
                        break
                if field in values: break

        # ============================================
        # 4. BAŞLIKTAN REGEX
        # ============================================
        for field, pattern_list in patterns.items():
            if field not in values:
                for pattern, value in pattern_list:
                    if re.search(pattern, title_lower):
                        values[field] = value
                        break
        
        # ============================================
        # 5. AÇIKLAMADAN REGEX
        # ============================================
        if desc_lower:
            for field, pattern_list in patterns.items():
                if field not in values:
                    for pattern, value in pattern_list:
                        if re.search(pattern, desc_lower):
                            values[field] = value
                            break
        
        return values
    
    @staticmethod
    def get_metafields_for_category(category: str) -> Dict[str, dict]:
        return CategoryMetafieldManager.get_category_metafields().get(category, {})
    
    @staticmethod
    def prepare_metafields_for_shopify(
        category: str, 
        product_title: str,
        product_description: str = "",
        variants: List[Dict] = None,
        shopify_recommendations: Dict = None,
        tags: List[str] = None,
        product_type: str = None
    ) -> List[Dict]:
        """
        Shopify GraphQL için metafield input formatını hazırlar.
        """
        metafield_templates = CategoryMetafieldManager.get_metafields_for_category(category)
        
        extracted_values = CategoryMetafieldManager.extract_metafield_values(
            product_title=product_title,
            category=category,
            product_description=product_description,
            variants=variants,
            shopify_recommendations=shopify_recommendations,
            tags=tags,
            product_type=product_type
        )
        
        shopify_metafields = []
        
        for field_key, template in metafield_templates.items():
            key = template['key']
            
            if key in extracted_values:
                value = extracted_values[key]
                shopify_metafields.append({
                    'namespace': template['namespace'],
                    'key': template['key'],
                    'value': value,
                    'type': template['type']
                })
        
        return shopify_metafields

    @staticmethod
    def get_category_summary() -> Dict[str, int]:
        summary = {}
        metafields = CategoryMetafieldManager.get_category_metafields()
        for category, fields in metafields.items():
            summary[category] = len(fields)
        return summary
