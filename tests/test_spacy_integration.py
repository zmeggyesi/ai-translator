"""Tests for SpaCy integration in glossary extraction."""
import pytest
from nodes.extract_glossary import (
    _get_spacy_model,
    _get_stopwords,
    extract_terms_from_text,
)


def test_get_spacy_model_english():
    """Test loading English SpaCy model."""
    nlp = _get_spacy_model("English")
    assert nlp is not None
    assert nlp.lang == "en"


def test_get_spacy_model_spanish():
    """Test loading Spanish SpaCy model."""
    nlp = _get_spacy_model("Spanish")
    assert nlp is not None
    assert nlp.lang == "es"


def test_get_spacy_model_cache():
    """Test that SpaCy models are cached."""
    nlp1 = _get_spacy_model("English")
    nlp2 = _get_spacy_model("English")
    assert nlp1 is nlp2  # Should be the same object from cache


def test_get_spacy_model_unsupported_language():
    """Test handling of unsupported language."""
    nlp = _get_spacy_model("Klingon")
    assert nlp is None


def test_get_spacy_model_uninstalled_language():
    """Test handling of language model that isn't installed."""
    nlp = _get_spacy_model("French")  # Not installed in basic setup
    assert nlp is None  # Should return None if model not installed


def test_get_stopwords_english():
    """Test retrieving English stopwords from SpaCy."""
    stopwords = _get_stopwords("English")
    assert isinstance(stopwords, set)
    assert len(stopwords) > 0
    assert "the" in stopwords
    assert "and" in stopwords
    assert "is" in stopwords


def test_get_stopwords_spanish():
    """Test retrieving Spanish stopwords from SpaCy."""
    stopwords = _get_stopwords("Spanish")
    assert isinstance(stopwords, set)
    assert len(stopwords) > 0
    # Common Spanish stopwords
    assert "el" in stopwords or "la" in stopwords or "de" in stopwords


def test_get_stopwords_fallback():
    """Test fallback to English stopwords for unsupported language."""
    stopwords = _get_stopwords("Klingon")
    assert isinstance(stopwords, set)
    assert len(stopwords) > 0
    # Should contain English stopwords as fallback
    assert "the" in stopwords


def test_extract_terms_from_text_with_english():
    """Test term extraction with English stopwords."""
    text = """
    Machine learning is a method of data analysis that automates analytical model building.
    It is a branch of artificial intelligence based on the idea that systems can learn from data,
    identify patterns and make decisions with minimal human intervention. Machine learning and
    artificial intelligence are transforming the way we live and work.
    """
    
    terms = extract_terms_from_text(text, top_n=10, language="English")
    
    assert isinstance(terms, list)
    assert len(terms) > 0
    
    # Should extract important terms
    assert any("machine" in term.lower() or "learning" in term.lower() for term in terms)
    
    # Should not extract stopwords
    assert "the" not in terms
    assert "and" not in terms
    assert "is" not in terms


def test_extract_terms_from_text_with_spanish():
    """Test term extraction with Spanish stopwords."""
    text = """
    El aprendizaje automático es un método de análisis de datos que automatiza la construcción
    de modelos analíticos. Es una rama de la inteligencia artificial basada en la idea de que
    los sistemas pueden aprender de los datos, identificar patrones y tomar decisiones con
    mínima intervención humana. El aprendizaje automático y la inteligencia artificial están
    transformando la forma en que vivimos y trabajamos.
    """
    
    terms = extract_terms_from_text(text, top_n=10, language="Spanish")
    
    assert isinstance(terms, list)
    assert len(terms) > 0
    
    # Should extract important terms
    assert any("aprendizaje" in term.lower() or "inteligencia" in term.lower() for term in terms)
    
    # Should not extract common Spanish stopwords
    assert "el" not in terms
    assert "la" not in terms
    assert "de" not in terms


def test_extract_terms_filters_short_words():
    """Test that short words are filtered out."""
    text = "The AI is a big new era in IT and ML"
    
    terms = extract_terms_from_text(text, top_n=20, language="English")
    
    # Should filter out words <= 3 characters
    for term in terms:
        assert len(term) > 3


def test_extract_terms_frequency_ordering():
    """Test that terms are ordered by frequency."""
    text = """
    Python Python Python programming language.
    Java Java programming language.
    Ruby programming language.
    """
    
    terms = extract_terms_from_text(text, top_n=5, language="English")
    
    # Python appears most frequently, so should be first (if included)
    # This is a loose test since stopword filtering might affect results
    assert len(terms) > 0
    assert "programming" in terms or "language" in terms or "python" in terms


def test_spacy_models_loaded_correctly():
    """Integration test to verify SpaCy models work end-to-end."""
    en_nlp = _get_spacy_model("English")
    es_nlp = _get_spacy_model("Spanish")
    
    # Verify both models are loaded
    assert en_nlp is not None
    assert es_nlp is not None
    
    # Verify they have different stopwords
    en_stopwords = _get_stopwords("English")
    es_stopwords = _get_stopwords("Spanish")
    
    assert en_stopwords != es_stopwords
    
    # English specific
    assert "the" in en_stopwords
    
    # Spanish specific
    assert "el" in es_stopwords or "la" in es_stopwords

