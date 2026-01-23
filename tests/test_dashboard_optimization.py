
import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI
from datetime import datetime, timedelta

class TestDashboardOptimization:
    def test_get_dashboard_stats_optimized(self):
        """
        Tests that get_dashboard_stats now makes a SINGLE API call.
        """
        api = ShopifyAPI("test.myshopify.com", "token")

        # Mock execute_graphql
        api.execute_graphql = Mock()

        # Combined response
        combined_response = {
            "shop": {"name": "Test Shop", "currencyCode": "USD"},
            "products": {"edges": [{"node": {"id": "1"}} for _ in range(10)], "pageInfo": {"hasNextPage": False}},
            "ordersToday": {
                "edges": [
                    {
                        "node": {
                            "id": "1",
                            "name": "#1001",
                            "createdAt": "2023-10-27T10:00:00Z",
                            "totalPriceSet": {"shopMoney": {"amount": "50.00", "currencyCode": "USD"}},
                            "customer": {"firstName": "John", "lastName": "Doe"}
                        }
                    }
                ]
            },
            "ordersWeek": {
                "edges": [
                    {"node": {"id": "1", "totalPriceSet": {"shopMoney": {"amount": "50.00"}}}},
                    {"node": {"id": "2", "totalPriceSet": {"shopMoney": {"amount": "100.00"}}}}
                ]
            },
            "ordersMonth": {
                "edges": [
                    {"node": {"id": "1", "totalPriceSet": {"shopMoney": {"amount": "50.00"}}}},
                    {"node": {"id": "2", "totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                    {"node": {"id": "3", "totalPriceSet": {"shopMoney": {"amount": "75.00"}}}}
                ]
            }
        }

        api.execute_graphql.return_value = combined_response

        stats = api.get_dashboard_stats()

        # Assertions
        assert api.execute_graphql.call_count == 1  # Verify reduced from 6 to 1

        # Check call args to verify variables
        call_args = api.execute_graphql.call_args
        assert call_args is not None
        # query is args[0], variables is args[1] if positional, or in kwargs
        # method signature: execute_graphql(self, query, variables=None)

        args, kwargs = call_args
        if len(args) > 1:
            variables = args[1]
        else:
            variables = kwargs.get('variables', {})

        assert 'todayQuery' in variables
        assert 'weekQuery' in variables
        assert 'monthQuery' in variables

        # Verify stats parsing
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 10
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 50.0
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 225.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
