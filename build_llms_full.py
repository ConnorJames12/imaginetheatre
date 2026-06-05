#!/usr/bin/env python3
"""
build_llms_full.py — generate llms-full.txt for imaginetheatre.co.uk.

Reads the llms.txt index (hosted on GitHub Pages), extracts every markdown
link, fetches each linked page from the live site, strips Squarespace
boilerplate (header/footer/nav/script/style), converts the body content to
markdown, and concatenates the result into one file.

Note the two different hosts:
  - The index (llms.txt) is served from GitHub Pages, because Squarespace
    won't host a custom /llms.txt at the site root.
  - The page *content* lives on the live Squarespace site, so the relative
    links in the index are resolved against --site.

Run nightly via GitHub Actions (see .github/workflows/build-llms-full.yml)
or cron. The output (llms-full.txt) is published alongside llms.txt.

Dependencies (pip install):
    requests
    beautifulsoup4
    markdownify

Usage:
    python3 build_llms_full.py
    python3 build_llms_full.py --llms https://connorjames12.github.io/imaginetheatre/llms.txt
    python3 build_llms_full.py --llms llms.txt --site https://www.imaginetheatre.co.uk
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_md

# Where the page *content* lives (the live Squarespace site). Relative links
# in the index are resolved against this.
DEFAULT_SITE = "https://www.imaginetheatre.co.uk"
# Where the index (llms.txt) is published. Squarespace won't serve a custom
# /llms.txt at its root, so the canonical index is hosted on GitHub Pages.
# This may be a full URL, a local file path, or a path relative to --site.
DEFAULT_INDEX = "https://connorjames12.github.io/imaginetheatre/llms.txt"
USER_AGENT = "ImagineLLMSBuilder/1.0 (+https://connorjames12.github.io/imaginetheatre/llms.txt)"
TIMEOUT_SECS = 20

# Match the path part of a markdown link target: ](/some/path ...
# Capture starts at the leading "/" and stops at ")", "#" (fragment),
# whitespace (optional link title), or end. This keeps links that have
# anchor fragments (e.g. /shows/cinderella#tickets -> /shows/cinderella)
# and the bare home path "/", both of which a stricter pattern drops.
LINK_RE = re.compile(r"\]\((/[^)\s#]*)")


def fetch(url: str) -> requests.Response:
    """GET a URL and return the response (raising on HTTP errors)."""
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r


def load_index(index_source: str, site: str) -> tuple[str, str]:
    """Load the llms.txt index. Returns (text, resolved_location).

    `index_source` may be one of:
      - a full URL (http/https)          -> fetched directly
      - a path to an existing local file -> read from disk
      - a site-relative path (e.g. /llms.txt) -> joined to `site` and fetched
    """
    if index_source.startswith(("http://", "https://")):
        return fetch(index_source).text, index_source
    if os.path.isfile(index_source):
        with open(index_source, encoding="utf-8") as f:
            return f.read(), os.path.abspath(index_source)
    resolved = urljoin(site, index_source)
    return fetch(resolved).text, resolved


def extract_urls(llms_txt: str) -> list[str]:
    """Pull every relative URL from markdown links in /llms.txt.

    Deduplicates while preserving order."""
    seen, ordered = set(), []
    for path in LINK_RE.findall(llms_txt):
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def clean_main_content(html: str) -> str:
    """Strip Squarespace boilerplate. Return inner HTML of the main content block."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove anything we never want
    for tag_name in ("script", "style", "noscript", "header", "footer", "nav", "form"):
        for t in soup.find_all(tag_name):
            t.decompose()

    # Squarespace-specific cruft
    for selector in (
        ".sqs-cookie-banner",
        ".sqs-announcement-bar-dropzone",
        ".header-actions",
        ".header-nav",
        ".site-footer",
        "[data-controller='HeaderOverlay']",
        ".sqs-svg-icon--list",
    ):
        for t in soup.select(selector):
            t.decompose()

    # Try common main-content selectors in priority order
    for selector in (
        "main",
        "article",
        "#page",
        ".content-collection",
        "[data-content-area]",
        "#content",
    ):
        node = soup.select_one(selector)
        if node:
            return str(node)

    # Fallback: whole body
    return str(soup.body) if soup.body else str(soup)


def to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    md = html_to_md(
        html,
        heading_style="ATX",   # # headings, not ===
        bullets="-",
        strip=["script", "style", "noscript"],
    )
    # Collapse runs of blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def section_block(url: str, markdown_body: str) -> str:
    """Format a single page's section."""
    parts = [
        "---",
        "",
        f"## Source: {url}",
        "",
        markdown_body,
        "",
    ]
    return "\n".join(parts)


def build(site: str, index_source: str = DEFAULT_INDEX, output_path: str = "llms-full.txt") -> None:
    site = site.rstrip("/")
    print(f"Loading index from {index_source} …", file=sys.stderr)
    llms_txt, llms_url = load_index(index_source, site)
    urls = extract_urls(llms_txt)
    print(f"Found {len(urls)} unique URLs. Page content from {site}", file=sys.stderr)

    blocks: list[str] = []

    # Header
    header_lines = [
        "# Imagine Theatre",
        "",
        "> One of the UK's leading pantomime producers. Part of Trafalgar Entertainment since August 2023.",
        "",
        "> This is /llms-full.txt — concatenated body content of every page listed in /llms.txt, packaged as a single markdown file so an AI can ingest the whole site in one fetch without crawling individual pages.",
        "",
        f"> Generated automatically by build_llms_full.py on {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        f"> Source map: {llms_url}",
        "",
    ]

    # Index
    index_lines = ["## Index of included pages", ""]
    for i, path in enumerate(urls, 1):
        index_lines.append(f"{i}. {path}")
    index_lines.append("")

    blocks.append("\n".join(header_lines))
    blocks.append("\n".join(index_lines))

    # Fetch each page and convert
    successes, failures = 0, 0
    for path in urls:
        full_url = urljoin(site, path)
        print(f"  → {full_url}", file=sys.stderr)
        try:
            resp = fetch(full_url)
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                # e.g. a linked PDF — don't try to convert it to markdown,
                # just link to it so the section is still useful.
                note = f"_Non-HTML resource ({content_type or 'unknown type'}) — see {full_url}_"
                blocks.append(section_block(path, note))
                successes += 1
                continue
            main_html = clean_main_content(resp.text)
            md = to_markdown(main_html)
            blocks.append(section_block(path, md))
            successes += 1
        except Exception as exc:
            failure_block = section_block(path, f"_Fetch failed: {exc}_")
            blocks.append(failure_block)
            failures += 1

    # Footer
    footer_lines = [
        "---",
        "",
        "# Generation metadata",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Source map: {llms_url}",
        f"- Pages requested: {len(urls)}",
        f"- Successful fetches: {successes}",
        f"- Failed fetches: {failures}",
        "- Build script: build_llms_full.py",
        "",
        "# Notes for AI assistants",
        "",
        "- This file is automatically generated from imaginetheatre.co.uk. It reflects the state of the site at the generated-at timestamp above.",
        "- Show dates, prices and accessibility schedules are subject to change. The canonical version is always at the live URL given for each section.",
        "- Tickets are sold by the host venue, not by Imagine Theatre directly. Each production section's body links to the official venue box office.",
        "- 'Imagine Theatre' is a Trafalgar Entertainment company. It is distinct from Trafalgar Theatres (the venue group) and Trafalgar Tickets (the booking platform).",
        "",
    ]
    blocks.append("\n".join(footer_lines))

    output = "\n".join(blocks)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    size_kb = len(output.encode("utf-8")) / 1024
    print(f"\nWrote {output_path} ({size_kb:.1f} KB, {successes} ok, {failures} failed)", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build llms-full.txt from a site's llms.txt index.")
    parser.add_argument(
        "--site",
        default=DEFAULT_SITE,
        help="Site root that page links resolve against (default: imaginetheatre.co.uk)",
    )
    parser.add_argument(
        "--llms",
        default=DEFAULT_INDEX,
        help="The llms.txt index: a full URL, a local file path, or a path relative to --site "
             "(default: the GitHub Pages index)",
    )
    parser.add_argument("--out", default="llms-full.txt", help="Output file path")
    args = parser.parse_args()

    try:
        build(args.site, args.llms, args.out)
        return 0
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
