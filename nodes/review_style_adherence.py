"""nodes.review_style_adherence
------------------------------
Review node responsible for evaluating style guide adherence in translations.

This node uses an LLM with a focused prompt to evaluate only the style
aspects of the translation, including:
- Tone and register (formal, informal, professional, etc.)
- Voice (active vs passive)
- Consistency with brand guidelines
- Target audience appropriateness

Key features:
- LLM-based evaluation with focused style prompt
- Scores from -1.0 to 1.0 based on style guide compliance
- Detailed explanations for style violations
- Token-efficient evaluation (focused scope)
"""

import json
import logging
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompt_values import PromptValue
from state import TranslationState
from langgraph.types import Command
from typing import Literal, Any
from nodes.style_guide import infer_style_guide_from_tmx
from nodes.utils import extract_response_content

# Configure logging
logger = logging.getLogger(__name__)

STYLE_REVIEW_PROMPT = """
You are a style and tone expert specializing in translation quality assessment. Evaluate ONLY how well the translation adheres to the specified style guide.

---
**Original Text ({source_language}):**
{original_content}

**Translation ({target_language}):**
{translated_content}

**Style Guide:**
{style_guide}
---

Focus exclusively on these style aspects:
1. **Tone and Register**: Does the translation match the required formality level?
2. **Voice**: Does it follow active/passive voice requirements?
3. **Style Consistency**: Is the writing style consistent throughout?
4. **Target Audience**: Is the language appropriate for the intended audience?
5. **Brand Voice**: Does it maintain the prescribed brand personality?

Do NOT evaluate:
- Grammar or linguistic correctness
- Translation accuracy or meaning preservation
- Glossary term usage

Provide your assessment as a JSON object:
{{
    "score": <float between -1.0 and 1.0>,
    "explanation": "<detailed explanation if score < 0.7, otherwise empty string>"
}}

Scoring criteria for style adherence only:
- 1.0: Perfect adherence to style guide with consistent tone and voice
- 0.7-0.9: Good style compliance with minor inconsistencies
- 0.3-0.6: Acceptable style but noticeable deviations from guidelines
- 0.0-0.2: Poor style compliance with significant violations
- -1.0 to -0.1: Very poor style that contradicts the style guide

Only provide an explanation if the score is below 0.7. Focus on specific style violations and recommendations.
"""

def evaluate_style_adherence(state: TranslationState) -> Command[Literal["aggregator"]]:
    """
    Evaluates how well the translation adheres to the specified style guide.
    
    This evaluation focuses specifically on style, tone, and voice aspects
    without considering grammatical correctness or translation accuracy.
    
    Args:
        state: TranslationState containing translation and style guide information
    
    Returns:
        Command: Handoff command with style adherence score and explanation
    """
    logger.info("Evaluating style adherence...")
    
    # -------------------------------------------------------------
    # Handle missing style guide by inferring style from TMX entries
    # -------------------------------------------------------------
    style_guide = state.get("style_guide", "")
    if not str(style_guide).strip():
        try:
            inferred = infer_style_guide_from_tmx(state.get("tmx_memory", {}))
        except ValueError as exc:
            logger.warning("Style guide inference failed: %s", exc)
            inferred = ""

        if inferred:
            logger.info("No style guide provided; inferring style from TMX entries.")
            style_guide = inferred
        else:
            logger.info("No style guide provided and no TMX entries available; proceeding without explicit style guidance.")
    # Persist inferred style for rest of review pipeline
    state["style_guide"] = style_guide
    # -------------------------------------------------------------
    
    # Check if we have the required content
    if not state.get("translated_content"):
        logger.error("No translated content found for style review")
        return Command(
            update={
                "style_adherence_score": -1.0,
                "style_adherence_explanation": "ERROR: No translated content available for style review"
            },
            goto="aggregator"
        )
    
    try:
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is not set in environment variables!")
            return Command(
                update={
                    "style_adherence_score": 0.0,
                    "style_adherence_explanation": "ERROR: OpenAI API key not found. Cannot perform style evaluation."
                },
                goto="aggregator"
            )
        
        prompt = ChatPromptTemplate.from_template(STYLE_REVIEW_PROMPT)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Prepare the prompt messages
        prompt_messages: PromptValue = prompt.invoke({
            "original_content": state["original_content"],
            "translated_content": state["translated_content"],
            "style_guide": style_guide,
            "source_language": state["source_language"],
            "target_language": state["target_language"],
        })

        logger.debug("Style evaluation prompt prepared, calling LLM...")

        # Handle both real LLM and mock implementations (for testing)
        if hasattr(llm, "invoke"):
            response: Any = llm.invoke(prompt_messages)
        elif hasattr(llm, "__ror__"):
            # Fallback for mocked implementations in tests
            chain: Any = llm.__ror__(prompt_messages)  # type: ignore[operator]
            if hasattr(chain, "invoke"):
                response = chain.invoke(None)  # type: ignore[assignment]
            else:
                raise TypeError(
                    "Fallback style review chain produced by mocked LLM does not "
                    "expose an 'invoke' method as expected."
                )
        else:
            raise TypeError(
                "The provided language model must expose either an 'invoke' "
                "method or support piping via the '|' operator."
            )

        # Parse the JSON response
        try:
            response_content = extract_response_content(response).strip()
            
            # Handle cases where the LLM wraps the JSON in markdown code blocks
            if response_content.startswith("```") and response_content.endswith("```"):
                # Extract content between code blocks
                lines = response_content.split('\n')
                # Skip the first line (```json or ```) and the last line (```)
                response_content = '\n'.join(lines[1:-1])
            elif response_content.startswith("```json") and response_content.endswith("```"):
                # Handle ```json specifically
                response_content = response_content[7:-3].strip()
            
            review_data = json.loads(response_content)
            score = float(review_data.get("score", 0.0))
            explanation = review_data.get("explanation", "")
            
            # Ensure score is within valid range
            score = max(-1.0, min(1.0, score))
            
            logger.info(f"Style evaluation complete. Score: {score:.2f}")
            
            return Command(
                update={
                    "style_adherence_score": score,
                    "style_adherence_explanation": explanation
                },
                goto="aggregator"
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing style review response: {e}")
            logger.error(f"Raw response: {extract_response_content(response)}")
            return Command(
                update={
                    "style_adherence_score": 0.0,
                    "style_adherence_explanation": f"ERROR: Could not parse style review response - {str(e)}"
                },
                goto="aggregator"
            )
    
    except Exception as e:
        logger.error(f"Error during style evaluation: {type(e).__name__}: {str(e)}")
        return Command(
            update={
                "style_adherence_score": 0.0,
                "style_adherence_explanation": f"ERROR during style evaluation: {type(e).__name__}: {str(e)}"
            },
            goto="aggregator"
        )