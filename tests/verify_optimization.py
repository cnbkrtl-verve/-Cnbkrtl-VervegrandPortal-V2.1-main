
import unittest
from unittest.mock import MagicMock, patch
import json
from connectors.shopify_api import ShopifyAPI

class TestOptimization(unittest.TestCase):
    def setUp(self):
        self.api = ShopifyAPI("test.myshopify.com", "token")
        self.api.execute_graphql = MagicMock()
        # Mock response structure
        self.api.execute_graphql.return_value = {
            "products": {
                "edges": []
            }
        }

    @patch('time.sleep')
    def test_get_variant_ids_by_skus_batch_size(self, mock_sleep):
        # Create 45 SKUs to test batching (should be 3 batches: 20, 20, 5)
        skus = [f"SKU-{i}" for i in range(45)]

        self.api.get_variant_ids_by_skus(skus)

        # Verify call count
        self.assertEqual(self.api.execute_graphql.call_count, 3)

        # Verify first call arguments
        args, kwargs = self.api.execute_graphql.call_args_list[0]
        query = args[0]
        variables = args[1]

        # Check if 'first' variable is set to 50 (buffer for duplicates)
        self.assertEqual(variables['first'], 50)

        # Verify sleep was NOT called (except potentially by execute_graphql which we mocked, so checking global sleep calls)
        # Since we mocked execute_graphql, any sleep inside get_variant_ids_by_skus would be caught
        mock_sleep.assert_not_called()

        print("✅ get_variant_ids_by_skus verified: Batch size 20, first=50 param, no sleep.")

if __name__ == '__main__':
    unittest.main()
