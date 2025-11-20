# operations/product_images.py
"""
Ürün görsellerini yönetme modülü
"""

import logging
from collections import defaultdict

class ProductImageManager:
    """Ürün görsellerini çeken ve cache'leyen sınıf"""
    
    def __init__(self, sentos_api):
        """
        Args:
            sentos_api: SentosAPI instance
        """
        self.sentos_api = sentos_api
        self.image_cache = {}  # SKU -> image_url mapping
    
    def get_product_image(self, sku, product_id=None):
        """
        Ürün görseli al (cache'den veya API'den)
        
        Args:
            sku: Ürün SKU kodu
            product_id: Ürün ID (varsa)
            
        Returns:
            str: İlk ürün görseli URL'si veya None
        """
        # Cache'de var mı?
        if sku in self.image_cache:
            return self.image_cache[sku]
        
        # API'den çek
        try:
            if product_id:
                product_detail = self.sentos_api.get_product_by_id(product_id)
            elif sku:
                # SKU ile ara
                products = self.sentos_api.get_products(sku=sku, page_size=1)
                if products and len(products) > 0:
                    product_detail = products[0]
                else:
                    product_detail = None
            else:
                product_detail = None
            
            if product_detail:
                # İlk görseli al
                images = product_detail.get('images', [])
                if images and len(images) > 0:
                    # İlk görsel
                    first_image = images[0]
                    if isinstance(first_image, dict):
                        image_url = first_image.get('url', first_image.get('image_url'))
                    else:
                        image_url = first_image
                    
                    # Cache'e kaydet
                    self.image_cache[sku] = image_url
                    return image_url
        
        except Exception as e:
            logging.warning(f"Ürün görseli alınamadı (SKU: {sku}): {e}")
        
        return None
    
    def get_multiple_product_images(self, sku_list, progress_callback=None):
        """
        Birden fazla ürünün görsellerini toplu olarak al
        
        Args:
            sku_list: SKU listesi
            progress_callback: İlerleme callback
            
        Returns:
            dict: {sku: image_url} mapping
        """
        results = {}
        total = len(sku_list)
        
        for idx, sku in enumerate(sku_list):
            if progress_callback and idx % 10 == 0:
                progress_callback({
                    'message': f'Ürün görselleri yükleniyor... {idx}/{total}',
                    'progress': int((idx / total) * 100)
                })
            
            image_url = self.get_product_image(sku)
            if image_url:
                results[sku] = image_url
        
        return results
