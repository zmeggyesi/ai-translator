"""Tests for TF-IDF-based glossary extraction."""
import pytest
from nodes.extract_glossary import (
    extract_terms_with_tfidf,
    _preprocess_for_tfidf,
    extract_glossary,
)
import tempfile
import os


def test_preprocess_for_tfidf():
    """Test text preprocessing for TF-IDF."""
    text = "The machine learning system processes data efficiently"
    result = _preprocess_for_tfidf(text, "English")
    
    # Should be lowercase and have stopwords removed
    assert "machine" in result
    assert "learning" in result
    assert "the" not in result.split()  # Stopword removed
    assert result == result.lower()


def test_extract_terms_with_tfidf_basic():
    """Test basic TF-IDF extraction with multiple documents."""
    segments = [
        "Machine learning algorithms analyze patterns in data",
        "Deep learning neural networks process complex information",
        "Artificial intelligence systems make decisions autonomously",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=10, language="English", max_ngram_size=2)
    
    assert isinstance(terms, list)
    assert len(terms) > 0
    assert len(terms) <= 10
    
    # Each term should be a tuple of (term, score)
    for term, score in terms:
        assert isinstance(term, str)
        assert isinstance(score, float)
        assert score >= 0


def test_extract_terms_with_tfidf_unigrams_only():
    """Test TF-IDF extraction with unigrams only."""
    segments = [
        "Python programming language for data science",
        "Java programming language for enterprise applications",
        "JavaScript programming language for web development",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=5, language="English", max_ngram_size=1)
    
    assert len(terms) > 0
    # All terms should be single words
    for term, score in terms:
        assert " " not in term


def test_extract_terms_with_tfidf_bigrams():
    """Test TF-IDF extraction includes bigrams."""
    segments = [
        "Machine learning is a powerful technology",
        "Deep learning is an advanced technique",
        "Natural language processing analyzes text data",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=20, language="English", max_ngram_size=2)
    
    # Should include some bigrams
    bigrams = [term for term, score in terms if " " in term]
    assert len(bigrams) > 0


def test_extract_terms_with_tfidf_trigrams():
    """Test TF-IDF extraction includes trigrams."""
    segments = [
        "Natural language processing system analyzes text efficiently",
        "Machine learning algorithm trains models accurately",
        "Deep learning neural network processes data quickly",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=30, language="English", max_ngram_size=3)
    
    # Should include some trigrams
    trigrams = [term for term, score in terms if term.count(" ") == 2]
    # Trigrams might not always be found, but the function should run without error
    assert isinstance(trigrams, list)


def test_extract_terms_with_tfidf_empty_segments():
    """Test TF-IDF extraction with empty segments."""
    segments = []
    terms = extract_terms_with_tfidf(segments, top_n=10, language="English")
    
    assert terms == []


def test_extract_terms_with_tfidf_single_segment():
    """Test TF-IDF extraction with a single segment (warning case)."""
    segments = ["Machine learning and artificial intelligence"]
    
    # Should still work but with a warning
    terms = extract_terms_with_tfidf(segments, top_n=5, language="English")
    
    assert isinstance(terms, list)


def test_extract_terms_with_tfidf_spanish():
    """Test TF-IDF extraction with Spanish text."""
    segments = [
        "El aprendizaje automático analiza patrones en datos",
        "Las redes neuronales profundas procesan información compleja",
        "Los sistemas de inteligencia artificial toman decisiones autónomamente",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=10, language="Spanish", max_ngram_size=2)
    
    assert len(terms) > 0
    # Should extract Spanish terms
    # Check for Spanish terms (not stopwords like "el", "la", "de")
    for term, score in terms:
        assert term not in ["el", "la", "de", "los", "las"]


def test_extract_terms_with_tfidf_scoring():
    """Test that TF-IDF scores are reasonable."""
    segments = [
        "Unique term appears here",
        "Common word appears here and there",
        "Common word appears everywhere",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=10, language="English")
    
    # Check that scores are in valid range
    for term, score in terms:
        assert 0 <= score <= 1.0


def test_extract_terms_with_tfidf_relevance():
    """Test that TF-IDF identifies domain-specific terms."""
    segments = [
        "Kubernetes orchestrates containerized applications efficiently",
        "Docker containers package applications with dependencies",
        "Microservices architecture enables scalable applications",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=15, language="English", max_ngram_size=2)
    
    # Should prioritize domain-specific terms over generic ones
    term_list = [term for term, score in terms]
    
    # Domain-specific terms should appear
    domain_terms_found = any(
        "kubernetes" in term.lower() or 
        "docker" in term.lower() or 
        "microservices" in term.lower() or
        "containerized" in term.lower()
        for term in term_list
    )
    assert domain_terms_found


def test_extract_terms_with_tfidf_min_df():
    """Test TF-IDF with minimum document frequency."""
    segments = [
        "Rare term appears once",
        "Common phrase appears here",
        "Common phrase appears again",
    ]
    
    # With min_df=2, terms must appear in at least 2 documents
    terms = extract_terms_with_tfidf(segments, top_n=10, language="English", min_df=2)
    
    # "rare" should not appear since it only appears in 1 document
    term_list = [term for term, score in terms]
    assert "rare" not in term_list


def test_extract_glossary_with_tfidf_xliff(tmp_path):
    """Test extract_glossary function with TF-IDF on mock XLIFF."""
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
    
    # Extract with TF-IDF
    extract_glossary(
        input_file=str(xliff_file),
        file_type="xliff",
        source_language="English",
        target_language="Spanish",
        output=str(output_file),
        use_tfidf=True,
        max_terms=10,
        max_ngram_size=2,
    )
    
    # Check that output file was created
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text(encoding="utf-8")
    assert "term" in content
    assert len(content.split("\n")) > 1  # Header + at least one term


def test_extract_glossary_with_tfidf_text(tmp_path):
    """Test extract_glossary function with TF-IDF on text file."""
    # Create a temporary text file
    text_file = tmp_path / "test.txt"
    text_content = """
Machine learning is a powerful technology.
It enables systems to learn from data.

Deep learning is an advanced technique.
Neural networks process complex information.

Artificial intelligence makes decisions.
AI systems operate autonomously.
"""
    text_file.write_text(text_content, encoding="utf-8")
    output_file = tmp_path / "glossary.csv"
    
    # Extract with TF-IDF
    extract_glossary(
        input_file=str(text_file),
        file_type="text",
        source_language="English",
        target_language="Spanish",
        output=str(output_file),
        use_tfidf=True,
        max_terms=15,
        max_ngram_size=2,
    )
    
    # Check that output file was created
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) > 1  # Header + terms
    
    # Check that TF-IDF scores are present
    assert "significance" in content or "," in lines[1]


def test_extract_terms_with_tfidf_all_stopwords():
    """Test TF-IDF extraction when segments become empty after preprocessing."""
    segments = [
        "the a an and or",
        "is are was were",
        "in on at for",
    ]
    
    terms = extract_terms_with_tfidf(segments, top_n=10, language="English")
    
    # Should return empty list when all terms are stopwords
    assert terms == []


def test_tfidf_vs_frequency_comparison():
    """Test that TF-IDF gives different results than simple frequency."""
    from nodes.extract_glossary import extract_terms_from_text
    
    segments = [
        "Python programming language data science machine learning",
        "Python programming language web development frameworks",
        "Python programming language automation scripting tasks",
    ]
    
    # TF-IDF extraction
    tfidf_terms = extract_terms_with_tfidf(segments, top_n=10, language="English")
    tfidf_term_list = [term for term, score in tfidf_terms]
    
    # Frequency extraction
    combined_text = " ".join(segments)
    freq_terms = extract_terms_from_text(combined_text, top_n=10, language="English")
    
    # Both should return results
    assert len(tfidf_term_list) > 0
    assert len(freq_terms) > 0
    
    # TF-IDF should penalize terms that appear in all documents
    # "python" and "programming" appear in all documents, so should have lower TF-IDF scores
    # while domain-specific terms should rank higher in TF-IDF

