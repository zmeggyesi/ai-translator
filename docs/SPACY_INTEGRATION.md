# SpaCy Integration for Glossary Extraction

## Overview

The glossary extraction module now integrates with [SpaCy](https://spacy.io/) to provide language-specific stopword filtering and improved tokenization. This enhancement allows for more accurate term extraction across multiple languages.

## Features

- **Language-Specific Stopwords**: Uses SpaCy's language models to filter out stopwords appropriate for each language
- **Model Caching**: Loaded language models are cached for better performance
- **Fallback Support**: Falls back to English stopwords if a language model is not available
- **Multi-Language Support**: Supports 15+ languages out of the box

## Supported Languages

The following languages have SpaCy model mappings configured:

| Language | SpaCy Model |
|----------|-------------|
| English | en_core_web_sm |
| Spanish | es_core_news_sm |
| French | fr_core_news_sm |
| German | de_core_news_sm |
| Italian | it_core_news_sm |
| Portuguese | pt_core_news_sm |
| Dutch | nl_core_news_sm |
| Greek | el_core_news_sm |
| Norwegian | nb_core_news_sm |
| Polish | pl_core_news_sm |
| Romanian | ro_core_news_sm |
| Russian | ru_core_news_sm |
| Chinese | zh_core_web_sm |
| Japanese | ja_core_news_sm |
| Danish | da_core_news_sm |
| Finnish | fi_core_news_sm |
| Swedish | sv_core_news_sm |
| Catalan | ca_core_news_sm |

## Installation

### 1. Install SpaCy

SpaCy is automatically installed as a dependency:

```bash
uv sync
```

### 2. Download Language Models

Download the language models you need. For example, to download English and Spanish models:

```bash
# English
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Spanish
uv pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl

# French
uv pip install https://github.com/explosion/spacy-models/releases/download/fr_core_news_sm-3.8.0/fr_core_news_sm-3.8.0-py3-none-any.whl
```

For other languages, replace the model name and version accordingly. See the [SpaCy models documentation](https://spacy.io/models) for more information.

## Usage

### Basic Usage

The SpaCy integration is used automatically when extracting terms from text:

```python
from nodes.extract_glossary import extract_terms_from_text

# Extract English terms
terms = extract_terms_from_text(
    text="Your English text here...",
    top_n=50,
    language="English"
)

# Extract Spanish terms
terms = extract_terms_from_text(
    text="Tu texto en español aquí...",
    top_n=50,
    language="Spanish"
)
```

### CLI Usage

When using the CLI for glossary extraction, specify the source language:

```bash
# Extract glossary from XLIFF file (English)
uv run python cli.py extract-glossary \
    --input data/sample.xliff \
    --file-type xliff \
    --source-language English \
    --output glossary-en.csv

# Extract glossary from text file (Spanish)
uv run python cli.py extract-glossary \
    --input data/input.txt \
    --file-type text \
    --source-language Spanish \
    --output glossary-es.csv
```

## How It Works

1. **Model Loading**: When a language is specified, the system attempts to load the corresponding SpaCy model
2. **Stopword Retrieval**: If the model loads successfully, language-specific stopwords are extracted from the model
3. **Fallback**: If the model is not available, the system falls back to English stopwords
4. **Caching**: Loaded models are cached in memory to avoid reloading them for subsequent requests
5. **Term Filtering**: During term extraction, tokens matching the stopwords are filtered out

## Example: English vs Spanish Stopwords

### English Text
```python
text = "The machine learning system processes data and learns patterns."
terms = extract_terms_from_text(text, language="English")
# Filters: "the", "and" (English stopwords)
# Result: "machine", "learning", "system", "processes", "data", "learns", "patterns"
```

### Spanish Text
```python
text = "El sistema de aprendizaje automático procesa datos y aprende patrones."
terms = extract_terms_from_text(text, language="Spanish")
# Filters: "el", "de", "y" (Spanish stopwords)
# Result: "sistema", "aprendizaje", "automático", "procesa", "datos", "aprende", "patrones"
```

## Benefits

1. **Improved Accuracy**: Language-specific stopwords lead to more relevant term extraction
2. **Better Multilingual Support**: Each language gets appropriate filtering
3. **Automatic Fallback**: System continues to work even if specific language models aren't installed
4. **Performance**: Model caching ensures efficient repeated operations

## Troubleshooting

### Model Not Found

If you see a warning like:
```
SpaCy model 'fr_core_news_sm' not found. Install it with: python -m spacy download fr_core_news_sm
```

Install the model using:
```bash
uv pip install https://github.com/explosion/spacy-models/releases/download/fr_core_news_sm-3.8.0/fr_core_news_sm-3.8.0-py3-none-any.whl
```

### Fallback Behavior

If a language model is not installed, the system will:
1. Log a warning message
2. Fall back to English stopwords
3. Continue processing without errors

This ensures the system remains functional even without all language models installed.

## Testing

Run the SpaCy integration tests:

```bash
uv run pytest tests/test_spacy_integration.py -v
```

Run all tests:

```bash
uv run pytest tests/ -v
```

## Adding New Languages

To add support for a new language:

1. Update the `LANGUAGE_TO_SPACY_MODEL` dictionary in `nodes/extract_glossary.py`:

```python
LANGUAGE_TO_SPACY_MODEL = {
    # ... existing languages ...
    "korean": "ko_core_news_sm",  # Add new language
}
```

2. Install the corresponding SpaCy model:

```bash
uv pip install https://github.com/explosion/spacy-models/releases/download/ko_core_news_sm-3.8.0/ko_core_news_sm-3.8.0-py3-none-any.whl
```

3. Test the integration with sample text in the new language

## References

- [SpaCy Documentation](https://spacy.io/)
- [SpaCy Models](https://spacy.io/models)
- [SpaCy Language Support](https://spacy.io/usage/models#languages)

