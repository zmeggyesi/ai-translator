import logging
from pathlib import Path
from typing import List
import os

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

    # ------------------------------------------------------------------
    # Decide whether LLM can be used
    # ------------------------------------------------------------------
    use_llm = bool(os.getenv("OPENAI_API_KEY"))

    if use_llm:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate

            SAMPLE_COUNT = 50
            sample_segments = target_segments[:SAMPLE_COUNT]

            PROMPT = """
You are a professional localisation specialist and technical writer.
Analyse the example target-language segments below (originally translated
from {source_language} to {target_language}).  Based on the patterns you see
— tone, formality level, punctuation usage, domain-specific terminology,
brand voice, common phrasing, etc. — produce a **Markdown** style guide that
future translators should follow.

The guide **must** include:
1. Overall tone / formality description (e.g. friendly, formal, technical).
2. Voice guidelines (active vs passive, first vs third person).
3. Terminology consistency rules (highlight frequently used terms).
4. Punctuation and typography preferences (Oxford comma, quote style).
5. Country or region-specific conventions (spelling variants, units).
6. Examples drawn from the corpus to illustrate rules (quote short phrases).

Start the document with a H1 heading "Translation Style Guide" and use
bullet points or sub-headings where appropriate.

Statistical context you might find useful:
- Average sentence length: ~{avg_len:.1f} words
- Exclamation usage: {exclam_pct:.1f}% of segments
- Question usage: {quest_pct:.1f}% of segments

Example segments (max {SAMPLE_COUNT}):
"""

            # Build prompt messages ------------------------------------------------
            prompt_template = ChatPromptTemplate.from_template(PROMPT)
            prompt_messages = prompt_template.invoke(
                {
                    "source_language": source_language,
                    "target_language": target_language,
                    "avg_len": avg_len,
                    "exclam_pct": exclam_pct,
                    "quest_pct": quest_pct,
                }
            )

            # Append examples as separate user message to keep formatting clean
            examples_block = "\n".join(f"- {seg}" for seg in sample_segments)
            prompt_messages.append({"role": "user", "content": examples_block})  # type: ignore[arg-type]

            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            response = llm.invoke(prompt_messages)

            style_guide_md = response.content.strip()
            logger.info("LLM-generated style guide length: %d chars", len(style_guide_md))

        except Exception as e:
            logger.error("LLM style extraction failed (%s). Falling back to heuristics.", e)
            use_llm = False  # fall back

    if not use_llm:
        # --- Compose heuristic guide -----------------------------------
        lines = [
            "# Translation Style Guide (Automatic Heuristic)",
            "",
            f"- Write in a {tone} style (average sentence length ≈ {avg_len:.1f} words).",
            "- Maintain consistent punctuation and capitalisation.",
            "- Prefer active voice and clear phrasing.",
        ]

        if exclam_pct > 5:
            lines.append(
                f"- Exclamation marks appear in ~{exclam_pct:.1f}% of segments; retain them when appropriate."
            )
        if quest_pct > 1:
            lines.append(
                f"- Questions occur in ~{quest_pct:.1f}% of segments; mirror the interrogative tone faithfully."
            )

        style_guide_md = "\n".join(lines) + "\n"

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s (via %s)", out_path, "LLM" if use_llm else "heuristics")

    return style_guide_md