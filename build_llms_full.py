#!/usr/bin/env python3
"""
build_llms_full.py — generate llms-full.txt for imaginetheatre.co.uk.

Fetches /llms.txt, extracts every markdown link, fetches each linked page,
strips Squarespace boilerplate (header/footer/nav/script/style), converts
the body content to markdown, and concatenates the result into one file.

Run nightly via cron, GitHub Actions or a Cloudflare Worker.
Output (llms-full.txt) gets uploaded back to the host (Cloudflare Workers
KV, GitHub Pages, S3, etc.) at the same external URL that /llms.txt
redirects to on imaginetheatre.co.uk.

Dependencies (pip install):
    requests
    beautifulsoup4
    markdownify

Usage:
    python3 build_llms_full.py [--site https://www.imaginetheatre.co.uk] [--out llms-full.txt]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_md

DEFAULT_SITE = "https://www.imaginetheatre.co.uk"
USER_AGENT = "ImagineLLMSBuilder/1.0 (+https://www.imaginetheatre.co.uk/llms.txt)"
TIMEOUT_SECS = 20

# Match the path part of a markdown link target: ](/some/path ...
# Capture starts at the leading "/" and stops at ")", "#" (fragment),
# whitespace (optional link title), or end. This keeps links that have
# anchor fragments (e.g. /shows/cinderella#tickets -> /shows/cinderella)
# and the bare home path "/", both of which a stricter pattern drops.
LINK_RE = re.compile(r"\]\((/[^)\s#]*)")


def fetch(url: str) -> str:
    """GET a URL and return text."""
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.text


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


def build(site: str, llms_txt_path: str = "/llms.txt", output_path: str = "llms-full.txt") -> None:
    site = site.rstrip("/")
    llms_url = urljoin(site, llms_txt_path)
    print(f"Fetching {llms_url} …", file=sys.stderr)
    llms_txt = fetch(llms_url)
    urls = extract_urls(llms_txt)
    print(f"Found {len(urls)} unique URLs.", file=sys.stderr)

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
            html = fetch(full_url)
            main_html = clean_main_content(html)
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
    parser = argparse.ArgumentParser(description="Build llms-full.txt from a site's /llms.txt index.")
    parser.add_argument("--site", default=DEFAULT_SITE, help="Site root URL (default: imaginetheatre.co.uk)")
    parser.add_argument("--llms", default="/llms.txt", help="Path to llms.txt on the site")
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
