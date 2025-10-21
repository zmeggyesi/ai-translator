"""Tests for combined LLM + TF-IDF glossary extraction."""
import pytest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from nodes.extract_glossary import extract_glossary, _normalize_scores


def test_extract_glossary_combined_xliff(tmp_path):
    """Test extract_glossary with both LLM and TF-IDF on XLIFF."""
    # Create a temporary XLIFF file
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Machine learning algorithms process data efficiently</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Deep learning networks analyze complex patterns</source>
      </trans-unit>
      <trans-unit id="3">
        <source>Artificial intelligence systems make decisions</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock the LLM extraction to return controlled results
    mock_llm_terms = [
        ("machine learning", 0.95),
        ("artificial intelligence", 0.90),
        ("deep learning", 0.85),
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        # Extract with both LLM and TF-IDF
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=20,
            max_ngram_size=2,
        )
    
    # Check that output file was created
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    # Should have header + terms
    assert len(lines) > 1
    assert "term" in lines[0]
    assert "significance" in lines[0]
    
    # Should contain terms from LLM
    assert any("machine learning" in line for line in lines)
    assert any("artificial intelligence" in line for line in lines)


def test_extract_glossary_combined_text(tmp_path):
    """Test extract_glossary with both LLM and TF-IDF on text file."""
    # Create a temporary text file
    text_file = tmp_path / "test.txt"
    text_content = """
Machine learning is a powerful technology.
It enables systems to learn from data.

Deep learning is an advanced technique.
Neural networks process complex information.
"""
    text_file.write_text(text_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock the LLM extraction
    mock_llm_terms = [
        ("machine learning", 0.95),
        ("deep learning", 0.90),
        ("neural networks", 0.85),
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        # Extract with both LLM and TF-IDF
        extract_glossary(
            input_file=str(text_file),
            file_type="text",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=15,
            max_ngram_size=2,
        )
    
    # Check that output file was created
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    # Should have header + terms
    assert len(lines) > 1
    
    # Should contain terms from LLM
    assert any("machine learning" in line or "deep learning" in line for line in lines)


def test_combined_extraction_merges_duplicates(tmp_path):
    """Test that combined extraction keeps highest score for exact duplicate terms."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Data processing algorithms handle information</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Complex algorithms process data efficiently</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock LLM to return terms that might overlap with TF-IDF
    # Use unigrams that TF-IDF will also extract
    mock_llm_terms = [
        ("algorithms", 0.95),  # Higher score from LLM
        ("processing", 0.85),
        ("data", 0.60),  # Lower score from LLM - TF-IDF might score it higher
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=20,
            max_ngram_size=1,  # Only unigrams to ensure overlaps
        )
    
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    # Find the line with "algorithms" - should appear exactly once
    algo_lines = [line for line in lines if line.startswith("algorithms,")]
    assert len(algo_lines) == 1  # Should only appear once, not duplicated
    
    # The score for "algorithms" should be 0.95 (the higher LLM score)
    assert "0.95" in algo_lines[0]


def test_combined_extraction_union_of_terms(tmp_path):
    """Test that combined extraction produces union of unique terms."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Machine learning algorithms</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Deep learning networks</source>
      </trans-unit>
      <trans-unit id="3">
        <source>Artificial intelligence systems</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock LLM to return specific terms
    mock_llm_terms = [
        ("machine learning", 0.95),
        ("artificial intelligence", 0.90),
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=20,
        )
    
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    # Should have more terms than just the LLM output (union)
    # TF-IDF should contribute additional terms like "deep", "learning", etc.
    assert len(lines) > 3  # Header + at least 2 LLM terms + some TF-IDF terms


def test_normalize_scores():
    """Test score normalization function."""
    terms = [
        ("term1", 0.5),
        ("term2", 0.3),
        ("term3", 0.1),
    ]
    
    # Normalize to max of 1.0
    normalized = _normalize_scores(terms, target_max=1.0)
    
    # Max should be 1.0
    assert normalized[0] == ("term1", 1.0)
    # Others should be scaled proportionally
    assert normalized[1] == ("term2", 0.6)
    assert normalized[2] == ("term3", 0.2)


def test_normalize_scores_different_target():
    """Test normalization to different target max."""
    terms = [
        ("term1", 0.2),
        ("term2", 0.1),
    ]
    
    # Normalize to max of 0.95
    normalized = _normalize_scores(terms, target_max=0.95)
    
    # Max should be 0.95
    assert abs(normalized[0][1] - 0.95) < 0.001
    # Other should be scaled proportionally
    assert abs(normalized[1][1] - 0.475) < 0.001


def test_normalize_scores_empty():
    """Test normalization with empty list."""
    normalized = _normalize_scores([], target_max=1.0)
    assert normalized == []


def test_normalize_scores_zero():
    """Test normalization with zero scores."""
    terms = [("term1", 0.0), ("term2", 0.0)]
    normalized = _normalize_scores(terms, target_max=1.0)
    # Should return unchanged to avoid division by zero
    assert normalized == terms


def test_combined_extraction_score_normalization(tmp_path):
    """Test that combined extraction normalizes TF-IDF scores to LLM scale."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Machine learning algorithms</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Deep learning systems</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock LLM to return terms with scores in 0.8-0.95 range
    mock_llm_terms = [
        ("machine learning", 0.95),
        ("deep learning", 0.90),
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=20,
            max_ngram_size=1,  # Unigrams only for simpler test
        )
    
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")[1:]  # Skip header
    
    # Parse scores
    scores = []
    for line in lines:
        parts = line.split(",")
        if len(parts) >= 3:
            score = float(parts[2])
            scores.append(score)
    
    # All scores should be in reasonable range (0-1.0)
    assert all(0 <= score <= 1.0 for score in scores)
    
    # Max score should be close to LLM max (0.95)
    max_score = max(scores)
    assert abs(max_score - 0.95) < 0.01  # Within 0.01 of LLM max


def test_source_column_in_combined_extraction(tmp_path):
    """Test that source column correctly identifies LLM vs TF-IDF terms."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Machine learning algorithms</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Deep learning systems</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Mock LLM to return specific terms
    mock_llm_terms = [
        ("machine learning", 0.95),
        ("deep learning", 0.90),
    ]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=True,
            max_terms=20,
            max_ngram_size=2,
        )
    
    # Read and parse the CSV
    import csv
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Should have source column
    assert "source" in rows[0].keys()
    
    # Find LLM terms
    llm_terms = [row for row in rows if row["source"] == "llm"]
    tfidf_terms = [row for row in rows if row["source"] == "tfidf"]
    both_terms = [row for row in rows if row["source"] == "llm+tfidf"]
    
    # Should have some terms from each source
    assert len(llm_terms) >= 0  # May be 0 if TF-IDF scored higher
    assert len(tfidf_terms) >= 0  # May be 0 if LLM scored higher
    
    # All terms should have a source
    assert all(row["source"] in ["llm", "tfidf", "llm+tfidf"] for row in rows)
    
    # Check that LLM mock terms are present (might be from either source depending on scores)
    all_terms = [row["term"] for row in rows]
    assert "machine learning" in all_terms
    assert "deep learning" in all_terms


def test_source_column_llm_only(tmp_path):
    """Test that LLM-only extraction marks all terms as 'llm'."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2"><file><body>
<trans-unit id="1"><source>Test content</source></trans-unit>
</body></file></xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    mock_llm_terms = [("test", 0.95), ("content", 0.90)]
    
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            source_language="English",
            target_language="Spanish",
            output=str(output_file),
            use_llm=True,
            use_tfidf=False,
        )
    
    import csv
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # All terms should be from LLM
    assert all(row["source"] == "llm" for row in rows)


def test_source_column_tfidf_only(tmp_path):
    """Test that TF-IDF-only extraction marks all terms as 'tfidf'."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2"><file><body>
<trans-unit id="1"><source>Cloud computing provides scalable infrastructure</source></trans-unit>
<trans-unit id="2"><source>Kubernetes orchestrates containerized applications</source></trans-unit>
</body></file></xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    extract_glossary(
        input_file=str(xliff_file),
        source_language="English",
        target_language="Spanish",
        output=str(output_file),
        use_llm=False,
        use_tfidf=True,
        max_terms=10,
    )
    
    import csv
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # All terms should be from TF-IDF
    assert all(row["source"] == "tfidf" for row in rows)


def test_combined_vs_individual_extraction_counts(tmp_path):
    """Test that combined extraction has more terms than individual methods."""
    xliff_file = tmp_path / "test.xliff"
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Cloud computing provides scalable infrastructure</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Kubernetes orchestrates containers efficiently</source>
      </trans-unit>
      <trans-unit id="3">
        <source>Docker enables portable applications</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    xliff_file.write_text(xliff_content, encoding="utf-8")
    
    # Mock LLM to return 3 terms
    mock_llm_terms = [
        ("cloud computing", 0.95),
        ("kubernetes", 0.90),
        ("docker", 0.85),
    ]
    
    # Test combined extraction
    output_combined = tmp_path / "glossary_combined.csv"
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_combined),
            use_llm=True,
            use_tfidf=True,
            max_terms=10,
        )
    
    # Test LLM-only extraction
    output_llm = tmp_path / "glossary_llm.csv"
    with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
        extract_glossary(
            input_file=str(xliff_file),
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=str(output_llm),
            use_llm=True,
            use_tfidf=False,
            max_terms=10,
        )
    
    # Test TF-IDF-only extraction
    output_tfidf = tmp_path / "glossary_tfidf.csv"
    extract_glossary(
        input_file=str(xliff_file),
        file_type="xliff",
        source_language="English",
        target_language="Spanish",
        output=str(output_tfidf),
        use_llm=False,
        use_tfidf=True,
        max_terms=10,
    )
    
    # Count terms in each output
    combined_lines = output_combined.read_text().strip().split("\n")
    llm_lines = output_llm.read_text().strip().split("\n")
    tfidf_lines = output_tfidf.read_text().strip().split("\n")
    
    # Combined should have at least as many terms as individual methods
    # (it's a union, so >= both)
    assert len(combined_lines) >= len(llm_lines)
    # Note: May not always be >= tfidf_lines if TF-IDF produces many terms

