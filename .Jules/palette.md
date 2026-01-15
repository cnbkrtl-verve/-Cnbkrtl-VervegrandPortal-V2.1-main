## 2024-05-23 - Status Container for Process Steps
**Learning:** `st.status` provides a much better UX for multi-step processes than `st.expander` + `st.spinner`. It automatically handles the "running" state and allows for a cleaner summary upon completion (success/error/warning icons).
**Action:** Use `st.status` for all long-running operations that have sub-steps or logs, instead of manually managing expanders and placeholders.

## 2025-05-23 - Concise Status Badges
**Learning:** Using `st.badge` for status indicators in lists (e.g., Payment Status) is much cleaner and more space-efficient than full-width alert components like `st.success` or `st.warning`. It keeps the visual flow of the list intact while still providing clear color-coded feedback.
**Action:** Use `st.badge` for status columns in data grids or lists instead of alerts.

## 2026-01-15 - Double-Ring Focus Indicators
**Learning:** Default browser focus rings (outlines) often have poor contrast in custom dark themes or are overridden by CSS resets. A double-ring `box-shadow` (inner ring matching the background color, outer ring matching the accent color) guarantees visibility and accessibility regardless of the surrounding contrast, significantly improving keyboard navigation.
**Action:** Use `.element:focus-visible { box-shadow: 0 0 0 2px var(--bg-color), 0 0 0 4px var(--accent-color); outline: none; }` for all interactive elements in dark mode.
