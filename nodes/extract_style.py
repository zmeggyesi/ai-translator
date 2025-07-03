import logging
from pathlib import Path
from typing import List
import os

from nodes.tmx_loader import parse_tmx_file, infer_style_guide_from_tmx

logger = logging.getLogger(__name__)


def _canonical(code: str) -> str:
    """Return base ISO language code (strip region / script variants)."""
    return code.lower().split("-")[0].split("_")[0]


def _flatten_target_segments(tmx_data: dict, source_language: str, target_language: str) -> List[dict]:
    """Return a list of *target* text segments for the requested language pair.

    Falls back gracefully to any segments that match the canonicalised
    language codes if no exact pair is found.
    """
    src_base = _canonical(source_language)
    tgt_base = _canonical(target_language)

    # 1) Exact key first -------------------------------------------------
    key = f"{src_base}->{tgt_base}"
    entries = tmx_data.get(key, [])

    # 2) Fallback: aggregate over keys whose canonicalised codes match ----
    if not entries:
        for pair_key, pair_entries in tmx_data.items():
            try:
                src, tgt = pair_key.split("->", 1)
            except ValueError:
                continue
            if _canonical(src) == src_base and _canonical(tgt) == tgt_base:
                entries.extend(pair_entries)

    # 3) Final fallback: ANY entry where target matches the requested ----
    if not entries:
        for pair_entries in tmx_data.values():
            for entry in pair_entries:
                if _canonical(entry.get("target_lang", "")) == tgt_base:
                    entries.append(entry)

    # Return the **full** entry dictionaries so that downstream consumers (e.g.
    # ``infer_style_guide_from_tmx``) have access to both *source* and *target*
    # as well as auxiliary metadata (usage_count, etc.).

    return [e for e in entries if isinstance(e, dict) and e.get("target")]


def extract_style_guide(
    tmx_path: str,
    source_language: str,
    target_language: str,
    output_path: str = "extracted_style.md",
) -> str:
    """Generate a **comprehensive** style guide using TMX data.

    The function now follows a *hybrid* strategy:

    1. **Statistical Heuristics** – Fast, deterministic metrics such as
       average sentence length, punctuation frequency, and exclamation /
       question usage.  These numbers are included verbatim in the prompt so
       the LLM can reason with concrete evidence.

    2. **LLM Analysis** – If an `OPENAI_API_KEY` is configured the function
       uses `ChatOpenAI` (or the mock equivalent in the test-suite) to analyse
       stylistic patterns, domain-specific terminology, tone / formality, and
       brand voice.  The LLM returns a **Markdown** document that becomes the
       final style guide.

    3. **Graceful Fallback** – When no API key is available (e.g. in CI) we
       fall back to a purely heuristic guide similar to the previous
       implementation, ensuring offline determinism for tests.
    """
    tmx_file = Path(tmx_path)
    if not tmx_file.exists():
        raise FileNotFoundError(f"TMX file not found: {tmx_path}")

    logger.info("Parsing TMX file for style extraction → %s", tmx_file)
    tmx_data = parse_tmx_file(str(tmx_file))

    # Leverage the shared TMX inference utility which already supports LLM + fallback
    tmx_memory = {
        "entries": _flatten_target_segments(tmx_data, source_language, target_language),
        "language_pair": f"{source_language}->{target_language}",
    }

    style_guide_md = infer_style_guide_from_tmx(tmx_memory, use_llm=True)
    if not style_guide_md:
        raise ValueError("Failed to generate style guide from TMX entries.")

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s", out_path)

    return style_guide_md