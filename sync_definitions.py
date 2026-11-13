#!/usr/bin/env python3
"""
sync_definitions.py
Fetches LaTeX definitions from GitHub repos & Beamer lectures:
  - skitchwinters/MATH-301-Extras (Definitions_Hammack.tex) - Intro to Proofs
  - skitchwinters/MATH-410-Extras (Definitions.tex) - Abstract Algebra
  - skitchwinters/MATH-461-Extras (Definitions_Marsden.tex) - Real Analysis
  - skitchwinters/MATH-350-Extras (Definitions.tex) - Modern Geometry
  - skitchwinters/Beamer-Lectures (MATH 140) - Calculus I
  - skitchwinters/Beamer-Lectures (MATH 141) - Calculus II
  - skitchwinters/Beamer-Lectures (MATH 102) - Precalculus & Trigonometry
Parses them into structured course/chapter/card data and outputs definitions.json and definitions.js.
Ensures 100% KaTeX compatibility, clean paragraph spacing, and proper entity handling.
"""

import os
import re
import json
import base64
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BEAMER_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "temp_beamer")

COURSES_CONFIG = [
    {
        "type": "standalone",
        "id": "MATH-301",
        "code": "MATH 301",
        "title": "Intro to Proofs",
        "textbook": "Book of Proof (Hammack)",
        "repo": "skitchwinters/MATH-301-Extras",
        "filename": "Definitions_Hammack.tex",
        "color": "#3b82f6"
    },
    {
        "type": "standalone",
        "id": "MATH-410",
        "code": "MATH 410",
        "title": "Abstract Algebra",
        "textbook": "Contemporary Abstract Algebra (Gallian)",
        "repo": "skitchwinters/MATH-410-Extras",
        "filename": "Definitions.tex",
        "color": "#8b5cf6"
    },
    {
        "type": "standalone",
        "id": "MATH-461",
        "code": "MATH 461",
        "title": "Real Analysis",
        "textbook": "Elementary Classical Analysis (Marsden & Hoffman)",
        "repo": "skitchwinters/MATH-461-Extras",
        "filename": "Definitions_Marsden.tex",
        "color": "#10b981"
    },
    {
        "type": "standalone",
        "id": "MATH-350",
        "code": "MATH 350",
        "title": "Modern Geometry",
        "textbook": "Euclidean & Non-Euclidean Geometries (Greenberg)",
        "repo": "skitchwinters/MATH-350-Extras",
        "filename": "Definitions.tex",
        "color": "#f59e0b"
    },
    {
        "type": "beamer",
        "id": "MATH-140",
        "code": "MATH 140",
        "title": "Calculus I",
        "textbook": "APEX Calculus (Hartman)",
        "folder": "MATH 140",
        "color": "#06b6d4"
    },
    {
        "type": "beamer",
        "id": "MATH-141",
        "code": "MATH 141",
        "title": "Calculus II",
        "textbook": "APEX Calculus (Hartman)",
        "folder": "MATH 141 (APEX v3.0)",
        "color": "#e11d48"
    },
    {
        "type": "beamer",
        "id": "MATH-102",
        "code": "MATH 102",
        "title": "Precalculus & Trigonometry",
        "textbook": "Precalculus (Stewart / OpenStax)",
        "folder": "MATH 102",
        "color": "#6366f1"
    }
]

def get_balanced_arg(text, start_pos):
    pos = start_pos
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos < len(text) and text[pos] == '<':
        end_overlay = text.find('>', pos)
        if end_overlay != -1:
            pos = end_overlay + 1
            while pos < len(text) and text[pos].isspace():
                pos += 1
    if pos >= len(text) or text[pos] != '{':
        return None, start_pos
    
    depth = 0
    start = pos + 1
    for i in range(pos, len(text)):
        if text[i] == '{' and (i == 0 or text[i-1] != '\\'):
            depth += 1
        elif text[i] == '}' and (i == 0 or text[i-1] != '\\'):
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
    return None, len(text)

def clean_term(term: str) -> str:
    if not term: return "Definition"
    term = term.strip()
    term = re.sub(r'\\mbox\{([^}]+)\}', r'\1', term)
    term = re.sub(r'\\phantom\{[^}]+\}', '', term)
    term = re.sub(r'\\textcolor\{[^}]+\}\{([^}]+)\}', r'\1', term)
    term = re.sub(r'^\s*\{\s*', '', term)
    term = re.sub(r'\s*\}\s*$', '', term)
    return term.strip()

def clean_latex_body(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if re.match(r'^\s*%(?!%)', line):
            continue
        line = re.sub(r'(?<!\\)%.*$', '', line)
        lines.append(line)
    text = '\n'.join(lines)
    
    text = re.sub(r'^\s*\{\}\s*', '', text)
    text = re.sub(r'\\(?:medskip|bigskip|smallskip|noindent|rmfamily|par)\b', '', text)
    
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

    tokens = re.split(r'(\\\[.*?\\\]|(?<!\\)\$.*?(?<!\\)\$)', text, flags=re.DOTALL)
    cleaned_tokens = []
    for t in tokens:
        if t.startswith(r'\[') or (t.startswith('$') and t.endswith('$') and len(t) > 1):
            cleaned_tokens.append(t)
        else:
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
            
            cleaned_tokens.append(replace_text_emph(t))
            
    text = ''.join(cleaned_tokens)
    text = re.sub(r'``', '“', text)
    text = re.sub(r"''", '”', text)
    text = re.sub(r'\s*\\\[\s*', r'\n\\[', text)
    text = re.sub(r'\s*\\\]\s*', r'\\]\n', text)
    text = re.sub(r'\n\s*\n\s*(\n\s*)+', '\n\n', text)
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

def parse_standalone_course(course_info: dict, content: str) -> dict:
    course_id = course_info["id"]
    tokens = re.split(r'(\\section\*?\{[^}]+\}|\\textbf\{Chapter \d+\})', content)
    
    current_chapter = "Chapter 1" if course_id != "MATH-461" else "Chapter 0"
    current_section = ""
    cards = []
    chapters_ordered = []
    
    for t in tokens:
        sec_m = re.match(r'\\section\*?\{([^}]+)\}', t)
        ch_m = re.match(r'\\textbf\{(Chapter \d+)\}', t)
        if sec_m:
            header = sec_m.group(1).strip()
            if "Chapter" in header:
                current_chapter = header
                current_section = ""
                if current_chapter not in chapters_ordered:
                    chapters_ordered.append(current_chapter)
            else:
                current_section = header
        elif ch_m:
            current_chapter = ch_m.group(1).strip()
            current_section = ""
            if current_chapter not in chapters_ordered:
                chapters_ordered.append(current_chapter)
        else:
            pos = 0
            while True:
                idx = t.find(r'\begin{definition}', pos)
                if idx == -1: break
                end_tag = idx + len(r'\begin{definition}')
                
                rest = t[end_tag:].lstrip()
                if rest.startswith('['):
                    closing_bracket = rest.find(']')
                    if closing_bracket != -1:
                        end_tag = end_tag + (len(t[end_tag:]) - len(rest)) + closing_bracket + 1
                        
                arg1, after1 = get_balanced_arg(t, end_tag)
                if not arg1:
                    pos = end_tag
                    continue
                    
                end_def = t.find(r'\end{definition}', after1)
                raw_body = t[after1:end_def].strip() if end_def != -1 else t[after1:].strip()
                
                term = clean_term(arg1)
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
                
                pos = end_def + len(r'\end{definition}') if end_def != -1 else len(t)
                
    chapter_stats = []
    for ch in chapters_ordered:
        count = sum(1 for c in cards if c["chapter"] == ch)
        if count > 0:
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

def parse_beamer_course(course_info: dict, folder_name: str) -> dict:
    course_id = course_info["id"]
    folder_path = os.path.join(BEAMER_DIR, folder_name)
    tex_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.tex')])
    
    cards = []
    chapters_ordered = []
    
    for fname in tex_files:
        fpath = os.path.join(folder_path, fname)
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            
        ch_num = re.findall(r'\\ChapterNumber\{([^}]+)\}', c)
        ch_title = re.findall(r'\\ChapterTitle\{([^}]+)\}', c)
        sec_num = re.findall(r'\\SectionNumber\{([^}]+)\}', c)
        sec_title = re.findall(r'\\SectionTitle\{([^}]+)\}', c)
        
        if ch_num:
            ch_name = f"Chapter {ch_num[0]}"
            if ch_title:
                ch_name += f": {ch_title[0]}"
        else:
            m_sec = re.search(r'MATH 102\s+([0-9]+)\.', fname)
            if m_sec:
                ch_name = f"Chapter {m_sec.group(1)}"
            else:
                ch_name = "General"
                
        if ch_name not in chapters_ordered:
            chapters_ordered.append(ch_name)
            
        section_label = ""
        if sec_num:
            section_label = f"Sec {sec_num[0]}"
            if sec_title:
                section_label += f" ({sec_title[0]})"
        else:
            m_sec2 = re.search(r'MATH 102\s+([0-9\.]+(?:-[0-9\.]+)?(?:_S\d+)?)', fname)
            if m_sec2:
                section_label = f"Sec {m_sec2.group(1)}"
                
        pos = 0
        while True:
            idx = c.find(r'\begin{definition}', pos)
            if idx == -1: break
            end_tag = idx + len(r'\begin{definition}')
            
            arg1, after1 = get_balanced_arg(c, end_tag)
            arg2, after2 = get_balanced_arg(c, after1)
            
            end_def = c.find(r'\end{definition}', after2)
            raw_body = c[after2:end_def].strip() if end_def != -1 else c[after2:].strip()
            
            if arg2:
                num = arg1.strip()
                term = clean_term(arg2)
            elif arg1:
                num = ""
                term = clean_term(arg1)
            else:
                num = ""
                term = "Definition"
                
            body = clean_latex_body(raw_body)
            card_id = f"{course_id}-c{len(cards) + 1}"
            
            sec_display = section_label
            if num:
                sec_display = f"Def {num}" + (f" • {section_label}" if section_label else "")
                
            cards.append({
                "id": card_id,
                "courseId": course_id,
                "chapter": ch_name,
                "section": sec_display,
                "term": term,
                "definition": body
            })
            
            pos = end_def + len(r'\end{definition}') if end_def != -1 else after2
            
    chapter_stats = []
    for ch in chapters_ordered:
        count = sum(1 for card in cards if card["chapter"] == ch)
        if count > 0:
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
    
    for conf in COURSES_CONFIG:
        if conf["type"] == "standalone":
            content = fetch_file_content(conf["repo"], conf["filename"])
            course_data = parse_standalone_course(conf, content)
        else:
            course_data = parse_beamer_course(conf, conf["folder"])
            
        all_courses.append(course_data)
        total_definitions += course_data["totalTerms"]
        print(f"[{course_data['code']}] {course_data['title']}: {course_data['totalTerms']} definitions across {len(course_data['chapters'])} chapters")
        
    output_data = {
        "totalCourses": len(all_courses),
        "totalDefinitions": total_definitions,
        "courses": all_courses
    }
    
    json_path = os.path.join(PROJECT_DIR, "definitions.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved structured JSON to {json_path}")
    
    js_path = os.path.join(PROJECT_DIR, "definitions.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("/**\n * definitions.js - Pre-compiled Math Flashcard Database\n * Auto-generated by sync_definitions.py\n */\n")
        f.write("window.FLASHCARD_DATA = ")
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        f.write(";\n")
    print(f"Saved global JS database to {js_path}")
    print(f"\nSync complete! Total courses: {len(all_courses)}, Total flashcards: {total_definitions}")

if __name__ == "__main__":
    main()
