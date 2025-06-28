import csv
import json
import logging
import argparse
from dotenv import load_dotenv
from graph import create_translator
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
import uuid

def setup_logging():
    """Configures the logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Set the logging level for this application's logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)


def main():
    """
    Main function to run the translation process.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Translate content using AI with glossary and style guide")
    parser.add_argument(
        "-sl", "--source-language",
        type=str,
        default="English",
        help="Source language of the input text (default: English)"
    )
    parser.add_argument(
        "-tl", "--target-language",
        type=str,
        default="Spanish",
        help="Target language for translation (default: Spanish)"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="data/input.txt",
        help="Input file path (default: data/input.txt)"
    )
    parser.add_argument(
        "-g", "--glossary",
        type=str,
        default="data/glossary.csv",
        help="Glossary CSV file path (default: data/glossary.csv)"
    )
    parser.add_argument(
        "-s", "--style-guide",
        type=str,
        default="data/style_guide.md",
        help="Style guide file path (default: data/style_guide.md)"
    )
    # Keep backward compatibility with -l/--language for target language
    parser.add_argument(
        "-l", "--language",
        type=str,
        help="Target language for translation (deprecated, use --target-language instead)"
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Enable automatic translation review and scoring"
    )
    args = parser.parse_args()

    # Handle backward compatibility
    target_language = args.target_language
    if args.language:
        target_language = args.language
        print("Warning: -l/--language is deprecated, use -tl/--target-language instead")

    load_dotenv()
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting translation from {args.source_language} to {target_language}")
    if args.review:
        logger.info("Translation review is enabled")

    # 1. Load data
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            original_content = f.read()
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input}")
        return
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return

    glossary = {}
    try:
        with open(args.glossary, "r", encoding="utf-8", newline="") as f:
            # First, try to read with headers
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            # Check if the CSV has proper headers (term, translation)
            if fieldnames and "term" in fieldnames and "translation" in fieldnames:
                # CSV has proper headers
                for row in reader:
                    if row["term"] and row["translation"]:  # Skip empty rows
                        glossary[row["term"]] = row["translation"]
                logger.info(f"Loaded glossary with headers from {args.glossary}")
            else:
                # CSV doesn't have proper headers, treat as headerless
                # Reset file pointer to beginning
                f.seek(0)
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if len(row) >= 2 and row[0] and row[1]:  # Ensure we have at least 2 columns and they're not empty
                        glossary[row[0]] = row[1]  # First column = term, second = translation
                    elif len(row) < 2:
                        logger.warning(f"Skipping row {row_num} in glossary: insufficient columns")
                logger.info(f"Loaded headerless glossary from {args.glossary} (assuming first column=term, second=translation)")
                
    except FileNotFoundError:
        logger.error(f"Glossary file not found: {args.glossary}")
        return
    except Exception as e:
        logger.error(f"Error reading glossary file {args.glossary}: {e}")
        logger.error("Please ensure the CSV file either has 'term,translation' headers or is formatted with term in first column, translation in second column")
        return

    try:
        with open(args.style_guide, "r", encoding="utf-8") as f:
            style_guide = f.read()
    except FileNotFoundError:
        logger.error(f"Style guide file not found: {args.style_guide}")
        return
    except Exception as e:
        logger.error(f"Error reading style guide file: {e}")
        return

    # 2. Create and run the graph
    checkpointer = InMemorySaver()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    translator_app = create_translator(checkpointer=checkpointer, include_review=args.review)
    initial_state = {
        "original_content": original_content,
        "glossary": glossary,
        "style_guide": style_guide,
        "source_language": args.source_language,
        "target_language": target_language,
        "messages": [], # Initialize messages list
    }

    # First invocation
    result = translator_app.invoke(initial_state, config=config)

    # Check if we're in an interrupted state
    while isinstance(result, dict) and "__interrupt__" in result:
        print("\n--- Human Review Interrupt ---")
        interrupts = result.get("__interrupt__", [])
        if interrupts:
            interrupt_info = interrupts[0] if isinstance(interrupts, tuple) else interrupts
            print(f"Interrupt payload: {interrupt_info}")
        
        print("\n--- Waiting for human input ---")
        print("To provide a new glossary, enter a JSON string. Otherwise, press Enter to continue.")
        user_input = input("> ")

        resume_value = ""  # Default to empty string
        if user_input:
            try:
                # Pass the new glossary directly as the resume value
                resume_value = json.loads(user_input)
            except json.JSONDecodeError:
                print("Invalid JSON. Resuming with no changes.")
                resume_value = ""  # Keep as empty string
        
        # Resume the graph
        result = translator_app.invoke(Command(resume=resume_value), config=config)
    
    # At this point, result should contain the final state
    final_state = result
    
    # 3. Print results
    print("\n--- Original Content ---")
    print(original_content)
    print(f"\n--- Translated Content ({args.source_language} → {target_language}) ---")
    print(final_state.get("translated_content"))
    
    # Print review results if enabled
    if args.review and final_state.get("review_score") is not None:
        print(f"\n--- Translation Review ---")
        score = final_state.get("review_score")
        explanation = final_state.get("review_explanation", "")
        
        print(f"Overall Review Score: {score:.2f} (on scale from -1.0 to 1.0)")
        
        if score >= 0.7:
            print("Quality Assessment: Good to Excellent")
        elif score >= 0.3:
            print("Quality Assessment: Acceptable")
        elif score >= 0.0:
            print("Quality Assessment: Poor - Needs Improvement")
        else:
            print("Quality Assessment: Very Poor - Major Revision Required")
        
        # Show detailed breakdown from multi-agent review
        print(f"\n--- Detailed Score Breakdown ---")
        glossary_score = final_state.get("glossary_faithfulness_score")
        grammar_score = final_state.get("grammar_correctness_score")
        style_score = final_state.get("style_adherence_score")
        
        if glossary_score is not None:
            print(f"Glossary Faithfulness: {glossary_score:.2f}")
        if grammar_score is not None:
            print(f"Grammar Correctness: {grammar_score:.2f}")
        if style_score is not None:
            print(f"Style Adherence: {style_score:.2f}")
        
        if explanation:
            print(f"\nReview Explanation: {explanation}")
        else:
            print("\nReview Explanation: None needed (score is sufficiently high)")
        
        # Show individual dimension explanations if available
        dimension_explanations = [
            ("Glossary", final_state.get("glossary_faithfulness_explanation", "")),
            ("Grammar", final_state.get("grammar_correctness_explanation", "")),
            ("Style", final_state.get("style_adherence_explanation", ""))
        ]
        
        individual_issues = [f"{dim}: {expl}" for dim, expl in dimension_explanations if expl]
        if individual_issues:
            print(f"\nDetailed Issues:")
            for issue in individual_issues:
                print(f"  - {issue}")

if __name__ == "__main__":
    main()
