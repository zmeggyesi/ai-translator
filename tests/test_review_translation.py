"""Tests for the review_translation node.

Tests cover various scenarios including high/low scores, error handling,
and the standalone review functionality.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from typing import cast
from types import SimpleNamespace

from nodes.review_translation import review_translation, review_translation_standalone
from state import TranslationState


class MockLLMResponse:
    """Mock LLM response for testing."""
    def __init__(self, content: str):
        self.content = content


class MockLLM:
    """Mock LLM implementation for testing."""
    def __init__(self, response_content: str):
        self.response_content = response_content
    
    def invoke(self, prompt_messages):
        return MockLLMResponse(self.response_content)
    
    def __ror__(self, prompt_messages):
        # Return a mock chain that can be invoked
        mock_chain = SimpleNamespace()
        mock_chain.invoke = lambda _: MockLLMResponse(self.response_content)
        return mock_chain


def test_review_translation_high_score():
    """Test review with high score (no explanation needed)."""
    
    # Mock the LLM to return a high score
    mock_response = json.dumps({
        "score": 0.9,
        "explanation": ""
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Hello world",
            "translated_content": "Hola mundo",
            "style_guide": "formal tone",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {"hello": "hola"},
            "filtered_glossary": {"hello": "hola"},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        assert "review_score" in result
        assert "review_explanation" in result
        assert result["review_score"] == 0.9
        assert result["review_explanation"] == ""


def test_review_translation_low_score():
    """Test review with low score (explanation required)."""
    
    # Mock the LLM to return a low score with explanation
    mock_response = json.dumps({
        "score": 0.3,
        "explanation": "The translation lacks formal tone and has grammatical errors."
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Good morning, sir",
            "translated_content": "Buenos dias",
            "style_guide": "formal and professional tone",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {"good morning": "buenos días"},
            "filtered_glossary": None,  # Should fall back to main glossary
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        assert result["review_score"] == 0.3
        assert "grammatical errors" in result["review_explanation"]


def test_review_translation_score_bounds():
    """Test that scores are properly bounded between -1.0 and 1.0."""
    
    # Mock the LLM to return an out-of-bounds score
    mock_response = json.dumps({
        "score": 1.5,  # Out of bounds
        "explanation": ""
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Test",
            "translated_content": "Prueba",
            "style_guide": "formal",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        # Score should be clamped to 1.0
        assert result["review_score"] == 1.0


def test_review_translation_no_api_key():
    """Test behavior when OpenAI API key is not available."""
    
    with patch('os.getenv', return_value=None):  # No API key
        state = cast(TranslationState, {
            "original_content": "Test content",
            "translated_content": "Contenido de prueba",
            "style_guide": "formal",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        assert result["review_score"] == 0.0
        assert "OpenAI API key not found" in result["review_explanation"]


def test_review_translation_no_content():
    """Test behavior when there's no translated content to review."""
    
    state = cast(TranslationState, {
        "original_content": "Test content",
        "translated_content": None,  # No translation to review
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {},
        "filtered_glossary": {},
        "messages": [],
        "review_score": None,
        "review_explanation": None
    })
    
    result = review_translation(state)
    
    assert result["review_score"] == -1.0
    assert "No translated content available" in result["review_explanation"]


def test_review_translation_invalid_json():
    """Test behavior when LLM returns invalid JSON."""
    
    # Mock the LLM to return invalid JSON
    mock_response = "This is not valid JSON"
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Test",
            "translated_content": "Prueba",
            "style_guide": "formal",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        assert result["review_score"] == 0.0
        assert "Could not parse review response" in result["review_explanation"]


def test_review_translation_missing_score():
    """Test behavior when LLM response is missing required fields."""
    
    # Mock the LLM to return JSON without required fields
    mock_response = json.dumps({
        "explanation": "Some explanation"
        # Missing "score" field
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Test",
            "translated_content": "Prueba",
            "style_guide": "formal",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        # Should default to 0.0 when score is missing
        assert result["review_score"] == 0.0
        assert result["review_explanation"] == "Some explanation"


def test_review_translation_standalone():
    """Test the standalone review function."""
    
    # Mock the LLM to return a score
    mock_response = json.dumps({
        "score": 0.8,
        "explanation": ""
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        score, explanation = review_translation_standalone(
            original_content="Hello world",
            translated_content="Hola mundo",
            glossary={"hello": "hola", "world": "mundo"},
            style_guide="Use formal tone",
            source_language="English",
            target_language="Spanish"
        )
        
        assert score == 0.8
        assert explanation == ""


def test_review_translation_standalone_with_explanation():
    """Test standalone review with low score requiring explanation."""
    
    # Mock the LLM to return a low score with explanation
    mock_response = json.dumps({
        "score": 0.4,
        "explanation": "Translation needs improvement in formal tone usage."
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        score, explanation = review_translation_standalone(
            original_content="Good evening",
            translated_content="Buenas",
            glossary={"good evening": "buenas tardes"},
            style_guide="Professional and complete translations",
            source_language="English",
            target_language="Spanish"
        )
        
        assert score == 0.4
        assert "formal tone" in explanation


def test_review_translation_with_mock_chain():
    """Test the fallback path for mocked LLM implementations."""
    
    mock_response = json.dumps({
        "score": 0.75,
        "explanation": ""
    })
    
    # Create a mock LLM that uses the __ror__ pattern
    class MockChainLLM:
        def __ror__(self, prompt_messages):
            mock_chain = SimpleNamespace()
            mock_chain.invoke = lambda _: MockLLMResponse(mock_response)
            return mock_chain
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_translation.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockChainLLM()
        
        state = cast(TranslationState, {
            "original_content": "Test",
            "translated_content": "Prueba",
            "style_guide": "formal",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "review_score": None,
            "review_explanation": None
        })
        
        result = review_translation(state)
        
        assert result["review_score"] == 0.75
        assert result["review_explanation"] == ""