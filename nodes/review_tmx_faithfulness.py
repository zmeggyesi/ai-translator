"""nodes.review_tmx_faithfulness
-------------------------------
Review node responsible for evaluating TMX (Translation Memory) faithfulness in translations.

This node checks whether the translation correctly follows the patterns and style
established in the TMX translation memory. It validates both exact matches and
stylistic consistency with similar segments from the translation memory.

Key features:
- Non-LLM based evaluation (fast and cost-effective)
- Validates exact TMX matches were used when available
- Checks stylistic consistency with similar TMX entries
- Provides detailed explanations for TMX-related issues
- Scores from -1.0 to 1.0 based on TMX compliance and style consistency

Testing strategy
----------------
Unit tests mock TMX data to test matching logic without requiring actual TMX files.
The module handles missing TMX data gracefully and provides clear feedback.
"""

import logging
from rapidfuzz import fuzz
from state import TranslationState
from nodes.tmx_loader import find_tmx_matches
from langgraph.types import Command
from typing import Literal

# Configure logging
logger = logging.getLogger(__name__)

def evaluate_tmx_faithfulness(state: TranslationState) -> Command[Literal["style_adherence", "aggregator"]]:
    """
    Evaluates how well the translation adheres to TMX translation memory patterns.
    
    This evaluation:
    1. Checks if exact TMX matches should have been used
    2. Validates style consistency with similar TMX entries
    3. Calculates a score based on TMX compliance
    4. Provides detailed explanations for any issues
    
    Args:
        state: TranslationState containing translation and TMX memory information
    
    Returns:
        Command: Handoff command with TMX faithfulness score and explanation
    """
    logger.info("Evaluating TMX faithfulness...")
    
    # Check if we have the required content
    if not state.get("translated_content"):
        logger.error("No translated content found for TMX review")
        return Command(
            update={
                "tmx_faithfulness_score": -1.0,
                "tmx_faithfulness_explanation": "ERROR: No translated content available for TMX review"
            },
            goto="aggregator"
        )
    
    original_content = state["original_content"]
    translated_content = state["translated_content"]
    
    # Get TMX memory
    tmx_memory = state.get("tmx_memory", {})
    
    if not tmx_memory or "entries" not in tmx_memory:
        logger.info("No TMX memory available for evaluation")
        return Command(
            update={
                "tmx_faithfulness_score": 1.0,  # Perfect score if no TMX to check
                "tmx_faithfulness_explanation": ""
            },
            goto="style_adherence"
        )
    
    tmx_entries = tmx_memory["entries"]
    
    if not tmx_entries:
        logger.info("No TMX entries available for current language pair")
        return Command(
            update={
                "tmx_faithfulness_score": 1.0,  # Perfect score if no entries
                "tmx_faithfulness_explanation": ""
            },
            goto="style_adherence"
        )
    
    # Check for exact matches that should have been used
    exact_matches = find_tmx_matches(original_content, tmx_entries, threshold=100.0)
    score = 1.0
    explanation = ""
    
    if exact_matches:
        # There should be an exact TMX match used
        best_exact_match = exact_matches[0]
        expected_translation = best_exact_match["target"]
        
        # Check if the actual translation matches the expected TMX translation
        translation_similarity = fuzz.ratio(translated_content.lower().strip(), 
                                          expected_translation.lower().strip())
        
        if translation_similarity < 95.0:  # Allow for minor variations
            score = -0.5
            explanation = (f"Available exact TMX match was not used. "
                          f"Expected: \"{expected_translation}\" "
                          f"(from TMX entry: \"{best_exact_match['source']}\" -> \"{best_exact_match['target']}\"), "
                          f"but got: \"{translated_content}\"")
            logger.warning(f"Exact TMX match not used: expected '{expected_translation}', got '{translated_content}'")
        else:
            logger.info("Translation correctly uses exact TMX match")
    
    else:
        # No exact matches - check for style consistency with similar entries
        fuzzy_matches = find_tmx_matches(original_content, tmx_entries, threshold=70.0)
        
        if fuzzy_matches:
            # Analyze style consistency
            style_scores = []
            
            for match in fuzzy_matches[:3]:  # Check top 3 matches
                # Simple style consistency check - could be more sophisticated
                tmx_target = match["target"]
                
                # Check for similar patterns (length, punctuation, capitalization)
                length_ratio = len(translated_content) / max(len(tmx_target), 1)
                if 0.5 <= length_ratio <= 2.0:  # Reasonable length similarity
                    style_scores.append(0.8)
                else:
                    style_scores.append(0.3)
                
                # Check punctuation consistency
                if (translated_content.endswith('.') == tmx_target.endswith('.') and
                    translated_content.endswith('?') == tmx_target.endswith('?') and
                    translated_content.endswith('!') == tmx_target.endswith('!')):
                    style_scores.append(0.9)
                else:
                    style_scores.append(0.5)
            
            if style_scores:
                avg_style_score = sum(style_scores) / len(style_scores)
                
                if avg_style_score < 0.6:
                    score = 0.2
                    explanation = (f"Translation style is inconsistent with similar TMX entries. "
                                 f"Similar TMX entries suggest different style patterns.")
                    logger.info("Translation style inconsistent with TMX patterns")
                elif avg_style_score < 0.8:
                    score = 0.7
                    explanation = (f"Translation style partially matches TMX patterns but could be more consistent.")
                    logger.info("Translation style partially consistent with TMX patterns")
                else:
                    logger.info("Translation style consistent with TMX patterns")
    
    # Calculate final score
    if explanation:
        logger.info(f"TMX faithfulness evaluation complete. Score: {score:.2f}")
    else:
        logger.info(f"TMX faithfulness evaluation complete. Score: {score:.2f} (no issues found)")
    
    # Determine next node - skip style_adherence if score is very low
    next_node = "style_adherence" if score >= -0.2 else "aggregator"
    
    return Command(
        update={
            "tmx_faithfulness_score": score,
            "tmx_faithfulness_explanation": explanation
        },
        goto=next_node
    )