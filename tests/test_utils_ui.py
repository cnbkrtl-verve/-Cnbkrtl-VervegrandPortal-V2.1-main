
import pytest
from utils_ui import get_status_badge_html

class TestUtilsUI:
    def test_get_status_badge_html_success(self):
        """✅ Known success statuses should map to badge-success"""
        html = get_status_badge_html('PAID', 'PAID')
        assert 'badge-success' in html
        assert 'PAID' in html

        html = get_status_badge_html('FULFILLED', 'FULFILLED')
        assert 'badge-success' in html

    def test_get_status_badge_html_warning(self):
        """✅ Known warning statuses should map to badge-warning"""
        html = get_status_badge_html('PENDING', 'PENDING')
        assert 'badge-warning' in html

    def test_get_status_badge_html_case_insensitive(self):
        """✅ Status mapping should be case insensitive for keys"""
        html = get_status_badge_html('paid', 'paid')
        assert 'badge-success' in html

    def test_get_status_badge_html_explicit_status(self):
        """✅ Explicit status argument should override text mapping"""
        html = get_status_badge_html('Custom Text', 'success')
        assert 'badge-success' in html
        assert 'Custom Text' in html

    def test_get_status_badge_html_unknown_fallback(self):
        """✅ Unknown statuses should fallback to badge-default"""
        html = get_status_badge_html('Unknown Status', 'Unknown Status')
        assert 'badge-default' in html
