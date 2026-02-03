import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from connectors.shopify_api import ShopifyAPI

class TestShopifyAPIDashboard:
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_consolidated_query(self, mock_execute_graphql):
        """
        Tests that get_dashboard_stats uses a single query and processes data correctly.
        """
        api = ShopifyAPI("test.myshopify.com", "token")

        # Prepare mock data
        # We use UTC times for the mock response as Shopify returns UTC
        # Note: In the implementation, we compare against system local time.
        # For the test to be robust without patching datetime.now(), we construct
        # timestamps that we know will fall into "Today" relative to the system time.

        real_now = datetime.now()
        # Today in UTC (approx)
        date_today = real_now

        mock_response = {
            "shop": {
                "name": "Test Shop",
                "currencyCode": "USD"
            },
            "products": {
                "edges": [{"node": {"id": "1"}}, {"node": {"id": "2"}}], # 2 products
                "pageInfo": {"hasNextPage": False}
            },
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "name": "#1001",
                            # Use system time for creation to ensure it matches "Today" check
                            "createdAt": date_today.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
                            "customer": {"firstName": "John", "lastName": "Doe"}
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/Order/2",
                            "name": "#1002",
                            "createdAt": date_today.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "totalPriceSet": {"shopMoney": {"amount": "50.00", "currencyCode": "USD"}},
                            "customer": {"firstName": "Jane", "lastName": "Doe"}
                        }
                    }
                ]
            }
        }

        mock_execute_graphql.return_value = mock_response

        stats = api.get_dashboard_stats()

        # Verify execute_graphql called once
        assert mock_execute_graphql.call_count == 1

        # Verify Stats
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 2

        # Verify Orders Stats (Today)
        # We put 2 orders for today.
        assert stats['orders_today'] == 2
        assert stats['revenue_today'] == 150.00

        # Verify Week/Month (should include Today's orders)
        assert stats['orders_this_week'] >= 2
        assert stats['revenue_this_week'] >= 150.00
        assert stats['orders_this_month'] >= 2
        assert stats['revenue_this_month'] >= 150.00

        # Verify Recent Orders
        assert len(stats['recent_orders']) == 2
        assert stats['recent_orders'][0]['name'] == "#1001"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
