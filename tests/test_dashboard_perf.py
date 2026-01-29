import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from connectors.shopify_api import ShopifyAPI

class TestDashboardStats:
    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    @patch('connectors.shopify_api.datetime')
    def test_get_dashboard_stats_calculation(self, mock_datetime, mock_execute_graphql):
        # Fix "Now" to be a Wednesday: 2023-10-25 (Wed).
        # Week start (Mon): 2023-10-23
        # Month start: 2023-10-01

        fixed_now = datetime(2023, 10, 25, 12, 0, 0) # Noon
        # We need to mock 'now' but allow other datetime methods to work if needed.
        # Since 'from datetime import datetime' is used in the module, patching it there is tricky if not careful.
        # But 'connectors.shopify_api.datetime' patch should work for the imported name.

        mock_datetime.now.return_value = fixed_now
        # Side effect: if the code calls datetime.strptime or similar on the mock, it might fail if we don't configure it.
        # But the code only calls datetime.now().
        # However, timedelta usage might be affected if we are not careful? No, timedelta is separate.

        api = ShopifyAPI("test.myshopify.com", "token")

        # Metadata Response
        metadata_resp = {
            "shop": {"name": "Test Shop", "currencyCode": "USD"},
            "products": {"edges": [{"node": {"id": "1"}}], "pageInfo": {"hasNextPage": False}}
        }

        # Orders Response
        # 1. Today (2023-10-25T10:00:00) -> $100
        # 2. Yesterday (2023-10-24T10:00:00) -> $200 (This Week)
        # 3. Monday (2023-10-23T10:00:00) -> $300 (This Week)
        # 4. Last Sunday (2023-10-22T10:00:00) -> $400 (Last Week - NOT This Week, but This Month)
        # 5. Last Month (2023-09-30T10:00:00) -> $500 (Not This Month)

        orders_resp = {
            "orders": {
                "edges": [
                    {"node": {"id": "1", "createdAt": "2023-10-25T10:00:00", "totalPriceSet": {"shopMoney": {"amount": "100.0"}}}},
                    {"node": {"id": "2", "createdAt": "2023-10-24T10:00:00", "totalPriceSet": {"shopMoney": {"amount": "200.0"}}}},
                    {"node": {"id": "3", "createdAt": "2023-10-23T10:00:00", "totalPriceSet": {"shopMoney": {"amount": "300.0"}}}},
                    {"node": {"id": "4", "createdAt": "2023-10-22T10:00:00", "totalPriceSet": {"shopMoney": {"amount": "400.0"}}}},
                    {"node": {"id": "5", "createdAt": "2023-09-30T10:00:00", "totalPriceSet": {"shopMoney": {"amount": "500.0"}}}},
                ]
            }
        }

        mock_execute_graphql.side_effect = [metadata_resp, orders_resp]

        stats = api.get_dashboard_stats()

        # Assertions
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 1

        # Today: Only order 1 ($100)
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0

        # This Week: Orders 1, 2, 3 ($100 + $200 + $300 = $600)
        # Order 4 is Sunday (22nd), Week start is Monday (23rd).
        assert stats['orders_this_week'] == 3
        assert stats['revenue_this_week'] == 600.0

        # This Month: Orders 1, 2, 3, 4 ($100+$200+$300+$400 = $1000)
        # Order 5 is Sep 30.
        assert stats['orders_this_month'] == 4
        assert stats['revenue_this_month'] == 1000.0

        # Verify Query Calls
        assert mock_execute_graphql.call_count == 2

        # Verify 2nd Query args (Orders)
        # min_date should be 2023-10-01 (Month Start) because week start is 2023-10-23.
        call_args = mock_execute_graphql.call_args_list[1]
        query_sent = call_args[0][0]
        assert "created_at:>='2023-10-01T00:00:00'" in query_sent

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
