import csv
import logging
import re
from collections import Counter
from pathlib import Path
from typing import List, Tuple, Set, Optional

from nodes.tmx_loader import parse_tmx_file

logger = logging.getLogger(__name__)

# A *very* small English stop-word list – not language-specific but good enough
STOPWORDS: Set[str] = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "in",
    "on",
    "at",
    "for",
    "with",
    "to",
    "from",
    "by",
    "of",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "as",
    "about",
    "into",
    "over",
    "after",
    "before",
    "between",
    "among",
    "within",
    "without",
    "against",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical(code: str) -> str:
    return code.lower().split("-")[0].split("_")[0]


def _tokenise(text: str) -> List[str]:
    """A naive tokenizer that keeps diacritics and apostrophes."""
    return re.findall(r"[A-Za-zÀ-ÿ\u00f1\u00d1'-]+", text)


# ---------------------------------------------------------------------------
# TMX-based extraction
# ---------------------------------------------------------------------------

def _collect_tmx_entries(
    tmx_data: dict, source_language: str, target_language: str
) -> List[Tuple[str, str]]:
    src_base = _canonical(source_language)
    tgt_base = _canonical(target_language)
    entries: List[Tuple[str, str]] = []

    # 1) Exact key --------------------------------------------------------
    key = f"{src_base}->{tgt_base}"
    for entry in tmx_data.get(key, []):
        entries.append((entry["source"], entry["target"]))

    # 2) Fallback: aggregate over canonicalised pairs --------------------
    if not entries:
        for pair_key, pair_entries in tmx_data.items():
            try:
                src, tgt = pair_key.split("->", 1)
            except ValueError:
                continue
            if _canonical(src) == src_base and _canonical(tgt) == tgt_base:
                for entry in pair_entries:
                    entries.append((entry["source"], entry["target"]))

    return entries


def extract_glossary_from_tmx(
    tmx_path: str, source_language: str, target_language: str, max_len: int = 3
) -> List[Tuple[str, str]]:
    """Extract short source-target pairs from a TMX file as glossary terms."""
    if not Path(tmx_path).exists():
        raise FileNotFoundError(f"TMX file not found: {tmx_path}")

    logger.info("Parsing TMX for glossary extraction → %s", tmx_path)
    tmx_data = parse_tmx_file(tmx_path)
    pairs = _collect_tmx_entries(tmx_data, source_language, target_language)

    seen: Set[str] = set()
    glossary: List[Tuple[str, str]] = []

    for src, tgt in pairs:
        if 1 <= len(src.split()) <= max_len:
            key = src.lower()
            if key not in seen:
                seen.add(key)
                glossary.append((src.strip(), tgt.strip()))
    logger.info("Collected %d glossary term pairs from TMX", len(glossary))
    return glossary


# ---------------------------------------------------------------------------
# Monolingual extraction
# ---------------------------------------------------------------------------

def extract_terms_from_text(text: str, top_n: int = 50) -> List[str]:
    tokens = [tok.lower() for tok in _tokenise(text)]
    tokens = [tok for tok in tokens if tok not in STOPWORDS and len(tok) > 3]
    freq = Counter(tokens)
    return [term for term, _ in freq.most_common(top_n)]


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def write_glossary_csv(rows: List[Tuple[str, str]], output_path: str):
    out_file = Path(output_path)
    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["term", "translation"])
        writer.writerows(rows)
    logger.info("Glossary written → %s", out_file)


def extract_glossary(
    *,
    tmx: Optional[str] = None,
    input_file: Optional[str] = None,
    source_language: str = "English",
    target_language: str = "Spanish",
    output: str = "glossary.csv",
):
    """Entry-point used by the CLI."""

    if not tmx and not input_file:
        raise ValueError("Either a TMX file or an input file must be provided.")

    if tmx:
        terms = extract_glossary_from_tmx(tmx, source_language, target_language)
        write_glossary_csv(terms, output)
    else:
        # Type checker: input_file is guaranteed not None in this branch
        txt = Path(str(input_file)).read_text(encoding="utf-8")
        terms = [(term, "") for term in extract_terms_from_text(txt)]
        write_glossary_csv(terms, output)