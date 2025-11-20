"""
🏷️ Otomatik Kategori ve Meta Alan Yöneticisi

Ürün başlıklarından otomatik kategori tespiti ve kategori bazlı meta alanlarını doldurur.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

# Kategori tespit için anahtar kelimeler (küçük harf, Türkçe karakterlerle)
CATEGORY_KEYWORDS = {
    "T-shirt": [
        "t-shirt", "tshirt", "tişört", "tisort", "polo", "body"
    ],
    "Elbise": [
        "elbise", "dress", "gömlek elbise"
    ],
    "Bluz": [
        "bluz", "blouse", "gömlek", "tunik"
    ],
    "Pantolon": [
        "pantolon", "pant", "jean", "kot", "eşofman altı"
    ],
    "Şort": [
        "şort", "sort", "short", "bermuda"
    ],
    "Etek": [
        "etek", "skirt"
    ],
    "Ceket": [
        "ceket", "jacket", "blazer", "mont", "kaban", "yelek", "hırka", "hirka", "trençkot", "trenckot", "parka"
    ],
    "Kazak": [
        "kazak", "sweater", "sweatshirt", "hoodie", "kapşonlu"
    ],
    "Takım": [
        "takım", "takım elbise", "suit", "set", "ikili takım", "üçlü takım"
    ],
    "Tulum": [
        "tulum", "jumpsuit", "overall"
    ],
    "Tayt": [
        "tayt", "legging", "tayt", "spor tayt"
    ],
    "Eşofman": [
        "eşofman", "esofman", "tracksuit"
    ],
    "Mayo": [
        "mayo", "bikini", "tankini", "swimsuit", "plaj"
    ],
    "İç Giyim": [
        "iç giyim", "sütyen", "külot", "boxer", "atlet", "termal", "gecelik", "pijama"
    ],
    "Aksesuar": [
        "çanta", "kemer", "şapka", "bere", "eldiven", "atkı", "şal", "kolye", "küpe", "bileklik"
    ]
}

# Kategori bazlı meta alanları tanımları
CATEGORY_METAFIELDS = {
    "T-shirt": {
        "yaka_tipi": {
            "namespace": "custom",
            "key": "yaka_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Bisiklet Yaka": ["bisiklet", "crew", "round"],
                "V Yaka": ["v yaka", "v-yaka"],
                "Polo Yaka": ["polo"],
                "Düğmeli": ["düğmeli", "dugmeli", "button"],
                "Kapüşonlu": ["kapüşonlu", "kapusonlu", "hoodie", "hood"]
            }
        },
        "kol_tipi": {
            "namespace": "custom",
            "key": "kol_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Kısa Kollu": ["kısa kollu", "kisa kollu", "short sleeve"],
                "Uzun Kollu": ["uzun kollu", "long sleeve"],
                "Kolsuz": ["kolsuz", "sleeveless"],
                "Reglan Kol": ["reglan"]
            }
        },
        "desen": {
            "namespace": "custom",
            "key": "desen",
            "type": "single_line_text_field",
            "keywords": {
                "Düz": ["düz renk", "tek renk", "solid"],
                "Çizgili": ["çizgili", "cizgili", "stripe"],
                "Desenli": ["desenli", "baskılı", "baskili", "print"],
                "Nakışlı": ["nakışlı", "nakisli", "embroidery"],
                "Leopar": ["leopar"],
                "Çiçekli": ["çiçekli", "çiçek", "floral"]
            }
        }
    },
    "Elbise": {
        "elbise_tipi": {
            "namespace": "custom",
            "key": "elbise_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Mini": ["mini"],
                "Midi": ["midi", "diz üstü", "diz altı"],
                "Maxi": ["maxi", "uzun", "long"],
                "Gömlek Elbise": ["gömlek elbise", "shirt dress"]
            }
        },
        "yaka_tipi": {
            "namespace": "custom",
            "key": "yaka_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "V Yaka": ["v yaka", "v-yaka"],
                "Bisiklet Yaka": ["bisiklet"],
                "Yakasız": ["yakasız", "strapless"],
                "Halter Yaka": ["halter"],
                "Düğmeli": ["düğmeli", "dugmeli"]
            }
        },
        "kol_tipi": {
            "namespace": "custom",
            "key": "kol_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Kısa Kollu": ["kısa kollu", "kisa kollu"],
                "Uzun Kollu": ["uzun kollu"],
                "Kolsuz": ["kolsuz", "askılı", "askili"],
                "Yarım Kollu": ["yarım kollu", "yarim kollu"]
            }
        },
        "desen": {
            "namespace": "custom",
            "key": "desen",
            "type": "single_line_text_field",
            "keywords": {
                "Düz": ["düz renk", "tek renk"],
                "Çiçekli": ["çiçekli", "çiçek", "floral"],
                "Çizgili": ["çizgili", "stripe"],
                "Puantiyeli": ["puantiyeli", "puantiye", "dot"],
                "Leopar": ["leopar"],
                "Desenli": ["desenli", "baskılı", "print"]
            }
        }
    },
    "Bluz": {
        "yaka_tipi": {
            "namespace": "custom",
            "key": "yaka_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "V Yaka": ["v yaka"],
                "Bisiklet Yaka": ["bisiklet"],
                "Gömlek Yaka": ["gömlek yaka", "klasik yaka"],
                "Hakim Yaka": ["hakim"],
                "Düğmeli": ["düğmeli"]
            }
        },
        "kol_tipi": {
            "namespace": "custom",
            "key": "kol_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Kısa Kollu": ["kısa kollu"],
                "Uzun Kollu": ["uzun kollu"],
                "Kolsuz": ["kolsuz"],
                "Yarım Kollu": ["yarım kollu"],
                "Balon Kol": ["balon kol"]
            }
        },
        "desen": {
            "namespace": "custom",
            "key": "desen",
            "type": "single_line_text_field",
            "keywords": {
                "Düz": ["düz renk"],
                "Çiçekli": ["çiçekli", "floral"],
                "Çizgili": ["çizgili"],
                "Desenli": ["desenli", "baskılı"]
            }
        }
    },
    "Pantolon": {
        "pantolon_tipi": {
            "namespace": "custom",
            "key": "pantolon_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Jean": ["jean", "kot", "denim"],
                "Kumaş Pantolon": ["kumaş", "klasik"],
                "Tayt": ["tayt", "legging"],
                "Eşofman Altı": ["eşofman", "esofman"],
                "Kargo": ["kargo"],
                "Palazzo": ["palazzo", "bol paça"]
            }
        },
        "bel_tipi": {
            "namespace": "custom",
            "key": "bel_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Yüksek Bel": ["yüksek bel", "high waist"],
                "Normal Bel": ["normal bel", "mid waist"],
                "Düşük Bel": ["düşük bel", "low waist"]
            }
        },
        "paça_tipi": {
            "namespace": "custom",
            "key": "paca_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Bol Paça": ["bol paça", "wide leg", "palazzo"],
                "Dar Paça": ["dar paça", "skinny", "slim"],
                "Düz Paça": ["düz paça", "straight"]
            }
        }
    },
    "Şort": {
        "sort_tipi": {
            "namespace": "custom",
            "key": "sort_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Jean Şort": ["jean", "kot", "denim"],
                "Kumaş Şort": ["kumaş"],
                "Bermuda": ["bermuda"],
                "Spor Şort": ["spor"]
            }
        },
        "bel_tipi": {
            "namespace": "custom",
            "key": "bel_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Yüksek Bel": ["yüksek bel"],
                "Normal Bel": ["normal bel"],
                "Düşük Bel": ["düşük bel"]
            }
        }
    },
    "Etek": {
        "etek_tipi": {
            "namespace": "custom",
            "key": "etek_tipi",
            "type": "single_line_text_field",
            "keywords": {
                "Mini": ["mini"],
                "Midi": ["midi", "diz üstü"],
                "Maxi": ["maxi", "uzun"],
                "Kalem": ["kalem"],
                "Pileli": ["pileli"],
                "Kloş": ["kloş", "A kesim"]
            }
        },
        "desen": {
            "namespace": "custom",
            "key": "desen",
            "type": "single_line_text_field",
            "keywords": {
                "Düz": ["düz renk"],
                "Çiçekli": ["çiçekli"],
                "Çizgili": ["çizgili"],
                "Desenli": ["desenli"]
            }
        }
    }
}


def detect_category_from_title(title: str) -> Optional[str]:
    """
    Ürün başlığından kategoriyi otomatik tespit eder.
    
    Args:
        title: Ürün başlığı
        
    Returns:
        Kategori adı veya None
        
    Örnek:
        detect_category_from_title("Büyük Beden Kısa Kollu T-shirt") → "T-shirt"
        detect_category_from_title("Uzun Elbise Çiçekli") → "Elbise"
    """
    if not title:
        return None
    
    title_lower = title.lower()
    
    # Her kategori için anahtar kelimeleri kontrol et
    # Öncelik sırası: En spesifik kategoriden en genele
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                logging.info(f"✅ Kategori tespit edildi: '{category}' (anahtar: '{keyword}')")
                return category
    
    logging.warning(f"⚠️ Kategori tespit edilemedi: '{title}'")
    return None


def extract_metafield_values(title: str, description: str, category: str) -> Dict[str, str]:
    """
    Ürün bilgilerinden kategori bazlı meta alanlarını otomatik çıkarır.
    
    Args:
        title: Ürün başlığı
        description: Ürün açıklaması
        category: Ürün kategorisi
        
    Returns:
        Meta alan key-value dictionary
        
    Örnek:
        extract_metafield_values(
            "Büyük Beden Kısa Kollu V Yaka Çizgili T-shirt",
            "...",
            "T-shirt"
        ) → {
            "yaka_tipi": "V Yaka",
            "kol_tipi": "Kısa Kollu",
            "desen": "Çizgili"
        }
    """
    if category not in CATEGORY_METAFIELDS:
        logging.warning(f"⚠️ Kategori '{category}' için meta alan tanımı yok")
        return {}
    
    metafields = {}
    combined_text = f"{title} {description}".lower()
    
    # Bu kategoriye ait meta alanları tara
    for field_key, field_config in CATEGORY_METAFIELDS[category].items():
        keywords_map = field_config.get("keywords", {})
        
        # Her değer için anahtar kelimeleri kontrol et
        for value, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in combined_text:
                    metafields[field_key] = value
                    logging.info(f"  ✅ {field_key} = '{value}' (anahtar: '{keyword}')")
                    break  # İlk eşleşmeyi al, diğerlerini atla
            
            if field_key in metafields:
                break  # Bu alan için değer bulundu, diğer değerleri kontrol etme
    
    return metafields


def get_metafield_definitions_for_category(category: str) -> List[Dict]:
    """
    Bir kategori için gerekli meta alan tanımlarını döndürür.
    
    Args:
        category: Kategori adı
        
    Returns:
        Meta alan tanımları listesi
    """
    if category not in CATEGORY_METAFIELDS:
        return []
    
    definitions = []
    for field_key, field_config in CATEGORY_METAFIELDS[category].items():
        definitions.append({
            "namespace": field_config["namespace"],
            "key": field_key,
            "type": field_config["type"],
            "name": field_key.replace("_", " ").title()
        })
    
    return definitions


def auto_categorize_and_fill_metafields(product_title: str, product_description: str = "") -> Tuple[Optional[str], Dict[str, str]]:
    """
    Ürün bilgilerinden otomatik kategori tespit eder ve meta alanlarını doldurur.
    
    Args:
        product_title: Ürün başlığı
        product_description: Ürün açıklaması (opsiyonel)
        
    Returns:
        (kategori, metafields_dict) tuple
        
    Örnek:
        category, metafields = auto_categorize_and_fill_metafields(
            "Büyük Beden Kısa Kollu V Yaka Çizgili T-shirt 303734"
        )
        # category = "T-shirt"
        # metafields = {
        #     "yaka_tipi": "V Yaka",
        #     "kol_tipi": "Kısa Kollu",
        #     "desen": "Çizgili"
        # }
    """
    # 1. Kategoriyi tespit et
    category = detect_category_from_title(product_title)
    
    if not category:
        return None, {}
    
    # 2. Meta alanlarını çıkar
    metafields = extract_metafield_values(product_title, product_description, category)
    
    return category, metafields


# Test fonksiyonu
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    test_products = [
        "Büyük Beden Kısa Kollu V Yaka Çizgili T-shirt 303734",
        "Uzun Kollu Çiçekli Maxi Elbise",
        "Yüksek Bel Skinny Jean Pantolon",
        "V Yaka Balon Kol Desenli Bluz",
        "Mini Pileli Etek"
    ]
    
    print("🧪 Test Sonuçları:")
    print("=" * 60)
    
    for product in test_products:
        print(f"\n📦 Ürün: {product}")
        category, metafields = auto_categorize_and_fill_metafields(product)
        print(f"   Kategori: {category}")
        print(f"   Meta Alanlar: {metafields}")
