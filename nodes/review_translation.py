"""nodes.review_translation
----------------------------
LangGraph node responsible for reviewing and grading the translation quality.

This node evaluates the translated content on three dimensions:
1. Overall quality 
2. Faithfulness to the glossary
3. Adherence to the style guide

The review produces a score between -1.0 and 1.0, where:
- 1.0 = Excellent translation
- 0.0 = Acceptable/average translation
- -1.0 = Poor translation requiring revision

If the score is sufficiently high (≥ 0.7), no explanation is provided.
For lower scores, a detailed explanation is included to guide improvements.

Testing strategy
----------------
Unit tests mock the LLM dependency and test various score ranges and explanation
generation logic to ensure the grading system works consistently.
"""

import json
import logging
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompt_values import PromptValue
from state import TranslationState
from nodes.tmx_loader import infer_style_guide_from_tmx
from nodes.utils import extract_response_content
from typing import Any, cast

# Configure logging
logger = logging.getLogger(__name__)

REVIEW_PROMPT = """
You are an expert translation reviewer. Evaluate the following translation on three key dimensions:

1. **Overall Quality**: Grammar, fluency, naturalness in the target language
2. **Faithfulness to Glossary**: Correct usage of specified terminology 
3. **Adherence to Style Guide**: Following the prescribed tone and style

---
**Original Text ({source_language}):**
{original_content}

**Translation ({target_language}):**
{translated_content}

**Glossary (JSON format):**
{glossary}

**Style Guide:**
{style_guide}
---

Provide your assessment as a JSON object with the following structure:
{{
    "score": <float between -1.0 and 1.0>,
    "explanation": "<detailed explanation if score < 0.7, otherwise empty string>"
}}

Scoring criteria:
- 1.0: Excellent - Perfect translation with flawless quality, terminology, and style
- 0.7-0.9: Good - High quality with minor issues
- 0.3-0.6: Acceptable - Average quality with some noticeable issues
- 0.0-0.2: Poor - Significant issues requiring revision
- -1.0 to -0.1: Very poor - Major errors, incorrect terminology, or wrong style

Only provide an explanation if the score is below 0.7. The explanation should be constructive and specific about what needs improvement.
"""

def review_translation(state: TranslationState) -> dict:
    """
    Reviews and grades the translation quality on multiple dimensions.
    
    Args:
        state: TranslationState containing the original content, translation,
               glossary, and style guide
    
    Returns:
        dict: Contains review_score (float) and review_explanation (str)
    """
    logger.info("Starting translation review...")
    
    # Check if we have the required content to review
    if not state.get("translated_content"):
        logger.error("No translated content found to review")
        return {
            "review_score": -1.0,
            "review_explanation": "ERROR: No translated content available for review"
        }
    
    try:
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is not set in environment variables!")
            return {
                "review_score": 0.0,
                "review_explanation": "ERROR: OpenAI API key not found. Cannot perform automated review."
            }
        
        prompt = ChatPromptTemplate.from_template(REVIEW_PROMPT)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Get the filtered glossary or fall back to the original glossary
        glossary = state.get("filtered_glossary") or state.get("glossary", {})
        logger.debug(f"Using glossary for review: {glossary}")

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
        # Persist for downstream nodes
        state["style_guide"] = style_guide
        # -------------------------------------------------------------

        # Prepare the prompt messages
        prompt_messages: PromptValue = prompt.invoke({
            "original_content": state["original_content"],
            "translated_content": state["translated_content"],
            "glossary": json.dumps(glossary, ensure_ascii=False),
            "style_guide": style_guide,
            "source_language": state["source_language"],
            "target_language": state["target_language"],
        })

        logger.debug("Prompt prepared, calling LLM for review...")

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
                    "Fallback review chain produced by mocked LLM does not "
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
            
            logger.info(f"Review complete. Score: {score}")
            
            return {
                "review_score": score,
                "review_explanation": explanation
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing review response: {e}")
            logger.error(f"Raw response: {extract_response_content(response)}")
            return {
                "review_score": 0.0,
                "review_explanation": f"ERROR: Could not parse review response - {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"Error during translation review: {type(e).__name__}: {str(e)}")
        return {
            "review_score": 0.0,
            "review_explanation": f"ERROR during review: {type(e).__name__}: {str(e)}"
        }


def review_translation_standalone(
    original_content: str,
    translated_content: str,
    glossary: dict,
    style_guide: str,
    source_language: str = "English",
    target_language: str = "Spanish"
) -> tuple[float, str]:
    """
    Standalone function to review a translation without using LangGraph state.
    
    This allows the review agent to be called independently from the main graph.
    
    Args:
        original_content: The original text to be translated
        translated_content: The translated text to be reviewed
        glossary: Dictionary of term translations
        style_guide: Style guidelines for the translation
        source_language: Source language name
        target_language: Target language name
    
    Returns:
        tuple: (score, explanation) where score is float between -1.0 and 1.0
               and explanation is str (empty if score >= 0.7)
    """
    # Create a minimal state dict for the review function
    state_dict: dict = {
        "original_content": original_content,
        "translated_content": translated_content,
        "glossary": glossary,
        "filtered_glossary": None,  # Will use main glossary
        "style_guide": style_guide,
        "source_language": source_language,
        "target_language": target_language,
        "messages": []
    }
    
    # Call the main review function
    result_ts = cast(TranslationState, review_translation(cast(TranslationState, state_dict)))
    score_raw = result_ts.get("review_score")
    score: float = float(score_raw or 0.0)
    explanation: str = str(result_ts.get("review_explanation", ""))
    return score, explanation


if __name__ == "__main__":
    """
    Command-line interface for standalone translation review.
    """
    import argparse
    import csv
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Review a translation quality")
    parser.add_argument("-o", "--original", required=True, help="Original text file")
    parser.add_argument("-t", "--translation", required=True, help="Translated text file")
    parser.add_argument("-g", "--glossary", default="data/glossary.csv", help="Glossary CSV file")
    parser.add_argument("-s", "--style-guide", default="data/style_guide.md", help="Style guide file")
    parser.add_argument("-sl", "--source-language", default="English", help="Source language")
    parser.add_argument("-tl", "--target-language", default="Spanish", help="Target language")
    
    args = parser.parse_args()
    
    # Load files
    try:
        with open(args.original, "r", encoding="utf-8") as f:
            original = f.read().strip()
        with open(args.translation, "r", encoding="utf-8") as f:
            translation = f.read().strip()
        with open(args.style_guide, "r", encoding="utf-8") as f:
            style_guide = f.read().strip()
        
        # Load glossary
        glossary = {}
        with open(args.glossary, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "term" in reader.fieldnames and "translation" in reader.fieldnames:
                for row in reader:
                    if row["term"] and row["translation"]:
                        glossary[row["term"]] = row["translation"]
            else:
                f.seek(0)
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0] and row[1]:
                        glossary[row[0]] = row[1]
        
        # Perform review
        score, explanation = review_translation_standalone(
            original, translation, glossary, style_guide,
            args.source_language, args.target_language
        )
        
        print(f"Review Score: {score:.2f}")
        if explanation:
            print(f"Explanation: {explanation}")
        else:
            print("Explanation: None (score is sufficiently high)")
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")