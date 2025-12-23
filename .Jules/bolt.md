## 2024-05-23 - [ShopifyAPI Batch Processing Bottleneck]
**Learning:** Manual `time.sleep` in batch processing loops can be extremely detrimental to performance, especially when rate limiting is already handled at a lower level.
**Action:** When implementing batch processing, rely on robust, adaptive rate limiters (like token bucket) instead of fixed, conservative sleeps. Always verify if a "critical" comment about performance limitation is still valid or if it was a temporary hotfix.
