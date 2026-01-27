
import sys
import os
import time
from unittest.mock import MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.shopify_api import ShopifyAPI

def benchmark_dashboard_stats():
    print("🚀 Benchmarking get_dashboard_stats...")

    # Mock ShopifyAPI
    api = ShopifyAPI("test.myshopify.com", "token")

    # Counter for API calls
    call_count = 0

    # Mock execute_graphql
    original_execute = api.execute_graphql

    def mock_execute_graphql(query, variables=None):
        nonlocal call_count
        call_count += 1
        print(f"  Query {call_count}: {query[:50].replace('\n', ' ')}...")

        # Metadata Query (contains shop, products, customers)
        if "shop {" in query and "products(" in query and "customers(" in query:
            return {
                "shop": {"name": "Test Shop", "currencyCode": "USD", "plan": {"displayName": "Basic"}},
                "products": {"edges": [{"node": {"id": "1"}}]*100, "pageInfo": {"hasNextPage": False}},
                "customers": {"edges": [{"node": {"id": "1"}}]*50, "pageInfo": {"hasNextPage": False}}
            }

        # Orders Query
        elif "orders(" in query and "sortKey: CREATED_AT" in query:
            edges = []
            now = datetime.now()
            # Generate some dummy orders with dates
            for i in range(10):
                # Mix of today, yesterday, last week
                if i < 2: date = now # Today
                elif i < 5: date = now - timedelta(days=3) # This week
                else: date = now - timedelta(days=15) # This month

                edges.append({
                    "node": {
                        "id": f"gid://shopify/Order/{i}",
                        "name": f"#100{i}",
                        "createdAt": date.isoformat(),
                        "totalPriceSet": {"shopMoney": {"amount": "10.00", "currencyCode": "USD"}},
                        "customer": {"firstName": "John", "lastName": "Doe"}
                    }
                })
            return {"orders": {"edges": edges, "pageInfo": {"hasNextPage": False}}}

        # Fallback for older queries (if any remaining) or other calls
        elif "shop {" in query:
            return {"shop": {"name": "Test Shop", "currencyCode": "USD", "plan": {"displayName": "Basic"}}}
        elif "products(" in query:
            return {"products": {"edges": [{"node": {"id": "1"}}]*100, "pageInfo": {"hasNextPage": False}}}
        elif "customers(" in query:
            return {"customers": {"edges": [{"node": {"id": "1"}}]*50}}

        return {}

    api.execute_graphql = mock_execute_graphql

    # Run the method
    start_time = time.time()
    stats = api.get_dashboard_stats()
    end_time = time.time()

    print(f"\n📊 Results:")
    print(f"  Total API Calls: {call_count}")
    print(f"  Execution Time: {end_time - start_time:.4f}s (simulated)")
    print(f"  Stats keys: {list(stats.keys())}")

    # Verify stats
    print(f"  Orders Today: {stats['orders_today']}")
    print(f"  Orders Week: {stats['orders_this_week']}")
    print(f"  Orders Month: {stats['orders_this_month']}")
    print(f"  Products: {stats['products_count']}")

    return call_count

if __name__ == "__main__":
    benchmark_dashboard_stats()
