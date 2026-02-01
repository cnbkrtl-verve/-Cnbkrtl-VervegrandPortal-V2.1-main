
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from connectors.shopify_api import ShopifyAPI

# Helper to create an order object structure
def create_mock_order(id, created_at, amount):
    return {
        "node": {
            "id": id,
            "name": f"Order {id}",
            "createdAt": created_at,
            "totalPriceSet": {
                "shopMoney": {
                    "amount": str(amount),
                    "currencyCode": "TRY"
                }
            },
            "customer": {
                "firstName": "Test",
                "lastName": "User"
            }
        }
    }

class TestDashboardStats:

    @patch('connectors.shopify_api.datetime')
    def test_get_dashboard_stats_optimized(self, mock_datetime):
        # Setup fixed "Now": 2023-10-15 (Sunday)
        # Week start (Monday): 2023-10-09
        # Month start: 2023-10-01
        fixed_now = datetime(2023, 10, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_now
        # Side effect for other datetime calls (like replace, strptime) to work if needed
        # But datetime is a class, so we need to be careful.
        # It's better to mock the module or use freezegun if available.
        # Since I can't install packages, I'll use a custom mock.

        # Actually, simpler: just mock the dates used in logic if possible.
        # But logic calls datetime.now().
        # Let's use a class mock for datetime.
        mock_datetime.now.return_value = fixed_now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.strptime = datetime.strptime

        # Test Data
        orders_data = [
            create_mock_order("1", "2023-10-15T10:00:00", 100.0), # Today
            create_mock_order("2", "2023-10-14T10:00:00", 50.0),  # Yesterday (This Week)
            create_mock_order("3", "2023-10-10T10:00:00", 20.0),  # Tuesday (This Week)
            create_mock_order("4", "2023-10-05T10:00:00", 200.0), # Last Week (This Month)
        ]

        # Mock API
        api = ShopifyAPI("test.myshopify.com", "token")

        # Mock execute_graphql
        def side_effect(query, variables=None):
            if "shop {" in query and "products(" in query:
                # Combined metadata query
                return {
                    "shop": {
                        "name": "Test Shop",
                        "currencyCode": "TRY",
                        "plan": {"displayName": "Basic"},
                        "primaryDomain": {"host": "test.myshopify.com"},
                        "email": "test@example.com",
                        "billingAddress": {"country": "TR"}
                    },
                    "products": {
                        "edges": [{"node": {"id": "1"}} for _ in range(10)], # 10 products
                        "pageInfo": {"hasNextPage": False}
                    }
                }
            elif "orders(" in query:
                # Consolidated orders query
                # Verify sortKey and reverse are present (optimization requirement)
                if "sortKey: CREATED_AT" not in query or "reverse: true" not in query:
                    raise ValueError("Orders query must use sortKey: CREATED_AT and reverse: true")

                return {
                    "orders": {
                        "edges": orders_data
                    }
                }
            return {}

        api.execute_graphql = Mock(side_effect=side_effect)

        # Execute
        stats = api.get_dashboard_stats()

        # Verify
        # 1. Requests count: Should be 2 (metadata + orders)
        # We might call execute_graphql more if logic is different, but ideally 2.
        assert api.execute_graphql.call_count == 2

        # 2. Metadata
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 10

        # 3. Orders Stats
        # Today: Order 1 (100.0)
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0

        # Week: Orders 1, 2, 3 (100 + 50 + 20 = 170.0)
        assert stats['orders_this_week'] == 3
        assert stats['revenue_this_week'] == 170.0

        # Month: Orders 1, 2, 3, 4 (100 + 50 + 20 + 200 = 370.0)
        assert stats['orders_this_month'] == 4
        assert stats['revenue_this_month'] == 370.0

        # Recent orders (should be top 5 from TODAY, as per original logic)
        # Only Order 1 is from today (2023-10-15)
        assert len(stats['recent_orders']) == 1
        assert stats['recent_orders'][0]['id'] == "1"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
