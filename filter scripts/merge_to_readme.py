"""
Merge generated {year}-{CONF}.txt files into README.md in TOC order.

Usage: python merge_to_readme.py <txt_file> [txt_file ...]

Example:
    python merge_to_readme.py 2026-AAAI.txt 2026-WWW.txt

Inserts each conference section into README.md at the correct position
following the canonical TOC order, and updates/creates the TOC line for each year.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, "..", "README.md")

# Canonical TOC order (same as 2022-2024 README conventions)
TOC_ORDER = [
    "IJCAI", "ICML", "KDD", "SIGIR", "NeurIPS", "CIKM",
    "AAAI", "ICLR", "WSDM", "WWW", "ICDE", "SIGMOD",
]


def parse_filename(filename):
    """From '2026-AAAI.txt' extract ('AAAI', '2026')."""
    basename = os.path.basename(filename)
    m = re.match(r'(\d{4})-(\w+)\.txt$', basename)
    if not m:
        raise ValueError(f"Cannot parse year/conf from: {basename}")
    return m.group(2).upper(), m.group(1)


def read_txt(filepath):
    with open(filepath, "r", encoding="utf8") as f:
        content = f.read().strip()
    return content if content else None


def build_section(conf, year, content):
    header = f"### [{conf}-{year}](#contents)"
    return header + "\n" + content


def toc_index(conf):
    """Return the TOC_ORDER index for a conference."""
    try:
        return TOC_ORDER.index(conf.upper())
    except ValueError:
        return len(TOC_ORDER)


# ---- Section insertion helpers ----

def find_anchor_after(conf, year, readme):
    """Find the section header that should come AFTER `conf` in the same year."""
    idx = toc_index(conf)
    for next_conf in TOC_ORDER[idx + 1:]:
        m = re.search(rf"### \[{next_conf}-{year}\]", readme)
        if m:
            return m.group(0)
    return None


def find_first_section_of_year(year, readme):
    """Find the first section header (by TOC order) of the given year."""
    for conf in TOC_ORDER:
        m = re.search(rf"### \[{conf}-{year}\]", readme)
        if m:
            return m.group(0)
    return None


def find_next_older_year_anchor(year, readme):
    """Find the first section header of the closest older year (e.g. 2025 for 2026)."""
    best = None
    best_year = None
    for m in re.finditer(r"### \[\w+-(\d{4})\]\(#contents\)", readme):
        y = int(m.group(1))
        if y < int(year):
            if best_year is None or y > best_year:
                best_year = y
                best = m.group(0)
    return best


# ---- TOC line management ----

def get_all_years(readme):
    """Return sorted list of years (descending) that have sections in README."""
    years = set()
    for m in re.finditer(r"### \[\w+-(\d{4})\]", readme):
        years.add(m.group(1))
    return sorted(years, reverse=True)


def rebuild_toc(readme):
    """Rebuild the full TOC section based on current section headers."""
    years = get_all_years(readme)

    lines = readme.split("\n")
    # Locate TOC boundaries
    toc_header_idx = None
    old_toc_start = None
    old_toc_end = None

    for i, line in enumerate(lines):
        if line.strip() == "## [Contents]" and "## [Contents](#contents)" in line:
            toc_header_idx = i
        if toc_header_idx is not None and i > toc_header_idx:
            if line.startswith("  - [") or line.startswith("  - ["):
                if old_toc_start is None:
                    old_toc_start = i
                old_toc_end = i
            elif old_toc_end is not None and not line.startswith("  -"):
                break

    if toc_header_idx is None:
        return readme

    # Remove old TOC lines
    if old_toc_start is not None:
        del lines[old_toc_start:old_toc_end + 1]

    # Build new TOC lines
    new_toc_lines = []
    for year in years:
        items = []
        for conf in TOC_ORDER:
            if re.search(rf"### \[{conf}-{year}\]", readme):
                items.append(f"[{conf}-{year}](#{conf.lower()}-{year})")
        # Also include non-standard conferences present in this year
        for m in re.finditer(rf"### \[(\w+)-{year}\]", readme):
            c = m.group(1)
            if c not in TOC_ORDER:
                items.append(f"[{c}-{year}](#{c.lower()}-{year})")
        if items:
            new_toc_lines.append("  - " + " ".join(items))

    # Insert new TOC lines after the toc header
    insert_at = toc_header_idx + 1
    for tline in reversed(new_toc_lines):
        lines.insert(insert_at, tline)

    return "\n".join(lines)


# ---- Main ----

def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_to_readme.py <txt_file> [txt_file ...]")
        print("Example: python merge_to_readme.py 2026-AAAI.txt 2026-WWW.txt")
        sys.exit(1)

    # Collect sections grouped by year
    sections_by_year = {}  # year -> [(conf, section_text), ...]
    for filepath in sys.argv[1:]:
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found — skipping.")
            continue
        conf, year = parse_filename(filepath)
        content = read_txt(filepath)
        if not content:
            print(f"WARNING: {filepath} is empty — skipping.")
            continue
        sections_by_year.setdefault(year, []).append((conf, build_section(conf, year, content)))
        print(f"  Loaded {year}-{conf} ({content.count(chr(10))} lines)")

    if not sections_by_year:
        print("No valid sections to merge.")
        sys.exit(0)

    with open(README_PATH, "r", encoding="utf8") as f:
        readme = f.read()

    # Insert sections year by year (newest first)
    for year in sorted(sections_by_year.keys(), reverse=True):
        entries = sections_by_year[year]
        entries.sort(key=lambda x: toc_index(x[0]))
        confs_str = ", ".join(c for c, _ in entries)

        # Determine if this year already has sections in README
        existing = bool(re.search(rf"### \[\w+-{year}\]", readme))

        if existing:
            # Insert each new section at its TOC-ordered position
            for conf, section_text in entries:
                if re.search(rf"### \[{conf}-{year}\]", readme):
                    print(f"    {conf}-{year} already exists in README — skipping.")
                    continue
                anchor = find_anchor_after(conf, year, readme)
                if anchor:
                    readme = readme.replace(
                        "\n" + anchor,
                        "\n\n" + section_text + "\n\n" + anchor
                    )
                else:
                    # Last in TOC order — insert before next older year
                    anchor = find_next_older_year_anchor(year, readme)
                    if anchor:
                        readme = readme.replace(
                            "\n" + anchor,
                            "\n\n" + section_text + "\n\n" + anchor
                        )
                print(f"    Inserted {conf}-{year}")
        else:
            # New year — insert all its sections before the closest older year
            print(f"  New year {year}, inserting sections: {confs_str}")
            anchor = find_next_older_year_anchor(year, readme)
            if anchor:
                block = "\n\n".join(s for _, s in entries)
                readme = readme.replace(
                    "\n" + anchor,
                    "\n\n" + block + "\n\n" + anchor
                )
            else:
                print(f"    WARNING: Could not find insertion point for {year}")

    # Rebuild TOC
    readme = rebuild_toc(readme)

    with open(README_PATH, "w", encoding="utf8") as f:
        f.write(readme)

    total = sum(len(v) for v in sections_by_year.values())
    print(f"\nDone. Updated {README_PATH} with {total} sections.")


if __name__ == "__main__":
    main()
