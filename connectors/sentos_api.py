# connectors/sentos_api.py - Eski çalışan koddan uyarlanmış

import requests
import time
import logging
import re
import json
from urllib.parse import urljoin, urlparse
from requests.auth import HTTPBasicAuth

class SentosAPI:
    """Sentos API ile iletişimi yöneten sınıf."""
    def __init__(self, api_url, api_key, api_secret, api_cookie=None):
        self.api_url = api_url.strip().rstrip('/')
        self.auth = HTTPBasicAuth(api_key, api_secret)
        self.api_cookie = api_cookie
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        # Yeniden deneme ayarları
        self.max_retries = 5
        self.base_delay = 15 # saniye cinsinden

    def _make_request(self, method, endpoint, auth_type='basic', data=None, params=None, is_internal_call=False):
        if is_internal_call:
            parsed_url = urlparse(self.api_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            url = f"{base_url}{endpoint}"
        else:
            url = urljoin(self.api_url + '/', endpoint.lstrip('/'))
        
        headers = self.headers.copy()
        auth = None
        
        if auth_type == 'cookie':
            if not self.api_cookie:
                raise ValueError("Cookie ile istek için Sentos API Cookie ayarı gereklidir.")
            headers['Cookie'] = self.api_cookie
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            auth = self.auth

        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, headers=headers, auth=auth, data=data, params=params, timeout=90)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                # GÜNCELLEME: 500 (Sunucu hatası) ve 429 (Too Many Requests) hatalarında tekrar dene
                if e.response.status_code in [500, 429] and attempt < self.max_retries - 1:
                    wait_time = self.base_delay * (2 ** attempt)  # Üstel geri çekilme
                    # GÜNCELLEME: Log mesajı daha açıklayıcı hale getirildi.
                    logging.warning(f"Sentos API'den {e.response.status_code} hatası alındı. {wait_time} saniye beklenip tekrar denenecek... (Deneme {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    # Diğer hatalarda veya son denemede istisnayı yükselt
                    logging.error(f"Sentos API Hatası ({url}): {e}")
                    raise Exception(f"Sentos API Hatası ({url}): {e}")
            except requests.exceptions.RequestException as e:
                # Bağlantı ve diğer genel istek hatalarını yakala
                logging.error(f"Sentos API Bağlantı Hatası ({url}): {e}")
                raise Exception(f"Sentos API Bağlantı Hatası ({url}): {e}")
    
    def get_all_products(self, progress_callback=None, page_size=100):
        all_products, page = [], 1
        total_elements = None
        start_time = time.monotonic()

        while True:
            endpoint = f"/products?page={page}&size={page_size}"
            try:
                response = self._make_request("GET", endpoint).json()
                products_on_page = response.get('data', [])
                
                if not products_on_page and page > 1: break
                all_products.extend(products_on_page)
                
                if total_elements is None: 
                    total_elements = response.get('total_elements', 'Bilinmiyor')

                if progress_callback:
                    elapsed_time = time.monotonic() - start_time
                    message = f"Sentos'tan ürünler çekiliyor ({len(all_products)} / {total_elements})... Geçen süre: {int(elapsed_time)}s"
                    progress = int((len(all_products) / total_elements) * 100) if isinstance(total_elements, int) and total_elements > 0 else 0
                    progress_callback({'message': message, 'progress': progress})
                
                if len(products_on_page) < page_size: break
                page += 1
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Sayfa {page} çekilirken hata: {e}")
                # Hata durumunda işlemi sonlandır. _make_request zaten tekrar denemeyi yönetiyor.
                raise Exception(f"Sentos API'den ürünler çekilemedi: {e}")
            
        logging.info(f"Sentos'tan toplam {len(all_products)} ürün çekildi.")
        return all_products

    def get_ordered_image_urls(self, product_id):
        """
        ESKİ KODDAN ALINMIŞ ÇALIŞAN VERSİYON
        Cookie eksikse None döner (bu kritik!)
        """
        if not self.api_cookie:
            logging.warning(f"Sentos Cookie ayarlanmadığı için sıralı resimler alınamıyor (Ürün ID: {product_id}).")
            return None  # ← Bu None dönmesi kritik!

        try:
            endpoint = "/urun_sayfalari/include/ajax/fetch_urunresimler.php"
            payload = {
                'draw': '1', 'start': '0', 'length': '100',
                'search[value]': '', 'search[regex]': 'false',
                'urun': product_id, 'model': '0', 'renk': '0',
                'order[0][column]': '0', 'order[0][dir]': 'desc'
            }

            logging.info(f"Ürün ID {product_id} için sıralı resimler çekiliyor...")
            response = self._make_request("POST", endpoint, auth_type='cookie', data=payload, is_internal_call=True)
            response_json = response.json()

            ordered_urls = []
            for item in response_json.get('data', []):
                if len(item) > 2:
                    html_string = item[2]
                    # Orijinal regex pattern'i kullan
                    match = re.search(r'href="(https?://[^"]+/o_[^"]+)"', html_string)
                    if match:
                        ordered_urls.append(match.group(1))

            logging.info(f"Ürün ID {product_id} için {len(ordered_urls)} adet sıralı resim URL'si bulundu.")
            return ordered_urls
            
        except ValueError as ve:
            logging.error(f"Resim sırası alınamadı: {ve}")
            return None
        except Exception as e:
            logging.error(f"Sıralı resimler çekilirken hata oluştu (Ürün ID: {product_id}): {e}")
            return []  # Hata durumunda boş liste döner

    def get_product_by_sku(self, sku):
        """Verilen SKU'ya göre Sentos'tan tek bir ürün çeker."""
        if not sku:
            raise ValueError("Aranacak SKU boş olamaz.")
        endpoint = "/products"
        params = {'sku': sku.strip()}
        try:
            response = self._make_request("GET", endpoint, params=params).json()
            products = response.get('data', [])
            if not products:
                logging.warning(f"Sentos API'de '{sku}' SKU'su ile ürün bulunamadı.")
                return None
            
            # Tam eşleşme kontrolü (Case insensitive)
            target_sku = sku.strip().lower()
            
            # 1. Ana ürünlerde ara
            for product in products:
                p_sku = str(product.get('sku', '')).strip().lower()
                if p_sku == target_sku:
                    return product
            
            # 2. Varyantlarda ara
            for product in products:
                for variant in product.get('variants', []):
                    v_sku = str(variant.get('sku', '')).strip().lower()
                    if v_sku == target_sku:
                        # Varyant bulundu, ana ürünü döndür (fiyat bilgisi için)
                        return product

            # Eğer tam eşleşme yoksa, None döndür (YANLIŞ EŞLEŞMEYİ ÖNLEMEK İÇİN)
            logging.warning(f"SKU '{sku}' için tam eşleşme bulunamadı. (Bulunanlar: {[p.get('sku') for p in products]})")
            return None
            
        except Exception as e:
            logging.error(f"Sentos'ta SKU '{sku}' aranırken hata: {e}")
            raise

    def get_product_by_barcode(self, barcode):
        """Verilen Barkoda göre Sentos'tan tek bir ürün çeker."""
        if not barcode:
            return None
        endpoint = "/products"
        params = {'barcode': barcode.strip()}
        try:
            response = self._make_request("GET", endpoint, params=params).json()
            products = response.get('data', [])
            if not products:
                logging.warning(f"Sentos API'de '{barcode}' barkodu ile ürün bulunamadı.")
                return None
            
            # Tam eşleşme kontrolü
            target_barcode = barcode.strip().lower()
            
            # 1. Ana ürünlerde ara
            for product in products:
                p_barcode = str(product.get('barcode', '')).strip().lower()
                if p_barcode == target_barcode:
                    return product
            
            # 2. Varyantlarda ara
            for product in products:
                for variant in product.get('variants', []):
                    v_barcode = str(variant.get('barcode', '')).strip().lower()
                    if v_barcode == target_barcode:
                        return product

            # Eğer tam eşleşme yoksa, None döndür
            logging.warning(f"Barkod '{barcode}' için tam eşleşme bulunamadı. (Bulunanlar: {[p.get('barcode') for p in products]})")
            return None
            
        except Exception as e:
            logging.error(f"Sentos'ta Barkod '{barcode}' aranırken hata: {e}")
            return None

    def get_warehouses(self):
        """
        YENİ FONKSİYON: Sentos'taki tüm depoları çeker.
        """
        endpoint = "/warehouses"
        try:
            response = self._make_request("GET", endpoint)
            warehouses = response.get('data', [])
            logging.info(f"Sentos'tan {len(warehouses)} adet depo çekildi.")
            return warehouses
        except Exception as e:
            logging.error(f"Sentos depoları çekilirken hata: {e}")
            return []

    def update_shopify_location_mapping(self, sentos_magaza_id, shopify_location_id, sentos_warehouse_id):
        """
        YENİ FONKSİYON (PLACEHOLDER): Shopify konumu ile Sentos deposu eşleştirmesini günceller.
        Bu fonksiyonun içi, Sentos panelinin ayarları kaydetmek için kullandığı gerçek
        iç API isteği (muhtemelen bir PHPLiveX çağrısı) ile doldurulmalıdır.
        """
        logging.warning("update_shopify_location_mapping fonksiyonu henüz tam olarak implemente edilmemiştir. Gerçek endpoint ve payload gereklidir.")
        return {"success": True, "message": f"Eşleştirme '{sentos_magaza_id}' için güncellendi (SIMULASYON)."}    

    def test_connection(self):
        try:
            response = self._make_request("GET", "/products?page=1&size=1").json()
            return {'success': True, 'total_products': response.get('total_elements', 0), 'message': 'REST API OK'}
        except Exception as e:
            return {'success': False, 'message': f'REST API failed: {e}'}

    def test_image_fetch_debug(self, product_id):
        """Debug amaçlı görsel çekme testi"""
        result = {
            "product_id": product_id,
            "cookie_available": bool(self.api_cookie),
            "cookie_length": len(self.api_cookie) if self.api_cookie else 0,
            "success": False,
            "images_found": [],
            "error": None
        }
        
        if not self.api_cookie:
            result["error"] = "Cookie mevcut değil"
            return result
        
        try:
            # Cookie preview (güvenlik için sadece başını göster)
            if self.api_cookie:
                logging.info(f"Cookie preview: {self.api_cookie[:50]}...")
            
            endpoint = "/urun_sayfalari/include/ajax/fetch_urunresimler.php"
            payload = {
                'draw': '1', 'start': '0', 'length': '100',
                'search[value]': '', 'search[regex]': 'false',
                'urun': product_id, 'model': '0', 'renk': '0',
                'order[0][column]': '0', 'order[0][dir]': 'desc'
            }

            logging.info(f"Test: Endpoint {endpoint} için request gönderiliyor...")
            logging.info(f"Test: Payload: {payload}")
            
            response = self._make_request("POST", endpoint, auth_type='cookie', data=payload, is_internal_call=True)
            
            logging.info(f"Test: Response status: {response.status_code}")
            logging.info(f"Test: Response content (ilk 200 char): {response.text[:200]}")
            
            response_json = response.json()
            logging.info(f"Test: JSON parse başarılı, data count: {len(response_json.get('data', []))}")

            ordered_urls = []
            for i, item in enumerate(response_json.get('data', [])):
                if len(item) > 2:
                    html_string = item[2]
                    logging.info(f"Test: Item {i} HTML: {html_string[:100]}...")
                    match = re.search(r'href="(https?://[^"]+/o_[^"]+)"', html_string)
                    if match:
                        url = match.group(1)
                        ordered_urls.append(url)
                        logging.info(f"Test: URL bulundu: {url}")

            result["success"] = True
            result["images_found"] = ordered_urls
            logging.info(f"Test: Toplam {len(ordered_urls)} görsel URL'si bulundu")
            
        except Exception as e:
            result["error"] = str(e)
            logging.error(f"Test: Hata oluştu: {e}")
        
        return result

    # ========== DASHBOARD İÇİN YENİ METODLAR ==========
    
    def get_dashboard_stats(self):
        """Dashboard için Sentos API istatistikleri"""
        stats = {
            'total_products': 0,
            'categories_count': 0,
            'recent_updates': [],
            'stock_alerts': [],
            'api_status': 'unknown'
        }
        
        try:
            # Ürün sayısını al (ilk sayfayı çekerek toplam sayıyı öğren)
            response = self._make_request("GET", "/products?page=1&size=1").json()
            stats['total_products'] = response.get('total_elements', 0)
            stats['api_status'] = 'connected'
            
            # Son eklenen ürünleri al
            recent_response = self._make_request("GET", "/products?page=1&size=10").json()
            stats['recent_updates'] = recent_response.get('data', [])[:5]
            
            # Kategori bilgileri (eğer API'da varsa)
            try:
                categories_response = self._make_request("GET", "/categories?page=1&size=1").json()
                stats['categories_count'] = categories_response.get('total_elements', 0)
            except:
                stats['categories_count'] = 0
            
        except Exception as e:
            logging.error(f"Sentos dashboard istatistikleri alınırken hata: {e}")
            stats['api_status'] = 'failed'
            stats['error'] = str(e)
        
        return stats
    
    def get_order_detail(self, order_id):
        """
        Tek bir siparişin detayını çeker (items dahil)
        
        Args:
            order_id: Sipariş ID'si
            
        Returns:
            dict: Detaylı sipariş bilgisi
        """
        try:
            endpoint = f"/orders/{order_id}"
            response = self._make_request("GET", endpoint)
            return response.json()
        except Exception as e:
            logging.error(f"Sipariş detayı çekilirken hata (ID: {order_id}): {e}")
            return None
    
    def get_sales_orders(self, start_date=None, end_date=None, marketplace=None, status=None, 
                        page=1, page_size=100, progress_callback=None):
        """
        Sentos'tan satış siparişlerini çeker - Sadece E-Ticaret kanalı
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında)
            marketplace: Pazar yeri filtresi (örn: 'trendyol', 'hepsiburada')
            status: Sipariş durumu filtresi
            page: Sayfa numarası
            page_size: Sayfa başına kayıt sayısı
            progress_callback: İlerleme callback fonksiyonu
            
        Returns:
            dict: {
                'orders': [...],  # Sipariş listesi
                'total': int,     # Toplam sipariş sayısı
                'page': int,      # Mevcut sayfa
                'total_pages': int  # Toplam sayfa sayısı
            }
        """
        params = {
            'page': page,
            'size': page_size,
            'sort': 'createdDate,desc',  # En yeni siparişler önce
            'channel': 'ECOMMERCE'  # Sadece e-ticaret siparişleri
        }
        
        # Tarih filtreleri
        if start_date:
            params['startDate'] = start_date
            params['start_date'] = start_date  # Alternatif
            print(f"🗓️ Tarih filtresi: {start_date} - {end_date}")
        if end_date:
            params['endDate'] = end_date
            params['end_date'] = end_date  # Alternatif
            
        # Pazar yeri filtresi
        if marketplace:
            params['marketplace'] = marketplace.upper()
            print(f"🏪 Pazar yeri filtresi: {marketplace}")
            
        # Durum filtresi
        if status:
            params['status'] = status
        
        try:
            endpoint = "/orders"
            
            # Debug: API parametrelerini göster
            print(f"\n{'='*60}")
            print(f"🌐 SENTOS API İSTEĞİ")
            print(f"{'='*60}")
            print(f"Endpoint: {endpoint}")
            print(f"Parametreler: {params}")
            print(f"{'='*60}\n")
            
            response = self._make_request("GET", endpoint, params=params)
            response_data = response.json()
            
            # Debug: İlk çağrıda response yapısını logla
            if page == 1:
                print(f"\n{'='*60}")
                print(f"🌐 SENTOS API RESPONSE DEBUG")
                print(f"{'='*60}")
                print(f"Response type: {type(response_data)}")
                
                if isinstance(response_data, dict):
                    print(f"Response keys: {list(response_data.keys())}")
                    if 'data' in response_data:
                        print(f"Data type: {type(response_data['data'])}")
                        print(f"Data length: {len(response_data['data']) if response_data['data'] else 0}")
                        if response_data['data']:
                            print(f"First order keys: {list(response_data['data'][0].keys())}")
                            print(f"First order sample: {response_data['data'][0]}")
                elif isinstance(response_data, list):
                    print(f"Response is list, length: {len(response_data)}")
                    if response_data:
                        print(f"First order keys: {list(response_data[0].keys())}")
                        print(f"First order sample: {response_data[0]}")
                
                print(f"{'='*60}\n")
                
                logging.info(f"Sentos API Response Yapısı: {list(response_data.keys()) if isinstance(response_data, dict) else 'LIST'}")
                if isinstance(response_data, dict) and response_data:
                    first_key = list(response_data.keys())[0]
                    logging.info(f"İlk key: {first_key}, değer tipi: {type(response_data[first_key])}")
                    if isinstance(response_data.get('data'), list) and response_data['data']:
                        logging.info(f"İlk sipariş keys: {list(response_data['data'][0].keys())}")
                elif isinstance(response_data, list) and response_data:
                    logging.info(f"Response liste. İlk eleman keys: {list(response_data[0].keys())}")
            
            # Response yapısına göre veriyi çıkar
            if isinstance(response_data, dict):
                # Response bir dict ise (pagination bilgisi var)
                orders = response_data.get('data', response_data.get('orders', response_data.get('content', [])))
                total_elements = response_data.get('total', response_data.get('totalElements', response_data.get('total_elements', len(orders))))
                total_pages = response_data.get('totalPages', response_data.get('total_pages', 1))
                
                print(f"📊 RESPONSE SUMMARY:")
                print(f"   Total Elements (Toplam Kayıt): {total_elements}")
                print(f"   Total Pages (Toplam Sayfa): {total_pages}")
                print(f"   Orders in this page (Bu sayfadaki sipariş): {len(orders)}")
                print(f"{'='*60}\n")
            elif isinstance(response_data, list):
                # Response direkt liste ise (pagination yok)
                orders = response_data
                total_elements = len(orders)
                total_pages = 1
            else:
                orders = []
                total_elements = 0
                total_pages = 1
            
            if progress_callback:
                progress_callback({
                    'message': f"Sentos siparişleri çekiliyor... Sayfa {page}/{total_pages} ({len(orders)} sipariş)",
                    'progress': int((page / total_pages) * 100) if total_pages > 0 else 0
                })
            
            return {
                'orders': orders,
                'total': total_elements,
                'page': page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logging.error(f"Sentos siparişleri çekilirken hata: {e}")
            raise Exception(f"Sentos API'den siparişler çekilemedi: {e}")
    
    def get_all_sales_orders(self, start_date=None, end_date=None, marketplace=None, 
                            status=None, progress_callback=None, page_size=100):
        """
        Sentos'tan TÜM satış siparişlerini pagination ile çeker
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD)
            end_date: Bitiş tarihi (YYYY-MM-DD)
            marketplace: Pazar yeri filtresi
            status: Sipariş durumu filtresi
            progress_callback: İlerleme callback
            page_size: Sayfa başına kayıt sayısı
            
        Returns:
            list: Tüm siparişlerin listesi
        """
        all_orders = []
        page = 1
        total_pages = None
        start_time = time.monotonic()
        
        while True:
            try:
                result = self.get_sales_orders(
                    start_date=start_date,
                    end_date=end_date,
                    marketplace=marketplace,
                    status=status,
                    page=page,
                    page_size=page_size,
                    progress_callback=None  # Kendi callback'imizi kullanacağız
                )
                
                orders = result.get('orders', [])
                if not orders:
                    break
                
                # İlk siparişi kontrol et - items var mı?
                if page == 1 and orders:
                    first_order = orders[0]
                    # Sentos'ta 'lines' field'ı kullanılıyor
                    items = first_order.get('lines', first_order.get('items', first_order.get('orderItems', first_order.get('products', []))))
                    
                    print(f"\n{'='*60}")
                    print(f"🔍 ITEMS KONTROLÜ (İlk Sipariş)")
                    print(f"{'='*60}")
                    print(f"Lines field var mı? {'lines' in first_order}")
                    print(f"Items field var mı? {'items' in first_order}")
                    print(f"Lines değeri: {items}")
                    print(f"Lines uzunluk: {len(items) if items else 0}")
                    print(f"{'='*60}\n")
                    
                    if not items:
                        # Items boş - detay çekmemiz gerekiyor
                        logging.warning("⚠️ Siparişlerde 'items' field'ı boş! Detay endpoint kullanılacak.")
                        logging.info("Bu işlem daha uzun sürecek...")
                        
                        # İlk 5 siparişin detayını çek (test için)
                        detailed_orders = []
                        for order in orders[:5]:
                            order_id = order.get('id')
                            if order_id:
                                detail = self.get_order_detail(order_id)
                                if detail:
                                    detailed_orders.append(detail)
                                time.sleep(0.2)  # Rate limiting
                        
                        if detailed_orders:
                            logging.info(f"Detaylı sipariş örneği: {detailed_orders[0]}")
                            # Eğer detaylı versiyonda items varsa, tüm siparişler için detay çekelim
                            detail_items = detailed_orders[0].get('items', detailed_orders[0].get('orderItems', []))
                            if detail_items:
                                logging.info("✅ Detay endpoint'inde items var! Tüm siparişler için detay çekilecek.")
                                # Tüm siparişleri detaylı olarak yeniden çek
                                orders = []
                                for order in result.get('orders', []):
                                    order_id = order.get('id')
                                    if order_id:
                                        detail = self.get_order_detail(order_id)
                                        if detail:
                                            orders.append(detail)
                                        time.sleep(0.2)
                
                all_orders.extend(orders)
                
                if total_pages is None:
                    total_pages = result.get('total_pages', 1)
                
                if progress_callback:
                    elapsed_time = time.monotonic() - start_time
                    progress_callback({
                        'message': f"Sentos siparişleri çekiliyor... {len(all_orders)} / {result.get('total', 0)} (Sayfa {page}/{total_pages}) - {int(elapsed_time)}s",
                        'progress': int((page / total_pages) * 100) if total_pages > 0 else 0
                    })
                
                # Son sayfaya ulaştıysak dur
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                logging.error(f"Sayfa {page} çekilirken hata: {e}")
                raise Exception(f"Sentos siparişleri çekilemedi (Sayfa {page}): {e}")
        
        logging.info(f"Sentos'tan toplam {len(all_orders)} sipariş çekildi.")
        return all_orders