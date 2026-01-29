## 2024-05-22 - Shopify GraphQL Root Query Limitation
**Learning:** `productVariants` is not available as a root query in the Shopify Admin GraphQL API (2024-10). Variants must be accessed via `products { variants }` or `productVariant(id: ...)`.
**Action:** Always verify GraphQL schema support for root queries in the Admin API docs before attempting optimizations that flatten nested queries.

## 2024-05-22 - Extraneous Tests
**Learning:** Adding test files for features that are not yet implemented or were reverted can cause confusion and build failures.
**Action:** Ensure test files are strictly scoped to the active changes in the PR. Remove any tests related to reverted or abandoned experiments immediately.

## 2024-05-22 - Dashboard Optimization: GraphQL Query Consolidation
**Learning:** Sequential GraphQL queries for dashboard metrics (Shop, Products, Orders Today/Week/Month) caused significant latency (6 separate calls).
**Action:** Consolidated into 2 optimized queries:
1. Metadata (Shop + Products count).
2. Orders (Single query fetching orders >= min_date, sorting by CREATED_AT desc).
   Python-side filtering handles the specific time windows (Today/Week/Month) from the single order list. This reduces API overhead by ~66%.
