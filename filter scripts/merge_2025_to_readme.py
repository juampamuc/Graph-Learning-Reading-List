"""
Merge generated 2025-{CONF}.txt files into README.md.

Usage: python merge_2025_to_readme.py

Run this AFTER scrape_2025_dblp.py has generated the .txt files.
Inserts new 2025 sections into README.md in TOC order and updates the TOC line.
"""

import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, "..", "README.md")

# TOC order for 2025, matching the 2024 ordering convention:
#   IJCAI, ICML, KDD, SIGIR, NeurIPS, CIKM, AAAI, ICLR, WSDM, WWW, ICDE, SIGMOD
#
# Conferences already in README (SIGIR, AAAI) act as boundary anchors.
# Group A: before AAAI-2025  (insert right after SIGIR-2025 section)
# Group B: after  AAAI-2025  (insert right before IJCAI-2024 section)
#
# NeurIPS is in the ordering but skipped until the HTML file is available.

TOC_ORDER_2025 = [
    "IJCAI", "ICML", "KDD", "SIGIR", "NeurIPS", "CIKM",
    "AAAI", "ICLR", "WSDM", "WWW", "ICDE", "SIGMOD",
]

# These are already in README.md as full sections — do NOT re-insert.
EXISTING_IN_README = {"AAAI", "SIGIR"}


def read_txt(conf_name):
    """Read a generated .txt file, return its content as a string."""
    filepath = os.path.join(SCRIPT_DIR, f"2025-{conf_name}.txt")
    if not os.path.exists(filepath):
        print(f"  SKIP: {filepath} not found.")
        return None
    with open(filepath, "r", encoding="utf8") as f:
        content = f.read().strip()
    if not content:
        print(f"  SKIP: {filepath} is empty.")
        return None
    return content


def build_section(conf_name, content):
    header = f"### [{conf_name}-2025](#contents)"
    return header + "\n" + content


def main():
    with open(README_PATH, "r", encoding="utf8") as f:
        readme = f.read()

    # ---- Step 1: Collect new sections in TOC order ----
    group_a = []  # before AAAI-2025
    group_b = []  # after AAAI-2025, before IJCAI-2024
    past_aaai = False

    for conf in TOC_ORDER_2025:
        if conf in EXISTING_IN_README:
            if conf == "AAAI":
                past_aaai = True
            continue

        content = read_txt(conf)
        if content is None:
            continue

        section = build_section(conf, content)
        if past_aaai:
            group_b.append(section)
        else:
            group_a.append(section)

        print(f"  Loaded 2025-{conf}.txt ({content.count(chr(10))} lines)")

    if not group_a and not group_b:
        print("No new sections to add.")
        return

    # ---- Step 2: Insert group A before AAAI-2025 ----
    anchor_a = "### [AAAI-2025](#contents)"
    if group_a:
        insert_a = "\n\n" + "\n\n".join(group_a) + "\n\n"
        readme = readme.replace("\n" + anchor_a, insert_a + anchor_a)

    # ---- Step 3: Insert group B before IJCAI-2024 ----
    anchor_b = "### [IJCAI-2024](#contents)"
    if group_b:
        insert_b = "\n\n" + "\n\n".join(group_b) + "\n\n"
        readme = readme.replace("\n" + anchor_b, insert_b + anchor_b)

    # ---- Step 4: Rebuild the 2025 TOC line ----
    toc_items = []
    for conf in TOC_ORDER_2025:
        txt_path = os.path.join(SCRIPT_DIR, f"2025-{conf}.txt")
        if conf in EXISTING_IN_README or os.path.exists(txt_path):
            toc_items.append(f"[{conf}-2025](#{conf.lower()}-2025)")

    new_toc_line = "  - " + " ".join(toc_items)

    old_line_pattern = r"  - \[AAAI-2025\].*\[SIGIR-2025\].*\n"
    readme = re.sub(old_line_pattern, new_toc_line + "\n", readme)

    # ---- Write back ----
    with open(README_PATH, "w", encoding="utf8") as f:
        f.write(readme)

    added = len(group_a) + len(group_b)
    print(f"\nDone. Added {added} sections to README.md (Group A: {len(group_a)}, Group B: {len(group_b)})")


if __name__ == "__main__":
    main()
