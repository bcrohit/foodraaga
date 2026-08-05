"""Identify ingestible page ranges from a PDF table of contents.

Uses pymupdf-style TOC entries: [(level, title, page), ...].
"""

import re

# Exact titles after normalization (front/back matter, publisher pages, etc.)
SKIP_EXACT = {
    "cover",
    "title",
    "title page",
    "half title",
    "copyright",
    "colophon",
    "contents",
    "table of contents",
    "dedication",
    "glossary",
    "references",
    "selected references",
    "bibliography",
    "methodology",
    "afterword",
    "conversions",
    "contributors",
    "permissions",
    "food",  # half-title leftover in some chemistry editions
    "follow penguin",
    "internet recommendations",
    "author bio",
    "the birth of this book",
}

# Prefixes that catch variants ("Preface to the Seventh Edition", "Also by …")
SKIP_PREFIXES = (
    "about the author",
    "also by ",
    "other books by",
    "appendix",
    "appendices",
    "preface",
    "foreword",
    "list of ",
    "praise for ",
    "acknowledg",  # acknowledgements / acknowledgments
    "further reading",
    "tips for further",
)

# Recipe/Subject/Dietary Index, plain Index, etc.
INDEX_RE = re.compile(r"\bindex\b")


def norm(title: str) -> str:
    title = title.replace("\n", " ").replace("\r", " ")
    title = title.lower()
    title = re.sub(r"\s+", " ", title)
    title = title.strip(" .:-\t")
    # Some TOCs bake the page into the title ("Index 218", "Foreword 6")
    return re.sub(r"\s+\d+$", "", title)


def is_boilerplate(title: str) -> bool:
    """True for front/back matter and other non-ingestible TOC entries."""
    t = norm(title)
    if not t:
        return True
    if t in SKIP_EXACT:
        return True
    if INDEX_RE.search(t):
        return True
    return any(t.startswith(p) for p in SKIP_PREFIXES)


def _level1_entries(toc: list) -> list[tuple[str, int]]:
    entries = [(title, page) for level, title, page in toc if level == 1]
    if len(entries) < 2:
        entries = [(title, page) for _, title, page in toc]
    return entries


def useful_sections(toc: list, page_count: int) -> list[tuple[str, int, int]]:
    """
    Return non-boilerplate TOC sections as (title, start_page, end_page).

    end_page is inclusive and stops at the next TOC entry with a later page
    (so skipped entries like Acknowledgments create gaps).
    """
    assert page_count > 0, "page_count must be positive"
    entries = _level1_entries(toc)
    if not entries:
        return []

    sections = []
    for i, (title, page) in enumerate(entries):
        if is_boilerplate(title):
            continue

        end = page_count
        for _, next_page in entries[i + 1 :]:
            if next_page > page:
                end = next_page - 1
                break

        if end >= page:
            sections.append((title, page, end))

    return sections


def useful_page_ranges(toc: list, page_count: int) -> list[tuple[int, int]]:
    """Merged inclusive (start, end) page ranges ready for extraction."""
    ranges: list[tuple[int, int]] = []
    for _, start, end in useful_sections(toc, page_count):
        if ranges and start <= ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
        else:
            ranges.append((start, end))
    return ranges
