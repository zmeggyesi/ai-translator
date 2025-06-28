"""nodes.review_agent
----------------------
Multi-agent translation review system using LangGraph's Agent Communication Protocol.

This module creates a specialized review graph that breaks down translation
evaluation into focused dimensions:
- Glossary faithfulness (non-LLM based)
- Grammar correctness (LLM-based)
- Style adherence (LLM-based)
- Score aggregation (algorithmic)

The multi-agent approach provides:
- Better performance through specialized evaluation
- Token efficiency with focused prompts
- Modular testing and maintenance
- Parallel evaluation potential
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from state import TranslationState
from nodes.review_glossary_faithfulness import evaluate_glossary_faithfulness
from nodes.review_grammar_correctness import evaluate_grammar_correctness
from nodes.review_style_adherence import evaluate_style_adherence
from nodes.review_aggregator import aggregate_review_scores

# Configure logging
logger = logging.getLogger(__name__)

def create_review_agent(checkpointer: BaseCheckpointSaver = None):
    """
    Creates and compiles the multi-agent translation review graph.
    
    The review agent uses the Agent Communication Protocol to coordinate
    between specialized evaluation nodes, allowing for efficient and
    focused assessment of translation quality.
    
    Graph topology:
    
    [glossary_faithfulness] → [grammar_correctness] → [style_adherence] → [aggregator] → END
                           ↘                      ↘
                             [aggregator] ← [aggregator]
    
    Args:
        checkpointer: Optional checkpoint saver for state persistence
    
    Returns:
        Compiled LangGraph for translation review
    """
    logger.info("Creating multi-agent review graph...")
    
    # Create the review graph
    review_graph = StateGraph(TranslationState)
    
    # Add specialized review nodes
    review_graph.add_node("glossary_faithfulness", evaluate_glossary_faithfulness)
    review_graph.add_node("grammar_correctness", evaluate_grammar_correctness) 
    review_graph.add_node("style_adherence", evaluate_style_adherence)
    review_graph.add_node("aggregator", aggregate_review_scores)
    
    # Set the entry point - always start with glossary evaluation
    review_graph.set_entry_point("glossary_faithfulness")
    
    # The specialized nodes use Command objects to determine routing
    # so we don't need to add explicit edges - the Command.goto handles routing
    
    # Final edge from aggregator to end
    review_graph.add_edge("aggregator", END)
    
    # Compile the graph
    if checkpointer:
        compiled_graph = review_graph.compile(checkpointer=checkpointer)
    else:
        compiled_graph = review_graph.compile()
    
    logger.info("Multi-agent review graph created successfully")
    return compiled_graph


def review_translation_multi_agent(state: TranslationState, checkpointer: BaseCheckpointSaver = None) -> dict:
    """
    Main function to review a translation using the multi-agent approach.
    
    This function serves as the primary interface for the multi-agent review
    system, maintaining compatibility with the existing review workflow.
    
    Args:
        state: TranslationState containing translation and evaluation criteria
        checkpointer: Optional checkpoint saver for state persistence
    
    Returns:
        dict: Updated state with review scores and explanations
    """
    logger.info("Starting multi-agent translation review...")
    
    # Create the review graph
    review_graph = create_review_agent(checkpointer)
    
    # Execute the review workflow
    try:
        # Run the multi-agent review
        result = review_graph.invoke(state)
        
        logger.info("Multi-agent review completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error during multi-agent review: {type(e).__name__}: {str(e)}")
        return {
            **state,
            "review_score": 0.0,
            "review_explanation": f"ERROR during multi-agent review: {type(e).__name__}: {str(e)}"
        }


def review_translation_standalone_multi_agent(
    original_content: str,
    translated_content: str,
    glossary: dict,
    style_guide: str,
    source_language: str = "English",
    target_language: str = "Spanish"
) -> tuple[float, str]:
    """
    Standalone function to review a translation using the multi-agent approach.
    
    This allows the multi-agent review system to be called independently
    from the main translation graph while maintaining the same interface
    as the original standalone function.
    
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
    state_dict = {
        "original_content": original_content,
        "translated_content": translated_content,
        "glossary": glossary,
        "filtered_glossary": None,  # Will use main glossary
        "style_guide": style_guide,
        "source_language": source_language,
        "target_language": target_language,
        "messages": [],
        # Initialize dimension scores to None
        "glossary_faithfulness_score": None,
        "glossary_faithfulness_explanation": None,
        "grammar_correctness_score": None,
        "grammar_correctness_explanation": None,
        "style_adherence_score": None,
        "style_adherence_explanation": None,
        "review_score": None,
        "review_explanation": None
    }
    
    # Call the main multi-agent review function
    result = review_translation_multi_agent(state_dict)
    
    return result.get("review_score", 0.0), result.get("review_explanation", "")


if __name__ == "__main__":
    """
    Command-line interface for standalone multi-agent translation review.
    """
    import argparse
    import csv
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Review a translation quality using multi-agent system")
    parser.add_argument("-o", "--original", required=True, help="Original text file")
    parser.add_argument("-t", "--translation", required=True, help="Translated text file")
    parser.add_argument("-g", "--glossary", default="data/glossary.csv", help="Glossary CSV file")
    parser.add_argument("-s", "--style-guide", default="data/style_guide.md", help="Style guide file")
    parser.add_argument("-sl", "--source-language", default="English", help="Source language")
    parser.add_argument("-tl", "--target-language", default="Spanish", help="Target language")
    parser.add_argument("--breakdown", action="store_true", help="Show detailed score breakdown")
    
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
        
        # Perform multi-agent review
        score, explanation = review_translation_standalone_multi_agent(
            original, translation, glossary, style_guide,
            args.source_language, args.target_language
        )
        
        print(f"Multi-Agent Review Score: {score:.2f}")
        if explanation:
            print(f"Review Explanation: {explanation}")
        else:
            print("Review Explanation: None (score is sufficiently high)")
        
        # Show detailed breakdown if requested
        if args.breakdown:
            state_dict = {
                "original_content": original,
                "translated_content": translation,
                "glossary": glossary,
                "filtered_glossary": None,
                "style_guide": style_guide,
                "source_language": args.source_language,
                "target_language": args.target_language,
                "messages": [],
                "glossary_faithfulness_score": None,
                "glossary_faithfulness_explanation": None,
                "grammar_correctness_score": None,
                "grammar_correctness_explanation": None,
                "style_adherence_score": None,
                "style_adherence_explanation": None,
                "review_score": None,
                "review_explanation": None
            }
            
            result = review_translation_multi_agent(state_dict)
            
            print("\n--- Detailed Score Breakdown ---")
            print(f"Glossary Faithfulness: {result.get('glossary_faithfulness_score', 'N/A')}")
            print(f"Grammar Correctness: {result.get('grammar_correctness_score', 'N/A')}")
            print(f"Style Adherence: {result.get('style_adherence_score', 'N/A')}")
            
            # Show individual explanations if any
            explanations = [
                ("Glossary", result.get('glossary_faithfulness_explanation', '')),
                ("Grammar", result.get('grammar_correctness_explanation', '')),
                ("Style", result.get('style_adherence_explanation', ''))
            ]
            
            for dimension, expl in explanations:
                if expl:
                    print(f"{dimension} Issues: {expl}")
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")