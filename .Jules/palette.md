## 2024-05-23 - Action Card Navigation Pattern
**Learning:** Semantic alert components (`st.info`, `st.error`, etc.) should not be used solely for their background colors to differentiate navigation items. It confuses screen readers and semantics.
**Action:** Use `st.container(border=True)` combined with colored Markdown headers (e.g., `:blue[Title]`) and `st.page_link` for a clean, accessible, and performant navigation card pattern.
