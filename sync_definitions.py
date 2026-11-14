#!/usr/bin/env python3
"""
sync_definitions.py
Fetches LaTeX definitions from GitHub repos & Beamer lectures:
  - skitchwinters/MATH-301-Extras (Definitions_Hammack.tex) - Intro to Proofs
  - skitchwinters/MATH-410-Extras (Definitions.tex) - Abstract Algebra
  - skitchwinters/MATH-461-Extras (Definitions_Marsden.tex) - Real Analysis
  - skitchwinters/MATH-350-Extras (Definitions.tex) - Modern Geometry
  - Beamer-Lectures (MATH 140) - Calculus I
  - Beamer-Lectures (MATH 141) - Calculus II
  - Beamer-Lectures (MATH 102) - Precalculus & Trigonometry
Parses them into structured course/chapter/card data and outputs definitions.json and definitions.js.
Ensures 100% KaTeX compatibility, clean paragraph spacing, and proper HTML/math separation.
"""

import os
import re
import json
import base64
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolve Beamer-Lectures directory (sibling under Antigravity/projects or fallback to temp_beamer)
_CANDIDATE_BEAMER_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(PROJECT_DIR)), "Beamer-Lectures"),
    os.path.join(os.path.dirname(PROJECT_DIR), "Beamer-Lectures"),
    os.path.join(os.path.dirname(PROJECT_DIR), "temp_beamer"),
]
BEAMER_DIR = next((p for p in _CANDIDATE_BEAMER_DIRS if os.path.isdir(p)), _CANDIDATE_BEAMER_DIRS[0])

MATH_BLOCK_RE = re.compile(
    r"(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|(?<!\\)\$[^$]+?(?<!\\)\$|\\\([\s\S]*?\\\))"
)

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


def get_balanced_arg(text: str, start_pos: int):
    """Extract a balanced {...} argument starting at or after start_pos (skipping whitespace & <overlay>)."""
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
        if text[i] == '{' and (i == 0 or text[i - 1] != '\\'):
            depth += 1
        elif text[i] == '}' and (i == 0 or text[i - 1] != '\\'):
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
    return None, len(text)


def _math_ranges(text: str):
    """Return list of (start, end) spans for math delimiters in text."""
    return [(m.start(), m.end()) for m in MATH_BLOCK_RE.finditer(text)]


def _in_ranges(pos: int, ranges) -> bool:
    for s, e in ranges:
        if s <= pos < e:
            return True
    return False


def replace_cmd_outside_math(text: str, cmd: str, num_args: int, replacer, allow_inside_math: bool = False) -> str:
    """
    Replace occurrences of `\\cmd{arg1}...{argN}` using balanced brace matching.
    By default skips occurrences that begin inside math mode so KaTeX commands stay intact.
    """
    pattern = re.compile(r'\\' + re.escape(cmd) + r'(?=\s*(?:<[^>]*>\s*)?\{)')
    while True:
        ranges = [] if allow_inside_math else _math_ranges(text)
        changed = False
        out = []
        pos = 0
        for m in pattern.finditer(text):
            if m.start() < pos:
                continue
            if not allow_inside_math and _in_ranges(m.start(), ranges):
                continue
            cur = m.end()
            args = []
            ok = True
            for _ in range(num_args):
                arg, nxt = get_balanced_arg(text, cur)
                if arg is None:
                    ok = False
                    break
                args.append(arg)
                cur = nxt
            if not ok:
                continue
            out.append(text[pos:m.start()])
            out.append(replacer(*args))
            pos = cur
            changed = True
        if not changed:
            break
        out.append(text[pos:])
        text = ''.join(out)
    return text


def strip_outer_braces(text: str) -> str:
    """Strip outer {...} only when they wrap the entire string as a single balanced group."""
    text = text.strip()
    while text.startswith('{') and text.endswith('}'):
        depth = 0
        all_enclosed = True
        for i, ch in enumerate(text):
            if ch == '{' and (i == 0 or text[i - 1] != '\\'):
                depth += 1
            elif ch == '}' and (i == 0 or text[i - 1] != '\\'):
                depth -= 1
                if depth == 0 and i < len(text) - 1:
                    all_enclosed = False
                    break
        if all_enclosed and depth == 0:
            text = text[1:-1].strip()
        else:
            break
    return text


def clean_term(term: str) -> str:
    """Clean a card title/term using brace-balanced LaTeX unwrapping."""
    if not term:
        return "Definition"
    term = strip_outer_braces(term)
    term = replace_cmd_outside_math(term, "mbox", 1, lambda a: a, allow_inside_math=True)
    term = replace_cmd_outside_math(term, "phantom", 1, lambda _a: "", allow_inside_math=True)
    term = replace_cmd_outside_math(term, "textcolor", 2, lambda _c, body: body, allow_inside_math=True)
    term = replace_cmd_outside_math(term, "textbf", 1, lambda a: a)
    term = replace_cmd_outside_math(term, "textit", 1, lambda a: a)
    term = replace_cmd_outside_math(term, "emph", 1, lambda a: a)
    return strip_outer_braces(term)


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if re.match(r'^\s*%(?!%)', line):
            continue
        line = re.sub(r'(?<!\\)%.*$', '', line)
        lines.append(line)
    return '\n'.join(lines)


def _split_outside_math(text: str, sep: str):
    """Split text on `sep` only at top level (not inside math blocks or {...})."""
    parts = []
    ranges = _math_ranges(text)
    depth = 0
    last = 0
    i = 0
    n = len(text)
    slen = len(sep)
    while i < n:
        if _in_ranges(i, ranges):
            i += 1
            continue
        ch = text[i]
        if ch == '{' and (i == 0 or text[i - 1] != '\\'):
            depth += 1
        elif ch == '}' and (i == 0 or text[i - 1] != '\\') and depth > 0:
            depth -= 1
        elif depth == 0 and text.startswith(sep, i):
            parts.append(text[last:i])
            i += slen
            last = i
            continue
        i += 1
    parts.append(text[last:])
    return parts


def _convert_tabulars(text: str) -> str:
    """Convert \\begin{tabular}{colspec} ... \\end{tabular} using balanced brace matching on colspec."""
    start_tag = r'\begin{tabular}'
    end_tag = r'\end{tabular}'
    while True:
        idx = text.find(start_tag)
        if idx == -1:
            break
        colspec, after_spec = get_balanced_arg(text, idx + len(start_tag))
        if colspec is None:
            break
        end_idx = text.find(end_tag, after_spec)
        if end_idx == -1:
            break
        body = text[after_spec:end_idx]
        body = re.sub(r'\\(?:hline|toprule|midrule|bottomrule)\b', '', body)
        rows = [r.strip() for r in _split_outside_math(body, r'\\') if r.strip()]
        html = ['<div class="def-table-wrap"><table class="def-table">']
        for r in rows:
            cells = [_clean_fragment(c.strip()) for c in _split_outside_math(r, '&')]
            if any(cells):
                html.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
        html.append('</table></div>')
        replacement = '\n\n' + '\n'.join(html) + '\n\n'
        text = text[:idx] + replacement + text[end_idx + len(end_tag):]
    return text


def _convert_itemize(text: str) -> str:
    """Convert \\begin{itemize} ... \\end{itemize}, stripping \\setlength\\itemsep safely."""
    def replace_itemize(match):
        inner = match.group(1)
        # Strip \setlength{\itemsep}{...} or \setlength\itemsep{...} BEFORE splitting \item
        inner = re.sub(
            r'\\setlength\s*(?:\{[^}]*\}|\\[a-zA-Z]+)\s*\{[^}]*\}',
            '',
            inner
        )
        # Split only on actual \item commands (never \itemsep)
        parts = re.split(r'\\item(?:\s*\[([^\]]*)\])?(?=\s|$|\\)', inner)
        # parts = [preamble, opt1, body1, opt2, body2, ...]
        res = ['<ul class="def-list">']
        for i in range(1, len(parts), 2):
            label = (parts[i] or '').strip()
            body = (parts[i + 1] if i + 1 < len(parts) else '').strip()
            cleaned_body = _clean_fragment(body)
            if not cleaned_body:
                continue
            if label and label not in (r'\textbullet', '•', '-', '*'):
                label_clean = _clean_fragment(label)
                res.append(f'<li><span class="list-item-label">{label_clean}</span> {cleaned_body}</li>')
            else:
                res.append(f'<li>{cleaned_body}</li>')
        res.append('</ul>')
        return '\n\n' + '\n'.join(res) + '\n\n'

    return re.sub(r'\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}', replace_itemize, text)


def _convert_text_only_segment(seg: str) -> str:
    """Apply text-mode LaTeX cleanups to a segment guaranteed to be outside math delimiters."""
    # Remove leftover spacing/layout commands
    seg = re.sub(r'\\setlength\s*(?:\{[^}]*\}|\\[a-zA-Z]+)\s*\{[^}]*\}', '', seg)
    seg = re.sub(r'\\(?:vspace|hspace)\*?\s*\{[^}]*\}', '', seg)
    seg = re.sub(r'\\label\s*\{[^}]*\}', '', seg)
    seg = re.sub(
        r'\\(?:medskip|bigskip|smallskip|noindent|indent|rmfamily|par|centering|raggedright|tiny|small|footnotesize|scriptsize|large|Large)\b',
        '',
        seg
    )

    # Convert \hfill <tag> into clean inline axiom tag (e.g. MATH-461 vector space / metric axioms)
    seg = re.sub(r'\s*\\hfill\s*<strong>(.*?)</strong>', r' <span class="axiom-tag">\1</span>', seg)
    seg = re.sub(r'\s*\\hfill\s*', ' ', seg)

    # Quotes & dashes (ONLY in text segments, never in math!)
    seg = seg.replace('``', '“').replace("''", '”')
    seg = seg.replace('---', '—').replace('--', '–')

    # Ellipsis in text mode
    seg = re.sub(r'\\ldots\s*\\(?=\s|$)', '… ', seg)
    seg = re.sub(r'\\ldots\b', '…', seg)

    # Non-breaking space ~
    seg = seg.replace('~', ' ')

    # Explicit LaTeX line break \\ or \newline in text mode -> <br>, \linebreak -> space
    seg = re.sub(r'\\linebreak\b\s*', ' ', seg)
    seg = re.sub(r'\\newline\b\s*', '<br>\n', seg)
    seg = re.sub(r'\\\\\s*', '<br>\n', seg)

    # Escaped LaTeX punctuation in text mode
    seg = seg.replace(r'\&', '&amp;').replace(r'\%', '%').replace(r'\#', '#').replace(r'\_', '_')

    return seg


def _clean_fragment(text: str) -> str:
    """Clean a LaTeX definition fragment without extracting footnotes to top level."""
    text = _strip_comments(text)
    text = re.sub(r'^\s*\{\}\s*', '', text)

    # Convert standalone \begin{align*} ... \end{align*} into \[ \begin{aligned} ... \end{aligned} \]
    def replace_align(m):
        inner = m.group(1).strip()
        return f"\n\\[\n\\begin{{aligned}}\n{inner}\n\\end{{aligned}}\n\\]\n"
    text = re.sub(r'\\begin\{align\*?\}([\s\S]*?)\\end\{align\*?\}', replace_align, text)

    # Convert \begin{quote} and \begin{center}
    text = re.sub(
        r'\\begin\{quote\}([\s\S]*?)\\end\{quote\}',
        lambda m: f'\n\n<div class="def-quote">{_clean_fragment(m.group(1))}</div>\n\n',
        text
    )
    text = re.sub(
        r'\\begin\{center\}([\s\S]*?)\\end\{center\}',
        lambda m: f'\n\n<div class="def-center">{_clean_fragment(m.group(1))}</div>\n\n',
        text
    )

    # Convert \begin{tabular} and \begin{itemize}
    text = _convert_tabulars(text)
    text = _convert_itemize(text)

    # Strip \underline{\hspace{...}} rule dividers
    text = re.sub(r'\\underline\s*\{\s*\\hspace\*?\s*\{[^}]*\}\s*\}\s*(?:\\\\)?', '', text)

    # Convert brace-balanced text formatting & links ONLY when starting outside math mode
    text = replace_cmd_outside_math(
        text, "href", 2,
        lambda url, label: f'<a href="{url.strip()}" target="_blank" rel="noopener noreferrer" class="def-link">{label}</a>'
    )
    text = replace_cmd_outside_math(
        text, "url", 1,
        lambda url: f'<a href="{url.strip()}" target="_blank" rel="noopener noreferrer" class="def-link">{url.strip()}</a>'
    )
    text = replace_cmd_outside_math(text, "emph", 1, lambda body: f'<span class="emph">{body}</span>')
    text = replace_cmd_outside_math(text, "textbf", 1, lambda body: f'<strong>{body}</strong>')
    text = replace_cmd_outside_math(text, "textit", 1, lambda body: f'<em>{body}</em>')
    text = replace_cmd_outside_math(text, "underline", 1, lambda body: f'<u>{body}</u>')

    # Clean leftover {\tiny ...} attribution blocks (like MATH-410-c10)
    def replace_tiny_group(m):
        inner = m.group(1).strip()
        inner = re.sub(
            r'(https?://[^\s<]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer" class="def-link">\1</a>',
            inner
        )
        return f'\n\n<div class="def-footnote">{_convert_text_only_segment(inner)}</div>\n\n'
    text = re.sub(r'\{\s*\\tiny\s+([^{}]+)\}', replace_tiny_group, text)

    # Split into math vs non-math segments and clean ONLY non-math segments
    tokens = MATH_BLOCK_RE.split(text)
    cleaned_tokens = []
    for idx, tok in enumerate(tokens):
        if idx % 2 == 1:
            # Inside math mode: collapse any blank lines so app.js paragraph splitter never breaks display math
            tok = re.sub(r'\n\s*\n+', '\n', tok)
            cleaned_tokens.append(tok)
        else:
            cleaned_tokens.append(_convert_text_only_segment(tok))

    text = ''.join(cleaned_tokens)

    # Normalize spacing around display math delimiters
    text = re.sub(r'\s*\\\[\s*', r'\n\\[', text)
    text = re.sub(r'\s*\\\]\s*', r'\\]\n', text)
    text = re.sub(r'\n\s*\n(?:\s*\n)+', '\n\n', text)
    text = re.sub(r'\t+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def clean_latex_body(text: str) -> str:
    """Clean a full definition body, moving any \\footnote{...} citations cleanly to the bottom."""
    footnotes = []

    def capture_footnote(body):
        cleaned = _clean_fragment(body)
        if cleaned:
            footnotes.append(f'<div class="def-footnote">{cleaned}</div>')
        return ""

    text = _strip_comments(text)
    text = replace_cmd_outside_math(text, "footnote", 1, capture_footnote)
    cleaned = _clean_fragment(text)
    if footnotes:
        cleaned = cleaned + "\n\n" + "\n".join(footnotes)
    return cleaned.strip()


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
                if idx == -1:
                    break
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
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Beamer folder not found: {folder_path}")
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
            if idx == -1:
                break
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
