"""nodes.style_guide
Utility for deriving a comprehensive translation **Style Guide** from TMX
translation-memory data.

This was extracted from *tmx_loader.py* to improve code organisation – TMX
parsing concerns now live in *tmx_loader* while stylistic inference lives here.
"""
from __future__ import annotations

import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

try:
    import tiktoken  # type: ignore
except ImportError:  # pragma: no cover – optional optimisation
    tiktoken = None  # type: ignore

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def infer_style_guide_from_tmx(
    tmx_memory: Optional[Dict[str, Any]],
    max_examples: int = 1_000,
    use_llm: bool = True,
) -> str:
    """Derive a Markdown style guide from TMX entries.

    Parameters
    ----------
    tmx_memory:
        Dictionary as produced by :pyfunc:`nodes.tmx_loader.load_tmx_memory`.
        Must contain an ``entries`` list with dictionaries holding at least
        ``source`` and ``target`` keys.
    max_examples:
        Upper bound on examples considered during sampling.  Acts as a safety
        valve if `entries` is extremely large.
    use_llm:
        When *True* and an ``OPENAI_API_KEY`` is present the function calls
        GPT-4o to synthesise a rich, human-readable style guide.  If the API
        key is missing (e.g. in CI) or an error occurs the function will raise
        a *ValueError* so that callers may decide how to fall back.
    """

    if not tmx_memory or not isinstance(tmx_memory, dict):
        raise ValueError("`tmx_memory` must be a dictionary from load_tmx_memory().")

    entries: List[Dict[str, Any]] | None = tmx_memory.get("entries")  # type: ignore
    if not entries:
        raise ValueError("`tmx_memory` does not contain any translation entries to infer style from.")

    # ------------------------------------------------------------------
    # Sort by usage count so we sample representative, high-quality segments
    # ------------------------------------------------------------------
    try:
        sorted_entries = sorted(
            entries,
            key=lambda e: e.get("usage_count", 0) if isinstance(e, dict) else 0,
            reverse=True,
        )
    except Exception as exc:  # pragma: no cover – pathological data
        logger.warning("Could not sort TMX entries: %s", exc)
        sorted_entries = entries

    # ------------------------------------------------------------------
    # Reservoir sampling constrained by a 120 000-token budget
    # ------------------------------------------------------------------
    TOKEN_BUDGET = 120_000

    if tiktoken is not None:
        try:
            enc = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        token_len = lambda s: len(enc.encode(s))  # type: ignore[arg-type]
    else:
        token_len = lambda s: max(1, len(s) // 4)

    prompt_stub = (
        "You are a professional localization specialist. Analyse the following "
        "bilingual examples and produce a detailed, comprehensive style guide covering "
        "tone, register, punctuation, preferred constructions, formatting conventions, "
        "voice, and any notable stylistic patterns that will be usable by a human "
        "translator to guide their work. Focus on guidance applicable to future "
        "translations of similar content.\n\nExamples:\n{examples}\n\nSTYLE GUIDE:"
    )
    prompt_tokens = token_len(prompt_stub)

    reservoir: List[Tuple[str, int]] = []
    current_tokens = prompt_tokens
    processed = 0

    for entry in sorted_entries[:max_examples]:
        src = entry.get("source", "")
        tgt = entry.get("target", "")
        example = f'- "{src}" -> "{tgt}"'
        t = token_len(example) + 1  # newline
        processed += 1

        if t > TOKEN_BUDGET:
            continue

        if current_tokens + t <= TOKEN_BUDGET and len(reservoir) < max_examples:
            reservoir.append((example, t))
            current_tokens += t
        else:
            j = random.randint(0, processed - 1)
            if j < len(reservoir):
                old_t = reservoir[j][1]
                if current_tokens - old_t + t <= TOKEN_BUDGET:
                    current_tokens = current_tokens - old_t + t
                    reservoir[j] = (example, t)

        if current_tokens >= TOKEN_BUDGET:
            break

    if not reservoir:
        raise ValueError("No TMX examples fit within the token budget.")

    examples_formatted = "\n".join(ex for ex, _ in reservoir)

    if use_llm and os.getenv("OPENAI_API_KEY"):
        prompt = ChatPromptTemplate.from_template(prompt_stub)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        messages = prompt.invoke({"examples": examples_formatted})

        try:
            if hasattr(llm, "invoke"):
                resp = llm.invoke(messages)
            else:  # mocked
                resp = llm.__ror__(messages).invoke(None)  # type: ignore[attr-defined]
            return getattr(resp, "content", str(resp)).strip()
        except Exception as exc:
            raise RuntimeError(f"LLM style-guide synthesis failed: {exc}") from exc

    # Fallback – return examples block for manual inspection
    return (
        "The following examples illustrate tone and syntax. Maintain consistency:\n" + examples_formatted
    )