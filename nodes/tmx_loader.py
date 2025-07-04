"""nodes.tmx_loader
-----------------
LangGraph node responsible for loading and parsing TMX (Translation Memory eXchange) files.

TMX files are XML-based translation memory files that contain source and target text segments
in multiple languages. This module parses TMX files and extracts relevant translation
memory entries for use during translation and review.

Key features:
- Parses TMX 1.4+ format files
- Extracts source-target segment pairs for the specified language pair
- Handles multiple translation units and variants
- Supports exact matching and fuzzy matching for translation memory lookup
- Provides style guidance from similar segments

Testing strategy
----------------
Unit tests mock file I/O and XML parsing to test the logic without requiring actual TMX files.
The module handles malformed XML gracefully and provides clear error messages.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from rapidfuzz import fuzz
from state import TranslationState
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import random
try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None  # type: ignore

# Configure logging
logger = logging.getLogger(__name__)

def parse_tmx_file(tmx_file_path: str) -> Dict[str, List[Dict]]:
    """
    Parses a TMX file and extracts translation memory entries.
    
    Args:
        tmx_file_path: Path to the TMX file
        
    Returns:
        Dictionary with language pairs as keys and lists of translation units as values.
        Format: {
            "en->fr": [
                {
                    "source": "Hello world", 
                    "target": "Bonjour le monde",
                    "source_lang": "en",
                    "target_lang": "fr",
                    "creation_date": "20240101T120000Z",
                    "usage_count": 5
                },
                ...
            ]
        }
    """
    logger.info(f"Parsing TMX file: {tmx_file_path}")
    
    try:
        # Parse the XML file
        tree = ET.parse(tmx_file_path)
        root = tree.getroot()
        
        # Verify it's a TMX file
        if root.tag != 'tmx':
            raise ValueError(f"Invalid TMX file: Root element is '{root.tag}', expected 'tmx'")
        
        # Extract header information
        header = root.find('header')
        if header is None:
            raise ValueError("Invalid TMX file: Missing header element")
            
        source_lang = header.get('srclang', '').lower()
        logger.debug(f"TMX source language: {source_lang}")
        
        # Extract translation units from body
        body = root.find('body')
        if body is None:
            raise ValueError("Invalid TMX file: Missing body element")
            
        translation_memory = {}
        
        for tu in body.findall('tu'):
            # Extract all translation unit variants (tuvs)
            tuvs = tu.findall('tuv')
            
            if len(tuvs) < 2:
                logger.debug("Skipping translation unit with less than 2 variants")
                continue
                
            # Group TUVs by language
            lang_segments = {}
            for tuv in tuvs:
                lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang') or tuv.get('xml:lang')
                if not lang:
                    logger.debug("Skipping TUV without language attribute")
                    continue
                    
                lang = lang.lower()
                # Extract the full textual content of the <seg> element *including* any
                # nested inline tags (e.g. <bpt>, <ept>, <ph>). ``Element.text`` only
                # captures the text preceding the first child which means segments that
                # start with markup would be silently ignored.  We therefore join all
                # pieces produced by ``itertext`` to faithfully reconstruct the full
                # segment string.
                seg = tuv.find('seg')
                if seg is not None:
                    seg_text = "".join(seg.itertext()).strip()
                    if seg_text:
                        lang_segments[lang] = seg_text
            
            # Create translation pairs for all language combinations
            languages = list(lang_segments.keys())
            for i, src_lang in enumerate(languages):
                for tgt_lang in languages[i+1:]:
                    if src_lang != tgt_lang:
                        # Create both directions (src->tgt and tgt->src)
                        for source_lang, target_lang in [(src_lang, tgt_lang), (tgt_lang, src_lang)]:
                            key = f"{source_lang}->{target_lang}"
                            
                            if key not in translation_memory:
                                translation_memory[key] = []
                            
                            # Extract additional metadata
                            creation_date = tu.get('creationdate', '')
                            usage_count = int(tu.get('usagecount', '0'))
                            
                            translation_memory[key].append({
                                "source": lang_segments[source_lang],
                                "target": lang_segments[target_lang],
                                "source_lang": source_lang,
                                "target_lang": target_lang,
                                "creation_date": creation_date,
                                "usage_count": usage_count
                            })
        
        logger.info(f"Successfully parsed TMX file. Found {sum(len(v) for v in translation_memory.values())} translation entries across {len(translation_memory)} language pairs")
        return translation_memory
        
    except ET.ParseError as e:
        logger.error(f"XML parsing error in TMX file: {e}")
        raise ValueError(f"Invalid TMX file format: {e}")
    except FileNotFoundError:
        logger.error(f"TMX file not found: {tmx_file_path}")
        raise FileNotFoundError(f"TMX file not found: {tmx_file_path}")
    except Exception as e:
        logger.error(f"Error parsing TMX file: {e}")
        raise


def find_tmx_matches(source_text: str, tmx_entries: List[Dict], threshold: float = 100.0) -> List[Dict]:
    """
    Finds matching translation memory entries for the given source text.
    
    Args:
        source_text: Text to find matches for
        tmx_entries: List of TMX entries for the language pair
        threshold: Minimum similarity score (0-100) for fuzzy matches
        
    Returns:
        List of matching entries sorted by similarity score (highest first)
    """
    if not tmx_entries:
        return []
    
    source_text = source_text.strip().lower()
    matches = []
    
    for entry in tmx_entries:
        entry_source = entry["source"].strip().lower()
        
        # Calculate similarity score
        similarity = fuzz.ratio(source_text, entry_source)
        
        if similarity >= threshold:
            match_entry = entry.copy()
            match_entry["similarity"] = similarity
            match_entry["match_type"] = "exact" if similarity == 100.0 else "fuzzy"
            matches.append(match_entry)
    
    # Sort by similarity (highest first), then by usage count
    matches.sort(key=lambda x: (x["similarity"], x["usage_count"]), reverse=True)
    
    logger.debug(f"Found {len(matches)} TMX matches for source text (threshold: {threshold}%)")
    return matches


def load_tmx_memory(state: TranslationState, tmx_file_path: str) -> dict:
    """
    Loads TMX translation memory for the current language pair.
    
    Args:
        state: TranslationState containing source and target language information
        tmx_file_path: Path to the TMX file to load
        
    Returns:
        Updated state with tmx_memory field populated
    """
    logger.info(f"Loading TMX memory from {tmx_file_path}")
    
    try:
        # Check if file exists
        if not Path(tmx_file_path).exists():
            logger.warning(f"TMX file not found: {tmx_file_path}")
            return {"tmx_memory": {}}
        
        # Parse the TMX file
        full_tmx_memory = parse_tmx_file(tmx_file_path)
        
        # Extract entries for the current language pair, taking into account
        # potential language-region variants (e.g. "en-US", "fr_FR") that may
        # appear as ``xml:lang`` attributes in multilingual TMX files.

        def _canonical(code: str) -> str:
            """Return base ISO language code (strip region/script variants)."""
            return code.lower().split("-")[0].split("_")[0]

        source_lang_raw = state["source_language"].lower()
        target_lang_raw = state["target_language"].lower()

        source_base = _canonical(source_lang_raw)
        target_base = _canonical(target_lang_raw)

        language_pair = f"{source_base}->{target_base}"

        # 1. First, try an exact key match (common case when TMX uses plain ISO codes)
        tmx_entries = full_tmx_memory.get(language_pair, [])

        # 2. If nothing found, aggregate over all keys whose canonicalised codes
        #    match the desired language pair (handles region/script variants).
        if not tmx_entries:
            aggregated: list = []
            for key, entries in full_tmx_memory.items():
                try:
                    src_code, tgt_code = key.split("->", 1)
                except ValueError:
                    continue

                if _canonical(src_code) == source_base and _canonical(tgt_code) == target_base:
                    aggregated.extend(entries)

            tmx_entries = aggregated

        if not tmx_entries:
            logger.info(
                f"No TMX entries found for language pair (with or without region variants): {source_base}->{target_base}"
            )
            available_pairs = list(full_tmx_memory.keys())
            logger.debug(f"Available language pairs in TMX: {available_pairs}")

        logger.info(f"Loaded {len(tmx_entries)} TMX entries for {source_base}->{target_base}")

        return {
            "tmx_memory": {
                "entries": tmx_entries,
                "language_pair": f"{source_base}->{target_base}",
                "source_lang": source_base,
                "target_lang": target_base
            }
        }
        
    except Exception as e:
        logger.error(f"Error loading TMX memory: {e}")
        return {"tmx_memory": {"error": str(e), "entries": []}}


def infer_style_guide_from_tmx(
    tmx_memory: Optional[Dict[str, Any]],
    max_examples: int = 1000,
    use_llm: bool = True,
) -> str:
    """Infer a minimal style guide string based on TMX entries.

    The function inspects the provided *tmx_memory* structure (as returned by
    :pyfunc:`load_tmx_memory`) and constructs a short instructional block that
    conveys the preferred tone, register, and syntactic style by example.  It
    returns an empty string when no suitable TMX entries are available.

    Args:
        tmx_memory: The TMX memory dictionary that may contain an "entries"
            list.  The function tolerates ``None`` or malformed structures
            gracefully.
        max_examples: Maximum number of high-usage TMX examples to include.
        use_llm: Whether to optionally leverage an LLM to synthesize style guide.

    Returns:
        A human-readable style guide snippet ready to embed in LLM prompts, or
        an empty string if nothing useful can be inferred.
    """
    # Sanity-check the provided TMX memory structure. We now raise explicit
    # exceptions instead of silently returning an empty string so that callers
    # can surface clear diagnostics to users when style-guide inference is
    # impossible.
    if not tmx_memory or not isinstance(tmx_memory, dict):
        raise ValueError("`tmx_memory` must be a non-empty dictionary produced by `load_tmx_memory`.")

    entries = tmx_memory.get("entries")
    if not entries:
        raise ValueError("`tmx_memory` does not contain any translation entries to infer style from.")

    # Sort entries by *usage_count* (defaulting to 0) so that we use the most
    # representative, frequently reviewed segments.
    try:
        sorted_entries = sorted(
            entries,
            key=lambda e: e.get("usage_count", 0) if isinstance(e, dict) else 0,
            reverse=True,
        )
    except Exception as exc:  # pragma: no cover – extreme edge case
        logger.warning("Could not sort TMX entries for style inference: %s", exc)
        sorted_entries = entries  # Fallback to original order

    # ------------------------------------------------------------------
    # Token-budget aware reservoir sampling (120k tokens)
    # ------------------------------------------------------------------
    token_budget = 120_000

    # Determine encoding for token counting
    if tiktoken is not None:
        try:
            encoding = tiktoken.encoding_for_model("gpt-4o")
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")
        token_len = lambda txt: len(encoding.encode(txt))  # type: ignore[arg-type]
    else:
        # Fallback: rough estimate – 1 token per 4 chars
        token_len = lambda txt: max(1, len(txt) // 4)

    reservoir: list[tuple[str,int]] = []
    processed = 0

    # Initial prompt (without examples) to account for budget
    prompt_stub = "Examples:\n"
    current_tokens = token_len(prompt_stub)

    for entry in sorted_entries:
        formatted = f'- "{entry.get("source", "")}" -> "{entry.get("target", "")}"'
        t = token_len(formatted) + 1  # +1 for newline
        processed += 1

        if t > token_budget:
            continue  # Single example exceeds budget

        if current_tokens + t <= token_budget and len(reservoir) < max_examples:
            reservoir.append((formatted, t))
            current_tokens += t
        else:
            # Reservoir replacement with probability len(reservoir)/processed
            j = random.randint(0, processed - 1)
            if j < len(reservoir):
                old_t = reservoir[j][1]
                if current_tokens - old_t + t <= token_budget:
                    current_tokens = current_tokens - old_t + t
                    reservoir[j] = (formatted, t)

        if current_tokens >= token_budget:
            break

    if not reservoir:
        raise ValueError("No suitable TMX examples available for style inference within token budget.")

    examples_formatted = "\n".join(fmt for fmt, _ in reservoir)

    if not examples_formatted.strip():
        raise ValueError("Failed to format TMX examples for style inference.")

    # Optionally synthesize a concise style guide via LLM
    if use_llm and os.getenv("OPENAI_API_KEY"):
        try:
            prompt = ChatPromptTemplate.from_template(
                """You are a professional localization specialist. Analyse the following bilingual examples and produce a comprehensive style guide (up to roughly three pages) covering tone, register, punctuation, preferred constructions, formatting conventions, voice, and any notable stylistic patterns. Focus on guidance applicable to future translations of similar content.\n\nExamples:\n{examples}\n\nSTYLE GUIDE:"""
            )
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            messages = prompt.invoke({"examples": examples_formatted})

            # Handle mocks in tests similarly to other nodes
            if hasattr(llm, "invoke"):
                response = llm.invoke(messages)
            else:
                chain = llm.__ror__(messages)  # type: ignore[operator]
                response = chain.invoke(None)  # type: ignore[assignment]

            content = getattr(response, "content", str(response)).strip()
            return content
        except Exception as exc:
            logger.warning("LLM style guide synthesis failed: %s", exc)

    # Fallback textual examples
    return (
        "The following examples illustrate the desired tone, register, and syntax. "
        "Maintain consistency with them:\n" + examples_formatted
    )