#!/usr/bin/env python3
"""Demo showing the source column in glossary extraction."""

from unittest.mock import patch
from nodes.extract_glossary import extract_glossary
import tempfile
import csv
import os


def demo_source_column():
    """Demonstrate the source column feature."""
    print("\n" + "=" * 70)
    print("SOURCE COLUMN DEMONSTRATION")
    print("=" * 70)
    
    # Create a temporary XLIFF file
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es">
    <body>
      <trans-unit id="1">
        <source>Kubernetes orchestrates containerized applications</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Docker enables portable application deployment</source>
      </trans-unit>
      <trans-unit id="3">
        <source>Microservices architecture provides scalability</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False, encoding='utf-8') as f:
        f.write(xliff_content)
        xliff_file = f.name
    
    try:
        # Mock LLM to return semantic terms
        mock_llm_terms = [
            ("Kubernetes", 0.95),
            ("Docker", 0.92),
            ("microservices architecture", 0.88),
        ]
        
        output_file = tempfile.mktemp(suffix='.csv')
        
        with patch('nodes.extract_glossary.extract_glossary_with_llm', return_value=mock_llm_terms):
            extract_glossary(
                input_file=xliff_file,
                file_type="xliff",
                source_language="English",
                target_language="Spanish",
                output=output_file,
                use_llm=True,
                use_tfidf=True,
                max_terms=15,
                max_ngram_size=3,
            )
        
        print("\n📊 COMBINED EXTRACTION RESULTS")
        print("=" * 70)
        print(f"{'#':<3} {'Term':<35} {'Score':<8} {'Source':<15}")
        print("-" * 70)
        
        with open(output_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            for i, row in enumerate(rows, 1):
                term = row['term']
                score = float(row['significance'])
                source = row['source']
                
                # Add visual indicators
                if source == 'llm':
                    indicator = '🧠'
                elif source == 'tfidf':
                    indicator = '📊'
                else:
                    indicator = '🤝'
                
                print(f"{i:<3} {term:<35} {score:<8.4f} {indicator} {source:<15}")
        
        print("\n" + "=" * 70)
        print("LEGEND")
        print("=" * 70)
        print("🧠 llm       - Term identified by LLM (semantic understanding)")
        print("📊 tfidf     - Term identified by TF-IDF (statistical importance)")
        print("🤝 llm+tfidf - Term identified by both with equal scores")
        
        # Show statistics
        llm_terms = [r for r in rows if r['source'] == 'llm']
        tfidf_terms = [r for r in rows if r['source'] == 'tfidf']
        both_terms = [r for r in rows if r['source'] == 'llm+tfidf']
        
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        print(f"Total terms: {len(rows)}")
        print(f"  From LLM:    {len(llm_terms):3d} ({len(llm_terms)/len(rows)*100:.1f}%)")
        print(f"  From TF-IDF: {len(tfidf_terms):3d} ({len(tfidf_terms)/len(rows)*100:.1f}%)")
        print(f"  From both:   {len(both_terms):3d} ({len(both_terms)/len(rows)*100:.1f}%)")
        
        print("\n" + "=" * 70)
        print("INSIGHTS")
        print("=" * 70)
        
        llm_avg = sum(float(r['significance']) for r in llm_terms) / len(llm_terms) if llm_terms else 0
        tfidf_avg = sum(float(r['significance']) for r in tfidf_terms) / len(tfidf_terms) if tfidf_terms else 0
        
        print(f"Average score for LLM terms:    {llm_avg:.4f}")
        print(f"Average score for TF-IDF terms: {tfidf_avg:.4f}")
        
        if llm_avg > tfidf_avg:
            print("\n→ LLM terms have higher average scores (semantic extraction working well)")
        else:
            print("\n→ TF-IDF terms competitive with LLM (statistical patterns effective)")
        
        print("\n" + "=" * 70)
        print("TOP CONTRIBUTORS")
        print("=" * 70)
        
        top_llm = sorted(llm_terms, key=lambda x: float(x['significance']), reverse=True)[:3]
        top_tfidf = sorted(tfidf_terms, key=lambda x: float(x['significance']), reverse=True)[:3]
        
        print("\n🧠 Top LLM terms:")
        for i, r in enumerate(top_llm, 1):
            print(f"  {i}. {r['term']:30s} ({float(r['significance']):.4f})")
        
        print("\n📊 Top TF-IDF terms:")
        for i, r in enumerate(top_tfidf, 1):
            print(f"  {i}. {r['term']:30s} ({float(r['significance']):.4f})")
        
        os.unlink(output_file)
        
    finally:
        os.unlink(xliff_file)


def demo_filtering_by_source():
    """Show how to filter results by source."""
    print("\n" + "=" * 70)
    print("FILTERING BY SOURCE")
    print("=" * 70)
    
    print("""
The source column enables powerful post-processing:

# Example Python code to filter by source:

import csv

# Load glossary
with open('glossary.csv') as f:
    rows = list(csv.DictReader(f))

# Get only LLM terms (semantic/conceptual)
llm_only = [r for r in rows if r['source'] == 'llm']

# Get only TF-IDF terms (statistical patterns)
tfidf_only = [r for r in rows if r['source'] == 'tfidf']

# Get high-confidence terms from TF-IDF
high_conf_tfidf = [
    r for r in rows 
    if r['source'] == 'tfidf' and float(r['significance']) > 0.8
]

# Use cases:
# - Export only LLM terms for human review
# - Compare LLM vs TF-IDF term quality
# - Validate extraction algorithm effectiveness
# - Build specialized glossaries by source
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("SOURCE COLUMN FEATURE DEMO")
    print("=" * 70)
    print("\nThe source column shows which algorithm extracted each term:")
    print("  • llm       - From LLM semantic understanding")
    print("  • tfidf     - From TF-IDF statistical analysis")
    print("  • llm+tfidf - Found by both with equal scores")
    
    try:
        demo_source_column()
        demo_filtering_by_source()
        
        print("\n" + "=" * 70)
        print("TRY IT YOURSELF")
        print("=" * 70)
        print("""
# Combined extraction with source tracking:
uv run python cli.py extract-glossary \\
    --input data/sample.xliff \\
    --source-language English \\
    --output glossary.csv \\
    --use-llm \\
    --use-tfidf

# View the source column:
head -20 glossary.csv
        """)
        
        print("For more information, see SOURCE_COLUMN_SUMMARY.md")
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()

