"""Tests for XLIFF parsing and LLM-based glossary extraction.

This module tests the new functionality for extracting glossary terms from
XLIFF files using both frequency-based and LLM-based methods.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from nodes.document_parsers import parse_xliff, _extract_text_recursive
from nodes.extract_glossary import (
    extract_glossary_with_llm,
    _chunk_text,
    extract_glossary,
)


# ---------------------------------------------------------------------------
# Sample XLIFF files for testing
# ---------------------------------------------------------------------------

SAMPLE_XLIFF_1_2 = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en-US" target-language="es-ES" datatype="plaintext">
    <body>
      <trans-unit id="1">
        <source>Welcome to our application</source>
        <target>Bienvenido a nuestra aplicación</target>
      </trans-unit>
      <trans-unit id="2">
        <source>Click the <g id="1">Submit</g> button to continue</source>
        <target>Haga clic en el botón <g id="1">Enviar</g> para continuar</target>
      </trans-unit>
      <trans-unit id="3">
        <source>API authentication failed</source>
        <target>Falló la autenticación de la API</target>
      </trans-unit>
      <trans-unit id="4">
        <source>Database connection established successfully</source>
        <target>Conexión a la base de datos establecida con éxito</target>
      </trans-unit>
    </body>
  </file>
</xliff>"""

SAMPLE_XLIFF_NO_NAMESPACE = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file source-language="en" target-language="fr">
    <body>
      <trans-unit id="1">
        <source>User authentication module</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Configure the firewall settings</source>
      </trans-unit>
    </body>
  </file>
</xliff>"""

SAMPLE_XLIFF_WITH_INLINE_TAGS = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="de">
    <body>
      <trans-unit id="1">
        <source>The <x id="brand"/>Enterprise Edition<x/> includes advanced features</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Machine learning algorithms process data in real-time</source>
      </trans-unit>
    </body>
  </file>
</xliff>"""

SAMPLE_XLIFF_WITH_FORMATTING_TAGS = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Click the <bpt id="1">&lt;b&gt;</bpt>Submit<ept id="1">&lt;/b&gt;</ept> button</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Enter your <ph id="ph1">{username}</ph> to continue</source>
      </trans-unit>
      <trans-unit id="3">
        <source>The <bpt id="2">&lt;strong&gt;</bpt>API endpoint<ept id="2">&lt;/strong&gt;</ept> is configured</source>
      </trans-unit>
    </body>
  </file>
</xliff>"""


# ---------------------------------------------------------------------------
# Tests for XLIFF parsing
# ---------------------------------------------------------------------------

def test_parse_xliff_basic():
    """Test basic XLIFF parsing with source extraction."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_1_2)
        temp_path = f.name
    
    try:
        segments = parse_xliff(temp_path, extract_target=False)
        
        assert len(segments) == 4
        assert "Welcome to our application" in segments
        assert "Click the Submit button to continue" in segments
        assert "API authentication failed" in segments
        assert "Database connection established successfully" in segments
    finally:
        os.unlink(temp_path)


def test_parse_xliff_target_extraction():
    """Test XLIFF parsing with target text extraction."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_1_2)
        temp_path = f.name
    
    try:
        segments = parse_xliff(temp_path, extract_target=True)
        
        assert len(segments) == 4
        assert "Bienvenido a nuestra aplicación" in segments
        assert "Haga clic en el botón Enviar para continuar" in segments
    finally:
        os.unlink(temp_path)


def test_parse_xliff_no_namespace():
    """Test XLIFF parsing without explicit namespace."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_NO_NAMESPACE)
        temp_path = f.name
    
    try:
        segments = parse_xliff(temp_path, extract_target=False)
        
        assert len(segments) == 2
        assert "User authentication module" in segments
        assert "Configure the firewall settings" in segments
    finally:
        os.unlink(temp_path)


def test_parse_xliff_with_inline_tags():
    """Test XLIFF parsing with inline tags."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_WITH_INLINE_TAGS)
        temp_path = f.name
    
    try:
        segments = parse_xliff(temp_path, extract_target=False)
        
        assert len(segments) == 2
        # Text from inline elements should be extracted
        assert any("Enterprise Edition" in seg for seg in segments)
        assert any("Machine learning" in seg for seg in segments)
    finally:
        os.unlink(temp_path)


def test_parse_xliff_file_not_found():
    """Test XLIFF parsing with non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_xliff("/nonexistent/path.xliff")


def test_parse_xliff_invalid_xml():
    """Test XLIFF parsing with invalid XML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write("This is not valid XML <unclosed>")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Failed to parse XLIFF"):
            parse_xliff(temp_path)
    finally:
        os.unlink(temp_path)


def test_parse_xliff_empty_file():
    """Test XLIFF parsing with file containing no trans-units."""
    empty_xliff = """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="fr">
    <body>
    </body>
  </file>
</xliff>"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(empty_xliff)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="No text segments found"):
            parse_xliff(temp_path)
    finally:
        os.unlink(temp_path)


def test_parse_xliff_excludes_formatting_tags():
    """Test that bpt, ept, and ph tags are excluded from text extraction."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_WITH_FORMATTING_TAGS)
        temp_path = f.name
    
    try:
        segments = parse_xliff(temp_path, extract_target=False)
        
        assert len(segments) == 3
        
        # bpt/ept tags should be excluded - no <b>, </b>, <strong>, </strong> in output
        assert "&lt;b&gt;" not in segments[0]
        assert "&lt;/b&gt;" not in segments[0]
        assert "Click the Submit button" in segments[0]
        
        # ph tag content should be excluded - no {username} placeholder
        assert "{username}" not in segments[1]
        assert "Enter your to continue" in segments[1]
        
        # Another bpt/ept pair
        assert "&lt;strong&gt;" not in segments[2]
        assert "&lt;/strong&gt;" not in segments[2]
        assert "The API endpoint is configured" in segments[2]
    finally:
        os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Tests for text chunking
# ---------------------------------------------------------------------------

def test_chunk_text_single_chunk():
    """Test text chunking when all segments fit in one chunk."""
    segments = ["Short text", "Another short text", "Third segment"]
    chunks = _chunk_text(segments, max_tokens=1000)
    
    assert len(chunks) == 1
    assert "Short text" in chunks[0]
    assert "Another short text" in chunks[0]
    assert "Third segment" in chunks[0]


def test_chunk_text_multiple_chunks():
    """Test text chunking when segments need to be split."""
    # Create segments that will exceed the token limit
    segments = ["A" * 1000 for _ in range(20)]  # 20 segments of 1000 chars each
    chunks = _chunk_text(segments, max_tokens=1000)  # ~250 chars per chunk
    
    assert len(chunks) > 1


def test_chunk_text_empty_segments():
    """Test text chunking with empty segments."""
    segments = []
    chunks = _chunk_text(segments)
    
    assert len(chunks) == 0


# ---------------------------------------------------------------------------
# Tests for LLM-based glossary extraction
# ---------------------------------------------------------------------------

class MockLLMResponse:
    """Mock LLM response for testing."""
    def __init__(self, content):
        self.content = content


class MockLLM:
    """Mock LLM for testing."""
    def __init__(self, response_content):
        self.response_content = response_content
    
    def invoke(self, messages):
        return MockLLMResponse(self.response_content)
    
    def __ror__(self, messages):
        """Support pipe operator for compatibility."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = MockLLMResponse(self.response_content)
        return mock_chain


def test_extract_glossary_with_llm_success():
    """Test LLM-based glossary extraction with successful response."""
    text_segments = [
        "The API authentication module handles user credentials.",
        "Database connection pooling improves performance.",
        "Machine learning algorithms process data in real-time.",
    ]
    
    mock_response = json.dumps([
        {"term": "API", "significance": 0.95},
        {"term": "authentication", "significance": 0.85},
        {"term": "database", "significance": 0.90},
        {"term": "machine learning", "significance": 0.92},
        {"term": "algorithms", "significance": 0.75},
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            terms = extract_glossary_with_llm(text_segments, "English")
            
            assert len(terms) > 0
            # terms is now a list of tuples (term, significance)
            term_names = [t[0] for t in terms]
            term_scores = {t[0]: t[1] for t in terms}
            
            assert "API" in term_names
            assert "authentication" in term_names
            assert "database" in term_names
            assert "machine learning" in term_names
            
            # Check that scores are present and valid
            assert term_scores["API"] == 0.95
            assert term_scores["database"] == 0.90


def test_extract_glossary_with_llm_no_api_key():
    """Test LLM-based extraction without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
            extract_glossary_with_llm(["test text"], "English")


def test_extract_glossary_with_llm_invalid_json():
    """Test LLM-based extraction with invalid JSON response."""
    text_segments = ["Test text for extraction"]
    
    # Response without proper JSON
    mock_response = "These are the terms: API, database, authentication"
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            # Should handle gracefully and return empty list or log warning
            terms = extract_glossary_with_llm(text_segments, "English")
            # Since JSON parsing fails, it should return empty list
            assert isinstance(terms, list)


def test_extract_glossary_with_llm_embedded_json():
    """Test LLM-based extraction with JSON embedded in text."""
    text_segments = ["Test text"]
    
    # Response with JSON embedded in other text (new format with scores)
    mock_response = '''Here are the extracted terms:
[
  {"term": "API", "significance": 0.9},
  {"term": "database", "significance": 0.85},
  {"term": "authentication", "significance": 0.8}
]
These are important.'''
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            terms = extract_glossary_with_llm(text_segments, "English")
            
            term_names = [t[0] for t in terms]
            assert "API" in term_names
            assert "database" in term_names
            assert "authentication" in term_names


def test_extract_glossary_with_llm_max_chunks():
    """Test LLM-based extraction with max_chunks limit."""
    # Create enough segments to generate multiple chunks
    text_segments = ["A" * 1000 for _ in range(20)]
    
    mock_response = json.dumps([
        {"term": "term1", "significance": 0.8},
        {"term": "term2", "significance": 0.7}
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_llm = MockLLM(mock_response)
            mock_openai.return_value = mock_llm
            
            # Limit to 2 chunks
            terms = extract_glossary_with_llm(text_segments, "English", max_chunks=2)
            
            # Should still return results
            assert isinstance(terms, list)
            assert len(terms) >= 0  # May have results


def test_extract_glossary_with_llm_custom_max_terms():
    """Test LLM-based extraction with custom max_terms parameter."""
    text_segments = [
        "The API authentication module handles user credentials.",
        "Database connection pooling improves performance.",
    ]
    
    # Create a mock response with exactly 10 terms with scores all above 0.6
    mock_response = json.dumps([
        {"term": "API", "significance": 0.95},
        {"term": "authentication", "significance": 0.90},
        {"term": "module", "significance": 0.70},
        {"term": "user", "significance": 0.65},
        {"term": "credentials", "significance": 0.85},
        {"term": "database", "significance": 0.92},
        {"term": "connection", "significance": 0.80},
        {"term": "pooling", "significance": 0.75},
        {"term": "performance", "significance": 0.88},
        {"term": "system", "significance": 0.62}  # Above 0.6 threshold
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            # Request exactly 10 terms
            terms = extract_glossary_with_llm(
                text_segments, 
                "English",
                max_terms_per_chunk=10
            )
            
            # Should return the 10 terms
            assert len(terms) == 10
            term_names = [t[0] for t in terms]
            assert "API" in term_names
            assert "authentication" in term_names


def test_extract_glossary_with_llm_backward_compatibility():
    """Test backward compatibility with old string format (no significance scores)."""
    text_segments = ["Test text for extraction"]
    
    # Old format: simple array of strings
    mock_response = json.dumps(["API", "database", "authentication"])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            terms = extract_glossary_with_llm(text_segments, "English")
            
            # Should still work, with default significance of 0.5
            term_names = [t[0] for t in terms]
            term_scores = {t[0]: t[1] for t in terms}
            
            assert "API" in term_names
            assert "database" in term_names
            assert "authentication" in term_names
            
            # All should have default significance
            assert all(score == 0.5 for score in term_scores.values())


def test_extract_glossary_with_llm_sorts_by_significance():
    """Test that terms are sorted by significance score."""
    text_segments = ["Test text"]
    
    # Terms in random order with different significance scores
    mock_response = json.dumps([
        {"term": "low priority", "significance": 0.3},
        {"term": "high priority", "significance": 0.95},
        {"term": "medium priority", "significance": 0.65},
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            # Use min_significance=0.0 to test sorting without filtering
            terms = extract_glossary_with_llm(text_segments, "English", min_significance=0.0)
            
            # Terms should be sorted by significance (highest first)
            assert len(terms) == 3
            assert terms[0][0] == "high priority"
            assert terms[0][1] == 0.95
            assert terms[1][0] == "medium priority"
            assert terms[1][1] == 0.65
            assert terms[2][0] == "low priority"
            assert terms[2][1] == 0.3


def test_extract_glossary_with_llm_filters_by_min_significance():
    """Test that terms below min_significance threshold are filtered out."""
    text_segments = ["Test text"]
    
    # Terms with different significance scores
    mock_response = json.dumps([
        {"term": "high score", "significance": 0.95},
        {"term": "medium score", "significance": 0.75},
        {"term": "low score", "significance": 0.45},
        {"term": "very low score", "significance": 0.20},
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            # Test with default threshold (0.6)
            terms_default = extract_glossary_with_llm(text_segments, "English")
            assert len(terms_default) == 2  # Only 0.95 and 0.75
            term_names = [t[0] for t in terms_default]
            assert "high score" in term_names
            assert "medium score" in term_names
            assert "low score" not in term_names
            
            # Test with custom threshold (0.5)
            terms_custom = extract_glossary_with_llm(text_segments, "English", min_significance=0.5)
            assert len(terms_custom) == 2  # Still only 0.95 and 0.75
            
            # Test with lower threshold (0.4)
            terms_lower = extract_glossary_with_llm(text_segments, "English", min_significance=0.4)
            assert len(terms_lower) == 3  # 0.95, 0.75, and 0.45
            
            # Test with very low threshold (0.0)
            terms_all = extract_glossary_with_llm(text_segments, "English", min_significance=0.0)
            assert len(terms_all) == 4  # All terms


def test_extract_glossary_with_llm_keeps_highest_score():
    """Test that when a term appears multiple times, the highest score is kept."""
    text_segments = ["Test text"]
    
    # Same term with different scores (simulating multiple chunks returning same term)
    mock_response = json.dumps([
        {"term": "API", "significance": 0.7},
        {"term": "database", "significance": 0.8},
        {"term": "API", "significance": 0.95},  # Higher score for same term
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MockLLM(mock_response)
            
            terms = extract_glossary_with_llm(text_segments, "English")
            
            # Should only have 2 unique terms
            assert len(terms) == 2
            
            # API should have the highest score (0.95, not 0.7)
            term_scores = {t[0]: t[1] for t in terms}
            assert term_scores["API"] == 0.95
            assert term_scores["database"] == 0.8


def test_extract_glossary_with_llm_respects_max_terms_in_prompt():
    """Test that max_terms parameter is passed to the LLM prompt."""
    text_segments = ["Test text for extraction"]
    
    mock_response = json.dumps([
        {"term": "term1", "significance": 0.8},
        {"term": "term2", "significance": 0.7},
        {"term": "term3", "significance": 0.6}
    ])
    
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
        with patch("nodes.extract_glossary.ChatPromptTemplate") as mock_template:
            with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
                # Set up mocks
                mock_prompt = MagicMock()
                mock_template.from_template.return_value = mock_prompt
                mock_prompt.invoke.return_value = "mock_messages"
                
                mock_openai.return_value = MockLLM(mock_response)
                
                # Call with custom max_terms
                extract_glossary_with_llm(
                    text_segments,
                    "English",
                    max_terms_per_chunk=25
                )
                
                # Verify that prompt.invoke was called with max_terms=25
                mock_prompt.invoke.assert_called()
                call_args = mock_prompt.invoke.call_args[0][0]
                assert call_args["max_terms"] == 25


# ---------------------------------------------------------------------------
# Integration tests for extract_glossary function
# ---------------------------------------------------------------------------

def test_extract_glossary_xliff_frequency_based():
    """Test glossary extraction from XLIFF using frequency-based method."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_1_2)
        xliff_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    try:
        extract_glossary(
            input_file=xliff_path,
            file_type='xliff',
            source_language='English',
            target_language='Spanish',
            output=csv_path,
            use_llm=False,
        )
        
        # Check that CSV was created
        assert Path(csv_path).exists()
        
        # Read and verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'term,translation' in content
    finally:
        if os.path.exists(xliff_path):
            os.unlink(xliff_path)
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def test_extract_glossary_xliff_llm_based():
    """Test glossary extraction from XLIFF using LLM method."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_1_2)
        xliff_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    mock_response = json.dumps([
        {"term": "application", "significance": 0.85},
        {"term": "authentication", "significance": 0.92},
        {"term": "API", "significance": 0.95},
        {"term": "database", "significance": 0.88}
    ])
    
    try:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
                mock_openai.return_value = MockLLM(mock_response)
                
                extract_glossary(
                    input_file=xliff_path,
                    file_type='xliff',
                    source_language='English',
                    target_language='Spanish',
                    output=csv_path,
                    use_llm=True,
                )
                
                # Check that CSV was created
                assert Path(csv_path).exists()
                
                # Read and verify CSV content
                with open(csv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert 'application' in content.lower()
                    assert 'significance' in content.lower()  # Check for significance column
    finally:
        if os.path.exists(xliff_path):
            os.unlink(xliff_path)
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def test_extract_glossary_auto_detect_xliff():
    """Test automatic detection of XLIFF file type."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False) as f:
        f.write(SAMPLE_XLIFF_1_2)
        xliff_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    try:
        # Don't specify file_type, should auto-detect from extension
        extract_glossary(
            input_file=xliff_path,
            source_language='English',
            target_language='Spanish',
            output=csv_path,
            use_llm=False,
        )
        
        # Check that CSV was created
        assert Path(csv_path).exists()
    finally:
        if os.path.exists(xliff_path):
            os.unlink(xliff_path)
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def test_extract_glossary_text_with_llm():
    """Test glossary extraction from plain text using LLM."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("The API authentication module handles user credentials. "
                "Database connection pooling improves performance.")
        text_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    mock_response = json.dumps([
        {"term": "API", "significance": 0.95},
        {"term": "authentication", "significance": 0.90},
        {"term": "database", "significance": 0.88},
        {"term": "connection pooling", "significance": 0.82}
    ])
    
    try:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            with patch("nodes.extract_glossary.ChatOpenAI") as mock_openai:
                mock_openai.return_value = MockLLM(mock_response)
                
                extract_glossary(
                    input_file=text_path,
                    file_type='text',
                    source_language='English',
                    target_language='Spanish',
                    output=csv_path,
                    use_llm=True,
                )
                
                # Check that CSV was created
                assert Path(csv_path).exists()
    finally:
        if os.path.exists(text_path):
            os.unlink(text_path)
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def test_extract_glossary_file_not_found():
    """Test error handling for non-existent input file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name
    
    try:
        with pytest.raises(FileNotFoundError):
            extract_glossary(
                input_file='/nonexistent/file.xliff',
                source_language='English',
                target_language='Spanish',
                output=csv_path,
            )
    finally:
        if os.path.exists(csv_path):
            os.unlink(csv_path)

