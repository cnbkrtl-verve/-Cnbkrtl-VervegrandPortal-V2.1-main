import sys
import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from connectors.shopify_api import ShopifyAPI

# --- MOCK DATA ---
SAMPLE_SHOP = {"shop": {"name": "Test Shop", "currencyCode": "USD"}}
SAMPLE_PRODUCTS = {"products": {"edges": [{"node": {"id": "p1"}}] * 10, "pageInfo": {"hasNextPage": False}}}
SAMPLE_CUSTOMERS = {"customers": {"edges": [{"node": {"id": "c1"}}] * 5, "pageInfo": {"hasNextPage": False}}}

today = datetime.now()
yesterday = today - timedelta(days=1)
# Ensure dates are compatible with logic
week_start = today - timedelta(days=today.weekday())
month_start = today.replace(day=1)

# Generate orders
def make_order(id, date, amount):
    return {
        "node": {
            "id": id,
            "name": f"Order {id}",
            "createdAt": date.isoformat(),
            "totalPriceSet": {"shopMoney": {"amount": str(amount), "currencyCode": "USD"}},
            "customer": {"firstName": "John", "lastName": "Doe"}
        }
    }

# Orders:
# t1: Today (Also in Week and Month usually)
# w1: This Week (but not today)
# m1: This Month (but not this week, if possible, or just earlier)
# old1: Old order

orders_today_list = [make_order("t1", today, 100)]
# This week order (make sure it's >= week_start but < today if possible)
orders_week_list = orders_today_list + [make_order("w1", week_start + timedelta(hours=1), 50)]
# This month order
orders_month_list = orders_week_list + [make_order("m1", month_start + timedelta(hours=1), 200)]

def mock_execute_graphql(query, variables=None):
    # print(f"DEBUG: Query: {query[:50]}...")

    # 1. Consolidated Query Detection
    if "ordersToday:" in query:
        return {
            "shop": SAMPLE_SHOP["shop"],
            "products": SAMPLE_PRODUCTS["products"],
            "customers": SAMPLE_CUSTOMERS["customers"],
            "ordersToday": {"edges": orders_today_list},
        }

    # 2. History Query Detection (sortKey: CREATED_AT)
    if "sortKey: CREATED_AT" in query:
        # Returns the superset (month list) which the python logic will filter
        return {"orders": {"edges": orders_month_list}}

    return {}

def run_simulation():
    # Initialize API with dummy data
    api = ShopifyAPI("test.myshopify.com", "token")

    # Patch execute_graphql
    api.execute_graphql = MagicMock(side_effect=mock_execute_graphql)

    print("--- Simulating New Optimization ---")

    # --- OPTIMIZED LOGIC START ---

    # We now call the REAL method from the updated class
    try:
        stats = api.get_dashboard_stats()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        stats = {}

    # --- OPTIMIZED LOGIC END ---

    print(f"Total API Calls: {api.execute_graphql.call_count}")
    print("Computed Stats:")
    print(json.dumps(stats, indent=2, default=str))

    # Assertions
    assert api.execute_graphql.call_count == 2
    assert stats['products_count'] == 10
    # t1 (100)
    assert stats['revenue_today'] == 100.0
    # t1 (100) + w1 (50) = 150
    assert stats['revenue_this_week'] == 150.0
    # t1 (100) + w1 (50) + m1 (200) = 350
    assert stats['revenue_this_month'] == 350.0

    print("\n✅ Verification Successful: 2 API calls produced correct aggregated stats.")

if __name__ == "__main__":
    run_simulation()
