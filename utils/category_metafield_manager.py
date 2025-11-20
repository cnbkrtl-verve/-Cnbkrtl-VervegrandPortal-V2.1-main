"""
🏷️ Otomatik Kategori ve Meta Alan Yönetim Sistemi

Ürün başlığından otomatik kategori tespiti ve kategori bazlı meta alanlarını doldurur.
Shopify'da manuel işlem yapmadan kategori ve meta alanlarını otomatik günceller.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

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
    
    # Kategori tespit için anahtar kelimeler (öncelik sırasına göre)
    # ÖNEMLİ: Daha spesifik kelimeler üstte olmalı!
    CATEGORY_KEYWORDS = {
        'Sweatshirt': ['sweatshirt', 'sweat', 'hoodie'],
        'T-shirt': ['t-shirt', 'tshirt', 'tişört', 'tisort'],
        'Elbise': ['elbise', 'dress'],
        'Bluz': ['bluz', 'blouse'],
        'Gömlek': ['gömlek', 'shirt', 'tunik gömlek'],
        'Pantolon': ['pantolon', 'pants', 'jean', 'kot'],
        'Jogger': ['jogger', 'jogging'],
        'Eşofman Altı': ['eşofman altı', 'eşofman alt', 'esofman alt', 'tracksuit bottom'],
        'Tayt': ['tayt', 'legging', 'レギンス'],
        'Şort': ['şort', 'sort', 'short', 'bermuda'],
        'Etek': ['etek', 'skirt'],
        'Ceket': ['ceket', 'jacket', 'blazer'],
        'Mont': ['mont', 'coat', 'parka', 'trençkot', 'trench'],
        'Kaban': ['kaban', 'palto', 'overcoat'],
        'Kazak': ['kazak', 'sweater', 'pullover', 'boğazlı', 'balıkçı yaka'],
        'Hırka': ['hırka', 'hirka', 'cardigan'],
        'Süveter': ['süveter', 'suveter', 'triko'],
        'Tunik': ['tunik', 'tunic'],
        'Yelek': ['yelek', 'vest'],
        'Şal': ['şal', 'sal', 'scarf', 'atkı', 'atki', 'eşarp'],
        'Takım': ['takım', 'takim', 'suit', 'set', 'ikili'],
        'Mayo': ['mayo', 'bikini', 'swimsuit', 'deniz'],
        'Gecelik': ['gecelik', 'pijama', 'nightgown', 'uyku'],
        'Tulum': ['tulum', 'jumpsuit', 'overall', 'salopet']
    }
    
    # Her kategori için meta alan şablonları
    # Shopify'daki standart meta alanlarına göre düzenlenmiştir
    CATEGORY_METAFIELDS = {
        'Elbise': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (V yaka, Bisiklet yaka, Halter vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Kısa kol, Uzun kol, Kolsuz vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Elbise boyu (Mini, Midi, Maxi, Diz üstü vb.)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen (Çiçekli, Düz, Leopar, Çizgili vb.)'
            },
            'custom.kullanim_alani': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kullanim_alani',
                'description': 'Kullanım alanı (Günlük, Gece, Kokteyl vb.)'
            }
        },
        'T-shirt': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (V yaka, Bisiklet yaka, Polo vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Kısa kol, Uzun kol vb.)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen (Baskılı, Düz, Çizgili vb.)'
            }
        },
        'Bluz': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (V yaka, Hakim yaka, Gömlek yaka vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Kısa kol, Uzun kol, 3/4 kol vb.)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen'
            }
        },
        'Pantolon': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.pacha_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'pacha_tipi',
                'description': 'Paça tipi (Dar paça, Bol paça, İspanyol paça vb.)'
            },
            'custom.bel_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'bel_tipi',
                'description': 'Bel tipi (Yüksek bel, Normal bel, Düşük bel vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Pantolon boyu (Uzun, 7/8, Capri vb.)'
            }
        },
        'Şort': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Şort boyu (Mini, Midi, Bermuda vb.)'
            },
            'custom.bel_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'bel_tipi',
                'description': 'Bel tipi (Yüksek bel, Normal bel vb.)'
            }
        },
        'Etek': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Etek boyu (Mini, Midi, Maxi vb.)'
            },
            'custom.model': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'model',
                'description': 'Model (Kalem, Pileli, A kesim vb.)'
            }
        },
        'Ceket': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            },
            'custom.kapanma_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kapanma_tipi',
                'description': 'Kapanma tipi (Fermuarlı, Düğmeli, Çıtçıtlı vb.)'
            }
        },
        'Mont': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol vb.)'
            },
            'custom.kapanma_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kapanma_tipi',
                'description': 'Kapanma tipi (Fermuarlı, Düğmeli, Çıtçıtlı vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Mont boyu (Kısa, Orta, Uzun vb.)'
            },
            'custom.kapusonlu': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kapusonlu',
                'description': 'Kapüşon durumu (Kapüşonlu, Kapüşonsuz)'
            }
        },
        'Gömlek': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (Klasik, Hakim, İtalyan vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen (Düz, Çizgili, Kareli vb.)'
            }
        },
        'Hırka': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol, Kolsuz vb.)'
            },
            'custom.kapanma_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kapanma_tipi',
                'description': 'Kapanma tipi (Düğmeli, Açık, Fermuarlı vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Hırka boyu (Kısa, Orta, Uzun vb.)'
            }
        },
        'Sweatshirt': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            },
            'custom.kapusonlu': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kapusonlu',
                'description': 'Kapüşon durumu (Kapüşonlu, Kapüşonsuz)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen (Baskılı, Düz, Logolu vb.)'
            }
        },
        'Kazak': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (Boğazlı, V yaka, Bisiklet yaka, Balıkçı vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            },
            'custom.desen': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'desen',
                'description': 'Desen (Düz, Örgü, Desenli vb.)'
            }
        },
        'Süveter': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (Boğazlı, V yaka, Bisiklet yaka vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            }
        },
        'Jogger': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.bel_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'bel_tipi',
                'description': 'Bel tipi (Lastikli, İpli vb.)'
            },
            'custom.pacha_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'pacha_tipi',
                'description': 'Paça tipi (Dar paça, Lastikli paça vb.)'
            },
            'custom.cep': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'cep',
                'description': 'Cep özellikleri (Cepli, Cepsiz vb.)'
            }
        },
        'Eşofman Altı': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.bel_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'bel_tipi',
                'description': 'Bel tipi (Lastikli, İpli vb.)'
            },
            'custom.pacha_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'pacha_tipi',
                'description': 'Paça tipi (Dar paça, Bol paça, Lastikli paça vb.)'
            },
            'custom.kullanim_alani': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kullanim_alani',
                'description': 'Kullanım alanı (Spor, Günlük vb.)'
            }
        },
        'Tayt': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.bel_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'bel_tipi',
                'description': 'Bel tipi (Yüksek bel, Normal bel vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Tayt boyu (Uzun, 7/8, Capri vb.)'
            },
            'custom.kullanim_alani': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kullanim_alani',
                'description': 'Kullanım alanı (Spor, Günlük vb.)'
            }
        },
        'Tunik': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.yaka_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'yaka_tipi',
                'description': 'Yaka tipi (V yaka, Hakim yaka, Bisiklet yaka vb.)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Tunik boyu (Kısa, Orta, Uzun vb.)'
            }
        },
        'Tulum': {
            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },
            'custom.kol_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'kol_tipi',
                'description': 'Kol tipi (Uzun kol, Kısa kol, Kolsuz vb.)'
            },
            'custom.pacha_tipi': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'pacha_tipi',
                'description': 'Paça tipi (Dar, Bol, İspanyol vb.)'
            },
            'custom.boy': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'boy',
                'description': 'Tulum boyu (Uzun, 7/8, Şort vb.)'
            }
        }
    }
    
    @staticmethod
    def detect_category(product_title: str) -> Optional[str]:
        """
        Ürün başlığından kategori tespit eder.
        
        Args:
            product_title: Ürün başlığı
            
        Returns:
            Tespit edilen kategori veya None
        """
        if not product_title:
            return None
        
        title_lower = product_title.lower()
        
        # Öncelik sırasına göre kontrol et
        for category, keywords in CategoryMetafieldManager.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    logging.info(f"Kategori tespit edildi: '{category}' (Anahtar: '{keyword}')")
                    return category
        
        logging.warning(f"'{product_title}' için kategori tespit edilemedi")
        return None
    
    @staticmethod
    def extract_metafield_values(
        product_title: str, 
        category: str,
        product_description: str = "",
        variants: List[Dict] = None,
        shopify_recommendations: Dict = None
    ) -> Dict[str, str]:
        """
        🔍 ÇOK KATMANLI META ALAN ÇIKARMA SİSTEMİ
        
        4 Katmanlı Veri Kaynağı (Öncelik Sırasına Göre):
        1. Shopify Önerileri (En yüksek öncelik - Shopify'ın AI önerileri)
        2. Varyant Bilgileri (Renk, Beden, Materyal seçenekleri)
        3. Ürün Başlığı (Regex pattern matching ile detaylı analiz)
        4. Ürün Açıklaması (Başlıkta bulunamayanlar için)
        
        Args:
            product_title: Ürün başlığı
            category: Tespit edilen kategori
            product_description: Ürün açıklaması (HTML olabilir)
            variants: Ürün varyantları [{title, options: [{name, value}]}]
            shopify_recommendations: Shopify'ın önerdiği attribute'ler
            
        Returns:
            Meta alan değerleri (key: value)
        """
        values = {}
        title_lower = product_title.lower()
        desc_lower = product_description.lower() if product_description else ""
        
        # Ortak kalıplar (Genişletilmiş + Öncelikli Sıralama)
        patterns = {
            'yaka_tipi': [
                (r'boğazlı\s*yaka', 'Boğazlı Yaka'),
                (r'boğazlı', 'Boğazlı'),
                (r'v\s*yaka', 'V Yaka'),
                (r'v\-yaka', 'V Yaka'),
                (r'bisiklet\s*yaka', 'Bisiklet Yaka'),
                (r'hakim\s*yaka', 'Hakim Yaka'),
                (r'polo\s*yaka', 'Polo Yaka'),
                (r'balıkçı\s*yaka', 'Balıkçı Yaka'),
                (r'balıkçı', 'Balıkçı Yaka'),
                (r'halter\s*yaka', 'Halter'),
                (r'halter', 'Halter'),
                (r'kayık\s*yaka', 'Kayık Yaka'),
                (r'gömlek\s*yaka', 'Gömlek Yaka'),
                (r'klasik\s*yaka', 'Klasik Yaka'),
                (r'yuvarlak\s*yaka', 'Yuvarlak Yaka'),
                (r'kare\s*yaka', 'Kare Yaka'),
                (r'askılı', 'Askılı'),
                (r'straplez', 'Straplez'),
                (r'tek\s*omuz', 'Tek Omuz'),
            ],
            'kol_tipi': [
                (r'uzun\s*kol', 'Uzun Kol'),
                (r'kısa\s*kol', 'Kısa Kol'),
                (r'kolsuz', 'Kolsuz'),
                (r'3/4\s*kol', '3/4 Kol'),
                (r'yarım\s*kol', 'Yarım Kol'),
                (r'balon\s*kol', 'Balon Kol'),
                (r'fırfırlı\s*kol', 'Fırfırlı Kol'),
                (r'volan\s*kol', 'Volan Kol'),
                (r'düşük\s*omuz', 'Düşük Omuz'),
            ],
            'boy': [
                (r'maxi\s*boy', 'Maxi'),
                (r'maxi', 'Maxi'),
                (r'midi\s*boy', 'Midi'),
                (r'midi', 'Midi'),
                (r'mini\s*boy', 'Mini'),
                (r'mini', 'Mini'),
                (r'diz\s*üst', 'Diz Üstü'),
                (r'diz\s*alt', 'Diz Altı'),
                (r'bilekli', 'Bilekli'),
                (r'uzun\s*boy', 'Uzun'),
                (r'orta\s*boy', 'Orta'),
                (r'kısa\s*boy', 'Kısa'),
            ],
            'desen': [
                (r'leopar\s*desen', 'Leopar'),
                (r'leopar', 'Leopar'),
                (r'çiçek\s*desen', 'Çiçekli'),
                (r'çiçekli', 'Çiçekli'),
                (r'çiçek', 'Çiçekli'),
                (r'desenli', 'Desenli'),
                (r'düz\s*renk', 'Düz'),
                (r'düz', 'Düz'),
                (r'çizgi\s*desen', 'Çizgili'),
                (r'çizgili', 'Çizgili'),
                (r'baskı\s*desen', 'Baskılı'),
                (r'baskılı', 'Baskılı'),
                (r'logolu', 'Logolu'),
                (r'puantiye\s*desen', 'Puantiyeli'),
                (r'puantiyeli', 'Puantiyeli'),
                (r'kareli', 'Kareli'),
                (r'örgü\s*desen', 'Örgü'),
                (r'örgü', 'Örgü'),
                (r'jakarlı', 'Jakarlı'),
                (r'geometrik', 'Geometrik'),
                (r'soyut', 'Soyut'),
            ],
            'pacha_tipi': [
                (r'dar\s*paça', 'Dar Paça'),
                (r'bol\s*paça', 'Bol Paça'),
                (r'ispanyol\s*paça', 'İspanyol Paça'),
                (r'düz\s*paça', 'Düz Paça'),
                (r'lastikli\s*paça', 'Lastikli Paça'),
                (r'wide\s*leg', 'Bol Paça'),
                (r'skinny', 'Dar Paça'),
            ],
            'bel_tipi': [
                (r'yüksek\s*bel', 'Yüksek Bel'),
                (r'normal\s*bel', 'Normal Bel'),
                (r'düşük\s*bel', 'Düşük Bel'),
                (r'lastikli\s*bel', 'Lastikli'),
                (r'ipli\s*bel', 'İpli'),
                (r'kemer\s*detaylı', 'Kemerli'),
            ],
            'kapanma_tipi': [
                (r'fermuarlı', 'Fermuarlı'),
                (r'fermuar', 'Fermuarlı'),
                (r'düğmeli', 'Düğmeli'),
                (r'düğme', 'Düğmeli'),
                (r'çıtçıtlı', 'Çıtçıtlı'),
                (r'çıtçıt', 'Çıtçıtlı'),
                (r'açık\s*model', 'Açık'),
                (r'önden\s*açık', 'Önden Açık'),
            ],
            'kapusonlu': [
                (r'kapüşonlu', 'Kapüşonlu'),
                (r'kapusonlu', 'Kapüşonlu'),
                (r'hoodie', 'Kapüşonlu'),
            ],
            'kullanim_alani': [
                (r'spor', 'Spor'),
                (r'günlük', 'Günlük'),
                (r'gece', 'Gece'),
                (r'kokteyl', 'Kokteyl'),
                (r'casual', 'Günlük'),
                (r'ofis', 'Ofis'),
                (r'iş', 'İş'),
                (r'düğün', 'Düğün'),
                (r'özel\s*gün', 'Özel Gün'),
            ],
            'cep': [
                (r'cepli', 'Cepli'),
                (r'cepsiz', 'Cepsiz'),
            ],
            'model': [
                (r'kalem\s*etek', 'Kalem'),
                (r'kalem', 'Kalem'),
                (r'pileli', 'Pileli'),
                (r'a\s*kesim', 'A Kesim'),
                (r'balon', 'Balon'),
                (r'saten', 'Saten'),
                (r'volanlı', 'Volanlı'),
            ],
            'kumaş': [
                # Kumaş tipleri (varyantlardan veya açıklamadan)
                (r'pamuklu', 'Pamuklu'),
                (r'pamuk', 'Pamuklu'),
                (r'viskon', 'Viskon'),
                (r'polyester', 'Polyester'),
                (r'likralı', 'Likralı'),
                (r'likra', 'Likralı'),
                (r'denim', 'Denim'),
                (r'kot', 'Denim'),
                (r'jean', 'Denim'),
                (r'saten', 'Saten'),
                (r'kadife', 'Kadife'),
                (r'triko', 'Triko'),
                (r'örme', 'Örme'),
                (r'dokuma', 'Dokuma'),
                (r'şifon', 'Şifon'),
                (r'krep', 'Krep'),
            ],
            'stil': [
                (r'oversize', 'Oversize'),
                (r'slim\s*fit', 'Slim Fit'),
                (r'regular\s*fit', 'Regular Fit'),
                (r'loose', 'Bol Kesim'),
                (r'fitted', 'Vücuda Oturan'),
                (r'boyfriend', 'Boyfriend'),
                (r'mom', 'Mom'),
                (r'vintage', 'Vintage'),
                (r'retro', 'Retro'),
            ]
        }
        
        # ============================================
        # KATMAN 1: SHOPIFY ÖNERİLERİNDEN AL (EN YÜKSEK ÖNCELİK)
        # ============================================
        if shopify_recommendations:
            recommended_attrs = shopify_recommendations.get('recommended_attributes', [])
            
            # recommended_attrs bir liste of strings'dir (örn: ["Collar Type", "Sleeve Length"])
            # Bu attribute isimleri sadece hangi alanların önemli olduğunu gösterir
            # Değerleri başlık, varyant veya açıklamadan çıkaracağız
            
            # Şimdilik Shopify attribute isimlerini logla (gelecekte API'den değer de alabiliriz)
            if recommended_attrs:
                logging.info(f"✨ Shopify önerilen attribute'ler: {', '.join(recommended_attrs)}")
                # Not: Shopify sadece attribute ismi öneriyor, değer önermiyor
                # Değerleri diğer katmanlardan (varyant, başlık, açıklama) çıkaracağız
        
        # ============================================
        # KATMAN 2: VARYANT BİLGİLERİNDEN AL
        # ============================================
        if variants:
            # Renk bilgisini çıkar (zaten get_color_list_as_string var)
            color_value = get_color_list_as_string(variants)
            if color_value and 'renk' not in values:
                values['renk'] = color_value
                logging.info(f"🎨 Varyantlardan renk çıkarıldı: '{color_value}'")
            
            # Diğer varyant seçeneklerini de kontrol et
            for variant in variants:
                options = variant.get('options', [])
                for option in options:
                    option_name = option.get('name', '').lower()
                    option_value = option.get('value', '')
                    
                    # Beden/Size
                    if option_name in ['size', 'beden', 'boyut'] and 'beden' not in values:
                        # Varyantlardan beden listesi çıkar
                        sizes = set()
                        for v in variants:
                            for opt in v.get('options', []):
                                if opt.get('name', '').lower() in ['size', 'beden', 'boyut']:
                                    sizes.add(opt.get('value', ''))
                        if sizes:
                            values['beden'] = ', '.join(sorted(list(sizes)))
                            logging.info(f"📏 Varyantlardan beden çıkarıldı: '{values['beden']}'")
                    
                    # Kumaş/Material
                    if option_name in ['material', 'kumaş', 'kumaş tipi', 'fabric'] and 'kumaş' not in values:
                        values['kumaş'] = option_value
                        logging.info(f"🧵 Varyantlardan kumaş çıkarıldı: '{option_value}'")
        
        # ============================================
        # KATMAN 3: BAŞLIKTAN REGEX İLE ÇIKAR
        # ============================================
        for field, pattern_list in patterns.items():
            if field not in values:  # Sadece henüz dolmamış alanları doldur
                for pattern, value in pattern_list:
                    if re.search(pattern, title_lower):
                        values[field] = value
                        logging.info(f"📝 Başlıktan çıkarıldı: {field} = '{value}'")
                        break  # İlk eşleşmeyi al
        
        # ============================================
        # KATMAN 4: AÇIKLAMADAN ÇIKAR (SON ÇARE)
        # ============================================
        if desc_lower:
            for field, pattern_list in patterns.items():
                if field not in values:  # Sadece henüz dolmamış alanları doldur
                    for pattern, value in pattern_list:
                        if re.search(pattern, desc_lower):
                            values[field] = value
                            logging.info(f"📄 Açıklamadan çıkarıldı: {field} = '{value}'")
                            break  # İlk eşleşmeyi al
        
        return values
    
    @staticmethod
    def get_metafields_for_category(category: str) -> Dict[str, dict]:
        """
        Belirtilen kategori için meta alan şablonlarını döndürür.
        
        Args:
            category: Kategori adı
            
        Returns:
            Meta alan şablonları
        """
        return CategoryMetafieldManager.CATEGORY_METAFIELDS.get(category, {})
    
    @staticmethod
    @staticmethod
    def prepare_metafields_for_shopify(
        category: str, 
        product_title: str,
        product_description: str = "",
        variants: List[Dict] = None,
        shopify_recommendations: Dict = None
    ) -> List[Dict]:
        """
        Shopify GraphQL için metafield input formatını hazırlar.
        
        Args:
            category: Ürün kategorisi
            product_title: Ürün başlığı
            product_description: Ürün açıklaması
            variants: Ürün varyantları (renk bilgisi için)
            shopify_recommendations: Shopify AI önerileri
            
        Returns:
            Shopify metafield input listesi
        """
        metafield_templates = CategoryMetafieldManager.get_metafields_for_category(category)
        
        # 🌟 UPGRADED: Tüm veri kaynaklarını kullan
        extracted_values = CategoryMetafieldManager.extract_metafield_values(
            product_title=product_title,
            category=category,
            product_description=product_description,
            variants=variants,
            shopify_recommendations=shopify_recommendations
        )
        
        shopify_metafields = []
        
        for field_key, template in metafield_templates.items():
            # Meta alan key'ini çıkar (custom.yaka_tipi -> yaka_tipi)
            key = template['key']
            
            # Çıkarılan değerler içinde varsa kullan
            if key in extracted_values:
                value = extracted_values[key]
                
                shopify_metafields.append({
                    'namespace': template['namespace'],
                    'key': template['key'],
                    'value': value,
                    'type': template['type']
                })
                
                logging.info(f"Shopify metafield hazırlandı: {template['namespace']}.{template['key']} = '{value}'")
        
        return shopify_metafields
    
    @staticmethod
    def get_category_summary() -> Dict[str, int]:
        """
        Kategori istatistiklerini döndürür.
        
        Returns:
            Kategori adı ve meta alan sayısı
        """
        summary = {}
        for category, metafields in CategoryMetafieldManager.CATEGORY_METAFIELDS.items():
            summary[category] = len(metafields)
        return summary


# Kullanım örneği
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    test_titles = [
        "Büyük Beden Uzun Kollu Leopar Desenli Diz Üstü Elbise 285058",
        "Büyük Beden Bisiklet Yaka Yarım Kollu Düz Renk T-shirt 303734",
        "Büyük Beden V Yaka Kısa Kol Çiçekli Bluz 256478",
        "Büyük Beden Yüksek Bel Dar Paça Siyah Pantolon 123456"
    ]
    
    for title in test_titles:
        print(f"\n{'='*60}")
        print(f"Ürün: {title}")
        print(f"{'='*60}")
        
        # Kategori tespit
        category = CategoryMetafieldManager.detect_category(title)
        print(f"Kategori: {category}")
        
        if category:
            # Meta alanları hazırla
            metafields = CategoryMetafieldManager.prepare_metafields_for_shopify(category, title)
            print(f"\nOluşturulan Meta Alanlar ({len(metafields)}):")
            for mf in metafields:
                print(f"  - {mf['namespace']}.{mf['key']} = '{mf['value']}'")
