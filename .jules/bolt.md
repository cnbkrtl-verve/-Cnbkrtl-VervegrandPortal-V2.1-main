## 2024-05-22 - Shopify GraphQL Root Query Limitation
**Learning:** `productVariants` is not available as a root query in the Shopify Admin GraphQL API (2024-10). Variants must be accessed via `products { variants }` or `productVariant(id: ...)`.
**Action:** Always verify GraphQL schema support for root queries in the Admin API docs before attempting optimizations that flatten nested queries.

## 2024-05-22 - Extraneous Tests
**Learning:** Adding test files for features that are not yet implemented or were reverted can cause confusion and build failures.
**Action:** Ensure test files are strictly scoped to the active changes in the PR. Remove any tests related to reverted or abandoned experiments immediately.

## 2024-05-22 - Timezone Sensitivity in Weekly Stats
**Learning:** When calculating "This Week" stats by filtering a larger "Month" dataset, logic must account for weeks that cross month boundaries. Querying only from the 1st of the month will miss days from the previous month that belong to the current week.
**Action:** Always calculate the query start date as `min(month_start, week_start)` when batching time-based queries to ensure complete data coverage. Use UTC consistently for API queries.
