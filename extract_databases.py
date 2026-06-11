import re

def extract_dict(text, dict_name):
    # Find the start of the dictionary or .update() block
    start_str = f"{dict_name} = {{"
    start_idx = text.find(start_str)
    is_update = False
    if start_idx == -1:
        start_str = f"{dict_name}.update({{"
        start_idx = text.find(start_str)
        is_update = True
    if start_idx == -1:
        return None, text
    
    # Count braces to find the exact end of the block
    brace_count = 0
    end_idx = -1
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    if is_update:
                        end_idx = text.find(')', i) + 1
                    else:
                        end_idx = i + 1
                    break
                    
    if end_idx != -1:
        extracted = text[start_idx:end_idx]
        remaining = text[:start_idx] + text[end_idx:]
        return extracted, remaining
    return None, text

# 1. Read the main file
with open('/root/omnint.py', 'r') as f:
    content = f.read()

# 2. Define the databases to extract
dicts_to_extract = [
    "NSFW_SITES", "GOV_SITES", "EU_SITES", "UNIVERSITY_LIBRARIES",
    "MEDICAL_JOURNALS", "SCIENCE_JOURNALS", "INTEL_DATABASES", "OSINT_ENGINES"
]

# 3. Build the new databases.py file
db_content = "# ==========================================\n"
db_content += "# OMNINT DATABASES (Auto-Extracted)\n"
db_content += "# ==========================================\n\n"

for d_name in dicts_to_extract:
    extracted, content = extract_dict(content, d_name)
    if extracted:
        db_content += extracted + "\n\n"
        print(f"[+] Extracted: {d_name}")
    else:
        print(f"[-] Skipped (Not found): {d_name}")

# 4. Add the import to the top of omnint.py
# We look for the first 'import' or 'from' and place our import right after it
lines = content.split('\n')
import_inserted = False
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        lines.insert(i + 1, "from databases import *")
        import_inserted = True
        break

if not import_inserted:
    lines.insert(0, "from databases import *")

content = '\n'.join(lines)

# 5. Write the files
with open('/root/databases.py', 'w') as f:
    f.write(db_content)

with open('/root/omnint.py', 'w') as f:
    f.write(content)

print("\n[✅] SUCCESS: Databases moved to databases.py")
print("[✅] SUCCESS: omnint.py updated with 'from databases import *'")
