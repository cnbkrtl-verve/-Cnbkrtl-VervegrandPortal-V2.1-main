
import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI
from datetime import datetime, timedelta

class TestShopifyDashboardOptimization:
    """Tests for the optimized get_dashboard_stats method."""

    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_optimization(self, mock_execute_graphql):
        """
        Verifies that get_dashboard_stats performs a single GraphQL query
        and correctly parses the consolidated response.
        """
        # Setup mock response
        mock_response = {
            "shop": {
                "name": "Test Shop",
                "currencyCode": "USD",
                "plan": {"displayName": "Basic"},
                "billingAddress": {"country": "US"}
            },
            "products": {
                "edges": [{"node": {"id": "gid://shopify/Product/1"}}] * 10, # 10 products
                "pageInfo": {"hasNextPage": False}
            },
            "customers": {
                "edges": [{"node": {"id": "gid://shopify/Customer/1"}}],
                "pageInfo": {"hasNextPage": True}
            },
            "orders_today": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
                            "createdAt": "2023-10-27T10:00:00Z"
                        }
                    }
                ]
            },
            "orders_week": {
                "edges": [
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "50.00"}}}}
                ]
            },
            "orders_month": {
                "edges": [
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "50.00"}}}},
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "20.00"}}}}
                ]
            }
        }

        mock_execute_graphql.return_value = mock_response

        # Initialize API
        api = ShopifyAPI("test.myshopify.com", "token")

        # Call method
        stats = api.get_dashboard_stats()

        # Assertions

        # 1. Verify execute_graphql was called EXACTLY ONCE
        assert mock_execute_graphql.call_count == 1, "execute_graphql should be called exactly once"

        # 2. Verify Data Parsing
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 10

        # Check Orders Today
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0

        # Check Orders Week
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0

        # Check Orders Month
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 170.0

        # 3. Verify Query Structure contains aliases
        call_args = mock_execute_graphql.call_args
        query_arg = call_args[0][0] # First arg is query string

        assert "orders_today: orders" in query_arg
        assert "orders_week: orders" in query_arg
        assert "orders_month: orders" in query_arg
        assert "products(first: 250)" in query_arg

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
