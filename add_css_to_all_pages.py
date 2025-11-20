# add_css_to_all_pages.py
"""
Tüm sayfalara CSS yükleyici ekleyen yardımcı script
"""

import os
import re

# Sayfalar dizini
pages_dir = r"c:\Users\User\Documents\vervegrand tema\-Cnbkrtl-VervegrandPortal-V2.1\pages"

# Eklenecek kod
css_loader_code = """
# 🎨 GLOBAL CSS YÜKLEME
from utils.style_loader import load_global_css
load_global_css()
"""

def add_css_loader_to_file(filepath):
    """Bir dosyaya CSS yükleyici ekler"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Zaten CSS loader varsa ekleme
    if 'load_global_css' in content:
        print(f"✓ Zaten var: {os.path.basename(filepath)}")
        return False
    
    # sys.path ekleme kısmını bul
    pattern = r"(if project_root not in sys\.path:\s+sys\.path\.insert\(0, project_root\))"
    
    if re.search(pattern, content):
        # sys.path eklemesinden sonra ekle
        new_content = re.sub(
            pattern,
            r"\1" + "\n" + css_loader_code,
            content
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Eklendi: {os.path.basename(filepath)}")
        return True
    else:
        # sys.path ekleme yoksa, import'lardan sonra ekle
        # İlk streamlit import'undan sonra ekle
        pattern = r"(import streamlit as st\s*\n)"
        
        if re.search(pattern, content):
            # Önce sys ve os import'larını ekle
            sys_imports = """import sys
import os

# Projenin ana dizinini Python'un arama yoluna ekle
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
"""
            
            # sys import var mı kontrol et
            if 'import sys' not in content:
                new_content = re.sub(
                    pattern,
                    r"\1" + sys_imports + "\n" + css_loader_code,
                    content
                )
            else:
                # sys import varsa sadece CSS loader ekle
                pattern2 = r"(if project_root not in sys\.path:\s+sys\.path\.insert\(0, project_root\)\s*\n)"
                if re.search(pattern2, content):
                    new_content = re.sub(
                        pattern2,
                        r"\1" + "\n" + css_loader_code,
                        content
                    )
                else:
                    # sys.path yok, import'lardan sonra ekle
                    import_section_end = content.find('\n\n', content.find('import'))
                    if import_section_end != -1:
                        new_content = content[:import_section_end] + "\n" + css_loader_code + content[import_section_end:]
                    else:
                        print(f"⚠️  Manuel ekle: {os.path.basename(filepath)}")
                        return False
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ Eklendi: {os.path.basename(filepath)}")
            return True
        else:
            print(f"⚠️  Manuel ekle: {os.path.basename(filepath)}")
            return False

# Tüm .py dosyalarını işle
if __name__ == "__main__":
    print("🎨 CSS Loader ekleniyor...\n")
    
    for filename in os.listdir(pages_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(pages_dir, filename)
            add_css_loader_to_file(filepath)
    
    print("\n✅ İşlem tamamlandı!")
