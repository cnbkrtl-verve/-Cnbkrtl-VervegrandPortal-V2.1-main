# utils/style_loader.py
"""
Global CSS Yükleyici
Tüm sayfalarda kullanılmak üzere CSS yükleme fonksiyonu
"""

import streamlit as st
import os

def load_global_css():
    """
    Global CSS dosyasını yükler - Tüm uygulamada geçerli olur.
    Her sayfanın başında çağrılmalıdır.
    
    Kullanım:
        from utils.style_loader import load_global_css
        load_global_css()
    """
    # Proje kök dizinini bul
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    css_file_path = os.path.join(project_root, 'style.css')
    
    if os.path.exists(css_file_path):
        with open(css_file_path, encoding='utf-8') as f:
            css_content = f.read()
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    else:
        # CSS dosyası bulunamazsa temel stiller
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            --primary-bg: #0f0f1e;
            --secondary-bg: #1a1a2e;
            --tertiary-bg: #252541;
            --accent-primary: #6366f1;
            --accent-secondary: #8b5cf6;
            --text-primary: #f9fafb;
            --text-secondary: #d1d5db;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--primary-bg);
            color: var(--text-primary);
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--secondary-bg) 0%, var(--primary-bg) 100%) !important;
            border-right: 1px solid #374151 !important;
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 0 20px rgba(99, 102, 241, 0.4);
        }
        </style>
        """, unsafe_allow_html=True)
