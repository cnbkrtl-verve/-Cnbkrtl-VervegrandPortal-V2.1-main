# tests/test_shopify_api.py
"""
ShopifyAPI için temel unit testler
CI/CD pipeline ile otomatik çalışır
"""

import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI


class TestShopifyAPIInit:
    """ShopifyAPI başlatma testleri"""
    
    def test_init_with_valid_credentials(self):
        """✅ Geçerli kimlik bilgileriyle başlatılabilmeli"""
        api = ShopifyAPI("test-store.myshopify.com", "test_token_12345")
        
        assert api.store_url == "https://test-store.myshopify.com"
        assert api.access_token == "test_token_12345"
        assert api.api_version == "2024-10"
    
    def test_init_with_http_url(self):
        """✅ HTTP URL'i olduğu gibi kalmalı (HTTPS zorlanmaz)"""
        api = ShopifyAPI("http://test-store.myshopify.com", "token")
        
        assert api.store_url == "http://test-store.myshopify.com"
    
    def test_init_without_http(self):
        """✅ URL başında http yoksa otomatik eklenmeli"""
        api = ShopifyAPI("test-store.myshopify.com", "token")
        
        assert api.store_url == "https://test-store.myshopify.com"
    
    def test_init_with_empty_store_url(self):
        """❌ Boş mağaza URL'i hata vermeli"""
        with pytest.raises(ValueError, match="Shopify Mağaza URL'si boş olamaz"):
            ShopifyAPI("", "token")
    
    def test_init_with_empty_token(self):
        """❌ Boş token hata vermeli"""
        with pytest.raises(ValueError, match="Shopify Erişim Token'ı boş olamaz"):
            ShopifyAPI("test-store.myshopify.com", "")
    
    def test_graphql_url_formation(self):
        """✅ GraphQL URL doğru oluşturulmalı"""
        api = ShopifyAPI("test-store.myshopify.com", "token")
        
        expected_url = "https://test-store.myshopify.com/admin/api/2024-10/graphql.json"
        assert api.graphql_url == expected_url


class TestRateLimiter:
    """Rate limiting mekanizması testleri"""
    
    def test_rate_limiter_initialization(self):
        """✅ Rate limiter başlangıç değerleri doğru olmalı"""
        api = ShopifyAPI("test-store.myshopify.com", "token")
        
        assert api.max_requests_per_minute == 30
        assert api.burst_tokens == 5
        assert api.current_tokens == 5
    
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limit_wait_with_tokens(self, mock_time, mock_sleep):
        """✅ Token varsa bekleme olmamalı"""
        mock_time.return_value = 1000.0
        
        api = ShopifyAPI("test-store.myshopify.com", "token")
        api.current_tokens = 5
        api.last_request_time = 999.0
        
        api._rate_limit_wait()
        
        # Token tüketilmeli
        assert api.current_tokens < 5
        # Ama sleep çağrılmamalı (yeterli token var)
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limit_wait_without_tokens(self, mock_time, mock_sleep):
        """✅ Token yoksa bekleme yapılmalı"""
        mock_time.return_value = 1000.0
        
        api = ShopifyAPI("test-store.myshopify.com", "token")
        api.current_tokens = 0
        api.last_request_time = 1000.0
        
        api._rate_limit_wait()
        
        # Sleep çağrılmalı
        mock_sleep.assert_called()


class TestGraphQLExecution:
    """GraphQL sorgu çalıştırma testleri"""
    
    @patch('requests.post')
    def test_execute_graphql_success(self, mock_post):
        """✅ Başarılı GraphQL sorgusu"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "products": {
                    "edges": [
                        {"node": {"id": "gid://shopify/Product/123"}}
                    ]
                }
            }
        }
        mock_post.return_value = mock_response
        
        api = ShopifyAPI("test-store.myshopify.com", "token")
        query = "query { products(first: 1) { edges { node { id } } } }"
        
        result = api.execute_graphql(query)
        
        assert "products" in result
        assert len(result["products"]["edges"]) == 1
    
    @patch('requests.post')
    def test_execute_graphql_with_errors(self, mock_post):
        """❌ GraphQL hatası exception fırlatmalı"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [
                {
                    "message": "Field 'invalidField' doesn't exist",
                    "locations": [{"line": 2, "column": 5}]
                }
            ]
        }
        mock_post.return_value = mock_response
        
        api = ShopifyAPI("test-store.myshopify.com", "token")
        query = "query { invalidField }"
        
        with pytest.raises(Exception, match="GraphQL Error"):
            api.execute_graphql(query)
    
    @patch('requests.post')
    @patch('time.sleep')
    def test_execute_graphql_with_throttle_retry(self, mock_sleep, mock_post):
        """✅ Throttle hatası varsa retry yapmalı"""
        # İlk istek: throttled
        mock_response_throttled = Mock()
        mock_response_throttled.status_code = 200
        mock_response_throttled.json.return_value = {
            "errors": [
                {
                    "message": "Throttled",
                    "extensions": {"code": "THROTTLED"}
                }
            ]
        }
        
        # İkinci istek: başarılı
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "data": {"shop": {"name": "Test Shop"}}
        }
        
        mock_post.side_effect = [mock_response_throttled, mock_response_success]
        
        api = ShopifyAPI("test-store.myshopify.com", "token")
        query = "query { shop { name } }"
        
        result = api.execute_graphql(query)
        
        # Retry yapıldığını doğrula
        assert mock_post.call_count == 2
        assert mock_sleep.called
        assert result["shop"]["name"] == "Test Shop"


class TestDashboardStats:
    """Dashboard istatistikleri testleri"""

    @patch('connectors.shopify_api.datetime')
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats(self, mock_execute, mock_datetime):
        """✅ Dashboard istatistikleri doğru hesaplanmalı (optimize edilmiş 2 sorgu)"""
        from datetime import datetime, timedelta

        # Fix date: 2023-10-15 (Sunday)
        # Week start (Monday): 2023-10-09
        # Month start: 2023-10-01
        fixed_now = datetime(2023, 10, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_now

        # Mock responses
        metadata_response = {
            "shop": {"name": "Test Shop", "currencyCode": "USD"},
            "products": {"edges": [{"node": {"id": "1"}}]*10, "pageInfo": {"hasNextPage": False}},
            "customers": {"edges": [{"node": {"id": "1"}}]*5}
        }

        # Orders:
        # 1. Today (2023-10-15) - ID: 1, Price: 100
        # 2. Week (2023-10-10) - ID: 2, Price: 50
        # 3. Month (2023-10-02) - ID: 3, Price: 20
        # 4. Old (2023-09-30) - Should not be in response if query filter works, but let's test Python filter
        #    Wait, query filter logic is outside Python control (it's string).
        #    But Python loop filters again?
        #    Python loop filters: >= month_iso (2023-10-01).
        #    So 2023-09-30 should be excluded from "month" stats even if returned.

        orders_response = {
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "1",
                            "createdAt": "2023-10-15T10:00:00",
                            "totalPriceSet": {"shopMoney": {"amount": "100.0", "currencyCode": "USD"}}
                        }
                    },
                    {
                        "node": {
                            "id": "2",
                            "createdAt": "2023-10-10T10:00:00",
                            "totalPriceSet": {"shopMoney": {"amount": "50.0", "currencyCode": "USD"}}
                        }
                    },
                    {
                        "node": {
                            "id": "3",
                            "createdAt": "2023-10-02T10:00:00",
                            "totalPriceSet": {"shopMoney": {"amount": "20.0", "currencyCode": "USD"}}
                        }
                    }
                ]
            }
        }

        mock_execute.side_effect = [metadata_response, orders_response]

        api = ShopifyAPI("test-store.myshopify.com", "token")
        stats = api.get_dashboard_stats()

        assert mock_execute.call_count == 2
        assert stats['products_count'] == 10
        assert stats['customers_count'] == 5

        # Verify stats
        # Today: ID 1
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0

        # Week: ID 1, 2 (10-15, 10-10 >= 10-09)
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0

        # Month: ID 1, 2, 3 (All >= 10-01)
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 170.0


# ============================================
# Test çalıştırma talimatları
# ============================================
"""
Bu testleri çalıştırmak için:

1. pytest kurulumu:
   pip install pytest pytest-cov pytest-mock

2. Tüm testleri çalıştır:
   pytest tests/ -v

3. Coverage raporu ile:
   pytest tests/ --cov=connectors --cov-report=html

4. Sadece bu dosyayı test et:
   pytest tests/test_shopify_api.py -v

5. Sadece bir test class'ını çalıştır:
   pytest tests/test_shopify_api.py::TestShopifyAPIInit -v

6. Sadece bir test fonksiyonunu çalıştır:
   pytest tests/test_shopify_api.py::TestShopifyAPIInit::test_init_with_valid_credentials -v
"""

if __name__ == "__main__":
    # Doğrudan çalıştırma (pytest kullanılmazsa)
    pytest.main([__file__, "-v", "--tb=short"])
