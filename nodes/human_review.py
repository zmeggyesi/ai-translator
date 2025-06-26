from typing import Dict, Any, Optional
from langgraph.types import interrupt
from state import TranslationState

def human_review(state: TranslationState) -> Dict[str, Any]:
    """
    A node that pauses the graph execution to allow for human review.
    The user can review the state and approve the continuation, optionally
    modifying the filtered glossary.
    """
    print("\n--- Human Review ---")
    print("Current filtered glossary:")
    print(state.get("filtered_glossary"))
    print("--------------------")
    
    # The interrupt will pause here and wait for user input
    # When resumed, it will return the value passed in Command(resume=...)
    user_input = interrupt({
        "message": "Review the filtered glossary. Provide a new glossary dict to update it, or empty string to continue.",
        "current_glossary": state.get("filtered_glossary"),
    })
    
    # Handle the resume value
    # If it's a dict, use it as the new glossary
    if isinstance(user_input, dict) and user_input:  # Non-empty dict
        print(f"Updating glossary with: {user_input}")
        return {"filtered_glossary": user_input}
    
    # If empty string or any other value, continue with existing glossary
    print("Continuing with existing glossary")
    return {} 