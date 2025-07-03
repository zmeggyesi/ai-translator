"""nodes.utils
Utility helpers shared across nodes.
"""
from typing import Any, cast

def extract_response_content(response: Any) -> str:
    """Return the text content of an LLM response object.

    The function attempts to retrieve the ``content`` attribute (as used by
    LangChain `ChatGeneration` and mocked classes in unit tests).  If that
    attribute is missing, it falls back to ``str(response)``.  The return value
    is always a string.
    """
    if hasattr(response, "content"):
        return cast(str, getattr(response, "content"))
    # Some custom mocks may expose a ``text`` field instead.
    if hasattr(response, "text"):
        return cast(str, getattr(response, "text"))
    # Fallback – best effort representation
    return str(response)