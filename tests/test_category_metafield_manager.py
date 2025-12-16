
import pytest
import re
from unittest.mock import patch, mock_open, MagicMock
from utils.category_metafield_manager import CategoryMetafieldManager

# Mock config data
MOCK_CONFIG = {
    "categories": {
        "Elbise": {
            "keywords": ["elbise"],
            "metafields": {}
        }
    },
    "patterns": {
        "yaka_tipi": [
            ["v\\s*yaka", "V Yaka"],
            ["bisiklet\\s*yaka", "Bisiklet Yaka"]
        ],
        "kol_tipi": [
            ["uzun\\s*kol", "Uzun Kol"]
        ]
    }
}

@pytest.fixture
def mock_config_manager():
    # Reset config before each test
    CategoryMetafieldManager._config = None
    CategoryMetafieldManager._compiled_patterns = None

    with patch("builtins.open", mock_open(read_data='{}')):
        with patch("json.load", return_value=MOCK_CONFIG):
            yield

def test_compile_patterns_on_load(mock_config_manager):
    """Test that patterns are compiled when config is loaded"""
    CategoryMetafieldManager._load_config()

    assert CategoryMetafieldManager._compiled_patterns is not None
    assert "yaka_tipi" in CategoryMetafieldManager._compiled_patterns

    compiled_list = CategoryMetafieldManager._compiled_patterns["yaka_tipi"]
    assert len(compiled_list) == 2

    pattern_obj, value = compiled_list[0]
    assert isinstance(pattern_obj, re.Pattern)
    assert value == "V Yaka"

    # Test matching
    assert pattern_obj.search("V Yaka Elbise")
    assert pattern_obj.search("v yaka elbise") # Ignore case

def test_extract_metafield_values_regex(mock_config_manager):
    """Test extracting values using regex from title"""

    values = CategoryMetafieldManager.extract_metafield_values(
        product_title="Kadın V Yaka Uzun Kol Elbise",
        category="Elbise"
    )

    assert values.get("yaka_tipi") == "V Yaka"
    assert values.get("kol_tipi") == "Uzun Kol"

def test_extract_metafield_values_regex_tags(mock_config_manager):
    """Test extracting values using regex from tags"""

    values = CategoryMetafieldManager.extract_metafield_values(
        product_title="Elbise",
        category="Elbise",
        tags=["Bisiklet Yaka"]
    )

    assert values.get("yaka_tipi") == "Bisiklet Yaka"

def test_extract_metafield_values_regex_description(mock_config_manager):
    """Test extracting values using regex from description"""

    values = CategoryMetafieldManager.extract_metafield_values(
        product_title="Elbise",
        category="Elbise",
        product_description="Bu ürün V Yaka tasarıma sahiptir."
    )

    assert values.get("yaka_tipi") == "V Yaka"
