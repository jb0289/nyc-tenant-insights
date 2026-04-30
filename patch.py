"""One-shot patch to wire live API fallback into app.py"""
content = open('app.py').read()

# 1. Add import at the top
if 'from nyc_api import check_nyc_live' not in content:
    content = content.replace(
        'import streamlit as st',
        'import streamlit as st\nfrom nyc_api import check_nyc_live',
        1
    )

# 2. Build the new "no match" block
new_block = '''with st.spinner(f"Checking NYC Open Data live for {user_input}..."):
                live = check_nyc_live(user_input)
            if live is None:
                st.warning(f"Couldn't parse address. Try: 149 W 80 St")
            elif live["complaints"] == 0 and live["violations"] == 0:
                st.success(f"**{user_input.upper()} — Clean Record (Grade A equivalent)**")
                st.caption(f"Verified live against NYC Open Data: zero 311 complaints and zero HPD violations on file since 2024-01-01.")
            else:
                st.warning(f"**{user_input.upper()}** — found {live['complaints']} complaints and {live['violations']} violations on NYC Open Data, but address didn't match our normalized dataset. Check [HPD Online](https://hpdonline.nyc.gov/).")
            user_query = ""'''

# 3. Replace both "no match" blocks
old_a = '''st.info(f"**\\'{user_input}\\' isn\\'t in our dataset.** Likely means no complaints or violations on file — a good sign. Check [HPD Online](https://hpdonline.nyc.gov/) for full history.")
            user_query = ""'''

old_b = '''st.info(f"**\\'{user_input}\\' isn\\'t in our dataset.** Likely means no complaints or violations on file — a good sign.")
                user_query = ""'''

count = 0
if old_a in content:
    content = content.replace(old_a, new_block, 1)
    count += 1

# Second block has extra indent
new_block_indented = new_block.replace('\n            ', '\n                ')
if old_b in content:
    content = content.replace(old_b, new_block_indented, 1)
    count += 1

open('app.py', 'w').write(content)
print(f"Replaced {count} blocks. Import added: {'check_nyc_live' in content}")
