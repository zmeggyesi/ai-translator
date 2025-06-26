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
        "-l", "--language",
        type=str,
        default="English",
        help="Target language for translation (default: English)"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="data/input.txt",
        help="Input file path (default: data/input.txt)"
    )
    args = parser.parse_args()

    load_dotenv()
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting translation to {args.language}")

    # 1. Load data
    with open(args.input, "r", encoding="utf-8") as f:
        original_content = f.read()

    glossary = {}
    with open("data/glossary.csv", "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            glossary[row["term"]] = row["translation"]

    with open("data/style_guide.md", "r", encoding="utf-8") as f:
        style_guide = f.read()

    # 2. Create and run the graph
    checkpointer = InMemorySaver()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    translator_app = create_translator(checkpointer=checkpointer)
    initial_state = {
        "original_content": original_content,
        "glossary": glossary,
        "style_guide": style_guide,
        "target_language": args.language,
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
    print(f"\n--- Translated Content ({args.language}) ---")
    print(final_state.get("translated_content"))

if __name__ == "__main__":
    main()
