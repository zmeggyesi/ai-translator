#!/usr/bin/env python3
"""Demo showing combined LLM + TF-IDF glossary extraction."""

from unittest.mock import patch
from nodes.extract_glossary import extract_glossary
import tempfile
import os


def demo_combined_extraction():
    """Demonstrate combined LLM + TF-IDF extraction."""
    print("\n" + "=" * 70)
    print("COMBINED LLM + TF-IDF EXTRACTION DEMO")
    print("=" * 70)
    
    # Create a temporary XLIFF file with technical content
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Kubernetes orchestrates containerized applications across clusters</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Docker enables portable application deployment with containers</source>
      </trans-unit>
      <trans-unit id="3">
        <source>Microservices architecture provides scalable system design</source>
      </trans-unit>
      <trans-unit id="4">
        <source>CI/CD pipelines automate software delivery workflows</source>
      </trans-unit>
      <trans-unit id="5">
        <source>Infrastructure as Code manages cloud resources efficiently</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False, encoding='utf-8') as f:
        f.write(xliff_content)
        xliff_file = f.name
    
    try:
        print("\nProcessing technical documentation XLIFF file...")
        print("=" * 70)
        
        # Mock LLM to return semantic/conceptual terms
        mock_llm_terms = [
            ("Kubernetes", 0.95),
            ("Docker", 0.92),
            ("containerized applications", 0.88),
            ("microservices architecture", 0.85),
            ("CI/CD pipelines", 0.83),
            ("Infrastructure as Code", 0.80),
        ]
        
        print("\n1️⃣  LLM EXTRACTION (Semantic Understanding)")
        print("-" * 70)
        print("LLM identifies terms based on semantic importance:")
        for term, score in mock_llm_terms:
            print(f"  • {term:35s} (score: {score:.2f})")
        
        # Run TF-IDF only to show what it finds
        output_tfidf = tempfile.mktemp(suffix='.csv')
        extract_glossary(
            input_file=xliff_file,
            file_type="xliff",
            source_language="English",
            target_language="Spanish",
            output=output_tfidf,
            use_tfidf=True,
            max_terms=15,
            max_ngram_size=2,
        )
        
        print("\n2️⃣  TF-IDF EXTRACTION (Statistical Importance)")
        print("-" * 70)
        print("TF-IDF identifies terms based on frequency and rarity:")
        
        with open(output_tfidf, 'r', encoding='utf-8') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines[:10]:  # Show top 10
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    term, _, score = parts[0], parts[1], parts[2]
                    print(f"  • {term:35s} (score: {float(score):.4f})")
        
        os.unlink(output_tfidf)
        
        # Run combined extraction
        output_combined = tempfile.mktemp(suffix='.csv')
        
        with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
            extract_glossary(
                input_file=xliff_file,
                file_type="xliff",
                source_language="English",
                target_language="Spanish",
                output=output_combined,
                use_llm=True,
                use_tfidf=True,
                max_terms=25,
                max_ngram_size=2,
            )
        
        print("\n3️⃣  COMBINED EXTRACTION (Union of Both)")
        print("-" * 70)
        print("Combined results merge both methods (union):")
        print("  • Keeps ALL unique terms from both algorithms")
        print("  • Normalizes TF-IDF scores to LLM scale for fair comparison")
        print("  • For duplicates, keeps the HIGHEST score")
        print()
        
        with open(output_combined, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Total unique terms extracted: {len(lines) - 1}")
            print("\nTop 15 terms from combined extraction:")
            
            for i, line in enumerate(lines[1:16], 1):  # Skip header, show top 15
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    term, _, score = parts[0], parts[1], parts[2]
                    # Indicate source
                    source = ""
                    if any(llm_term.lower() == term.lower() for llm_term, _ in mock_llm_terms):
                        source = " [from LLM]"
                    else:
                        source = " [from TF-IDF]"
                    print(f"  {i:2d}. {term:35s} (score: {float(score):.4f}){source}")
        
        os.unlink(output_combined)
        
        print("\n" + "=" * 70)
        print("KEY INSIGHTS")
        print("=" * 70)
        print("""
✅ LLM Benefits:
   • Identifies proper nouns (Kubernetes, Docker)
   • Understands multi-word concepts (Infrastructure as Code)
   • Semantic understanding of importance

✅ TF-IDF Benefits:
   • Statistical analysis finds common technical terms
   • Identifies important single words and bigrams
   • Fast and free (no API costs)

🎯 Combined Benefits:
   • UNION of both methods = more comprehensive coverage
   • LLM catches what TF-IDF misses (semantic terms)
   • TF-IDF catches what LLM misses (statistical patterns)
   • Score normalization ensures fair comparison
   • Highest scores preserved for duplicates
   • Best of both worlds!
        """)
        
    finally:
        os.unlink(xliff_file)


def demo_use_cases():
    """Show when to use combined extraction."""
    print("\n" + "=" * 70)
    print("WHEN TO USE COMBINED EXTRACTION")
    print("=" * 70)
    
    print("""
Use COMBINED extraction when:
  ✅ You want the most comprehensive glossary possible
  ✅ Working with technical documentation
  ✅ Need both semantic and statistical coverage
  ✅ Budget allows for LLM API costs
  ✅ Have time for thorough extraction (~30-60s per file)

Use LLM ONLY when:
  ✅ Semantic understanding is most important
  ✅ Need context-aware term extraction
  ✅ Budget allows for API costs
  ✅ Working with complex, nuanced text

Use TF-IDF ONLY when:
  ✅ Need fast, free extraction
  ✅ Have multiple text segments (XLIFF, etc.)
  ✅ Statistical importance is sufficient
  ✅ Working with structured technical content

Use FREQUENCY when:
  ✅ Need simplest, fastest extraction
  ✅ Working with single documents
  ✅ Basic term list is sufficient
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("COMBINED LLM + TF-IDF GLOSSARY EXTRACTION")
    print("=" * 70)
    print("\nThis demo shows how combining LLM and TF-IDF extraction")
    print("provides more comprehensive results than either method alone.")
    
    try:
        demo_combined_extraction()
        demo_use_cases()
        
        print("\n" + "=" * 70)
        print("TRY IT YOURSELF")
        print("=" * 70)
        print("""
Command line usage:

  # Combined extraction (requires OPENAI_API_KEY)
  uv run python cli.py extract-glossary \\
      --input data/sample.xliff \\
      --source-language English \\
      --output glossary.csv \\
      --use-llm \\
      --use-tfidf \\
      --max-terms 50 \\
      --max-ngram-size 3

Note: Make sure to set your OPENAI_API_KEY in the .env file!
        """)
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()

