# TF-IDF Integration for Glossary Extraction

## Overview

The glossary extraction module now supports **TF-IDF (Term Frequency-Inverse Document Frequency)** analysis for more intelligent term extraction. TF-IDF identifies terms that are important within documents while filtering out common terms that appear across many documents.

## What is TF-IDF?

**TF-IDF** is a numerical statistic that reflects how important a word is to a document in a collection of documents. It's calculated as:

```
TF-IDF = Term Frequency × Inverse Document Frequency
```

- **Term Frequency (TF)**: How often a term appears in a document
- **Inverse Document Frequency (IDF)**: How rare/common a term is across all documents

### Why TF-IDF is Better Than Frequency Counting

| Aspect | Frequency-Based | TF-IDF-Based |
|--------|----------------|--------------|
| **Common terms** | Ranks highly (appears often) | Ranks lowly (appears everywhere) |
| **Domain-specific terms** | May rank lowly | Ranks highly (distinctive) |
| **Multi-document analysis** | Treats all docs as one | Analyzes docs separately |
| **Term importance** | By frequency alone | By frequency AND rarity |
| **Best for** | Single documents | Multiple documents/segments |

### Example

Given three documents:
1. "Machine learning algorithms process data"
2. "Deep learning networks analyze data"
3. "Cloud computing processes data efficiently"

- **"data"** appears in all 3 documents → **Low TF-IDF** (too common)
- **"machine"** appears in 1 document → **High TF-IDF** (distinctive)
- **"learning"** appears in 2 documents → **Medium TF-IDF**

## Features

✨ **Multi-Document Analysis**: Treats each text segment as a separate document  
✨ **N-gram Support**: Extracts unigrams, bigrams, trigrams (up to configurable size)  
✨ **Language-Aware**: Uses SpaCy stopwords for multiple languages  
✨ **Configurable Thresholds**: Control minimum document frequency and max document frequency  
✨ **Score-Based Ranking**: Returns terms with their TF-IDF importance scores  

## Installation

TF-IDF support requires `scikit-learn`:

```bash
uv sync
```

This automatically installs scikit-learn and its dependencies (numpy, scipy).

## Usage

### Command Line Interface

#### Basic TF-IDF Extraction

```bash
# Extract from XLIFF file (best use case - multiple trans-units)
uv run python cli.py extract-glossary \
    --input data/sample.xliff \
    --source-language English \
    --output glossary_tfidf.csv \
    --use-tfidf \
    --max-terms 50

# Extract from text file (splits into paragraphs)
uv run python cli.py extract-glossary \
    --input data/input.txt \
    --source-language English \
    --output glossary_tfidf.csv \
    --use-tfidf \
    --max-terms 50
```

#### Advanced Options

```bash
# Control n-gram size
uv run python cli.py extract-glossary \
    --input data/sample.xliff \
    --source-language English \
    --output glossary.csv \
    --use-tfidf \
    --max-ngram-size 2 \        # 1=unigrams only, 2=up to bigrams, 3=up to trigrams
    --max-terms 100

# Spanish language
uv run python cli.py extract-glossary \
    --input data/spanish_content.xliff \
    --source-language Spanish \
    --output glossary_es.csv \
    --use-tfidf \
    --max-terms 75
```

### Python API

```python
from nodes.extract_glossary import extract_terms_with_tfidf

# Multiple text segments (each is a "document" for TF-IDF)
segments = [
    "Machine learning algorithms analyze data patterns",
    "Deep learning networks process complex information",
    "Artificial intelligence systems make decisions",
]

# Extract terms with TF-IDF
terms = extract_terms_with_tfidf(
    text_segments=segments,
    top_n=20,
    language="English",
    max_ngram_size=3,  # Include trigrams
    min_df=1,          # Minimum document frequency
)

# Results: list of (term, score) tuples
for term, score in terms:
    print(f"{term}: {score:.4f}")
```

### Full Glossary Extraction

```python
from nodes.extract_glossary import extract_glossary

# Extract from XLIFF with TF-IDF
extract_glossary(
    input_file="data/sample.xliff",
    file_type="xliff",
    source_language="English",
    target_language="Spanish",
    output="glossary_tfidf.csv",
    use_tfidf=True,
    max_terms=50,
    max_ngram_size=3,
)
```

## Parameters

### `extract_terms_with_tfidf()`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_segments` | List[str] | *required* | List of text segments (each treated as a document) |
| `top_n` | int | 50 | Maximum number of terms to return |
| `language` | str | "English" | Language for stopword filtering |
| `max_ngram_size` | int | 3 | Maximum n-gram size (1-3 typical) |
| `min_df` | int | 1 | Minimum document frequency for a term |

### `extract_glossary()` with TF-IDF

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_tfidf` | bool | False | Enable TF-IDF extraction |
| `max_ngram_size` | int | 3 | Maximum n-gram size for TF-IDF |
| `max_terms` | int | 50 | Maximum number of terms to extract |

## Best Practices

### When to Use TF-IDF

✅ **Use TF-IDF when:**
- Extracting from XLIFF files (multiple trans-units)
- Analyzing multiple related documents
- Seeking domain-specific terminology
- Need importance scores for terms
- Working with technical documentation

❌ **Don't use TF-IDF when:**
- Processing a single short text
- Only need simple word frequencies
- Performance is critical (TF-IDF is slower)
- Documents are very short (<50 words)

### Choosing N-gram Size

- **max_ngram_size=1**: Only single words
  - Fastest
  - Good for general vocabulary
  - Example: `machine`, `learning`, `data`

- **max_ngram_size=2**: Single words + two-word phrases
  - Balanced
  - Good for most use cases
  - Example: `machine learning`, `data science`

- **max_ngram_size=3**: Up to three-word phrases
  - Slower but most complete
  - Good for technical terms
  - Example: `natural language processing`, `machine learning algorithm`

### Choosing Term Count

```bash
# Few high-quality terms
--max-terms 25

# Balanced extraction
--max-terms 50

# Comprehensive extraction
--max-terms 150
```

## Examples

### Example 1: XLIFF File Extraction

```bash
# Input: XLIFF file with 1000 trans-units
uv run python cli.py extract-glossary \
    --input translations.xliff \
    --source-language English \
    --output glossary.csv \
    --use-tfidf \
    --max-terms 100 \
    --max-ngram-size 2

# Output: glossary.csv with top 100 terms ranked by TF-IDF
# term,translation,significance
# "api authentication",,"0.8542"
# "user credentials",,"0.7891"
# "database connection",,"0.7234"
```

### Example 2: Technical Documentation

```python
from nodes.extract_glossary import extract_terms_with_tfidf

# Technical documentation split into sections
sections = [
    "Kubernetes orchestrates containerized applications across clusters",
    "Docker containers package applications with dependencies",
    "Microservices architecture enables scalable deployment patterns",
]

terms = extract_terms_with_tfidf(
    sections, 
    top_n=15, 
    language="English",
    max_ngram_size=3
)

# Results prioritize technical terms:
# [('kubernetes orchestrates containerized', 0.89),
#  ('docker containers package', 0.85),
#  ('microservices architecture', 0.82), ...]
```

### Example 3: Multilingual Extraction

```python
# Spanish technical content
spanish_segments = [
    "El aprendizaje automático analiza patrones de datos",
    "Las redes neuronales procesan información compleja",
    "Los sistemas inteligentes toman decisiones autónomas",
]

terms = extract_terms_with_tfidf(
    spanish_segments,
    top_n=10,
    language="Spanish",
    max_ngram_size=2
)

# Uses Spanish stopwords automatically
```

## Comparison with Other Methods

The glossary extractor now supports **four extraction approaches**:

### 1. Frequency-Based (Default)
```bash
# No flags = frequency-based
uv run python cli.py extract-glossary --input file.txt ...
```
- **Pros**: Fast, simple, good for single documents
- **Cons**: Prioritizes common words, no importance scores

### 2. TF-IDF-Based
```bash
# --use-tfidf flag
uv run python cli.py extract-glossary --input file.xliff --use-tfidf ...
```
- **Pros**: Identifies important domain-specific terms, works well with multiple documents
- **Cons**: Slower, needs multiple segments for best results

### 3. LLM-Based
```bash
# --use-llm flag (requires OpenAI API key)
uv run python cli.py extract-glossary --input file.xliff --use-llm ...
```
- **Pros**: Most intelligent, understands context and semantics
- **Cons**: Requires API key, costs money, slower

### 4. Combined (LLM + TF-IDF) ⭐ NEW
```bash
# --use-llm --use-tfidf flags together
uv run python cli.py extract-glossary --input file.xliff --use-llm --use-tfidf ...
```
- **Pros**: Best of both worlds - semantic understanding + statistical importance, union of results
- **Cons**: Slowest (runs both), costs money (LLM), but most comprehensive
- **Merging**: Takes union of terms, keeping highest score for duplicates
- **Normalization**: TF-IDF scores are normalized to match LLM scale for fair comparison

## Performance

### Speed Comparison

For a typical XLIFF file with 500 trans-units:

| Method | Time | Cost |
|--------|------|------|
| Frequency | ~0.5s | Free |
| TF-IDF | ~2.0s | Free |
| LLM | ~30s | $0.01-0.10 |

### Memory Usage

TF-IDF requires more memory for the term-document matrix:

- Small corpus (<100 segments): <50 MB
- Medium corpus (100-1000 segments): 50-200 MB
- Large corpus (>1000 segments): 200+ MB

## Technical Details

### Algorithm

1. **Preprocessing**: Remove stopwords, filter short words, lowercase
2. **Vectorization**: Create TF-IDF matrix using `sklearn.TfidfVectorizer`
3. **N-gram Extraction**: Process unigrams, bigrams, trigrams separately
4. **Scoring**: Calculate average TF-IDF across all documents
5. **Ranking**: Sort by score, return top N terms

### TF-IDF Formula

```
TF-IDF(t, d, D) = TF(t, d) × IDF(t, D)

where:
  TF(t, d) = frequency of term t in document d
  IDF(t, D) = log(N / df(t))
  N = total number of documents
  df(t) = number of documents containing term t
```

### Filtering

- **min_df**: Terms must appear in at least this many documents (default: 1)
- **max_df**: Terms appearing in >95% of documents are ignored (too common)
- **Stopwords**: Language-specific stopwords removed via SpaCy
- **Short words**: Words ≤3 characters filtered out

## Testing

Run TF-IDF tests:

```bash
# All TF-IDF tests
uv run pytest tests/test_tfidf_extraction.py -v

# Specific test
uv run pytest tests/test_tfidf_extraction.py::test_extract_terms_with_tfidf_basic -v
```

## Demo

Interactive demo showing TF-IDF vs frequency-based extraction:

```bash
uv run python demo_tfidf.py
```

The demo shows:
- Frequency vs TF-IDF comparison
- N-gram size effects
- Multilingual extraction
- TF-IDF scoring explanation

## Troubleshooting

### Issue: Low-quality terms extracted

**Solution**: Increase `max_ngram_size` to capture multi-word terms:
```bash
--max-ngram-size 3
```

### Issue: Too many common words

**Solution**: Ensure SpaCy model is installed for your language:
```bash
uv pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

### Issue: Not enough terms returned

**Solution**: Lower `min_df` or increase `max_terms`:
```python
extract_terms_with_tfidf(segments, top_n=100, min_df=1)
```

### Issue: Memory error with large corpus

**Solution**: Process in batches or use frequency-based extraction instead.

## References

- [TF-IDF on Wikipedia](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [scikit-learn TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- Implementation: `nodes/extract_glossary.py`
- Tests: `tests/test_tfidf_extraction.py`
- Demo: `demo_tfidf.py`

