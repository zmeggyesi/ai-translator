from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class TranslationState(TypedDict):
    original_content: str
    glossary: dict
    style_guide: str
    source_language: str  # Source language for translation
    target_language: str  # Target language for translation
    filtered_glossary: Optional[dict]
    translated_content: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages] 