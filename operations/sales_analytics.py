# operations/sales_analytics.py
"""
Sentos Satış Analizi Modülü
E-Ticaret kanalından satış verilerini çeker ve detaylı analiz yapar
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict

class SalesAnalytics:
    """Satış verilerini analiz eden sınıf"""
    
    def __init__(self, sentos_api):
        """
        Args:
            sentos_api: SentosAPI instance
        """
        self.sentos_api = sentos_api
    
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
                'message': '📊 Satış verileri çekiliyor...',
                'progress': 0
            })
        
        # Tüm siparişleri çek
        all_orders = self.sentos_api.get_all_sales_orders(
            start_date=start_date,
            end_date=end_date,
            marketplace=marketplace,
            progress_callback=progress_callback
        )
        
        logging.info(f"Toplam {len(all_orders)} sipariş çekildi")
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG: Toplam {len(all_orders)} sipariş çekildi")
        print(f"{'='*60}")
        
        if all_orders:
            first_order = all_orders[0]
            print(f"\n📦 İLK SİPARİŞ YAPISI:")
            print(f"   Keys: {list(first_order.keys())}")
            print(f"   ID: {first_order.get('id')}")
            print(f"   Order Number: {first_order.get('order_id', first_order.get('order_code'))}")
            print(f"   Marketplace: {first_order.get('source', first_order.get('shop'))}")
            
            # Items kontrolü - Sentos'ta 'lines' field'ı kullanılıyor
            items = first_order.get('lines', first_order.get('items', first_order.get('orderItems', first_order.get('products', []))))
            print(f"\n📋 LINES/ITEMS KONTROLÜ:")
            print(f"   Lines field var mı? {'lines' in first_order}")
            print(f"   Lines değeri var mı? {items is not None}")
            print(f"   Lines uzunluk: {len(items) if items else 0}")
            
            if items:
                print(f"   ✅ LINES DOLU!")
                print(f"   İlk line keys: {list(items[0].keys())}")
                print(f"   İlk line örneği: {items[0]}")
            else:
                print(f"   ⚠️ LINES BOŞ!")
                print(f"   Sipariş tam yapısı: {first_order}")
            
            print(f"{'='*60}\n")
            logging.info(f"İlk sipariş örneği: {all_orders[0]}")
        else:
            print(f"\n❌ HİÇ SİPARİŞ ÇEKİLEMEDİ!")
            print(f"{'='*60}\n")
        
        if progress_callback:
            progress_callback({
                'message': '📈 Veriler analiz ediliyor...',
                'progress': 50
            })
        
        # Analiz yap
        analysis = self._analyze_orders(all_orders, progress_callback)
        
        if progress_callback:
            progress_callback({
                'message': '✅ Analiz tamamlandı!',
                'progress': 100
            })
        
        return analysis
    
    def _analyze_orders(self, orders, progress_callback=None):
        """
        Sipariş listesini detaylı analiz eder
        
        Returns:
            dict: {
                'summary': {...},           # Özet istatistikler
                'by_marketplace': {...},    # Pazar yeri bazında
                'by_date': {...},          # Tarih bazında
                'by_product': {...},       # Ürün bazında
                'returns': {...},          # İade analizi
                'profitability': {...}     # Karlılık analizi
            }
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
        
        # Status kodlarını topla (debug için)
        status_codes = set()
        status_counts = defaultdict(int)  # Her status'tan kaç tane var
        item_statuses = set()  # Tüm item status'ları topla
        shopify_item_statuses = set()  # 🔍 SHOPIFY'A ÖZEL item status'ları
        
        # Siparişleri işle
        total = len(orders)
        for idx, order in enumerate(orders):
            if progress_callback and idx % 100 == 0:
                progress_callback({
                    'message': f'📈 Sipariş {idx + 1}/{total} analiz ediliyor...',
                    'progress': 50 + int((idx / total) * 50)
                })
            
            self._process_order(
                order, 
                summary, 
                by_marketplace, 
                by_date, 
                by_product,
                status_codes,  # Status kodlarını topla
                status_counts,  # Status sayılarını topla
                item_statuses,  # Item status'ları topla
                shopify_item_statuses  # 🔍 Shopify item status'ları topla
            )
        
        # Status kodlarını göster
        print(f"\n{'='*60}")
        print(f"📊 TÜM STATUS KODLARI:")
        print(f"   Bulunan status kodları: {sorted(status_codes)}")
        print(f"   Toplam farklı status: {len(status_codes)}")
        print(f"\n📈 STATUS DAĞILIMI:")
        for status in sorted(status_counts.keys()):
            count = status_counts[status]
            percentage = (count / len(orders)) * 100
            print(f"   Status {status}: {count:4d} sipariş ({percentage:5.1f}%)")
        print(f"\n🏷️ ITEM STATUS KODLARI:")
        print(f"   Bulunan item status'ları: {sorted(item_statuses)}")
        print(f"   Toplam farklı item status: {len(item_statuses)}")
        print(f"\n🛍️ SHOPIFY ITEM STATUS KODLARI:")
        print(f"   Shopify'a özel item status'ları: {sorted(shopify_item_statuses)}")
        print(f"   Shopify'da toplam farklı item status: {len(shopify_item_statuses)}")
        if not shopify_item_statuses:
            print(f"   ⚠️ UYARI: Shopify siparişlerinde HIÇBIR item status bulunamadı!")
        print(f"{'='*60}\n")
        
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
        
        if summary['net_revenue'] > 0:
            summary['profit_margin'] = (summary['gross_profit'] / summary['net_revenue']) * 100
        
        # Pazar yeri bazında net hesaplamalar
        for mp_data in by_marketplace.values():
            mp_data['net_quantity'] = mp_data['gross_quantity'] - mp_data['return_quantity']
            mp_data['net_revenue'] = mp_data['gross_revenue'] - mp_data['return_amount']
            mp_data['gross_profit'] = mp_data['net_revenue'] - mp_data['total_cost']
            if mp_data['net_revenue'] > 0:
                mp_data['profit_margin'] = (mp_data['gross_profit'] / mp_data['net_revenue']) * 100
        
        # Tarih bazında net hesaplamalar
        for date_data in by_date.values():
            date_data['net_quantity'] = date_data['gross_quantity'] - date_data['return_quantity']
            date_data['net_revenue'] = date_data['gross_revenue'] - date_data['return_amount']
        
        # ✅ NET HESAPLAMALAR TAMAMLANDI - ŞİMDİ YAZDIRALIM
        print(f"\n{'='*60}")
        print(f"💰 MARKETPLACE CİRO DETAYLARI (NET HESAPLAMALAR SONRASI):")
        print(f"{'='*60}")
        for mp, data in by_marketplace.items():
            print(f"\n🏪 {mp}:")
            print(f"   Sipariş Sayısı: {data['order_count']}")
            print(f"   Brüt Adet: {data['gross_quantity']}")
            print(f"   İade Adet: {data['return_quantity']}")
            print(f"   Net Adet: {data['net_quantity']}")  # ← ŞİMDİ DOĞRU DEĞER!
            print(f"   Brüt Ciro: ₺{data['gross_revenue']:,.2f}")
            print(f"   İade Tutarı: ₺{data['return_amount']:,.2f}")
            print(f"   Net Ciro: ₺{data['net_revenue']:,.2f}")  # ← ŞİMDİ DOĞRU DEĞER!
        print(f"\n{'='*60}\n")
        
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
    
    def _process_order(self, order, summary, by_marketplace, by_date, by_product, status_codes, status_counts, item_statuses, shopify_item_statuses):
        """Tek bir siparişi işler ve istatistiklere ekler"""
        
        # Debug: İlk siparişin yapısını logla
        if summary['total_orders'] == 0:
            logging.info(f"Örnek sipariş yapısı: {order}")
            items_check = order.get('items', order.get('orderItems', order.get('products', [])))
            logging.info(f"Items field: {items_check}")
            logging.info(f"Items sayısı: {len(items_check) if items_check else 0}")
        
        # Temel bilgiler - Sentos API field isimleri
        order_status = order.get('status', order.get('orderStatus', 'UNKNOWN'))
        # Status string'e çevir (eğer int ise)
        order_status_str = str(order_status) if order_status else 'UNKNOWN'
        
        # Status kodunu kaydet (debug için)
        status_codes.add(order_status)
        status_counts[order_status] += 1
        
        # Marketplace için farklı olası field isimlerini kontrol et
        # Sentos'ta 'source' field'ı kullanılıyor!
        marketplace = (
            order.get('source') or          # Sentos gerçek field
            order.get('shop') or            # Alternatif
            order.get('marketplace') or 
            order.get('marketPlace') or 
            order.get('channel') or 
            order.get('salesChannel') or
            'UNKNOWN'
        )
        # Marketplace string'e çevir
        marketplace = str(marketplace) if marketplace else 'UNKNOWN'
        
        # Tarih için farklı olası field isimlerini kontrol et
        # Sentos'ta 'order_date' field'ı kullanılıyor!
        order_date = (
            order.get('order_date') or      # Sentos gerçek field
            order.get('created_at') or      # Alternatif
            order.get('createdDate') or 
            order.get('orderDate') or 
            order.get('date') or
            ''
        )
        # Tarih string'e çevir ve formatla
        order_date = str(order_date) if order_date else ''
        if order_date and len(order_date) >= 10:
            order_date = order_date[:10]  # YYYY-MM-DD formatına çevir
        else:
            order_date = 'UNKNOWN'
        
        # İade mi kontrol et
        # NOT: Sentos API dökümantasyonuna göre:
        # Status 1 = Onay Bekliyor
        # Status 2 = ONAYLANDI (İade DEĞİL!)
        # Status 3 = Tedarik Sürecinde
        # Status 4 = Hazırlanıyor
        # Status 5 = Kargoya Verildi
        # Status 6 = İptal/İade Edildi ← SENTOS RAPORUNDA "İPTAL/İADE" OLARAK GÖSTERİLİYOR
        # Status 99 = Teslim Edildi
        # 
        # İADELER/İPTALLER:
        # - Status 6 = Tüm sipariş iptal/iade
        # - Item status "rejected" = Kısmi iade (bazı ürünler)
        
        # Status 6 siparişleri İADE olarak işle
        is_cancelled_order = (order_status == 6)
        
        # Sipariş sayısı
        summary['total_orders'] += 1
        by_marketplace[marketplace]['order_count'] += 1
        by_date[order_date]['order_count'] += 1
        
        # Sipariş kalemleri - Farklı olası field isimlerini kontrol et
        # Sentos'ta 'lines' field'ı kullanılıyor!
        items = (
            order.get('lines') or           # Sentos gerçek field
            order.get('items') or 
            order.get('orderItems') or 
            order.get('products') or 
            []
        )
        
        for item in items:
            # Item status'u kaydet
            item_status = item.get('status', 'UNKNOWN')
            if item_status:
                item_statuses.add(str(item_status))
                
                # 🔍 SHOPIFY SİPARİŞİYSE ÖZEL OLARAK KAYDET
                if 'shopify' in marketplace.lower():
                    shopify_item_statuses.add(str(item_status))
            
            try:
                # Miktar - güvenli dönüşüm
                quantity_raw = (
                    item.get('quantity') or     # Sentos gerçek field
                    item.get('qty') or 
                    item.get('amount') or 
                    0
                )
                quantity = int(float(quantity_raw)) if quantity_raw else 0
                
                # İade kontrolü:
                # 1. Status 6 = Tüm sipariş iptal/iade (ciroya dahil değil)
                # 2. Item status "rejected" = Kısmi iade (bu ürün iade edilmiş)
                item_status_str = str(item_status).lower() if item_status else ''
                is_return_item = is_cancelled_order or (item_status_str == 'rejected')
                
                # Birim fiyat - güvenli dönüşüm
                unit_price_raw = (
                    item.get('price') or        # Sentos gerçek field
                    item.get('unitPrice') or 
                    item.get('salePrice') or 
                    0
                )
                unit_price = float(unit_price_raw) if unit_price_raw else 0.0
                
                # Toplam fiyat - güvenli dönüşüm
                total_price_raw = (
                    item.get('amount') or       # Sentos gerçek field (total amount)
                    item.get('totalPrice') or 
                    item.get('total') or 
                    None
                )
                if total_price_raw is not None:
                    item_total = float(total_price_raw)
                else:
                    item_total = quantity * unit_price
                
                # Maliyet bilgisi (eğer varsa) - güvenli dönüşüm
                # Sentos'ta maliyet bilgisi yok gibi görünüyor, 0 olarak bırak
                unit_cost_raw = (
                    item.get('cost') or
                    item.get('unitCost') or 
                    item.get('buyPrice') or 
                    0
                )
                unit_cost = float(unit_cost_raw) if unit_cost_raw else 0.0
                total_cost = unit_cost * quantity
                
            except (ValueError, TypeError) as e:
                logging.warning(f"Item verisi işlenirken hata: {e}, Item: {item}")
                # Hata durumunda sıfır değerler kullan
                quantity = 0
                unit_price = 0.0
                item_total = 0.0
                unit_cost = 0.0
                total_cost = 0.0
            
            # Ürün bilgileri
            product_name = (
                item.get('name') or             # Sentos gerçek field
                item.get('invoice_name') or     # Alternatif
                item.get('productName') or 
                item.get('title') or 
                'Bilinmeyen Ürün'
            )
            
            sku = (
                item.get('sku') or              # Sentos gerçek field
                item.get('barcode') or          # Alternatif
                item.get('productCode') or 
                ''
            )
            
            product_key = f"{sku}_{product_name}" if sku else product_name
            
            if not by_product[product_key]['product_name']:
                by_product[product_key]['product_name'] = product_name
                by_product[product_key]['sku'] = sku
                by_product[product_key]['unit_cost'] = unit_cost
            
            # HER ZAMAN BRÜT'E EKLE (iade/iptal dahil tüm siparişler)
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
            
            # EĞER İADE/İPTAL İSE, İADE'YE DE EKLE
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
