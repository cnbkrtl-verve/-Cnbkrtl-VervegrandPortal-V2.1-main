## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2026-01-31 - Action Cards vs Alerts
**Learning:** Replacing semantic alerts (`st.info`, `st.success`) with `st.container(border=True)` and colored Markdown headers creates a much cleaner "Action Card" pattern for navigation menus. Alerts carry a "system state" connotation that is distracting for static navigation options.
**Action:** Avoid using alerts for navigation or static layout elements; use bordered containers with colored text instead.
