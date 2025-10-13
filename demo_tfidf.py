#!/usr/bin/env python3
"""Demo script showing TF-IDF glossary extraction."""

from nodes.extract_glossary import extract_terms_with_tfidf, extract_terms_from_text


def demo_frequency_vs_tfidf():
    """Compare frequency-based and TF-IDF-based extraction."""
    print("\n" + "=" * 70)
    print("FREQUENCY-BASED vs TF-IDF EXTRACTION")
    print("=" * 70)
    
    # Three documents about different topics
    documents = [
        """
        Machine learning algorithms process data to identify patterns.
        Supervised learning uses labeled data for training models.
        Unsupervised learning discovers patterns without labels.
        Machine learning applications include image recognition.
        """,
        """
        Cloud computing provides scalable infrastructure services.
        Virtual machines enable efficient resource utilization.
        Container orchestration manages distributed applications.
        Cloud platforms offer serverless computing options.
        """,
        """
        Cybersecurity protects systems from malicious attacks.
        Encryption secures sensitive data transmissions.
        Authentication verifies user identities effectively.
        Firewalls prevent unauthorized network access attempts.
        """
    ]
    
    print("\nDocument Topics:")
    print("  1. Machine Learning")
    print("  2. Cloud Computing")
    print("  3. Cybersecurity")
    
    # Frequency-based extraction (all documents combined)
    print("\n" + "-" * 70)
    print("FREQUENCY-BASED EXTRACTION (Combined Text)")
    print("-" * 70)
    combined_text = " ".join(documents)
    freq_terms = extract_terms_from_text(combined_text, top_n=15, language="English")
    
    print(f"\nTop {len(freq_terms)} terms by frequency:")
    for i, term in enumerate(freq_terms, 1):
        print(f"  {i:2d}. {term}")
    
    # TF-IDF extraction (documents treated separately)
    print("\n" + "-" * 70)
    print("TF-IDF EXTRACTION (Separate Documents)")
    print("-" * 70)
    tfidf_terms = extract_terms_with_tfidf(
        documents, top_n=15, language="English", max_ngram_size=2
    )
    
    print(f"\nTop {len(tfidf_terms)} terms by TF-IDF score:")
    for i, (term, score) in enumerate(tfidf_terms, 1):
        print(f"  {i:2d}. {term:30s} (score: {score:.4f})")
    
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print("""
TF-IDF advantages over frequency-based extraction:
  • Identifies domain-specific terms unique to each document
  • Penalizes common terms that appear across all documents
  • Better at finding technical terminology and key concepts
  • Scores indicate term importance within the corpus

Frequency-based extraction:
  • Simpler and faster
  • Good for single document analysis
  • May prioritize common words that appear frequently
    """)


def demo_ngram_sizes():
    """Demonstrate different n-gram sizes."""
    print("\n" + "=" * 70)
    print("N-GRAM SIZE COMPARISON")
    print("=" * 70)
    
    documents = [
        "Natural language processing enables text analysis capabilities",
        "Machine learning algorithms power artificial intelligence systems",
        "Deep learning neural networks process complex data patterns",
    ]
    
    for n in [1, 2, 3]:
        print(f"\n{'-' * 70}")
        print(f"N-GRAM SIZE: {n} ({'unigrams' if n == 1 else 'up to ' + str(n) + '-grams'})")
        print(f"{'-' * 70}")
        
        terms = extract_terms_with_tfidf(
            documents, top_n=10, language="English", max_ngram_size=n
        )
        
        print(f"\nTop {len(terms)} terms:")
        for i, (term, score) in enumerate(terms, 1):
            word_count = term.count(" ") + 1
            ngram_type = f"{word_count}-gram"
            print(f"  {i:2d}. {term:35s} ({ngram_type}, score: {score:.4f})")


def demo_multilingual():
    """Demonstrate TF-IDF with different languages."""
    print("\n" + "=" * 70)
    print("MULTILINGUAL TF-IDF EXTRACTION")
    print("=" * 70)
    
    # English documents
    print("\n" + "-" * 70)
    print("ENGLISH")
    print("-" * 70)
    
    en_docs = [
        "Software development requires careful planning and testing",
        "Agile methodologies emphasize iterative development cycles",
        "Version control systems track code changes effectively",
    ]
    
    en_terms = extract_terms_with_tfidf(en_docs, top_n=8, language="English", max_ngram_size=2)
    print("\nTop English terms:")
    for i, (term, score) in enumerate(en_terms, 1):
        print(f"  {i}. {term:30s} ({score:.4f})")
    
    # Spanish documents
    print("\n" + "-" * 70)
    print("SPANISH")
    print("-" * 70)
    
    es_docs = [
        "El desarrollo de software requiere planificación cuidadosa",
        "Las metodologías ágiles enfatizan ciclos iterativos",
        "Los sistemas de control rastrean cambios efectivamente",
    ]
    
    es_terms = extract_terms_with_tfidf(es_docs, top_n=8, language="Spanish", max_ngram_size=2)
    print("\nTop Spanish terms:")
    for i, (term, score) in enumerate(es_terms, 1):
        print(f"  {i}. {term:30s} ({score:.4f})")


def demo_tfidf_scoring():
    """Explain TF-IDF scoring with a clear example."""
    print("\n" + "=" * 70)
    print("TF-IDF SCORING EXPLANATION")
    print("=" * 70)
    
    documents = [
        "Docker containers enable application portability",
        "Kubernetes orchestrates Docker containers efficiently",  
        "Docker simplifies application deployment processes",
    ]
    
    print("\nDocument corpus:")
    for i, doc in enumerate(documents, 1):
        print(f"  Doc {i}: {doc}")
    
    terms = extract_terms_with_tfidf(documents, top_n=10, language="English", max_ngram_size=2)
    
    print("\n" + "-" * 70)
    print("TF-IDF SCORES")
    print("-" * 70)
    
    print("\nTerm importance ranking:")
    for i, (term, score) in enumerate(terms, 1):
        # Count document frequency manually for explanation
        doc_count = sum(1 for doc in documents if term.lower() in doc.lower())
        
        print(f"\n  {i}. '{term}' (score: {score:.4f})")
        print(f"     Appears in {doc_count} out of {len(documents)} documents")
        
        if doc_count == len(documents):
            print("     → Low TF-IDF (appears in all documents)")
        elif doc_count == 1:
            print("     → High TF-IDF (unique to one document)")
        else:
            print("     → Medium TF-IDF (appears in multiple documents)")
    
    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print("""
TF-IDF = Term Frequency × Inverse Document Frequency

- Terms appearing in ALL documents get LOW scores
  (they're too common to be distinctive)

- Terms appearing in FEW documents get HIGH scores
  (they're more distinctive and important)

- Terms appearing FREQUENTLY within their documents get HIGHER scores
  (they're important in those specific contexts)
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("TF-IDF GLOSSARY EXTRACTION DEMO")
    print("=" * 70)
    print("\nThis demo shows how TF-IDF provides better term extraction")
    print("compared to simple frequency-based methods.")
    
    try:
        demo_frequency_vs_tfidf()
        demo_ngram_sizes()
        demo_multilingual()
        demo_tfidf_scoring()
        
        print("\n" + "=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print("\nTo use TF-IDF extraction with the CLI:")
        print("  uv run python cli.py extract-glossary \\")
        print("      --input data/sample.xliff \\")
        print("      --source-language English \\")
        print("      --output glossary.csv \\")
        print("      --use-tfidf \\")
        print("      --max-terms 50 \\")
        print("      --max-ngram-size 3")
        
        print("\nFor more information, see docs/TFIDF_INTEGRATION.md")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()

