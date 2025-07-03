"""nodes.review_grammar_correctness
-----------------------------------
Review node responsible for evaluating grammatical correctness in translations.

This node uses an LLM with a focused prompt to evaluate only the grammatical
aspects of the translation, including:
- Grammar rules and syntax
- Sentence structure and flow
- Proper conjugations and declensions
- Natural language usage

Key features:
- LLM-based evaluation with focused grammar prompt
- Scores from -1.0 to 1.0 based on grammatical quality
- Detailed explanations for grammatical issues
- Token-efficient evaluation (focused scope)
"""

import json
import logging
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import TranslationState
from langgraph.types import Command
from typing import Literal
from nodes.utils import extract_response_content

# Configure logging
logger = logging.getLogger(__name__)

GRAMMAR_REVIEW_PROMPT = """
You are a linguistic expert specializing in grammatical analysis. Evaluate ONLY the grammatical correctness of the following translation.

---
**Original Text ({source_language}):**
{original_content}

**Translation ({target_language}):**
{translated_content}
---

Focus exclusively on these grammatical aspects:
1. **Grammar Rules**: Correct verb conjugations, noun declensions, articles, etc.
2. **Sentence Structure**: Proper syntax and sentence formation
3. **Language Flow**: Natural rhythm and readability in the target language
4. **Technical Grammar**: Punctuation, capitalization, and linguistic conventions

Do NOT evaluate:
- Translation accuracy or meaning preservation
- Glossary term usage
- Style or tone adherence

Provide your assessment as a JSON object:
{{
    "score": <float between -1.0 and 1.0>,
    "explanation": "<detailed explanation if score < 0.7, otherwise empty string>"
}}

Scoring criteria for grammar only:
- 1.0: Perfect grammar with flawless linguistic structure
- 0.7-0.9: Good grammar with minor issues that don't impede understanding
- 0.3-0.6: Acceptable grammar but with noticeable errors
- 0.0-0.2: Poor grammar with significant errors affecting readability
- -1.0 to -0.1: Very poor grammar with major structural problems

Only provide an explanation if the score is below 0.7. Focus on specific grammatical errors and corrections.
"""

def evaluate_grammar_correctness(state: TranslationState) -> Command[Literal["style_adherence", "aggregator"]]:
    """
    Evaluates the grammatical correctness of the translation using an LLM.
    
    This evaluation focuses specifically on grammatical aspects and language
    structure without considering translation accuracy or style adherence.
    
    Args:
        state: TranslationState containing translation and language information
    
    Returns:
        Command: Handoff command with grammar correctness score and explanation
    """
    logger.info("Evaluating grammar correctness...")
    
    # Check if we have the required content
    if not state.get("translated_content"):
        logger.error("No translated content found for grammar review")
        return Command(
            update={
                "grammar_correctness_score": -1.0,
                "grammar_correctness_explanation": "ERROR: No translated content available for grammar review"
            },
            goto="aggregator"
        )
    
    try:
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is not set in environment variables!")
            return Command(
                update={
                    "grammar_correctness_score": 0.0,
                    "grammar_correctness_explanation": "ERROR: OpenAI API key not found. Cannot perform grammar evaluation."
                },
                goto="aggregator"
            )
        
        prompt = ChatPromptTemplate.from_template(GRAMMAR_REVIEW_PROMPT)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Prepare the prompt messages
        prompt_messages = prompt.invoke({
            "original_content": state["original_content"],
            "translated_content": state["translated_content"],
            "source_language": state["source_language"],
            "target_language": state["target_language"],
        })

        logger.debug("Grammar evaluation prompt prepared, calling LLM...")

        # Handle both real LLM and mock implementations (for testing)
        if hasattr(llm, "invoke"):
            response = llm.invoke(prompt_messages)
        elif hasattr(llm, "__ror__"):
            # Fallback for mocked implementations in tests
            chain = llm.__ror__(prompt_messages)
            if hasattr(chain, "invoke"):
                response = chain.invoke(None)
            else:
                raise TypeError(
                    "Fallback grammar review chain produced by mocked LLM does not "
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
            
            logger.info(f"Grammar evaluation complete. Score: {score:.2f}")
            
            # Determine next node - skip style if grammar is very poor
            next_node = "style_adherence" if score >= -0.5 else "aggregator"
            
            return Command(
                update={
                    "grammar_correctness_score": score,
                    "grammar_correctness_explanation": explanation
                },
                goto=next_node
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing grammar review response: {e}")
            logger.error(f"Raw response: {extract_response_content(response)}")
            return Command(
                update={
                    "grammar_correctness_score": 0.0,
                    "grammar_correctness_explanation": f"ERROR: Could not parse grammar review response - {str(e)}"
                },
                goto="aggregator"
            )
    
    except Exception as e:
        logger.error(f"Error during grammar evaluation: {type(e).__name__}: {str(e)}")
        return Command(
            update={
                "grammar_correctness_score": 0.0,
                "grammar_correctness_explanation": f"ERROR during grammar evaluation: {type(e).__name__}: {str(e)}"
            },
            goto="aggregator"
        )