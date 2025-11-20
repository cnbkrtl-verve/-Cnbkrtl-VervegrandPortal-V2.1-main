# operations/__init__.py
# Proje kök dizinini Python path'ine ekle

import sys
import os

# Proje kök dizinini bul ve sys.path'e ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
