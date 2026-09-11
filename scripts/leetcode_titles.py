#!/usr/bin/env python3
"""Give each LeetCode solution page an H1 naming its problem, and cross-link the
description and solution pages.

Why: Material's search plugin indexes a page under its first <h1>, falling back to
the nav or front-matter title only when no h1 exists (see create_entry_for_section
in material/plugins/search/plugin.py). Most solution.md files open with
`# Intuition` and never mention their problem number, so searching "3876" could not
reach the solution page even though every one of its sections was indexed.

Run against docs/leetcode/ *after* the copy in prepare.sh. docs/ is generated, so
the submodule and its GitBook publication stay untouched.
"""
import re
import sys
from pathlib import Path

DIFFICULTIES = ("Easy", "Medium", "Hard")

HEADING = re.compile(r"^( {0,3})(#{1,6})(\s|$)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SUMMARY_LINK = re.compile(r"\[([^\]]+)\]\(((?:Easy|Medium|Hard)/[^)]*?)/solution\.md\)")
# "3876.Construct-Uniform-Parity-Array-II", "122-Best-Time-...", "37. Sudoku Solver"
FOLDER = re.compile(r"^(\d+)[.\-\s]\s*(.*)$")

TO_DESCRIPTION = "[&larr; Problem statement](description.md)"
TO_SOLUTION = "[Solution &rarr;](solution.md)"


def scan(lines):
    """Yield (index, line, inside_code_fence) so callers never rewrite fenced text."""
    fence = None
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if fence is None:
            fence = m.group(1) if m else None
            yield i, line, fence is not None
        else:
            yield i, line, True
            # A closing fence uses the same character, is at least as long, and has
            # nothing after it.
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                if not line.strip()[len(m.group(1)):].strip():
                    fence = None


def first_heading(lines):
    """(index, level, text) of the first heading outside a code fence, or None."""
    for i, line, fenced in scan(lines):
        if fenced:
            continue
        m = HEADING.match(line)
        if m:
            return i, len(m.group(2)), line.strip().lstrip("#").strip()
    return None


def demote(lines):
    """Add one level to every heading outside a code fence. h6 is already the floor."""
    out = list(lines)
    for i, line, fenced in scan(lines):
        if fenced:
            continue
        m = HEADING.match(line)
        if m and len(m.group(2)) < 6:
            out[i] = f"{m.group(1)}#{line.lstrip(' ')}"
    return out


TAG = re.compile(r"<[^>]+>")


def description_title(folder):
    """The h1 of description.md, minus any <a> wrapper pasted in from LeetCode.

    This is the authoritative human title: the SUMMARY labels are generated from
    folder names by the submodule's tools/gen-summary.sh, so they lose hyphens and
    get title-cased ("Sort Array By Increasing Frequency", "Unique 3 Digit").
    """
    description = folder / "description.md"
    if not description.is_file():
        return None
    head = first_heading(description.read_text(encoding="utf-8").split("\n"))
    if head is None or head[1] != 1:
        return None
    text = re.sub(r"\s+", " ", TAG.sub("", head[2])).strip()
    return text if re.match(r"^\d+\.", text) else None


def title_for(folder, label):
    """description.md's h1, else the SUMMARY label, else the folder name."""
    from_description = description_title(folder)
    if from_description:
        return from_description
    if label and re.match(r"^\d+\.", label):
        return label
    m = FOLDER.match(folder.name)
    if not m:
        return label or folder.name
    name = re.sub(r"\s+", " ", m.group(2).replace("-", " ")).strip()
    return f"{m.group(1)}. {name}" if name else m.group(1)


def problem_number(folder):
    m = FOLDER.match(folder.name)
    return m.group(1) if m else None


def insert_after(lines, index, block):
    """Put `block` just after lines[index], keeping one blank line either side."""
    at = index + 1
    while at < len(lines) and not lines[at].strip():
        at += 1
    return lines[: index + 1] + ["", *block, ""] + lines[at:]


def parse_summary(path):
    path = Path(path)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    return {folder: label.strip() for label, folder in SUMMARY_LINK.findall(text)}


def main(docs_root, summary_path):
    docs_root = Path(docs_root)
    labels = parse_summary(summary_path)
    titled = kept = linked = 0

    for difficulty in DIFFICULTIES:
        base = docs_root / difficulty
        if not base.is_dir():
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            solution = folder / "solution.md"
            if not solution.is_file():
                continue

            title = title_for(folder, labels.get(f"{difficulty}/{folder.name}"))
            number = problem_number(folder)
            description = folder / "description.md"

            lines = solution.read_text(encoding="utf-8").split("\n")
            head = first_heading(lines)

            # Some solutions already lead with their own numbered H1 — leave those
            # structurally alone, they are correct as written.
            already_titled = (
                head is not None
                and head[1] == 1
                and number is not None
                and re.match(rf"^{re.escape(number)}[.\s]", head[2])
            )
            if already_titled:
                heading_index = head[0]
                kept += 1
                # Several of these h1s were themselves derived from the folder name
                # ("719. Find K th Smallest Pair Distance"). If the description
                # carries the real LeetCode title, prefer it so both pages agree.
                canonical = description_title(folder)
                if canonical and canonical != head[2]:
                    lines[heading_index] = f"# {canonical}"
            else:
                lines = [f"# {title}", ""] + demote(lines)
                heading_index = 0
                titled += 1

            if description.is_file():
                lines = insert_after(lines, heading_index, [TO_DESCRIPTION])
                linked += 1
            solution.write_text("\n".join(lines), encoding="utf-8")

            if description.is_file():
                dlines = description.read_text(encoding="utf-8").split("\n")
                dhead = first_heading(dlines)
                if dhead is not None and dhead[1] == 1:
                    dlines = insert_after(dlines, dhead[0], [TO_SOLUTION])
                else:
                    dlines = [f"# {title}", "", TO_SOLUTION, ""] + dlines
                description.write_text("\n".join(dlines), encoding="utf-8")

    print(
        f"LeetCode titles: {titled} solution page(s) retitled, {kept} already numbered, "
        f"{linked} cross-linked with a description"
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
