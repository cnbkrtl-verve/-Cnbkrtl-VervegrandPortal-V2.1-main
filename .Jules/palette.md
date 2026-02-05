## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2026-02-05 - Tooltips for Metric Clarity
**Learning:** When using `st.metric` with `delta` to display related but distinct values (e.g., Order Count vs. Revenue), adding a `help` tooltip is crucial. It clarifies the relationship without cluttering the UI with extra labels, keeping the design clean while solving ambiguity.
**Action:** Always add `help` tooltips to metrics that use `delta` for non-trend data or when the metric label alone isn't 100% self-explanatory.
