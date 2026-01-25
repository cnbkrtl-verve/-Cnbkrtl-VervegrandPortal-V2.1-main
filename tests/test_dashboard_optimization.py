import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI
from datetime import datetime, timedelta

class TestDashboardOptimization:

    @patch('connectors.shopify_api.datetime')
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_consolidated_query(self, mock_execute, mock_datetime):
        # Setup fixed time: 2024-05-22 12:00:00 (Wednesday)
        # Week starts on Monday, 2024-05-20
        # Month starts on 2024-05-01
        fixed_now = datetime(2024, 5, 22, 12, 0, 0)

        # Mock datetime.now() to return fixed_now
        # We need to ensure we don't break other datetime methods if used (like strptime/isoformat on instances)
        # But patching 'connectors.shopify_api.datetime' replaces the class/module.
        # We need to make sure the mocked class behaves like datetime for other things if needed.
        # Simplest is to set the return value of now.
        mock_datetime.now.return_value = fixed_now
        # Also need to support datetime(year, month, ...) constructor if called?
        # No, usually code calls datetime.now().
        # But if code uses datetime.strptime, it might be an issue if mock_datetime is a MagicMock.
        # Let's use a side_effect or wraps if necessary, but typically this works for .now() calls.
        # However, to be safe, let's allow it to act as the real datetime for other attributes?
        # A better way is to create a subclass of datetime and patch with that,
        # but datetime is immutable/C-extension.
        # Let's proceed with simple mock and see if it fails on other methods.

        # Mock response from GraphQL
        # Note: We simulate a consolidated response structure.
        # Even if the code is not yet optimized, this test asserts expectations for the OPTIMIZED version.
        mock_execute.return_value = {
            "shop": {
                "name": "Test Shop",
                "currencyCode": "USD",
                "plan": {"displayName": "Basic"},
                "billingAddress": {"country": "US"}
            },
            "products": {
                "pageInfo": {"hasNextPage": False},
                "edges": [{"node": {"id": "1"}}, {"node": {"id": "2"}}]
            },
            "orders": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "name": "#1001",
                            "createdAt": "2024-05-22T10:00:00", # Today
                            "totalPriceSet": {"shopMoney": {"amount": "100.0", "currencyCode": "USD"}},
                            "customer": {"firstName": "John", "lastName": "Doe"}
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/Order/2",
                            "name": "#1002",
                            "createdAt": "2024-05-21T10:00:00", # Yesterday (This Week)
                            "totalPriceSet": {"shopMoney": {"amount": "50.0", "currencyCode": "USD"}},
                            "customer": {"firstName": "Jane", "lastName": "Doe"}
                        }
                    },
                    {
                        "node": {
                            "id": "gid://shopify/Order/3",
                            "name": "#1003",
                            "createdAt": "2024-05-10T10:00:00", # This Month (Not Week)
                            "totalPriceSet": {"shopMoney": {"amount": "20.0", "currencyCode": "USD"}},
                            "customer": {"firstName": "Bob", "lastName": "Smith"}
                        }
                    }
                ]
            }
        }

        api = ShopifyAPI("test-store.myshopify.com", "token")
        stats = api.get_dashboard_stats()

        # 1. Verify consolidated call
        # We expect exactly 1 call to execute_graphql
        assert mock_execute.call_count == 1, f"Expected 1 call, got {mock_execute.call_count}"

        # 2. Verify Query Variables contain correct min_date filter
        # Min date should be start of month: 2024-05-01
        call_args = mock_execute.call_args
        query_arg = call_args[0][0]

        # We expect the query to include certain fields
        assert "shop {" in query_arg
        assert "products(" in query_arg
        assert "orders(" in query_arg
        # Expect filter for 2024-05-01
        assert "created_at:>='2024-05-01" in query_arg

        # 3. Verify Stats Calculation

        # Today: Only Order #1 (100.0)
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0

        # This Week: Order #1 (100) + Order #2 (50) = 150.0. Count 2.
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0

        # This Month: All 3 orders. Count 3. Total 170.0.
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 170.0

        # Product Count
        assert stats['products_count'] == 2

        # Recent Orders
        assert len(stats['recent_orders']) == 3
        assert stats['recent_orders'][0]['name'] == "#1001"
