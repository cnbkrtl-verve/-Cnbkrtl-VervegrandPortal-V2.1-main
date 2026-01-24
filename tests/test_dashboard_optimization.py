import pytest
from unittest.mock import Mock, patch
from connectors.shopify_api import ShopifyAPI
import datetime

class TestDashboardOptimization:

    @patch('requests.post')
    def test_get_dashboard_stats_optimized(self, mock_post):
        """
        Verify that get_dashboard_stats now makes a SINGLE API call with consolidated query.
        """
        # Mock consolidated response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "shop": {"name": "Test Shop Optimized", "currencyCode": "USD"},
                "products": {"edges": [{"node": {"id": "1"}}], "pageInfo": {"hasNextPage": False}},
                "customers": {"edges": [{"node": {"id": "1"}}], "pageInfo": {"hasNextPage": False}},
                "ordersToday": {"edges": [
                    {"node": {
                        "id": "o1",
                        "name": "#1001",
                        "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
                        "customer": {"firstName": "John", "lastName": "Doe"}
                    }}
                ]},
                "ordersWeek": {"edges": [
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                    {"node": {"totalPriceSet": {"shopMoney": {"amount": "200.00"}}}}
                ]},
                "ordersMonth": {"edges": [
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "100.00"}}}},
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "200.00"}}}},
                     {"node": {"totalPriceSet": {"shopMoney": {"amount": "300.00"}}}}
                ]}
            }
        }

        mock_post.return_value = mock_response

        api = ShopifyAPI("test.myshopify.com", "token")

        with patch('time.sleep'):
            stats = api.get_dashboard_stats()

        # Verify call count
        # It should be EXACTLY 1 call now
        assert mock_post.call_count == 1

        # Verify stats are populated correctly
        assert stats['shop_info']['name'] == "Test Shop Optimized"
        assert stats['products_count'] == 1
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 300.0
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 600.0

        # Verify call arguments contain our aliased keys (basic check)
        call_args = mock_post.call_args
        request_json = call_args[1]['json']
        query = request_json['query']
        assert "ordersToday:" in query
        assert "ordersWeek:" in query
        assert "ordersMonth:" in query
