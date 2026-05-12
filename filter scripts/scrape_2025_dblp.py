"""
Scrape 2025 conference papers from local DBLP HTML files and filter graph-learning papers.

Usage: cd "filter scripts" && python scrape_2025_dblp.py

Reads from ~/Downloads/dblp_*.html files (manually downloaded from DBLP).
Missing files are skipped with a message.
Each conference outputs a 2025-{CONF}.txt file in the current directory.
"""

import os
import glob
import numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm

DOWNLOADS = os.path.expanduser("~/Downloads")


# ---- Graph filter (same keywords as existing notebooks) ----
def graph_mask(title):
    t = title.lower()
    conditions = [
        "graph neural networks", "gnns", "gnn", "graph",
        "graph learning", "graph embedding", "network embedding",
    ]
    return np.any([c in t for c in conditions])


# ---- Parse local DBLP HTML file ----
def parse_dblp_html(filepath, ul_slice=slice(1, None)):
    """
    filepath : path to a local DBLP HTML file
    ul_slice : slice(start, end) to select which <ul class='publ-list'> blocks to parse.
    """
    print(f"  Reading: {os.path.basename(filepath)}")
    with open(filepath, "r", encoding="utf8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    all_uls = soup.find_all("ul", class_="publ-list")
    selected_uls = all_uls[ul_slice]
    if len(all_uls) > 1:
        print(f"  <ul> blocks: {len(all_uls)}, using {ul_slice}")

    titles, authors = [], []
    for ul in selected_uls:
        articles = ul.find_all("li", class_="entry inproceedings")
        for li in articles:
            title_el = li.find("span", class_="title")
            if not title_el:
                continue
            title = title_el.text
            author_list = [a.text for a in li.find_all("span", itemprop="name")]
            # last "name" span is often empty/editor placeholder
            titles.append(title)
            authors.append(", ".join(author_list[:-1]))

    return titles, authors


# ---- Write filtered results ----
def save_filtered(titles, authors, out_path):
    count = 0
    with open(out_path, "w", encoding="utf8") as fw:
        for t, n in zip(titles, authors):
            if graph_mask(t):
                fw.write(f"1. **{t}**\n\n")
                fw.write(f"    *{n}*\n\n")
                count += 1
    print(f"  Graph papers: {count} / {len(titles)} total  -> {out_path}")


def find_file(pattern):
    """Find a single HTML file in ~/Downloads matching the pattern (case-insensitive)."""
    pattern_lower = pattern.lower()
    for fp in glob.glob(os.path.join(DOWNLOADS, "dblp_*.html")):
        basename = os.path.basename(fp).lower()
        if pattern_lower in basename:
            return fp
    return None


# ---- Conference definitions ----
# (name, file_search_pattern, ul_slice, [multi_file_patterns])
# Use multi_file_patterns list for conferences split across multiple HTML files.
CONFERENCES = [
    ("ICLR",   "ICLR 2025",   slice(1, None)),
    ("WSDM",   "WSDM 2025",   slice(1, None)),
    ("WWW",    "WWW 2025",    slice(1, None)),
    ("IJCAI",  "IJCAI 2025",  slice(1, None)),
    ("ICML",   "ICML 2025",   slice(1, None)),
    ("CIKM",   "CIKM 2025",   slice(1, None)),
    ("ICDE",   "ICDE 2025",   slice(0, None)),  # only 1 <ul>, papers start at ul[0]
    ("SIGMOD", "SIGMOD Conference 2025", slice(1, None)),
    # KDD split into two files:
    ("KDD",    None,          slice(1, None)),
    # NeurIPS 2025 not yet on DBLP:
    # ("NeurIPS","NeurIPS 2025", slice(1, None)),
]

# Already done: AAAI-2025, SIGIR-2025 (in README already)

# KDD handled separately — two files combined
KDD_PATTERNS = ["KDD 2025.html", "KDD 2025-2.html"]


if __name__ == "__main__":
    for entry in CONFERENCES:
        name = entry[0]

        print(f"\n{'='*60}")
        print(f"Processing {name}-2025")
        print(f"{'='*60}")

        try:
            if name == "KDD":
                # Special case: KDD split across two files
                fps = []
                for pat in KDD_PATTERNS:
                    fp = find_file(pat)
                    if fp:
                        fps.append(fp)
                    else:
                        print(f"  WARNING: {pat} not found in ~/Downloads/")
                if not fps:
                    print(f"  SKIP: no KDD files found.")
                    continue
                all_titles, all_authors = [], []
                for fp in sorted(fps):
                    titles, authors = parse_dblp_html(fp, ul_slice=slice(1, None))
                    print(f"  Papers from this file: {len(titles)}")
                    all_titles.extend(titles)
                    all_authors.extend(authors)
                print(f"  Total papers: {len(all_titles)}")
                save_filtered(all_titles, all_authors, f"2025-{name}.txt")
            else:
                pattern = entry[1]
                ul_slc = entry[2]
                fp = find_file(pattern)
                if not fp:
                    print(f"  SKIP: no file matching '{pattern}' in ~/Downloads/")
                    continue
                titles, authors = parse_dblp_html(fp, ul_slice=ul_slc)
                print(f"  Total papers: {len(titles)}")
                save_filtered(titles, authors, f"2025-{name}.txt")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            print(f"  Skipping {name}-2025.")
