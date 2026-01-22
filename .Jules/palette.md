## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2025-02-13 - Action Card Pattern
**Learning:** Using semantic alerts (`st.info`, `st.success`) for navigation actions creates a confusing UX where "actions" look like "status messages".
**Action:** Use `st.container(border=True)` with a consistent header/icon pattern for navigation cards. Preserve color coding via text/icon color (`:blue[...]`) instead of background color.
