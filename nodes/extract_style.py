import logging
from pathlib import Path
from typing import List

from nodes.tmx_loader import parse_tmx_file

logger = logging.getLogger(__name__)


def _canonical(code: str) -> str:
    """Return base ISO language code (strip region / script variants)."""
    return code.lower().split("-")[0].split("_")[0]


def _flatten_target_segments(tmx_data: dict, source_language: str, target_language: str) -> List[str]:
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

    return [e["target"] for e in entries if e.get("target")]


def extract_style_guide(
    tmx_path: str,
    source_language: str,
    target_language: str,
    output_path: str = "extracted_style.md",
) -> str:
    """Infer a *very basic* style guide from a TMX file and write it out.

    The heuristic is intentionally lightweight – it looks only at simple
    statistics such as average sentence length and punctuation usage.
    This provides a baseline that users can refine manually later on.
    """
    tmx_file = Path(tmx_path)
    if not tmx_file.exists():
        raise FileNotFoundError(f"TMX file not found: {tmx_path}")

    logger.info("Parsing TMX file for style extraction → %s", tmx_file)
    tmx_data = parse_tmx_file(str(tmx_file))

    target_segments = _flatten_target_segments(tmx_data, source_language, target_language)
    if not target_segments:
        raise ValueError(
            f"No target-language segments found for {source_language}->{target_language} in TMX"
        )

    # --- Simple heuristics ---------------------------------------------
    word_counts = [len(seg.split()) for seg in target_segments if seg.strip()]
    avg_len = sum(word_counts) / len(word_counts)

    tone = (
        "concise" if avg_len <= 12 else "moderately long" if avg_len <= 20 else "detailed"
    )

    exclam_pct = (
        sum(1 for seg in target_segments if "!" in seg) / len(target_segments) * 100
    )
    quest_pct = (
        sum(1 for seg in target_segments if "?" in seg) / len(target_segments) * 100
    )

    # --- Compose markdown ----------------------------------------------
    lines = [
        "# Automatically Extracted Style Guide",
        "",
        f"- Write in a {tone} style (average sentence length ≈ {avg_len:.1f} words).",
        "- Maintain consistent punctuation and capitalisation.",
        "- Prefer active voice and clear phrasing.",
    ]

    if exclam_pct > 5:
        lines.append(
            f"- Exclamation marks are relatively common (~{exclam_pct:.1f}% of segments); retain them when appropriate."
        )
    if quest_pct > 1:
        lines.append(
            f"- Questions occur in the corpus (~{quest_pct:.1f}% of segments); mirror the interrogative tone faithfully."
        )

    style_guide_md = "\n".join(lines) + "\n"

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s", out_path)

    return style_guide_md