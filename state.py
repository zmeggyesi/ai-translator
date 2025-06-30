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
    # TMX fields
    tmx_memory: Optional[dict]  # Loaded TMX translation memory entries
    messages: Annotated[List[BaseMessage], add_messages]
    # Review fields
    review_score: Optional[float]  # Score between -1.0 and 1.0
    review_explanation: Optional[str]  # Explanation for low scores
    # Individual dimension scores for multi-node review
    glossary_faithfulness_score: Optional[float]  # Score for glossary compliance
    glossary_faithfulness_explanation: Optional[str]  # Explanation for glossary issues
    grammar_correctness_score: Optional[float]  # Score for grammar quality
    grammar_correctness_explanation: Optional[str]  # Explanation for grammar issues
    style_adherence_score: Optional[float]  # Score for style guide compliance
    style_adherence_explanation: Optional[str]  # Explanation for style issues
    tmx_faithfulness_score: Optional[float]  # Score for TMX compliance
    tmx_faithfulness_explanation: Optional[str]  # Explanation for TMX issues 