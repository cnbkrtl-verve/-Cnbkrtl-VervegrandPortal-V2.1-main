
import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI

class TestGetVariantIds:
    """get_variant_ids_by_skus metodunun testleri"""

    @patch('requests.post')
    def test_get_variant_ids_optimization(self, mock_post):
        """✅ productVariants query'si kullanılmalı ve batch'leme doğru olmalı"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "productVariants": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/123",
                                "sku": "SKU-1",
                                "product": {"id": "gid://shopify/Product/100"}
                            }
                        },
                        {
                            "node": {
                                "id": "gid://shopify/ProductVariant/456",
                                "sku": "SKU-2",
                                "product": {"id": "gid://shopify/Product/200"}
                            }
                        }
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        api = ShopifyAPI("test-store.myshopify.com", "token")

        # 3 SKU gönder, batch size 50 olduğu için tek istek gitmeli
        skus = ["SKU-1", "SKU-2", "SKU-3"]
        result = api.get_variant_ids_by_skus(skus)

        # Sonuç kontrolü
        assert len(result) == 2
        assert result["SKU-1"]["variant_id"] == "gid://shopify/ProductVariant/123"
        assert result["SKU-1"]["product_id"] == "gid://shopify/Product/100"

        # Sorgu kontrolü - productVariants kök sorgusu kullanılmalı
        call_args = mock_post.call_args
        request_body = call_args[1]['json']
        query = request_body['query']

        assert "productVariants(first: 100, query: $query)" in query
        assert "sku:\"SKU-1\"" in request_body['variables']['query']

    @patch('requests.post')
    def test_get_variant_ids_large_batch(self, mock_post):
        """✅ Çoklu batch işlemleri doğru çalışmalı"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"productVariants": {"edges": []}}}
        mock_post.return_value = mock_response

        api = ShopifyAPI("test-store.myshopify.com", "token")

        # 60 SKU gönder, batch size 50 olduğu için 2 istek gitmeli
        skus = [f"SKU-{i}" for i in range(60)]
        api.get_variant_ids_by_skus(skus)

        assert mock_post.call_count == 2
