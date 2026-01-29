## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2026-01-29 - Enable Enter Key Submission in Streamlit
**Learning:** Streamlit `text_input` and `number_input` widgets do not trigger associated `st.button` actions when "Enter" is pressed; the script reruns but the button state remains False. Users expect standard form behavior (Enter to submit).
**Action:** Wrap single-action input groups (like search or single-item updates) in `st.form` and use `st.form_submit_button`. This captures the Enter key event as a submission, improving keyboard accessibility and reducing friction.
