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

Output only the translated text in {target_language}.
"""

def translate_content(state: TranslationState) -> dict:
    """
    Translates the original content based on the filtered glossary and style guide.
    """
    logger.info(f"Translating content from {state['source_language']} to {state['target_language']}...")
    
    try:
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is not set in environment variables!")
            return {"translated_content": "ERROR: OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."}
        
        prompt = ChatPromptTemplate.from_template(TRANSLATION_PROMPT)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        glossary = state.get("filtered_glossary") or {}
        logger.debug(f"Using glossary for translation: {glossary}")

        # Prepare the prompt messages using the ChatPromptTemplate so that we can
        # invoke or otherwise pass them to the underlying model implementation.
        prompt_messages = prompt.invoke({
            "original_content": state["original_content"],
            "style_guide": state["style_guide"],
            "glossary": json.dumps(glossary, ensure_ascii=False),
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