#!/usr/bin/env python3
"""
Shopify OrderCreateOrderInput Schema Helper
Doğru field formatlarını sağlar
"""

import logging

def create_order_input_builder():
    """
    OrderCreateOrderInput için safe builder
    Shopify GraphQL schema'sına uygun format
    """
    
    def build_mailing_address(address_data):
        """MailingAddressInput formatında adres oluşturur"""
        if not address_data:
            return None
            
        # name field'ını firstName/lastName'e ayır
        full_name = address_data.get('name', '')
        first_name = address_data.get('firstName', '')
        last_name = address_data.get('lastName', '')
        
        if full_name and not first_name:
            name_parts = full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Null değerleri temizle
        address = {}
        if first_name:
            address["firstName"] = first_name
        if last_name:
            address["lastName"] = last_name
        if address_data.get('company'):  # ✅ ŞİRKET BİLGİSİ
            address["company"] = address_data.get('company')
        if address_data.get('address1'):
            address["address1"] = address_data.get('address1')
        if address_data.get('address2'):
            address["address2"] = address_data.get('address2')
        if address_data.get('city'):
            address["city"] = address_data.get('city')
        if address_data.get('province'):
            address["province"] = address_data.get('province')
        if address_data.get('zip'):
            address["zip"] = address_data.get('zip')
        if address_data.get('country'):
            address["country"] = address_data.get('country')
        if address_data.get('phone'):
            address["phone"] = address_data.get('phone')
            
        return address if address else None
    
    def build_transaction(transaction_data):
        """OrderCreateOrderTransactionInput formatında transaction oluşturur"""
        if not transaction_data:
            return None
        
        # Amount'u al - hem eski format (amount) hem yeni format (amountSet.shopMoney.amount) destekle
        amount = None
        currency = transaction_data.get('currency', 'TRY')
        
        # Yeni format: amountSet.shopMoney.amount
        if 'amountSet' in transaction_data:
            amount_set = transaction_data.get('amountSet', {})
            shop_money = amount_set.get('shopMoney', {})
            amount = shop_money.get('amount')
            currency = shop_money.get('currencyCode', currency)
        # Eski format: amount
        elif 'amount' in transaction_data:
            amount = transaction_data.get('amount')
        
        # ✅ Amount kontrolü - 0 veya None ise transaction oluşturma
        if not amount:
            logging.warning("Transaction amount boş veya 0, transaction oluşturulmadı")
            return None
        
        # String'e çevir ve validate et
        try:
            amount_float = float(str(amount).strip().replace(',', '.'))
            if amount_float <= 0:
                logging.warning(f"Transaction amount 0 veya negatif: {amount_float}, transaction oluşturulmadı")
                return None
        except (ValueError, TypeError) as e:
            logging.error(f"Transaction amount parse hatası: {amount} - {e}")
            return None
        
        transaction = {
            "gateway": transaction_data.get('gateway', 'manual'),
            "kind": transaction_data.get('kind', 'SALE'),
            "status": transaction_data.get('status', 'SUCCESS')
        }
        
        # amountSet formatı
        transaction["amountSet"] = {
            "shopMoney": {
                "amount": str(amount_float),  # Float'tan string'e güvenli çevrim
                "currencyCode": currency
            }
        }
        
        return transaction
    
    def build_line_item(line_item_data):
        """OrderCreateOrderLineItemInput formatında line item oluşturur"""
        if not line_item_data:
            return None
            
        line_item = {}
        
        if line_item_data.get('variantId'):
            line_item["variantId"] = line_item_data.get('variantId')
        
        # Quantity - güvenli dönüşüm
        if line_item_data.get('quantity'):
            try:
                quantity = int(line_item_data.get('quantity'))
                if quantity > 0:
                    line_item["quantity"] = quantity
            except (ValueError, TypeError):
                # Geçersiz quantity, line item'ı oluşturma
                return None
        
        # Price - priceSet formatında
        if line_item_data.get('price'):
            try:
                price = float(line_item_data.get('price'))
                if price > 0:
                    line_item["priceSet"] = {
                        "shopMoney": {
                            "amount": str(price),
                            "currencyCode": line_item_data.get('currency', 'TRY')
                        }
                    }
            except (ValueError, TypeError):
                # Geçersiz price, devam et ama priceSet ekleme
                pass
        
        # Custom Attributes (line item düzeyinde)
        custom_attrs = line_item_data.get('customAttributes')
        if custom_attrs:
            attrs = build_custom_attributes(custom_attrs)
            if attrs:
                line_item["customAttributes"] = attrs
            
        return line_item if line_item else None
    
    def build_tax_line(tax_line_data):
        """OrderCreateOrderTaxLineInput formatında tax line oluşturur"""
        if not tax_line_data:
            return None
        
        tax_line = {}
        
        # Tax title (örn: "KDV % 10 (Dahil)")
        if tax_line_data.get('title'):
            tax_line["title"] = tax_line_data.get('title')
        
        # Tax rate (örn: 0.1 = %10)
        if tax_line_data.get('rate') is not None:
            try:
                rate = float(tax_line_data.get('rate'))
                tax_line["rate"] = rate
            except (ValueError, TypeError):
                # Geçersiz rate, varsayılan 0.1 kullan
                tax_line["rate"] = 0.1
        
        # Tax price - priceSet formatında
        if tax_line_data.get('price'):
            try:
                price = float(tax_line_data.get('price'))
                if price >= 0:  # Vergi 0 olabilir
                    tax_line["priceSet"] = {
                        "shopMoney": {
                            "amount": str(price),
                            "currencyCode": tax_line_data.get('currency', 'TRY')
                        }
                    }
            except (ValueError, TypeError):
                # Geçersiz price
                pass
        
        return tax_line if tax_line else None
    
    def build_shipping_line(shipping_data):
        """OrderCreateOrderShippingLineInput formatında kargo bilgisi oluşturur"""
        if not shipping_data:
            return None
        
        shipping = {}
        
        # Kargo başlığı (örn: "MNG Kargo", "Aras Kargo")
        if shipping_data.get('title'):
            shipping["title"] = shipping_data.get('title')
        
        # Kargo kodu (opsiyonel)
        if shipping_data.get('code'):
            shipping["code"] = shipping_data.get('code')
        
        # Kargo ücreti - originalPriceSet veya priceSet
        price_set = shipping_data.get('originalPriceSet') or shipping_data.get('priceSet', {})
        shop_money = price_set.get('shopMoney', {})
        price = shop_money.get('amount')
        if price:
            try:
                price_float = float(price)
                if price_float >= 0:  # Ücretsiz kargo 0 olabilir
                    shipping["priceSet"] = {
                        "shopMoney": {
                            "amount": str(price_float),
                            "currencyCode": shop_money.get('currencyCode', 'TRY')
                        }
                    }
            except (ValueError, TypeError):
                # Geçersiz price
                pass
        
        return shipping if shipping else None
    
    def build_custom_attributes(attributes_data):
        """Özel alanları formatlar"""
        if not attributes_data:
            return None
        
        custom_attrs = []
        for attr in attributes_data:
            if isinstance(attr, dict) and attr.get('key') and attr.get('value'):
                custom_attrs.append({
                    "key": str(attr['key']),
                    "value": str(attr['value'])
                })
        
        return custom_attrs if custom_attrs else None
    
    def build_order_input(order_data):
        """Tam OrderCreateOrderInput oluşturur"""
        order_input = {}
        
        # Customer ID
        if order_data.get('customerId'):
            order_input["customerId"] = order_data.get('customerId')
        
        # Line Items
        line_items_data = order_data.get('lineItems', [])
        if line_items_data:
            line_items = []
            for item_data in line_items_data:
                item = build_line_item(item_data)
                if item:
                    line_items.append(item)
            if line_items:
                order_input["lineItems"] = line_items
        
        # Shipping Address
        shipping_address = build_mailing_address(order_data.get('shippingAddress'))
        if shipping_address:
            order_input["shippingAddress"] = shipping_address
        
        # Billing Address (opsiyonel)
        billing_address = build_mailing_address(order_data.get('billingAddress'))
        if billing_address:
            order_input["billingAddress"] = billing_address
        
        # Note
        if order_data.get('note'):
            order_input["note"] = order_data.get('note')
        
        # Transactions (opsiyonel - belirtilmezse Shopify otomatik hesaplar)
        transactions_data = order_data.get('transactions', [])
        if transactions_data:
            transactions = []
            for trans_data in transactions_data:
                trans = build_transaction(trans_data)
                if trans:
                    transactions.append(trans)
            if transactions:
                order_input["transactions"] = transactions
        # NOT: Transaction verilmezse Shopify line item'lardan toplam hesaplar
        
        # Email
        if order_data.get('email'):
            order_input["email"] = order_data.get('email')
        
        # Taxes Included (Fiyatlar vergi dahil mi?)
        # Türkiye'de genellikle fiyatlar KDV dahildir
        if order_data.get('taxesIncluded') is not None:
            order_input["taxesIncluded"] = order_data.get('taxesIncluded')
        
        # Tax Lines
        tax_lines_data = order_data.get('taxLines', [])
        if tax_lines_data:
            tax_lines = []
            for tax_data in tax_lines_data:
                tax = build_tax_line(tax_data)
                if tax:
                    tax_lines.append(tax)
            if tax_lines:
                order_input["taxLines"] = tax_lines
        
        # ❌ SHOPIFY KARGO LİMİTASYONU ❌
        # shippingLine OrderCreateOrderInput'ta DESTEKLENMIYOR!
        # Shopify API 2024-10'da orderCreate mutation shippingLine field'ını KABUL ETMİYOR
        # 
        # ÇÖZÜM SEÇENEKLERİ:
        # 1. DraftOrder API kullan (shippingLine destekler)
        # 2. Kargo ücretini custom line item olarak ekle
        # 3. Kargo ücretini nota ekle (şu an yapılıyor)
        #
        # Şu an için: Kargo bilgisi SADECE NOTA ekleniyor
        # shipping_line = order_data.get('shippingLine')
        # if shipping_line:
        #     shipping = build_shipping_line(shipping_line)
        #     if shipping:
        #         order_input["shippingLine"] = shipping  # ❌ HATA VERİR!
        
        # Tags (Etiketler)
        tags = order_data.get('tags')
        if tags:
            # Liste veya string olabilir
            if isinstance(tags, list):
                order_input["tags"] = ", ".join(str(t) for t in tags if t)
            elif isinstance(tags, str) and tags.strip():
                order_input["tags"] = tags
        
        # Custom Attributes (Özel alanlar)
        custom_attrs = order_data.get('customAttributes')
        if custom_attrs:
            attrs = build_custom_attributes(custom_attrs)
            if attrs:
                order_input["customAttributes"] = attrs
        
        return order_input
    
    return {
        'build_order_input': build_order_input,
        'build_mailing_address': build_mailing_address,
        'build_transaction': build_transaction,
        'build_line_item': build_line_item,
        'build_tax_line': build_tax_line,
        'build_shipping_line': build_shipping_line,
        'build_custom_attributes': build_custom_attributes
    }

def test_builder():
    """Builder'ı test eder"""
    builder = create_order_input_builder()
    
    # Test data
    test_data = {
        "customerId": "gid://shopify/Customer/123456789",
        "lineItems": [
            {
                "variantId": "gid://shopify/ProductVariant/987654321",
                "quantity": 2,
                "price": "29.99"
            }
        ],
        "shippingAddress": {
            "name": "John Doe",
            "address1": "123 Test St",
            "city": "Istanbul",
            "country": "Turkey",
            "phone": "+905551234567"
        },
        "note": "Test order",
        "transactions": [
            {
                "gateway": "manual",
                "amount": "59.98",
                "currency": "TRY"
            }
        ],
        "email": "test@example.com"
    }
    
    result = builder['build_order_input'](test_data)
    
    print("🧪 Test Result:")
    import json
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    print("🔧 Shopify OrderCreateOrderInput Builder Test")
    print("=" * 50)
    test_builder()