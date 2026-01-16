import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI
from datetime import datetime, timedelta

class TestShopifyDashboard:
    """Tests for get_dashboard_stats optimization"""

    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_consolidated_query(self, mock_execute):
        """
        Verify that get_dashboard_stats uses a single consolidated query
        instead of multiple sequential queries.
        """
        # Setup mock return value for the consolidated query
        mock_execute.return_value = {
            "shop": {
                "name": "Test Shop",
                "email": "test@example.com",
                "primaryDomain": {"host": "test.myshopify.com"},
                "currencyCode": "USD",
                "plan": {"displayName": "Basic"},
                "billingAddress": {"country": "US"}
            },
            "products_count": {
                "pageInfo": {"hasNextPage": False},
                "edges": [{"node": {"id": "1"}}, {"node": {"id": "2"}}]
            },
            # customers_count removed as it was unused
            "orders_today": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "name": "#1001",
                            "createdAt": datetime.now().isoformat(),
                            "totalPriceSet": {"shopMoney": {"amount": "50.00", "currencyCode": "USD"}},
                            "customer": {"firstName": "John", "lastName": "Doe"}
                        }
                    }
                ]
            },
            "orders_week": {
                "edges": [
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "50.00"}}}},
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}}
                ]
            },
            "orders_month": {
                "edges": [
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "50.00"}}}},
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "200.00"}}}}
                ]
            }
        }

        api = ShopifyAPI("test-store", "token")
        stats = api.get_dashboard_stats()

        # Assertions
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 2
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 50.0
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 350.0

        # Verify that execute_graphql was called exactly ONCE
        # This will FAIL with the current implementation (which calls it ~6 times)
        assert mock_execute.call_count == 1

        # Verify query structure contains aliases
        call_args = mock_execute.call_args
        query = call_args[0][0]
        assert "products_count: products" in query
        assert "orders_today: orders" in query
        assert "orders_week: orders" in query
        assert "orders_month: orders" in query
