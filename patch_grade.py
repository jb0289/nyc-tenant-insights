content = open('prep_data.py').read()

old = """# A-F grade
def grade(s):
    if s <= 20: return 'A'
    elif s <= 40: return 'B'
    elif s <= 60: return 'C'
    elif s <= 80: return 'D'
    else: return 'F'

building['grade'] = building['quality_score'].apply(grade)"""

new = """# Fixed-threshold A+ to F grading based on absolute counts
def grade_tier(row):
    c = int(row.get('complaint_count', 0))
    v = int(row.get('violation_count', 0))
    o = int(row.get('open_complaints', 0)) + int(row.get('open_violations', 0))
    cc = int(row.get('class_c', 0))

    if c >= 300 or cc >= 11: return 'F'
    if c >= 150 or cc >= 7: return 'D-'
    if c >= 75 or v >= 40 or cc >= 4: return 'D'
    if c >= 40 or v >= 25 or cc >= 3: return 'D+'
    if c >= 25 or v >= 15 or cc >= 2: return 'C-'
    if c >= 15 or v >= 10 or cc >= 1: return 'C'
    if c >= 8 or v >= 5: return 'C+'
    if c >= 5 or v >= 3 or o >= 2: return 'B-'
    if c >= 3 or v >= 2 or o >= 1: return 'B'
    if c >= 1 or v >= 1: return 'B+'
    if c == 0 and v <= 1 and o == 0: return 'A'
    return 'A+'

building['grade'] = building.apply(grade_tier, axis=1)"""

if old in content:
    content = content.replace(old, new)
    open('prep_data.py', 'w').write(content)
    print("Tiered grading installed")
else:
    print("Pattern not found — need to debug")
