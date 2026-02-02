## 2024-05-22 - Shopify GraphQL Root Query Limitation
**Learning:** `productVariants` is not available as a root query in the Shopify Admin GraphQL API (2024-10). Variants must be accessed via `products { variants }` or `productVariant(id: ...)`.
**Action:** Always verify GraphQL schema support for root queries in the Admin API docs before attempting optimizations that flatten nested queries.

## 2024-05-22 - Extraneous Tests
**Learning:** Adding test files for features that are not yet implemented or were reverted can cause confusion and build failures.
**Action:** Ensure test files are strictly scoped to the active changes in the PR. Remove any tests related to reverted or abandoned experiments immediately.

## 2024-05-22 - Dashboard Stats Query Batching
**Learning:** `get_dashboard_stats` was executing 6 sequential GraphQL queries, causing significant latency. Shopify GraphQL API supports multiple root fields in a single query.
**Action:** Combined queries into 2 batches (Metadata: Shop+Products; Orders: All periods combined), reducing round-trips by 66% and filtering data client-side (Python) which is efficient for dashboard scales.
