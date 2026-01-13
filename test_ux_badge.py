
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from utils_ui import render_status_badge

def test_badge_rendering():
    # Test success badge
    html = render_status_badge("Active", "success")
    print(f"Success Badge: {html}")
    assert 'class="badge badge-success"' in html
    assert '>Active<' in html

    # Test error badge
    html = render_status_badge("Error", "error")
    print(f"Error Badge: {html}")
    assert 'class="badge badge-error"' in html
    assert '>Error<' in html

    print("✅ All badge tests passed!")

if __name__ == "__main__":
    test_badge_rendering()
