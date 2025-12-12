
import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI

class TestShopifyAPICaching:
    def test_get_locations_caching(self):
        """
        Tests that get_locations caches the result and does not call the API again.
        """
        api = ShopifyAPI("test.myshopify.com", "token")

        # Mock execute_graphql
        api.execute_graphql = Mock()
        api.execute_graphql.return_value = {
            "locations": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Location/1",
                            "name": "Warehouse",
                            "address": {"city": "New York", "country": "US"}
                        }
                    }
                ]
            }
        }

        # First call
        locations1 = api.get_locations()
        assert len(locations1) == 1
        assert locations1[0]['id'] == "gid://shopify/Location/1"
        assert api.execute_graphql.call_count == 1

        # Second call
        locations2 = api.get_locations()
        assert len(locations2) == 1
        assert locations2 == locations1
        # Assert execute_graphql was NOT called again
        assert api.execute_graphql.call_count == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
