
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from connectors.shopify_api import ShopifyAPI

class TestShopifyDashboardStats:

    @pytest.fixture
    def api(self):
        return ShopifyAPI("test-store.myshopify.com", "test_token")

    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_call_count(self, mock_execute_graphql, api):
        """
        Verify that get_dashboard_stats makes exactly 2 GraphQL calls
        and returns the expected data structure.
        """
        # Mock responses based on query content
        def side_effect(query, variables=None):
            if "shop {" in query and "products(first: 250)" in query:
                # Combined Metadata Query
                return {
                    "shop": {"name": "Test Shop", "currencyCode": "USD"},
                    "products": {
                        "pageInfo": {"hasNextPage": False},
                        "edges": [{"node": {"id": "prod1"}} for _ in range(10)]
                    }
                }
            elif "orders(first: 250" in query and "sortKey: CREATED_AT" in query:
                # Combined Orders Query
                # Return dummy orders created "today"
                return {
                    "orders": {
                        "edges": [
                            {
                                "node": {
                                    "id": "order1",
                                    "name": "#1001",
                                    "createdAt": datetime.now().isoformat(),
                                    "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
                                    "customer": {"firstName": "John", "lastName": "Doe"}
                                }
                            }
                        ]
                    }
                }
            return {}

        mock_execute_graphql.side_effect = side_effect

        # Run the method
        stats = api.get_dashboard_stats()

        # Verify result structure
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 10
        # Check if orders were processed
        # The mock returns 1 order created "now".
        # It should count as today, this week, and this month.
        assert stats['orders_today'] == 1
        assert stats['orders_this_week'] == 1
        assert stats['orders_this_month'] == 1
        assert stats['revenue_today'] == 100.0

        # Verify optimization: Should be exactly 2 calls
        assert mock_execute_graphql.call_count == 2
