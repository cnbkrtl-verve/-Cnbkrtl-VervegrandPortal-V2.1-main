"""
Script to add 'renk' metafield to all categories in category_metafield_manager.py
"""

import re

# Read the file
with open('utils/category_metafield_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the renk metafield to add
renk_metafield = """            'custom.renk': {
                'type': 'single_line_text_field',
                'namespace': 'custom',
                'key': 'renk',
                'description': 'Renk (Varyantlardan otomatik doldurulur)'
            },"""

# Find all category definitions and add renk field if not exists
# Pattern to find the opening of each category's metafields
pattern = r"(\s+)'([^']+)':\s*\{(\s+)'custom\."

# Track if we need to make changes
modified = False

# Split by categories
lines = content.split('\n')
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Check if this is a category start (e.g., 'Elbise': {)
    if re.match(r"^\s+\'[^']+\':\s+\{$", line):
        new_lines.append(line)
        
        # Check if next few lines already have 'custom.renk'
        has_renk = False
        for j in range(i+1, min(i+10, len(lines))):
            if 'custom.renk' in lines[j]:
                has_renk = True
                break
        
        # If no renk field, add it after the opening brace
        if not has_renk and i+1 < len(lines):
            new_lines.append(renk_metafield)
            modified = True
            print(f"Added renk to category at line {i+1}")
    else:
        new_lines.append(line)
    
    i += 1

if modified:
    # Write back
    with open('utils/category_metafield_manager.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("\n✅ Successfully added 'renk' metafield to all categories!")
else:
    print("ℹ️ No changes needed - 'renk' field already exists in all categories")
