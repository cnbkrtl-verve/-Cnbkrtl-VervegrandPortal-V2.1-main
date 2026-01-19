from unittest.mock import patch
from connectors.shopify_api import ShopifyAPI


class TestShopifyDashboard:

    @patch('connectors.shopify_api.ShopifyAPI.execute_graphql')
    def test_get_dashboard_stats_optimized(self, mock_execute):
        """
        Verifies that get_dashboard_stats makes a single GraphQL call
        and correctly parses the response.
        """
        api = ShopifyAPI("test.myshopify.com", "token")

        # Mock response mimicking the consolidated query result
        mock_response = {
            "shop": {
                "name": "Test Shop",
                "email": "test@example.com",
                "currencyCode": "USD",
                "plan": {"displayName": "Basic"},
                "primaryDomain": {"host": "test.myshopify.com"},
            },
            "products": {
                # 10 products
                "edges": [{"node": {"id": "gid://shopify/Product/1"}}] * 10,
                "pageInfo": {"hasNextPage": False}
            },
            "ordersToday": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/Order/1",
                            "name": "#1001",
                            "createdAt": "2023-10-27T10:00:00Z",
                            "totalPriceSet": {
                                "shopMoney": {
                                    "amount": "100.00",
                                    "currencyCode": "USD"
                                }
                            },
                            "customer": {
                                "firstName": "John",
                                "lastName": "Doe"
                            }
                        }
                    }
                ]
            },
            "ordersWeek": {
                "edges": [
                    {
                        "node": {
                            "totalPriceSet": {
                                "shopMoney": {"amount": "50.00"}
                            }
                        }
                    },
                    {
                        "node": {
                            "totalPriceSet": {
                                "shopMoney": {"amount": "100.00"}
                            }
                        }
                    }
                ]
            },
            "ordersMonth": {
                "edges": [
                    {
                        "node": {
                            "totalPriceSet": {
                                "shopMoney": {"amount": "50.00"}
                            }
                        }
                    },
                    {
                        "node": {
                            "totalPriceSet": {
                                "shopMoney": {"amount": "100.00"}
                            }
                        }
                    },
                    {
                        "node": {
                            "totalPriceSet": {
                                "shopMoney": {"amount": "200.00"}
                            }
                        }
                    }
                ]
            }
        }

        mock_execute.return_value = mock_response

        # Run the method
        stats = api.get_dashboard_stats()

        # Assert execute_graphql was called exactly ONCE
        assert mock_execute.call_count == 1

        # Verify arguments contained expected aliases
        call_args = mock_execute.call_args
        query_arg = call_args[0][0]

        assert "ordersToday:" in query_arg
        assert "ordersWeek:" in query_arg
        assert "ordersMonth:" in query_arg
        assert "shop {" in query_arg
        assert "products(" in query_arg

        # Verify stats parsing
        assert stats['shop_info']['name'] == "Test Shop"
        assert stats['products_count'] == 10
        assert stats['orders_today'] == 1
        assert stats['revenue_today'] == 100.0
        assert stats['orders_this_week'] == 2
        assert stats['revenue_this_week'] == 150.0
        assert stats['orders_this_month'] == 3
        assert stats['revenue_this_month'] == 350.0
