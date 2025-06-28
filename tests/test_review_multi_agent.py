"""Tests for the multi-agent review system.

Tests cover the individual specialized nodes as well as the integrated
multi-agent workflow, including handoffs and score aggregation.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from typing import cast
from types import SimpleNamespace

from nodes.review_agent import review_translation_multi_agent, review_translation_standalone_multi_agent
from nodes.review_glossary_faithfulness import evaluate_glossary_faithfulness
from nodes.review_grammar_correctness import evaluate_grammar_correctness
from nodes.review_style_adherence import evaluate_style_adherence
from nodes.review_aggregator import aggregate_review_scores
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


def test_glossary_faithfulness_evaluation():
    """Test the glossary faithfulness evaluation node."""
    
    state = cast(TranslationState, {
        "original_content": "Chaos Engineering is an approach to identify critical failures.",
        "translated_content": "Kaos Engineering es un enfoque para identificar fallas críticas.",
        "style_guide": "formal tone",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "filtered_glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "messages": [],
        "glossary_faithfulness_score": None,
        "glossary_faithfulness_explanation": None,
        "grammar_correctness_score": None,
        "grammar_correctness_explanation": None,
        "style_adherence_score": None,
        "style_adherence_explanation": None,
        "review_score": None,
        "review_explanation": None
    })
    
    # This should find that "Chaos Engineering" should be "Ingeniería del Caos" but got "Kaos Engineering"
    result = evaluate_glossary_faithfulness(state)
    
    assert result.update["glossary_faithfulness_score"] < 0.7  # Should be poor due to incorrect term
    assert "Chaos Engineering" in result.update["glossary_faithfulness_explanation"]
    assert result.goto == "aggregator"  # Should skip to aggregator due to low score


def test_glossary_faithfulness_perfect_match():
    """Test glossary evaluation with perfect compliance."""
    
    state = cast(TranslationState, {
        "original_content": "Chaos Engineering is an approach.",
        "translated_content": "Ingeniería del Caos es un enfoque.",
        "style_guide": "formal tone",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "filtered_glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "messages": [],
        "glossary_faithfulness_score": None,
        "glossary_faithfulness_explanation": None,
        "grammar_correctness_score": None,
        "grammar_correctness_explanation": None,
        "style_adherence_score": None,
        "style_adherence_explanation": None,
        "review_score": None,
        "review_explanation": None
    })
    
    result = evaluate_glossary_faithfulness(state)
    
    assert result.update["glossary_faithfulness_score"] == 1.0  # Perfect score
    assert result.update["glossary_faithfulness_explanation"] == ""
    assert result.goto == "grammar_correctness"


def test_glossary_faithfulness_no_relevant_terms():
    """Test glossary evaluation when no relevant terms are found."""
    
    state = cast(TranslationState, {
        "original_content": "This is a simple sentence.",
        "translated_content": "Esta es una oración simple.",
        "style_guide": "formal tone",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {"technical term": "término técnico"},
        "filtered_glossary": {"technical term": "término técnico"},
        "messages": [],
        "glossary_faithfulness_score": None,
        "glossary_faithfulness_explanation": None,
        "grammar_correctness_score": None,
        "grammar_correctness_explanation": None,
        "style_adherence_score": None,
        "style_adherence_explanation": None,
        "review_score": None,
        "review_explanation": None
    })
    
    result = evaluate_glossary_faithfulness(state)
    
    assert result.update["glossary_faithfulness_score"] == 1.0  # Perfect score when no terms to check
    assert result.update["glossary_faithfulness_explanation"] == ""


def test_grammar_correctness_evaluation():
    """Test the grammar correctness evaluation node."""
    
    # Mock the LLM to return a good grammar score
    mock_response = json.dumps({
        "score": 0.8,
        "explanation": ""
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_grammar_correctness.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Hello world",
            "translated_content": "Hola mundo",
            "style_guide": "formal tone",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "glossary_faithfulness_score": None,
            "glossary_faithfulness_explanation": None,
            "grammar_correctness_score": None,
            "grammar_correctness_explanation": None,
            "style_adherence_score": None,
            "style_adherence_explanation": None,
            "review_score": None,
            "review_explanation": None
        })
        
        result = evaluate_grammar_correctness(state)
        
        assert result.update["grammar_correctness_score"] == 0.8
        assert result.update["grammar_correctness_explanation"] == ""
        assert result.goto == "style_adherence"


def test_style_adherence_evaluation():
    """Test the style adherence evaluation node."""
    
    # Mock the LLM to return a low style score with explanation
    mock_response = json.dumps({
        "score": 0.4,
        "explanation": "The translation is too informal for the required formal tone."
    })
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_style_adherence.ChatOpenAI') as mock_openai:
        
        mock_openai.return_value = MockLLM(mock_response)
        
        state = cast(TranslationState, {
            "original_content": "Good morning, sir",
            "translated_content": "¡Hola!",
            "style_guide": "formal and professional tone",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {},
            "filtered_glossary": {},
            "messages": [],
            "glossary_faithfulness_score": None,
            "glossary_faithfulness_explanation": None,
            "grammar_correctness_score": None,
            "grammar_correctness_explanation": None,
            "style_adherence_score": None,
            "style_adherence_explanation": None,
            "review_score": None,
            "review_explanation": None
        })
        
        result = evaluate_style_adherence(state)
        
        assert result.update["style_adherence_score"] == 0.4
        assert "informal" in result.update["style_adherence_explanation"]
        assert result.goto == "aggregator"


def test_review_aggregator():
    """Test the review score aggregation."""
    
    state = cast(TranslationState, {
        "original_content": "Test content",
        "translated_content": "Contenido de prueba",
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {},
        "filtered_glossary": {},
        "messages": [],
        "glossary_faithfulness_score": 0.9,
        "glossary_faithfulness_explanation": "",
        "grammar_correctness_score": 0.8,
        "grammar_correctness_explanation": "",
        "style_adherence_score": 0.6,
        "style_adherence_explanation": "Tone could be more formal",
        "review_score": None,
        "review_explanation": None
    })
    
    result = aggregate_review_scores(state)
    
    # Calculate expected weighted average: 0.9*0.4 + 0.8*0.35 + 0.6*0.25 = 0.79
    expected_score = 0.9 * 0.4 + 0.8 * 0.35 + 0.6 * 0.25
    assert abs(result["review_score"] - expected_score) < 0.01
    
    # Should include style explanation since style score < 0.7
    assert "Style Adherence" in result["review_explanation"]
    assert "Tone could be more formal" in result["review_explanation"]


def test_review_aggregator_missing_scores():
    """Test aggregation when some dimension scores are missing."""
    
    state = cast(TranslationState, {
        "original_content": "Test content",
        "translated_content": "Contenido de prueba",
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {},
        "filtered_glossary": {},
        "messages": [],
        "glossary_faithfulness_score": 1.0,
        "glossary_faithfulness_explanation": "",
        "grammar_correctness_score": None,  # Missing
        "grammar_correctness_explanation": None,
        "style_adherence_score": 0.8,
        "style_adherence_explanation": "",
        "review_score": None,
        "review_explanation": None
    })
    
    result = aggregate_review_scores(state)
    
    # Should calculate weighted average of available scores
    # 1.0*0.4 + 0.8*0.25 = 0.6 (normalized by total weight 0.65)
    expected_score = (1.0 * 0.4 + 0.8 * 0.25) / (0.4 + 0.25)
    assert abs(result["review_score"] - expected_score) < 0.01


def test_multi_agent_review_integration():
    """Test the full multi-agent review workflow."""
    
    # Mock the LLM responses for grammar and style evaluation
    grammar_response = json.dumps({"score": 0.9, "explanation": ""})
    style_response = json.dumps({"score": 0.8, "explanation": ""})
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_grammar_correctness.ChatOpenAI') as mock_grammar_llm, \
         patch('nodes.review_style_adherence.ChatOpenAI') as mock_style_llm:
        
        mock_grammar_llm.return_value = MockLLM(grammar_response)
        mock_style_llm.return_value = MockLLM(style_response)
        
        state = {
            "original_content": "Chaos Engineering helps identify failures.",
            "translated_content": "La Ingeniería del Caos ayuda a identificar fallas.",
            "style_guide": "formal and professional tone",
            "source_language": "English",
            "target_language": "Spanish",
            "glossary": {"Chaos Engineering": "Ingeniería del Caos"},
            "filtered_glossary": {"Chaos Engineering": "Ingeniería del Caos"},
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
        
        result = review_translation_multi_agent(state)
        
        # Should have all dimension scores
        assert result["glossary_faithfulness_score"] == 1.0  # Perfect glossary match
        assert result["grammar_correctness_score"] == 0.9
        assert result["style_adherence_score"] == 0.8
        
        # Should have final aggregated score
        assert result["review_score"] is not None
        assert result["review_score"] > 0.8  # Should be high due to good individual scores


def test_standalone_multi_agent_review():
    """Test the standalone multi-agent review function."""
    
    # Mock the LLM responses
    grammar_response = json.dumps({"score": 0.7, "explanation": ""})
    style_response = json.dumps({"score": 0.5, "explanation": "Tone is too casual for professional context"})
    
    with patch('os.getenv', return_value="fake-api-key"), \
         patch('nodes.review_grammar_correctness.ChatOpenAI') as mock_grammar_llm, \
         patch('nodes.review_style_adherence.ChatOpenAI') as mock_style_llm:
        
        mock_grammar_llm.return_value = MockLLM(grammar_response)
        mock_style_llm.return_value = MockLLM(style_response)
        
        score, explanation = review_translation_standalone_multi_agent(
            original_content="Hello, how are you?",
            translated_content="Hola, ¿qué tal?",
            glossary={"hello": "hola"},
            style_guide="Professional and formal tone",
            source_language="English",
            target_language="Spanish"
        )
        
        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0
        
        # Should have explanation since style score < 0.7
        assert "Style Adherence" in explanation
        assert "casual" in explanation


def test_error_handling_no_translation():
    """Test error handling when no translated content is available."""
    
    state = {
        "original_content": "Test content",
        "translated_content": None,  # Missing translation
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {},
        "filtered_glossary": {},
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
    
    result = review_translation_multi_agent(state)
    
    # Should handle gracefully and provide error scores
    assert result["glossary_faithfulness_score"] == -1.0
    assert "ERROR" in result["glossary_faithfulness_explanation"]


def test_performance_early_termination():
    """Test that poor scores can trigger early termination for efficiency."""
    
    state = cast(TranslationState, {
        "original_content": "Chaos Engineering helps identify failures.",
        "translated_content": "Wrong translation completely unrelated.",
        "style_guide": "formal tone",
        "source_language": "English",
        "target_language": "Spanish",
        "glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "filtered_glossary": {"Chaos Engineering": "Ingeniería del Caos"},
        "messages": [],
        "glossary_faithfulness_score": None,
        "glossary_faithfulness_explanation": None,
        "grammar_correctness_score": None,
        "grammar_correctness_explanation": None,
        "style_adherence_score": None,
        "style_adherence_explanation": None,
        "review_score": None,
        "review_explanation": None
    })
    
    # This should get a very poor glossary score and potentially skip other evaluations
    result = evaluate_glossary_faithfulness(state)
    
    assert result.update["glossary_faithfulness_score"] < -0.5
    # May route directly to aggregator for very poor scores
    assert result.goto in ["grammar_correctness", "aggregator"]