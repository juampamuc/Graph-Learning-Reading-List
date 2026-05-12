"""
Scrape DBLP HTML files and filter graph-learning papers.

Usage: python scrape_dblp.py <html_file> [html_file ...]

Example:
    python scrape_dblp.py ~/Downloads/dblp_AAAI\ 2026.html ~/Downloads/dblp_WWW\ 2026.html

Reads local DBLP HTML files, extracts paper titles/authors, filters for graph-learning
papers, and outputs {year}-{CONF}.txt in the current directory.

Conference name and year are auto-detected from the filename.
Filename convention: dblp_ {CONF} {YEAR}.html  (e.g. dblp_ AAAI 2026.html)
"""

import os
import re
import sys
import numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm


# ---- Graph filter ----
def graph_mask(title):
    t = title.lower()
    conditions = [
        "graph neural networks", "gnns", "gnn", "graph",
        "graph learning", "graph embedding", "network embedding",
    ]
    return np.any([c in t for c in conditions])


# ---- Parse local DBLP HTML ----
def parse_dblp_html(filepath, ul_slice=slice(1, None)):
    """Parse a local DBLP HTML file, return (titles, authors)."""
    print(f"  Reading: {os.path.basename(filepath)}")
    print(f"  Parsing HTML...")
    with open(filepath, "r", encoding="utf8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    all_uls = soup.find_all("ul", class_="publ-list")
    selected_uls = all_uls[ul_slice]
    print(f"  <ul> blocks: {len(all_uls)} (using {len(selected_uls)})")

    # Collect all paper entries first
    all_lis = []
    for ul in selected_uls:
        all_lis.extend(ul.find_all("li", class_="entry inproceedings"))

    titles, authors = [], []
    for li in tqdm(all_lis, desc="  Extracting papers", unit="paper"):
        title_el = li.find("span", class_="title")
        if not title_el:
            continue
        title = title_el.text
        author_list = [a.text for a in li.find_all("span", itemprop="name")]
        titles.append(title)
        authors.append(", ".join(author_list[:-1]))

    return titles, authors


def parse_with_fallback(filepath):
    """Try slice(1, None) first; if no papers found, fall back to slice(0, None)."""
    titles, authors = parse_dblp_html(filepath, ul_slice=slice(1, None))
    if len(titles) == 0:
        titles, authors = parse_dblp_html(filepath, ul_slice=slice(0, None))
    return titles, authors


# ---- Detect conf + year from filename ----
def detect_conf_year(filepath):
    """
    From 'dblp_ AAAI 2026.html' extract ('AAAI', '2026').
    Also handles 'dblp_ ACM SIGMOD Conference 2025 - Companion Volume.html'.
    """
    basename = os.path.basename(filepath)
    # Remove dblp_ prefix and .html suffix
    name = re.sub(r'^dblp_\s*', '', basename)
    name = re.sub(r'\.html$', '', name)

    known = [
        "AAAI", "ICLR", "WSDM", "WWW", "SIGIR", "IJCAI", "ICML",
        "KDD", "NeurIPS", "CIKM", "ICDE", "SIGMOD",
    ]
    for conf in known:
        pattern = re.compile(rf'\b{conf}\b', re.IGNORECASE)
        if pattern.search(name):
            year_match = re.search(r'\b(20\d{2})\b', name)
            year = year_match.group(1) if year_match else "????"
            return conf.upper(), year

    raise ValueError(f"Cannot detect conference/year from filename: {basename}")


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


# ---- Main ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_dblp.py <html_file> [html_file ...]")
        print("Example: python scrape_dblp.py ~/Downloads/dblp_AAAI\\ 2026.html")
        sys.exit(1)

    for filepath in sys.argv[1:]:
        if not os.path.exists(filepath):
            print(f"SKIP: file not found: {filepath}")
            continue

        print(f"\n{'='*60}")
        conf, year = detect_conf_year(filepath)
        print(f"Processing {conf}-{year}")

        try:
            titles, authors = parse_with_fallback(filepath)
            print(f"  Total papers: {len(titles)}")
            out_path = f"{year}-{conf}.txt"
            save_filtered(titles, authors, out_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
