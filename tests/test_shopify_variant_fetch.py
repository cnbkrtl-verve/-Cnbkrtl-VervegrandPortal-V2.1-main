
import pytest
from unittest.mock import MagicMock, patch
from connectors.shopify_api import ShopifyAPI

class TestShopifyVariantFetch:

    @patch('connectors.shopify_api.time.sleep')
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_variant_ids_by_skus_performance(self, mock_execute_graphql, mock_sleep):
        """
        Test that get_variant_ids_by_skus handles batching correctly.
        Optimized implementation should use batch size 20 and no explicit sleeps.
        """
        api = ShopifyAPI("test-store", "token")

        # Create a list of 20 SKUs
        skus = [f"SKU-{i}" for i in range(20)]

        # Mock response structure
        def side_effect(query, variables):
            # Verify dynamic 'first' variable matches batch size (20)
            assert variables['first'] == 20

            return {
                "products": {
                    "edges": []
                }
            }

        mock_execute_graphql.side_effect = side_effect

        api.get_variant_ids_by_skus(skus)

        # Verify optimized behavior
        # Batch size 20 -> 1 call for 20 SKUs
        assert mock_execute_graphql.call_count == 1

        # Sleep should be 0 (explicit sleeps removed)
        assert mock_sleep.call_count == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
