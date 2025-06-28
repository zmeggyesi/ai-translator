"""nodes.review_aggregator
--------------------------
Review aggregator node responsible for combining individual dimension scores
into a final translation review assessment.

This node takes the results from specialized review nodes and:
- Combines scores using weighted averages
- Aggregates explanations for scores below threshold
- Produces final review_score and review_explanation
- Maintains compatibility with existing review workflow

Key features:
- Configurable weights for different dimensions
- Intelligent explanation aggregation
- Fallback handling for missing dimension scores
- Final quality assessment categorization
"""

import logging
from state import TranslationState
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Default weights for combining dimension scores
# These can be adjusted based on translation priorities
DEFAULT_WEIGHTS = {
    "glossary_faithfulness": 0.4,  # High weight - terminology is critical
    "grammar_correctness": 0.35,   # High weight - readability is important
    "style_adherence": 0.25,       # Lower weight - style is less critical than accuracy
}

def aggregate_review_scores(state: TranslationState) -> dict:
    """
    Aggregates individual dimension scores into a final review assessment.
    
    This function combines scores from the specialized review nodes using
    weighted averages and consolidates explanations for comprehensive feedback.
    
    Args:
        state: TranslationState containing individual dimension scores
    
    Returns:
        dict: Final review_score and review_explanation for the translation
    """
    logger.info("Aggregating review scores...")
    
    # Extract individual dimension scores
    glossary_score = state.get("glossary_faithfulness_score")
    grammar_score = state.get("grammar_correctness_score")
    style_score = state.get("style_adherence_score")
    
    # Extract explanations
    glossary_explanation = state.get("glossary_faithfulness_explanation", "")
    grammar_explanation = state.get("grammar_correctness_explanation", "")
    style_explanation = state.get("style_adherence_explanation", "")
    
    # Collect available scores and their weights
    available_scores = {}
    total_weight = 0.0
    
    if glossary_score is not None:
        available_scores["glossary_faithfulness"] = glossary_score
        total_weight += DEFAULT_WEIGHTS["glossary_faithfulness"]
        logger.debug(f"Glossary faithfulness score: {glossary_score:.2f}")
    
    if grammar_score is not None:
        available_scores["grammar_correctness"] = grammar_score
        total_weight += DEFAULT_WEIGHTS["grammar_correctness"]
        logger.debug(f"Grammar correctness score: {grammar_score:.2f}")
    
    if style_score is not None:
        available_scores["style_adherence"] = style_score
        total_weight += DEFAULT_WEIGHTS["style_adherence"]
        logger.debug(f"Style adherence score: {style_score:.2f}")
    
    # Calculate weighted average if we have any scores
    if available_scores and total_weight > 0:
        weighted_sum = sum(
            available_scores[dimension] * DEFAULT_WEIGHTS[dimension]
            for dimension in available_scores
        )
        final_score = weighted_sum / total_weight
        
        # Ensure score is within bounds
        final_score = max(-1.0, min(1.0, final_score))
    else:
        # No scores available - this shouldn't happen in normal operation
        logger.error("No dimension scores available for aggregation")
        final_score = 0.0
    
    # Aggregate explanations for scores below the threshold (0.7)
    explanations = []
    
    if glossary_explanation and glossary_score is not None and glossary_score < 0.7:
        explanations.append(f"Glossary Compliance: {glossary_explanation}")
    
    if grammar_explanation and grammar_score is not None and grammar_score < 0.7:
        explanations.append(f"Grammar Quality: {grammar_explanation}")
    
    if style_explanation and style_score is not None and style_score < 0.7:
        explanations.append(f"Style Adherence: {style_explanation}")
    
    # Combine explanations
    final_explanation = ""
    if explanations:
        final_explanation = " | ".join(explanations)
    
    # Add summary if the final score is below threshold but no detailed explanations
    if final_score < 0.7 and not final_explanation:
        if available_scores:
            score_details = [
                f"{dimension.replace('_', ' ').title()}: {score:.2f}"
                for dimension, score in available_scores.items()
            ]
            final_explanation = f"Translation quality below threshold. Scores: {', '.join(score_details)}"
        else:
            final_explanation = "Translation quality assessment incomplete due to evaluation errors."
    
    logger.info(f"Review aggregation complete. Final score: {final_score:.2f}")
    logger.debug(f"Score breakdown: {available_scores}")
    
    return {
        "review_score": final_score,
        "review_explanation": final_explanation
    }


def get_quality_assessment(score: float) -> str:
    """
    Converts a numerical score to a human-readable quality assessment.
    
    Args:
        score: Numerical score between -1.0 and 1.0
    
    Returns:
        str: Human-readable quality assessment
    """
    if score >= 0.7:
        return "Good to Excellent"
    elif score >= 0.3:
        return "Acceptable"
    elif score >= 0.0:
        return "Poor - Needs Improvement"
    else:
        return "Very Poor - Major Revision Required"


def get_detailed_breakdown(state: TranslationState) -> Dict[str, Optional[float]]:
    """
    Extracts a detailed breakdown of all dimension scores.
    
    Args:
        state: TranslationState containing individual dimension scores
    
    Returns:
        dict: Mapping of dimension names to their scores
    """
    return {
        "glossary_faithfulness": state.get("glossary_faithfulness_score"),
        "grammar_correctness": state.get("grammar_correctness_score"),
        "style_adherence": state.get("style_adherence_score"),
    }