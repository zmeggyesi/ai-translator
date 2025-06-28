"""nodes.review_glossary_faithfulness
----------------------------------------
Review node responsible for evaluating glossary faithfulness in translations.

This node checks whether the translation correctly uses the specified glossary
terms without requiring an LLM. It uses string matching and fuzzy matching to
identify glossary term usage and calculates a score based on compliance.

Key features:
- Non-LLM based evaluation (fast and cost-effective)
- Fuzzy matching for variations in term usage
- Detailed explanations for missing or incorrect terms
- Scores from -1.0 to 1.0 based on glossary compliance
"""

import logging
from rapidfuzz import fuzz, process
from state import TranslationState
from langgraph.types import Command
from typing import Literal

# Configure logging
logger = logging.getLogger(__name__)

def evaluate_glossary_faithfulness(state: TranslationState) -> Command[Literal["tmx_faithfulness", "grammar_correctness", "aggregator"]]:
    """
    Evaluates how well the translation adheres to the specified glossary terms.
    
    This is a non-LLM based evaluation that:
    1. Identifies which glossary terms should appear in the translation
    2. Checks if the correct translations are used
    3. Calculates a score based on compliance percentage
    4. Provides detailed explanations for any issues
    
    Args:
        state: TranslationState containing translation and glossary information
    
    Returns:
        Command: Handoff command with glossary faithfulness score and explanation
    """
    logger.info("Evaluating glossary faithfulness...")
    
    # Check if we have the required content
    if not state.get("translated_content"):
        logger.error("No translated content found for glossary review")
        return Command(
            update={
                "glossary_faithfulness_score": -1.0,
                "glossary_faithfulness_explanation": "ERROR: No translated content available for glossary review"
            },
            goto="aggregator"
        )
    
    original_content = state["original_content"].lower()
    translated_content = state["translated_content"].lower()
    
    # Get the filtered glossary or fall back to the main glossary
    glossary = state.get("filtered_glossary") or state.get("glossary", {})
    
    if not glossary:
        logger.info("No glossary terms to check")
        # Route to TMX if available, otherwise to grammar
        next_node = "tmx_faithfulness" if (state.get("tmx_memory") and state["tmx_memory"].get("entries")) else "grammar_correctness"
        return Command(
            update={
                "glossary_faithfulness_score": 1.0,  # Perfect score if no terms to check
                "glossary_faithfulness_explanation": ""
            },
            goto=next_node
        )
    
    # Find glossary terms that appear in the original content
    relevant_terms = []
    for term, translation in glossary.items():
        term_lower = term.lower()
        
        # Check if the glossary term appears in the original content
        if term_lower in original_content:
            relevant_terms.append((term, translation))
            logger.debug(f"Found relevant glossary term: {term} -> {translation}")
    
    if not relevant_terms:
        logger.info("No relevant glossary terms found in original content")
        # Route to TMX if available, otherwise to grammar
        next_node = "tmx_faithfulness" if (state.get("tmx_memory") and state["tmx_memory"].get("entries")) else "grammar_correctness"
        return Command(
            update={
                "glossary_faithfulness_score": 1.0,  # Perfect score if no relevant terms
                "glossary_faithfulness_explanation": ""
            },
            goto=next_node
        )
    
    # Check each relevant term in the translation
    correct_terms = 0
    total_terms = len(relevant_terms)
    missing_terms = []
    incorrect_terms = []
    
    for term, expected_translation in relevant_terms:
        expected_lower = expected_translation.lower()
        
        # Check if the expected translation appears in the translated content
        if expected_lower in translated_content:
            correct_terms += 1
            logger.debug(f"Correct glossary usage: {term} -> {expected_translation}")
        else:
            # Check for fuzzy matches (maybe close but not exact)
            fuzzy_matches = process.extract(
                expected_lower,
                [translated_content],
                scorer=fuzz.partial_ratio,
                score_cutoff=75
            )
            
            if fuzzy_matches:
                # Found a close match, count as correct but note the variation
                correct_terms += 1
                logger.debug(f"Fuzzy match for glossary term: {term} -> {expected_translation}")
            else:
                # Term is missing or incorrectly translated
                missing_terms.append((term, expected_translation))
                logger.debug(f"Missing/incorrect glossary term: {term} -> {expected_translation}")
    
    # Calculate the score based on compliance percentage
    compliance_rate = correct_terms / total_terms if total_terms > 0 else 1.0
    
    # Scale the score:
    # 100% compliance = 1.0
    # 80%+ compliance = 0.5 to 0.9 (good but some issues)
    # 50%+ compliance = 0.0 to 0.5 (acceptable but needs improvement)
    # <50% compliance = -1.0 to 0.0 (poor, major issues)
    
    if compliance_rate >= 1.0:
        score = 1.0
    elif compliance_rate >= 0.8:
        score = 0.5 + (compliance_rate - 0.8) * 2.0  # Maps 0.8-1.0 to 0.5-0.9
    elif compliance_rate >= 0.5:
        score = (compliance_rate - 0.5) * 1.0  # Maps 0.5-0.8 to 0.0-0.5
    else:
        score = -1.0 + (compliance_rate * 2.0)  # Maps 0.0-0.5 to -1.0-0.0
    
    # Generate explanation if there are issues
    explanation = ""
    if missing_terms:
        explanation = f"Missing or incorrectly translated glossary terms: "
        term_details = [f"'{term}' (should be '{translation}')" for term, translation in missing_terms]
        explanation += ", ".join(term_details)
        explanation += f". Compliance rate: {compliance_rate:.1%} ({correct_terms}/{total_terms} terms correct)."
    
    logger.info(f"Glossary faithfulness evaluation complete. Score: {score:.2f}, Compliance: {compliance_rate:.1%}")
    
    # Determine next node - check for TMX first, then grammar, or skip to aggregator if score is very low
    if score >= -0.5:
        # Check if TMX memory is available
        if state.get("tmx_memory") and state["tmx_memory"].get("entries"):
            next_node = "tmx_faithfulness"
        else:
            next_node = "grammar_correctness"
    else:
        next_node = "aggregator"
    
    return Command(
        update={
            "glossary_faithfulness_score": score,
            "glossary_faithfulness_explanation": explanation
        },
        goto=next_node
    )