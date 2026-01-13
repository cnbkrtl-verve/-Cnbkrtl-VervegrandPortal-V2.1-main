
import unittest
from unittest.mock import MagicMock, patch
from connectors.shopify_api import ShopifyAPI

class TestShopifyPerf(unittest.TestCase):
    def test_get_variant_ids_by_skus_batching(self):
        """
        Verifies that get_variant_ids_by_skus batches requests correctly.
        """
        # Create API instance
        api = ShopifyAPI("test.myshopify.com", "token")

        # Mock execute_graphql
        # We need it to return a valid structure so the method proceeds
        api.execute_graphql = MagicMock(return_value={
            "products": {
                "edges": []
            }
        })

        # Mock time.sleep to avoid waiting during test
        with patch('time.sleep') as mock_sleep:
            # Generate 20 SKUs
            skus = [f"SKU-{i}" for i in range(20)]

            # Call the method
            api.get_variant_ids_by_skus(skus)

            # Check call count
            # Current implementation: batch_size=2 -> 20/2 = 10 calls
            # Optimized implementation: batch_size=10 -> 20/10 = 2 calls
            call_count = api.execute_graphql.call_count
            print(f"\n[PerfTest] execute_graphql called {call_count} times for {len(skus)} SKUs.")

            # Also check sleep calls
            sleep_count = mock_sleep.call_count
            print(f"[PerfTest] time.sleep called {sleep_count} times.")

            # Assertions
            self.assertEqual(call_count, 2, "Expected 2 calls for 20 SKUs with batch_size=10")
            self.assertEqual(sleep_count, 0, "Expected 0 sleep calls (removed manual sleep)")

if __name__ == '__main__':
    unittest.main()
