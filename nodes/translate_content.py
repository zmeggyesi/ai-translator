"""nodes.translate_content
--------------------------------
LangGraph node responsible for taking *original_content* plus auxiliary
information (style guide and a previously filtered glossary) and producing the
**translated** text.

The translation is performed by driving an LLM (OpenAI chat model by default)
with a carefully structured prompt that embeds both:

* The *style guide* — to keep tone and register consistent.
* The *filtered glossary* — to enforce domain-specific terminology.

Testing strategy
----------------
Unit-tests replace the heavy OpenAI dependency with a tiny **dummy** class that
implements only what the node needs. The dummy sits outside the LangChain
Runnable hierarchy, so we implement a small runtime shim (`invoke` vs. `__ror__`)
to keep both real and mocked models working without changes to the production
code.
"""

import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import TranslationState
from nodes.tmx_loader import find_tmx_matches
import os

# Configure logging
logger = logging.getLogger(__name__)

TRANSLATION_PROMPT = """
Translate the following content from {source_language} to {target_language}:

---
{original_content}
---

You MUST adhere to the following instructions:
1.  **Style Guide**: {style_guide}
2.  **Glossary**: Strictly use the translations provided in this JSON object for any applicable terms:
    {glossary}
3.  **Translation Memory**: {tmx_guidance}

Output only the translated text in {target_language}.
"""

def translate_content(state: TranslationState) -> dict:
    """
    Translates the original content based on the filtered glossary, style guide, and TMX memory.
    Uses exact TMX matches when available, otherwise uses fuzzy matches for style guidance.
    """
    logger.info(f"Translating content from {state['source_language']} to {state['target_language']}...")
    
    try:
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is not set in environment variables!")
            return {"translated_content": "ERROR: OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."}
        
        # Check for TMX exact matches first
        tmx_guidance = "No translation memory entries available."
        tmx_memory = state.get("tmx_memory", {})
        
        if tmx_memory and "entries" in tmx_memory:
            tmx_entries = tmx_memory["entries"]
            
            # Look for exact matches (100% similarity)
            exact_matches = find_tmx_matches(state["original_content"], tmx_entries, threshold=100.0)
            
            if exact_matches:
                # Use the first exact match (highest usage count)
                best_match = exact_matches[0]
                logger.info(f"Found exact TMX match: '{best_match['source']}' -> '{best_match['target']}'")
                return {"translated_content": best_match["target"]}
            
            # Look for fuzzy matches for style guidance (80%+ similarity)
            fuzzy_matches = find_tmx_matches(state["original_content"], tmx_entries, threshold=80.0)
            
            if fuzzy_matches:
                tmx_guidance = "Use the following translation memory examples for style and terminology guidance:\n"
                for i, match in enumerate(fuzzy_matches[:3]):  # Top 3 matches
                    tmx_guidance += f"- Source: \"{match['source']}\" -> Target: \"{match['target']}\" (similarity: {match['similarity']:.1f}%)\n"
                
                logger.info(f"Found {len(fuzzy_matches)} fuzzy TMX matches for style guidance")
            else:
                logger.info("No TMX matches found above threshold")
        
        # -------------------------------------------------------------
        # Handle missing style guide by inferring style from TMX entries
        # -------------------------------------------------------------
        style_guide = state.get("style_guide", "")
        if not str(style_guide).strip():
            # No explicit style guide provided
            if tmx_memory and "entries" in tmx_memory and tmx_memory["entries"]:
                logger.info("No style guide provided; inferring style from TMX entries.")
                # Use up to 5 examples with the highest usage_count to convey style
                example_entries = sorted(
                    tmx_memory["entries"],
                    key=lambda e: e.get("usage_count", 0),
                    reverse=True
                )[:5]
                examples_formatted = "\n".join(
                    f"- \"{e['source']}\" -> \"{e['target']}\"" for e in example_entries
                )
                style_guide = (
                    "The following examples illustrate the desired tone, register, and syntax. "
                    "Maintain consistency with them:\n" + examples_formatted
                )
            else:
                logger.info("No style guide provided and no TMX entries available; proceeding without explicit style guidance.")
        # -------------------------------------------------------------

        prompt = ChatPromptTemplate.from_template(TRANSLATION_PROMPT)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        glossary = state.get("filtered_glossary") or {}
        logger.debug(f"Using glossary for translation: {glossary}")

        # Prepare the prompt messages using the ChatPromptTemplate so that we can
        # invoke or otherwise pass them to the underlying model implementation.
        prompt_messages = prompt.invoke({
            "original_content": state["original_content"],
            "style_guide": style_guide,
            "glossary": json.dumps(glossary, ensure_ascii=False),
            "tmx_guidance": tmx_guidance,
            "source_language": state["source_language"],
            "target_language": state["target_language"],
        })

        logger.debug("Prompt messages prepared, calling LLM...")

        # Different mock strategies used in tests may patch ChatOpenAI with a dummy
        # implementation that does *not* inherit from LangChain Runnable classes.
        # To remain test- and runtime-agnostic we attempt the following, in order:
        # 1.  Use the standard ``invoke`` method that real LangChain models expose.
        # 2.  If unavailable, fall back to the ``__ror__`` pipe operator that is
        #     commonly implemented by simplistic mocks (see unit tests).
        # 3.  Raise a clear error if neither strategy is supported.
        if hasattr(llm, "invoke"):
            response = llm.invoke(prompt_messages)
        elif hasattr(llm, "__ror__"):
            # Mocks used in unit-tests often rely on ``prompt_messages | llm`` which
            # triggers ``llm.__ror__(prompt_messages)``. We replicate that behaviour
            # directly here to keep the implementation simple and dependency-free.
            chain = llm.__ror__(prompt_messages)
            if hasattr(chain, "invoke"):
                response = chain.invoke(None)
            else:
                raise TypeError(
                    "Fallback translation chain produced by mocked LLM does not "
                    "expose an 'invoke' method as expected."
                )
        else:
            raise TypeError(
                "The provided language model must expose either an 'invoke' "
                "method or support piping via the '|' operator."
            )

        logger.info("Translation complete.")
        # Real LLM responses provide the translated text in ``response.content``.
        # Mocks used in tests mirror that interface, so we access it uniformly.
        return {"translated_content": response.content}
    
    except Exception as e:
        logger.error(f"Error during translation: {type(e).__name__}: {str(e)}")
        return {"translated_content": f"ERROR during translation: {type(e).__name__}: {str(e)}"} 