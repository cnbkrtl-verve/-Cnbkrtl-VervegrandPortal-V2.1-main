"""
Variant (varyant) yardımcı fonksiyonları

Ürün varyantlarının boyut, renk ve sıralama işlemleri için
yardımcı fonksiyonlar.
"""

def get_variant_size(variant_data):
    """Varyant boyutunu al"""
    if not variant_data:
        return None
    
    # Option'lardan boyut bul
    for option in variant_data.get('options', []):
        if option.get('name', '').lower() in ['size', 'boyut', 'beden']:
            return option.get('value')
    
    # Title'dan boyut çıkar
    title = variant_data.get('title', '')
    size_keywords = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    for size in size_keywords:
        if size in title.upper():
            return size
    
    return None


def get_variant_color(variant_data):
    """Varyant rengini al"""
    if not variant_data:
        return None
    
    # Option'lardan renk bul
    for option in variant_data.get('options', []):
        if option.get('name', '').lower() in ['color', 'renk', 'colour']:
            return option.get('value')
    
    return None


def extract_colors_from_variants(variants):
    """
    Ürün varyantlarından tüm renkleri çıkarır
    
    Args:
        variants: Ürün varyantları listesi
        
    Returns:
        Renk listesi (benzersiz renkler)
    """
    colors = set()
    
    if not variants:
        return []
    
    for variant in variants:
        color = get_variant_color(variant)
        if color:
            colors.add(color)
    
    return sorted(list(colors))


def get_primary_color(variants):
    """
    Varyantlardan ana rengi tespit eder (ilk veya en yaygın renk)
    
    Args:
        variants: Ürün varyantları listesi
        
    Returns:
        Ana renk veya None
    """
    colors = extract_colors_from_variants(variants)
    
    if not colors:
        return None
    
    # Eğer tek renk varsa onu döndür
    if len(colors) == 1:
        return colors[0]
    
    # Birden fazla renk varsa, ilk rengi döndür (genellikle en popüler olanı)
    return colors[0]


def get_color_list_as_string(variants, separator=', '):
    """
    Varyantlardan renkleri virgülle ayrılmış string olarak döndürür
    
    Args:
        variants: Ürün varyantları listesi
        separator: Ayırıcı karakter (varsayılan: ', ')
        
    Returns:
        Renk listesi string formatında
    """
    colors = extract_colors_from_variants(variants)
    return separator.join(colors) if colors else None


def get_apparel_sort_key(size_str):
    """
    Giyim ürünleri için boyut sıralama anahtarı
    
    Boyutları mantıksal sıraya koyar:
    XXS < XS < S < M < L < XL < XXL < XXXL
    """
    if not size_str:
        return 999  # Boyutu olmayanlar sona
    
    size_order = {
        'XXS': 1,
        'XS': 2,
        'S': 3,
        'M': 4,
        'L': 5,
        'XL': 6,
        'XXL': 7,
        'XXXL': 8
    }
    
    size_upper = size_str.upper().strip()
    return size_order.get(size_upper, 999)
