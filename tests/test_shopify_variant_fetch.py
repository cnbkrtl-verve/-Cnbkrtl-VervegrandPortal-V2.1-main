
import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI

class TestShopifyVariantFetch:

    @pytest.fixture
    def api(self):
        return ShopifyAPI("test-store.myshopify.com", "test_token_12345")

    @patch('time.sleep')
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_variant_ids_by_skus_batching_optimized(self, mock_execute, mock_sleep, api):
        """
        Verifies the OPTIMIZED behavior:
        - Batch size is 10
        - NO unconditional sleeps
        """
        # Create 20 mock SKUs
        skus = [f"SKU_{i}" for i in range(20)]

        # Mock response structure
        mock_execute.return_value = {
            "products": {
                "edges": []
            }
        }

        # Call the method
        api.get_variant_ids_by_skus(skus)

        # ASSERTIONS FOR OPTIMIZED BEHAVIOR
        # 20 SKUs / 10 batch size = 2 calls
        assert mock_execute.call_count == 2

        # Verify sleep is NOT called (or at least not the big 3s sleep)
        # We might have small sleeps elsewhere, but definitely not 3s
        # Let's check call_args_list to be sure no 3s sleep
        for call in mock_sleep.call_args_list:
            args, _ = call
            assert args[0] != 3, f"Sleep called with {args[0]} seconds, likely unoptimized!"

        # In fact, we expect 0 calls now since we removed the sleep entirely
        assert mock_sleep.call_count == 0
