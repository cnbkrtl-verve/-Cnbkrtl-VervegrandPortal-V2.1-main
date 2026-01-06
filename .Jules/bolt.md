# Bolt's Journal

## 2024-05-23 - Initial Optimization
**Learning:** The application performs multiple sequential GraphQL queries to Shopify to fetch dashboard statistics. This is inefficient due to multiple network round-trips and potential rate limiting issues if calls are not batched.
**Action:** Combine these queries into a single GraphQL query using aliases to reduce network latency and improve load time.
