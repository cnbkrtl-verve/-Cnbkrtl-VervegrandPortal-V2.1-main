# operations/sales_analytics.py
"""
Sentos Satış Analizi Modülü
E-Ticaret kanalından satış verilerini çeker ve detaylı analiz yapar
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
import concurrent.futures
import time
import re

class SalesAnalytics:
    """Satış verilerini analiz eden sınıf"""
    
    def __init__(self, sentos_api):
        """
        Args:
            sentos_api: SentosAPI instance
        """
        self.sentos_api = sentos_api
    
    def _fetch_costs_for_skus(self, skus_or_map, progress_callback=None):
        """
        Verilen SKU listesi veya SKU->İsim haritası için Sentos'tan maliyet verilerini çeker.
        Multi-threading kullanarak hızlandırılmıştır.
        
        Args:
            skus_or_map: SKU listesi (set/list) veya {sku: product_name} sözlüğü
        """
        cost_map = {}
        if not skus_or_map:
            return cost_map
            
        # Girdi tipini kontrol et ve normalize et
        if isinstance(skus_or_map, dict):
            sku_list = list(skus_or_map.keys())
            sku_name_map = skus_or_map
        else:
            sku_list = list(skus_or_map)
            sku_name_map = {}
            
        total_skus = len(sku_list)
        logging.info(f"Toplam {total_skus} adet benzersiz SKU için maliyet aranacak.")
        
        if progress_callback:
            progress_callback({
                'message': f'🔍 {total_skus} ürün için maliyet verileri taranıyor...',
                'progress': 20
            })

        # ThreadPoolExecutor ile paralel çekim
        # Sentos API rate limitine dikkat etmek için worker sayısını makul tutuyoruz
        max_workers = 5 
        
        processed_count = 0
        
        def fetch_sku(sku):
            try:
                # Eğer bu SKU daha önce (başka bir varyant sorgusuyla) bulunduysa atla
                if sku in cost_map:
                    return
                
                product = self.sentos_api.get_product_by_sku(sku)
                
                # Fallback 1: SKU ile bulunamadıysa Barkod ile ara
                if not product:
                    product = self.sentos_api.get_product_by_barcode(sku)
                
                # Fallback 2: İsim ile ara (Eğer isim haritasında varsa)
                if not product and sku in sku_name_map:
                    name = sku_name_map[sku]
                    # İsim boş değilse ara
                    if name and len(name) > 3:
                        product = self.sentos_api.get_product_by_name(name)
                
                # Fallback 3: Model Kodu ile Ara (YENİ)
                if not product:
                    # Model kodunu SKU'dan veya İsimden çıkarmaya çalış
                    model_code = None
                    
                    # 1. SKU'dan çıkar (Örn: BYK-24Y-303080-M51-R15 -> 303080)
                    # Genellikle 6 haneli sayı, tire veya boşlukla çevrili olabilir
                    match = re.search(r'[- ](\d{6})[- ]', sku)
                    if not match:
                         # Belki SKU direkt model kodudur veya tire ile bitiyordur
                         match = re.search(r'[- ]?(\d{6})[- ]?', sku)
                    
                    if match:
                        model_code = match.group(1)
                    
                    # 2. İsimden çıkar (Örn: ... Bluz 303080 -> 303080)
                    if not model_code and sku in sku_name_map:
                        name = sku_name_map[sku]
                        # İsim sonunda veya içinde 6 haneli sayı
                        match = re.search(r'\b(\d{6})\b', name)
                        if match:
                            model_code = match.group(1)
                    
                    if model_code:
                        # logging.info(f"SKU {sku} için Model Kodu denenecek: {model_code}")
                        product = self.sentos_api.get_product_by_model_code(model_code)

                if not product:
                    logging.warning(f"SKU {sku} için ürün bulunamadı (SKU, Barkod, İsim ve Model Kodu denendi).")
                    return
                
                # Debug: Ürün verisini logla
                # logging.info(f"SKU {sku} Raw Data: {product}")
                
                # Ana ürün maliyeti
                main_sku = str(product.get('sku', '')).strip()
                main_barcode = str(product.get('barcode', '')).strip()
                
                # Fiyat Parse Etme Fonksiyonu
                def parse_price(val):
                    if val is None: return 0.0
                    try:
                        # String ise temizle
                        if isinstance(val, str):
                            val = val.replace(',', '.')
                            # Birden fazla nokta varsa (örn: 1.234.56) sonuncusu hariç hepsini kaldır
                            if val.count('.') > 1:
                                parts = val.split('.')
                                val = "".join(parts[:-1]) + "." + parts[-1]
                        return float(val)
                    except:
                        return 0.0

                price = parse_price(product.get('purchase_price') or product.get('AlisFiyati'))
                
                # Aranan SKU'yu da kesinlikle map'e ekle (Eşleşme garantisi için)
                cost_map[sku] = price
                
                if main_sku:
                    cost_map[main_sku] = price
                    logging.info(f"SKU {main_sku} Maliyet: {price}")
                if main_barcode:
                    cost_map[main_barcode] = price
                
                # Varyantların maliyetleri (Bir SKU sorgusu tüm varyantları getirebilir)
                for v in product.get('variants', []):
                    v_sku = str(v.get('sku', '')).strip()
                    v_barcode = str(v.get('barcode', '')).strip()
                    v_price = parse_price(v.get('purchase_price') or v.get('AlisFiyati'))
                    
                    # Varyant fiyatı 0 ise ana ürün fiyatını kullan
                    final_price = v_price if v_price > 0 else price
                    if v_sku:
                        cost_map[v_sku] = final_price
                    if v_barcode:
                        cost_map[v_barcode] = final_price
                        # logging.info(f"Varyant SKU {v_sku} Maliyet: {final_price}")
                        
            except Exception as e:
                logging.warning(f"SKU {sku} maliyeti çekilirken hata: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Future'ları oluştur
            future_to_sku = {executor.submit(fetch_sku, sku): sku for sku in sku_list}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_sku)):
                processed_count += 1
                if progress_callback and processed_count % 5 == 0:
                    progress = 20 + int((processed_count / total_skus) * 40) # 20% ile 60% arası
                    progress_callback({
                        'message': f'🔍 Maliyetler çekiliyor... ({processed_count}/{total_skus})',
                        'progress': progress
                    })
        
        logging.info(f"Maliyet taraması tamamlandı. {len(cost_map)} adet SKU için maliyet bulundu.")
        return cost_map

    def analyze_sales_data(self, start_date=None, end_date=None, marketplace=None, 
                          progress_callback=None):
        """
        Satış verilerini çeker ve detaylı analiz yapar
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD)
            end_date: Bitiş tarihi (YYYY-MM-DD)
            marketplace: Pazar yeri filtresi
            progress_callback: İlerleme callback fonksiyonu
            
        Returns:
            dict: Detaylı analiz sonuçları
        """
        
        if progress_callback:
            progress_callback({
                'message': '📦 Siparişler çekiliyor...',
                'progress': 0
            })
        
        # 1. Önce Siparişleri Çek
        all_orders = self.sentos_api.get_all_sales_orders(
            start_date=start_date,
            end_date=end_date,
            marketplace=marketplace,
            progress_callback=progress_callback
        )
        
        logging.info(f"Toplam {len(all_orders)} sipariş çekildi")
        
        # 2. Siparişlerdeki Benzersiz SKU'ları ve İsimleri Belirle
        sku_name_map = {}
        for order in all_orders:
            items = (
                order.get('lines') or
                order.get('items') or 
                order.get('orderItems') or 
                order.get('products') or 
                []
            )
            for item in items:
                sku = (
                    item.get('sku') or
                    item.get('barcode') or
                    item.get('productCode') or 
                    ''
                )
                sku = str(sku).strip()
                
                name = (
                    item.get('name') or
                    item.get('invoice_name') or
                    item.get('productName') or 
                    item.get('title') or 
                    ''
                )
                
                if sku:
                    # Eğer isim varsa ve daha önce eklenmemişse veya daha uzunsa güncelle
                    if sku not in sku_name_map or (name and len(name) > len(sku_name_map[sku])):
                        sku_name_map[sku] = name
        
        # 3. Sadece Bu SKU'lar İçin Maliyetleri Çek
        cost_map = self._fetch_costs_for_skus(sku_name_map, progress_callback)
        
        if progress_callback:
            progress_callback({
                'message': '📈 Veriler analiz ediliyor...',
                'progress': 60
            })
        
        # 4. Analiz yap
        analysis = self._analyze_orders(all_orders, cost_map, progress_callback)
        
        if progress_callback:
            progress_callback({
                'message': '✅ Analiz tamamlandı!',
                'progress': 100
            })
        
        return analysis
    
    def _analyze_orders(self, orders, cost_map, progress_callback=None):
        """
        Sipariş listesini detaylı analiz eder
        """
        
        # Veri yapıları
        summary = {
            'total_orders': 0,
            'gross_quantity': 0,
            'gross_revenue': 0,
            'return_quantity': 0,
            'return_amount': 0,
            'net_quantity': 0,
            'net_revenue': 0,
            'total_cost': 0,
            'gross_profit': 0,
            'profit_margin': 0
        }
        
        by_marketplace = defaultdict(lambda: {
            'order_count': 0,
            'gross_quantity': 0,
            'gross_revenue': 0,
            'return_quantity': 0,
            'return_amount': 0,
            'net_quantity': 0,
            'net_revenue': 0,
            'total_cost': 0,
            'gross_profit': 0
        })
        
        by_date = defaultdict(lambda: {
            'order_count': 0,
            'gross_quantity': 0,
            'gross_revenue': 0,
            'return_quantity': 0,
            'return_amount': 0,
            'net_quantity': 0,
            'net_revenue': 0
        })
        
        by_product = defaultdict(lambda: {
            'product_name': '',
            'sku': '',
            'quantity_sold': 0,
            'quantity_returned': 0,
            'net_quantity': 0,
            'gross_revenue': 0,
            'return_amount': 0,
            'net_revenue': 0,
            'unit_cost': 0,
            'total_cost': 0,
            'gross_profit': 0,
            'profit_margin': 0
        })
        
        returns_data = {
            'total_returns': 0,
            'return_rate': 0,
            'top_returned_products': []
        }
        
        # Siparişleri işle
        total = len(orders)
        for idx, order in enumerate(orders):
            if progress_callback and idx % 100 == 0:
                progress_callback({
                    'message': f'📈 Sipariş {idx + 1}/{total} analiz ediliyor...',
                    'progress': 60 + int((idx / total) * 40)
                })
            
            self._process_order(
                order, 
                cost_map,
                summary, 
                by_marketplace, 
                by_date, 
                by_product
            )
        
        # İade oranını hesapla
        if summary['gross_quantity'] > 0:
            returns_data['total_returns'] = summary['return_quantity']
            returns_data['return_rate'] = (summary['return_quantity'] / summary['gross_quantity']) * 100
        
        # En çok iade alan ürünleri bul
        products_with_returns = [
            {
                'product_name': data['product_name'],
                'sku': data['sku'],
                'return_quantity': data['quantity_returned'],
                'return_rate': (data['quantity_returned'] / data['quantity_sold'] * 100) if data['quantity_sold'] > 0 else 0
            }
            for data in by_product.values()
            if data['quantity_returned'] > 0
        ]
        returns_data['top_returned_products'] = sorted(
            products_with_returns, 
            key=lambda x: x['return_quantity'], 
            reverse=True
        )[:20]
        
        # Net değerleri hesapla
        summary['net_quantity'] = summary['gross_quantity'] - summary['return_quantity']
        summary['net_revenue'] = summary['gross_revenue'] - summary['return_amount']
        summary['gross_profit'] = summary['net_revenue'] - summary['total_cost']
        
        # Kargo Gideri ve Net Kar Hesaplama (Sipariş başı 85 TL)
        shipping_cost_per_order = 85.0
        summary['total_shipping_cost'] = summary['total_orders'] * shipping_cost_per_order
        summary['net_profit_real'] = summary['gross_profit'] - summary['total_shipping_cost']
        
        if summary['net_revenue'] > 0:
            summary['profit_margin'] = (summary['gross_profit'] / summary['net_revenue']) * 100
            summary['net_profit_margin'] = (summary['net_profit_real'] / summary['net_revenue']) * 100
        else:
            summary['profit_margin'] = 0
            summary['net_profit_margin'] = 0
        
        # Pazar yeri bazında net hesaplamalar
        for mp_data in by_marketplace.values():
            mp_data['net_quantity'] = mp_data['gross_quantity'] - mp_data['return_quantity']
            mp_data['net_revenue'] = mp_data['gross_revenue'] - mp_data['return_amount']
            mp_data['gross_profit'] = mp_data['net_revenue'] - mp_data['total_cost']
            
            # Pazar yeri bazlı kargo ve net kar
            mp_data['total_shipping_cost'] = mp_data['order_count'] * shipping_cost_per_order
            mp_data['net_profit_real'] = mp_data['gross_profit'] - mp_data['total_shipping_cost']
            
            if mp_data['net_revenue'] > 0:
                mp_data['profit_margin'] = (mp_data['gross_profit'] / mp_data['net_revenue']) * 100
                mp_data['net_profit_margin'] = (mp_data['net_profit_real'] / mp_data['net_revenue']) * 100
            else:
                mp_data['profit_margin'] = 0
                mp_data['net_profit_margin'] = 0
        
        # Tarih bazında net hesaplamalar
        for date_data in by_date.values():
            date_data['net_quantity'] = date_data['gross_quantity'] - date_data['return_quantity']
            date_data['net_revenue'] = date_data['gross_revenue'] - date_data['return_amount']
        
        # Ürün bazında karlılık hesapla
        for product_data in by_product.values():
            product_data['net_quantity'] = product_data['quantity_sold'] - product_data['quantity_returned']
            product_data['net_revenue'] = product_data['gross_revenue'] - product_data['return_amount']
            product_data['gross_profit'] = product_data['net_revenue'] - product_data['total_cost']
            if product_data['net_revenue'] > 0:
                product_data['profit_margin'] = (product_data['gross_profit'] / product_data['net_revenue']) * 100
        
        # Karlılık özeti
        profitability = {
            'total_cost': summary['total_cost'],
            'gross_profit': summary['gross_profit'],
            'profit_margin': summary['profit_margin'],
            'top_profitable_products': self._get_top_profitable_products(by_product, top_n=20),
            'low_margin_products': self._get_low_margin_products(by_product, threshold=10, top_n=20)
        }
        
        return {
            'summary': summary,
            'by_marketplace': dict(by_marketplace),
            'by_date': dict(sorted(by_date.items())),
            'by_product': dict(by_product),
            'returns': returns_data,
            'profitability': profitability
        }
    
    def _process_order(self, order, cost_map, summary, by_marketplace, by_date, by_product):
        """Tek bir siparişi işler ve istatistiklere ekler"""
        
        # Temel bilgiler
        order_status = order.get('status', order.get('orderStatus', 'UNKNOWN'))
        
        marketplace = (
            order.get('source') or
            order.get('shop') or
            order.get('marketplace') or 
            order.get('marketPlace') or 
            order.get('channel') or 
            order.get('salesChannel') or
            'UNKNOWN'
        )
        marketplace = str(marketplace) if marketplace else 'UNKNOWN'
        
        order_date = (
            order.get('order_date') or
            order.get('created_at') or
            order.get('createdDate') or 
            order.get('orderDate') or 
            order.get('date') or
            ''
        )
        order_date = str(order_date) if order_date else ''
        if order_date and len(order_date) >= 10:
            order_date = order_date[:10]
        else:
            order_date = 'UNKNOWN'
        
        # İade/İptal Kontrolü
        is_cancelled_order = (order_status == 6)
        
        # Sipariş sayısı
        summary['total_orders'] += 1
        by_marketplace[marketplace]['order_count'] += 1
        by_date[order_date]['order_count'] += 1
        
        # Sipariş kalemleri
        items = (
            order.get('lines') or
            order.get('items') or 
            order.get('orderItems') or 
            order.get('products') or 
            []
        )
        
        for item in items:
            item_status = item.get('status', 'UNKNOWN')
            
            try:
                # Miktar
                quantity_raw = (
                    item.get('quantity') or
                    item.get('qty') or 
                    item.get('amount') or 
                    0
                )
                quantity = int(float(quantity_raw)) if quantity_raw else 0
                
                # İade kontrolü
                item_status_str = str(item_status).lower() if item_status else ''
                is_return_item = is_cancelled_order or (item_status_str == 'rejected')
                
                # Birim fiyat
                unit_price_raw = (
                    item.get('price') or
                    item.get('unitPrice') or 
                    item.get('salePrice') or 
                    0
                )
                unit_price = float(unit_price_raw) if unit_price_raw else 0.0
                
                # Toplam fiyat
                total_price_raw = (
                    item.get('amount') or
                    item.get('totalPrice') or 
                    item.get('total') or 
                    None
                )
                if total_price_raw is not None:
                    item_total = float(total_price_raw)
                else:
                    item_total = quantity * unit_price
                
                # SKU ve Ürün Adı
                sku = (
                    item.get('sku') or
                    item.get('barcode') or
                    item.get('productCode') or 
                    ''
                )
                sku = str(sku).strip()
                
                product_name = (
                    item.get('name') or
                    item.get('invoice_name') or
                    item.get('productName') or 
                    item.get('title') or 
                    'Bilinmeyen Ürün'
                )
                
                # Maliyet Bulma (Cost Map'ten)
                unit_cost = cost_map.get(sku, 0.0)
                # KDV Ekleme (+%10)
                unit_cost = unit_cost * 1.10
                total_cost = unit_cost * quantity
                
            except (ValueError, TypeError) as e:
                logging.warning(f"Item verisi işlenirken hata: {e}, Item: {item}")
                quantity = 0
                unit_price = 0.0
                item_total = 0.0
                unit_cost = 0.0
                total_cost = 0.0
                sku = ''
                product_name = 'Hatalı Veri'
            
            product_key = f"{sku}_{product_name}" if sku else product_name
            
            if not by_product[product_key]['product_name']:
                by_product[product_key]['product_name'] = product_name
                by_product[product_key]['sku'] = sku
                by_product[product_key]['unit_cost'] = unit_cost
            
            # HER ZAMAN BRÜT'E EKLE
            summary['gross_quantity'] += quantity
            summary['gross_revenue'] += item_total
            summary['total_cost'] += total_cost
            
            by_marketplace[marketplace]['gross_quantity'] += quantity
            by_marketplace[marketplace]['gross_revenue'] += item_total
            by_marketplace[marketplace]['total_cost'] += total_cost
            
            by_date[order_date]['gross_quantity'] += quantity
            by_date[order_date]['gross_revenue'] += item_total
            
            by_product[product_key]['quantity_sold'] += quantity
            by_product[product_key]['gross_revenue'] += item_total
            by_product[product_key]['total_cost'] += total_cost
            
            # İADE İSE
            if is_return_item:
                summary['return_quantity'] += quantity
                summary['return_amount'] += item_total
                
                by_marketplace[marketplace]['return_quantity'] += quantity
                by_marketplace[marketplace]['return_amount'] += item_total
                
                by_date[order_date]['return_quantity'] += quantity
                by_date[order_date]['return_amount'] += item_total
                
                by_product[product_key]['quantity_returned'] += quantity
                by_product[product_key]['return_amount'] += item_total
    
    def _get_top_profitable_products(self, by_product, top_n=20):
        """En karlı ürünleri döndürür"""
        products = [
            {
                'product_name': data['product_name'],
                'sku': data['sku'],
                'net_quantity': data['net_quantity'],
                'net_revenue': data['net_revenue'],
                'total_cost': data['total_cost'],
                'gross_profit': data['gross_profit'],
                'profit_margin': data['profit_margin']
            }
            for data in by_product.values()
            if data['net_quantity'] > 0
        ]
        
        return sorted(products, key=lambda x: x['gross_profit'], reverse=True)[:top_n]
    
    def _get_low_margin_products(self, by_product, threshold=10, top_n=20):
        """Düşük marjlı ürünleri döndürür"""
        products = [
            {
                'product_name': data['product_name'],
                'sku': data['sku'],
                'net_quantity': data['net_quantity'],
                'net_revenue': data['net_revenue'],
                'total_cost': data['total_cost'],
                'gross_profit': data['gross_profit'],
                'profit_margin': data['profit_margin']
            }
            for data in by_product.values()
            if data['net_quantity'] > 0 and data['profit_margin'] < threshold
        ]
        
        return sorted(products, key=lambda x: x['profit_margin'])[:top_n]
