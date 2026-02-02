## 2024-05-23 - Streamlit Component Wrapping
**Learning:** Wrapping Streamlit widgets (like `st.metric`) inside custom HTML `<div>` tags using split `st.markdown` calls (opening tag in one call, widget, closing tag in another) does not work as expected. The browser or Streamlit's Markdown parser auto-closes the tags within the block, breaking the layout.
**Action:** Use native containers like `st.container(border=True)` for grouping and visual separation, or apply custom CSS classes to native containers if needed (though harder to target). Avoid split HTML injection for wrapping widgets.
