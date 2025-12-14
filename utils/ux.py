import streamlit as st
import streamlit.components.v1 as components

def badge(text, icon=None, color="gray"):
    """
    Renders a badge component similar to Shopify Polaris badges.

    Args:
        text (str): The text to display in the badge.
        icon (str, optional): An emoji or icon character to display before the text.
        color (str, optional): The color of the badge.
                               Options: 'green'/'success', 'yellow'/'warning', 'red'/'error', 'blue'/'info', 'gray'.
                               Also accepts hex codes (e.g., '#ff0000').
    """

    # Map colors to CSS styles
    # These colors match Shopify Polaris design system
    color_map = {
        "green": {"bg": "#e3f5ee", "text": "#004c3f"},
        "success": {"bg": "#e3f5ee", "text": "#004c3f"},
        "yellow": {"bg": "#fff8e1", "text": "#5c4813"},
        "warning": {"bg": "#fff8e1", "text": "#5c4813"},
        "red": {"bg": "#fef5f1", "text": "#8b1e0c"},
        "error": {"bg": "#fef5f1", "text": "#8b1e0c"},
        "blue": {"bg": "#e8f5fa", "text": "#1e4e79"},
        "info": {"bg": "#e8f5fa", "text": "#1e4e79"},
        "gray": {"bg": "#f1f2f3", "text": "#5c5f62"},
        "grey": {"bg": "#f1f2f3", "text": "#5c5f62"},
        "purple": {"bg": "#f4f1f8", "text": "#50248f"}, # Added purple for partial fulfillment
        "orange": {"bg": "#fff8e1", "text": "#5c4813"}, # Mapped to yellow/warning style
    }

    # Handle hex codes
    if str(color).startswith("#"):
        style = {"bg": color, "text": "white"} # Default text color for hex backgrounds
        # Simple contrast check could be added here, but white is a safe default for dark status colors usually used
        # If the background is very light, this might be hard to read, but existing app uses status_colors which seem to be standard names mostly.
        # However, to be safe, if we get a hex, we use it.
    else:
        style = color_map.get(str(color).lower(), color_map["gray"])

    icon_html = f'<span style="margin-right: 4px;">{icon}</span>' if icon else ""

    html = f"""
    <span style="
        display: inline-flex;
        align-items: center;
        background-color: {style['bg']};
        color: {style['text']};
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        line-height: 16px;
        white-space: nowrap;
    ">
        {icon_html}{text}
    </span>
    """

    st.markdown(html, unsafe_allow_html=True)

# Monkey-patch Streamlit to add the badge function
if not hasattr(st, 'badge'):
    setattr(st, 'badge', badge)
