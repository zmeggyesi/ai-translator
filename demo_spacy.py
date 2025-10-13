#!/usr/bin/env python3
"""Demo script showing SpaCy integration for glossary extraction."""

from nodes.extract_glossary import (
    _get_spacy_model,
    _get_stopwords,
    extract_terms_from_text,
)


def demo_english():
    """Demonstrate English stopword filtering."""
    print("\n" + "=" * 60)
    print("ENGLISH DEMO")
    print("=" * 60)
    
    text = """
    Machine learning is a method of data analysis that automates analytical 
    model building. It is a branch of artificial intelligence based on the 
    idea that systems can learn from data, identify patterns and make 
    decisions with minimal human intervention. Machine learning and 
    artificial intelligence are transforming the way we live and work.
    """
    
    print("\nOriginal text:")
    print(text.strip())
    
    print("\nExtracting terms with English stopwords...")
    terms = extract_terms_from_text(text, top_n=10, language="English")
    
    print(f"\nExtracted {len(terms)} terms:")
    for i, term in enumerate(terms, 1):
        print(f"  {i}. {term}")
    
    # Show some stopwords
    stopwords = _get_stopwords("English")
    print(f"\nEnglish stopwords count: {len(stopwords)}")
    print(f"Sample stopwords: {sorted(list(stopwords))[:10]}")


def demo_spanish():
    """Demonstrate Spanish stopword filtering."""
    print("\n" + "=" * 60)
    print("SPANISH DEMO")
    print("=" * 60)
    
    text = """
    El aprendizaje automático es un método de análisis de datos que 
    automatiza la construcción de modelos analíticos. Es una rama de la 
    inteligencia artificial basada en la idea de que los sistemas pueden 
    aprender de los datos, identificar patrones y tomar decisiones con 
    mínima intervención humana. El aprendizaje automático y la inteligencia 
    artificial están transformando la forma en que vivimos y trabajamos.
    """
    
    print("\nOriginal text:")
    print(text.strip())
    
    print("\nExtracting terms with Spanish stopwords...")
    terms = extract_terms_from_text(text, top_n=10, language="Spanish")
    
    print(f"\nExtracted {len(terms)} terms:")
    for i, term in enumerate(terms, 1):
        print(f"  {i}. {term}")
    
    # Show some stopwords
    stopwords = _get_stopwords("Spanish")
    print(f"\nSpanish stopwords count: {len(stopwords)}")
    print(f"Sample stopwords: {sorted(list(stopwords))[:10]}")


def demo_comparison():
    """Compare English and Spanish stopword sets."""
    print("\n" + "=" * 60)
    print("STOPWORDS COMPARISON")
    print("=" * 60)
    
    en_stopwords = _get_stopwords("English")
    es_stopwords = _get_stopwords("Spanish")
    
    print(f"\nEnglish stopwords: {len(en_stopwords)}")
    print(f"Spanish stopwords: {len(es_stopwords)}")
    
    # Show unique stopwords
    en_unique = en_stopwords - es_stopwords
    es_unique = es_stopwords - en_stopwords
    
    print(f"\nUnique to English (sample): {sorted(list(en_unique))[:15]}")
    print(f"Unique to Spanish (sample): {sorted(list(es_unique))[:15]}")


def demo_model_loading():
    """Demonstrate SpaCy model loading and caching."""
    print("\n" + "=" * 60)
    print("MODEL LOADING & CACHING")
    print("=" * 60)
    
    print("\nLoading English model...")
    nlp_en = _get_spacy_model("English")
    if nlp_en:
        print(f"  ✓ Loaded: {nlp_en.meta['name']} (language: {nlp_en.lang})")
    else:
        print("  ✗ Failed to load English model")
    
    print("\nLoading Spanish model...")
    nlp_es = _get_spacy_model("Spanish")
    if nlp_es:
        print(f"  ✓ Loaded: {nlp_es.meta['name']} (language: {nlp_es.lang})")
    else:
        print("  ✗ Failed to load Spanish model")
    
    print("\nLoading English model again (should use cache)...")
    nlp_en2 = _get_spacy_model("English")
    print(f"  Same object from cache: {nlp_en is nlp_en2}")
    
    print("\nTrying unsupported language...")
    nlp_klingon = _get_spacy_model("Klingon")
    if nlp_klingon:
        print("  ✓ Loaded Klingon model")
    else:
        print("  ✗ Klingon model not available (expected)")


if __name__ == "__main__":
    print("SpaCy Integration Demo")
    print("======================")
    print("\nThis demo shows how SpaCy integration provides language-specific")
    print("stopword filtering for more accurate glossary term extraction.")
    
    try:
        demo_model_loading()
        demo_english()
        demo_spanish()
        demo_comparison()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("\nFor more information, see docs/SPACY_INTEGRATION.md")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()

