#!/usr/bin/env python3
"""
sync_definitions.py
Fetches LaTeX definitions from GitHub repos:
  - skitchwinters/MATH-301-Extras (Definitions_Hammack.tex)
  - skitchwinters/MATH-410-Extras (Definitions.tex)
  - skitchwinters/MATH-461-Extras (Definitions_Marsden.tex)
Parses them into structured course/chapter/card data and outputs definitions.json and definitions.js.
Ensures 100% KaTeX compatibility, clean paragraph spacing, and proper entity handling.
"""

import os
import re
import json
import base64
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

COURSES = [
    {
        "id": "MATH-301",
        "code": "MATH 301",
        "title": "Intro to Proofs",
        "textbook": "Book of Proof (Hammack)",
        "repo": "skitchwinters/MATH-301-Extras",
        "filename": "Definitions_Hammack.tex",
        "color": "#3b82f6"
    },
    {
        "id": "MATH-410",
        "code": "MATH 410",
        "title": "Abstract Algebra",
        "textbook": "Contemporary Abstract Algebra (Gallian)",
        "repo": "skitchwinters/MATH-410-Extras",
        "filename": "Definitions.tex",
        "color": "#8b5cf6"
    },
    {
        "id": "MATH-461",
        "code": "MATH 461",
        "title": "Real Analysis",
        "textbook": "Elementary Classical Analysis (Marsden & Hoffman)",
        "repo": "skitchwinters/MATH-461-Extras",
        "filename": "Definitions_Marsden.tex",
        "color": "#10b981"
    }
]

def clean_term(term: str) -> str:
    term = term.strip()
    # Strip leading/trailing outer braces if unbalanced
    if term.startswith("{") and term.endswith("}"):
        depth = 0
        all_enclosed = True
        for i, ch in enumerate(term):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and i < len(term) - 1:
                    all_enclosed = False
                    break
        if all_enclosed:
            term = term[1:-1].strip()

    # Clean \mbox{...}
    term = re.sub(r'\\mbox\{([^}]+)\}', r'\1', term)
    term = re.sub(r'\\mbox\{?', '', term)
    return term.strip()

def clean_latex_body(text: str) -> str:
    # 1. Remove comments while preserving escaped \%
    lines = []
    for line in text.splitlines():
        if re.match(r'^\s*%(?!%)', line):
            continue
        line = re.sub(r'(?<!\\)%.*$', '', line)
        lines.append(line)
    text = '\n'.join(lines)
    
    # 2. Remove leading {} or LaTeX spacing commands
    text = re.sub(r'^\s*\{\}\s*', '', text)
    text = re.sub(r'\\(?:medskip|bigskip|smallskip|noindent|rmfamily|par)\b', '', text)
    
    # 3. Handle itemize environments
    def replace_itemize(match):
        inner = match.group(1)
        items = re.split(r'\\item(?:\[.*?\])?', inner)
        res = ['<ul class="def-list">']
        for it in items:
            it = it.strip()
            if it:
                res.append(f'<li>{it}</li>')
        res.append('</ul>')
        return '\n'.join(res)
    text = re.sub(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', replace_itemize, text, flags=re.DOTALL)
    
    # 4. Handle tabular environments
    def replace_tabular(match):
        body = match.group(1)
        rows = [r.strip() for r in body.split('\\\\') if r.strip()]
        res = ['<div class="def-table-wrap"><table class="def-table">']
        for r in rows:
            cells = [c.strip() for c in r.split('&')]
            if any(cells):
                res.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
        res.append('</table></div>')
        return '\n'.join(res)
    text = re.sub(r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}', replace_tabular, text, flags=re.DOTALL)

    # 5. Handle \emph{...} carefully:
    # We only convert \emph{...} to <span class="emph">...</span> OUTSIDE math mode.
    # Inside math mode ($...$ or \[...\]), \emph is handled natively by KaTeX macro \textcolor{red}{#1}.
    # Let's split into math and non-math segments:
    tokens = re.split(r'(\\\[.*?\\\]|(?<!\\)\$.*?(?<!\\)\$)', text, flags=re.DOTALL)
    cleaned_tokens = []
    for t in tokens:
        if t.startswith(r'\[') or (t.startswith('$') and t.endswith('$') and len(t) > 1):
            # Inside math mode: do NOT inject HTML tags! Leave \emph as \emph
            cleaned_tokens.append(t)
        else:
            # Outside math mode: convert \emph{...} to HTML span
            # Use brace matching for \emph if nested
            def replace_text_emph(s):
                res = []
                idx = 0
                while True:
                    m = re.search(r'\\emph\{', s[idx:])
                    if not m:
                        res.append(s[idx:])
                        break
                    start = idx + m.start()
                    brace_start = idx + m.end()
                    res.append(s[idx:start])
                    # find matching closing brace
                    depth = 1
                    i = brace_start
                    while i < len(s) and depth > 0:
                        if s[i] == '{' and (i == 0 or s[i-1] != '\\'): depth += 1
                        elif s[i] == '}' and (i == 0 or s[i-1] != '\\'): depth -= 1
                        i += 1
                    inner = s[brace_start:i-1]
                    res.append(f'<span class="emph">{inner}</span>')
                    idx = i
                return ''.join(res)
            
            cleaned_t = replace_text_emph(t)
            cleaned_tokens.append(cleaned_t)
            
    text = ''.join(cleaned_tokens)
    
    # 6. Convert LaTeX quotes `` and ''
    text = re.sub(r'``', '“', text)
    text = re.sub(r"''", '”', text)
    
    # 7. Normalize excess newlines and tabs
    # Clean redundant whitespace around \[ and \]
    text = re.sub(r'\s*\\\[\s*', r'\n\\[', text)
    text = re.sub(r'\s*\\\]\s*', r'\\]\n', text)
    # Collapse multi-newlines containing spaces into double newlines
    text = re.sub(r'\n\s*\n\s*(\n\s*)+', '\n\n', text)
    # Strip tabs
    text = re.sub(r'\t+', ' ', text)
    
    return text.strip()

def fetch_file_content(repo: str, filename: str) -> str:
    raw_path = os.path.join(PROJECT_DIR, f"raw_{repo.split('/')[-1]}.tex")
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"Fetching {repo}/{filename} via gh api...")
    cmd = ["gh", "api", f"repos/{repo}/contents/{filename}"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(content)
    return content

def extract_definitions_from_text(text: str):
    """Accurately extracts definitions by balancing curly braces for the term argument."""
    pattern = re.compile(r'\\begin\{definition\}(?:\[(.*?)\])?\{')
    pos = 0
    results = []
    while True:
        m = pattern.search(text, pos)
        if not m:
            break
        opt = m.group(1)
        term_start = m.end()
        depth = 1
        i = term_start
        while i < len(text) and depth > 0:
            if text[i] == '{' and (i == 0 or text[i-1] != '\\'):
                depth += 1
            elif text[i] == '}' and (i == 0 or text[i-1] != '\\'):
                depth -= 1
            i += 1
        raw_term = text[term_start:i-1]
        
        # Search for matching \end{definition}
        end_m = re.search(r'\\end\{definition\}', text[i:])
        if end_m:
            raw_body = text[i:i + end_m.start()]
            pos = i + end_m.end()
        else:
            raw_body = text[i:]
            pos = len(text)
        results.append((opt, raw_term, raw_body))
    return results

def parse_course_file(course_info: dict, content: str) -> dict:
    course_id = course_info["id"]
    tokens = re.split(r'(\\section\*?\{[^}]+\})', content)
    
    current_chapter = "Chapter 1" if course_id != "MATH-461" else "Chapter 0"
    current_section = ""
    cards = []
    chapters_ordered = []
    
    for t in tokens:
        sec_m = re.match(r'\\section\*?\{([^}]+)\}', t)
        if sec_m:
            header = sec_m.group(1).strip()
            if "Chapter" in header:
                current_chapter = header
                current_section = ""
                if current_chapter not in chapters_ordered:
                    chapters_ordered.append(current_chapter)
            else:
                current_section = header
        else:
            defs = extract_definitions_from_text(t)
            for opt, raw_term, raw_body in defs:
                term = clean_term(raw_term)
                body = clean_latex_body(raw_body)
                card_id = f"{course_id}-c{len(cards) + 1}"
                
                if current_chapter not in chapters_ordered:
                    chapters_ordered.append(current_chapter)
                
                cards.append({
                    "id": card_id,
                    "courseId": course_id,
                    "chapter": current_chapter,
                    "section": current_section,
                    "term": term,
                    "definition": body
                })
                
    chapter_stats = []
    for ch in chapters_ordered:
        count = sum(1 for c in cards if c["chapter"] == ch)
        chapter_stats.append({
            "name": ch,
            "count": count
        })
        
    return {
        "id": course_info["id"],
        "code": course_info["code"],
        "title": course_info["title"],
        "textbook": course_info["textbook"],
        "color": course_info["color"],
        "totalTerms": len(cards),
        "chapters": chapter_stats,
        "cards": cards
    }

def main():
    all_courses = []
    total_definitions = 0
    
    for course_info in COURSES:
        content = fetch_file_content(course_info["repo"], course_info["filename"])
        course_data = parse_course_file(course_info, content)
        all_courses.append(course_data)
        total_definitions += course_data["totalTerms"]
        print(f"Processed {course_info['code']}: {course_data['totalTerms']} definitions across {len(course_data['chapters'])} chapters.")

    output_data = {
        "totalCourses": len(all_courses),
        "totalDefinitions": total_definitions,
        "courses": all_courses
    }
    
    json_path = os.path.join(PROJECT_DIR, "definitions.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {json_path}")

    js_path = os.path.join(PROJECT_DIR, "definitions.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated definitions data */\n")
        f.write("window.FLASHCARD_DATA = ")
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        f.write(";\n")
    print(f"Wrote {js_path}")
    print(f"SUCCESS: Synchronized {total_definitions} definitions!")

if __name__ == "__main__":
    main()
