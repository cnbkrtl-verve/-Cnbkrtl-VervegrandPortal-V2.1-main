## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2025-10-27 - Forms for Single Input Actions
**Learning:** Single input actions (like "Search SKU" or "Quick Add") often frustrate users if they trigger a full app rerun on every keystroke/blur or if the "Enter" key doesn't submit. Wrapping them in `st.form` enables the expected "Type -> Enter -> Submit" workflow without accidental updates.
**Action:** Always wrap single-input-plus-button patterns in `st.form` unless real-time feedback (like search-as-you-type) is explicitly required.
