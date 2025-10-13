# XLIFF Glossary Extraction

This document describes the new XLIFF file support for glossary extraction in the AI Translator toolkit.

## Overview

The glossary extraction feature now supports XLIFF (XML Localization Interchange File Format) files, which are commonly used in the localization industry. The extractor can parse XLIFF files and identify significant terms using two methods:

1. **Frequency-based extraction**: Identifies the most common terms in the text
2. **LLM-based extraction**: Uses AI to intelligently identify domain-specific terminology

## Features

- **XLIFF 1.x and 2.x support**: Handles both major XLIFF versions
- **Namespace handling**: Works with or without explicit XML namespaces
- **Inline element support**: Correctly extracts text from inline elements like `<g>`, `<x>`, etc.
- **Source and target extraction**: Can extract from either source or target text
- **Automatic file type detection**: Detects XLIFF files by `.xlf` or `.xliff` extension

## Usage

### Basic Usage (Frequency-based)

Extract glossary terms from an XLIFF file using frequency-based analysis:

```bash
python cli.py extract-glossary \
  -i data/sample.xliff \
  -sl English \
  -tl Spanish \
  -o output/glossary.csv
```

### LLM-based Extraction

For more intelligent term extraction using OpenAI's GPT models:

```bash
python cli.py extract-glossary \
  -i data/sample.xliff \
  -sl English \
  -tl Spanish \
  -o output/glossary.csv \
  --use-llm
```

**Note**: LLM-based extraction requires an `OPENAI_API_KEY` environment variable to be set.

### Limiting the Number of Terms

Control how many terms are extracted (default: 50):

```bash
python cli.py extract-glossary \
  -i data/sample.xliff \
  -sl English \
  -tl Spanish \
  -o output/glossary.csv \
  --max-terms 20
```

This works with both frequency-based and LLM-based extraction.

### Explicit File Type Specification

If auto-detection doesn't work, you can explicitly specify the file type:

```bash
python cli.py extract-glossary \
  -i myfile.xml \
  -ft xliff \
  -sl English \
  -tl Spanish \
  -o output/glossary.csv
```

## Command-line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--input` | `-i` | Path to the input file (XLIFF, text, or use `--tmx` for TMX files) |
| `--file-type` | `-ft` | File type: `text` or `xliff` (auto-detected if not specified) |
| `--source-language` | `-sl` | Source language code (e.g., "English", "en", "en-US") |
| `--target-language` | `-tl` | Target language code (e.g., "Spanish", "es", "es-ES") |
| `--output` | `-o` | Output CSV file path |
| `--use-llm` | | Use LLM for intelligent term extraction (requires OpenAI API key) |
| `--max-terms` | | Maximum number of terms to extract (default: 50) |
| `--tmx` | `-t` | TMX file for bilingual extraction (mutually exclusive with `--input`) |

## XLIFF File Format

The parser supports standard XLIFF files with `trans-unit` elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en-US" target-language="es-ES">
    <body>
      <trans-unit id="1">
        <source>Welcome to our application</source>
        <target>Bienvenido a nuestra aplicación</target>
      </trans-unit>
      <trans-unit id="2">
        <source>Click the <g id="1">Submit</g> button</source>
        <target>Haga clic en el botón <g id="1">Enviar</g></target>
      </trans-unit>
      <trans-unit id="3">
        <source>Click <bpt id="1">&lt;b&gt;</bpt>here<ept id="1">&lt;/b&gt;</ept> to continue</source>
        <target>Haga clic <bpt id="1">&lt;b&gt;</bpt>aquí<ept id="1">&lt;/b&gt;</ept> para continuar</target>
      </trans-unit>
    </body>
  </file>
</xliff>
```

### Text Extraction Rules

The parser extracts text intelligently:

- ✅ **Included**: Content from `<source>` or `<target>` elements
- ✅ **Included**: Text within inline elements (`<g>`, `<x>`, `<bx>`, `<ex>`)
- ❌ **Excluded**: Formatting codes in `<bpt>` (begin paired tag) - e.g., `&lt;b&gt;`, `&lt;strong&gt;`
- ❌ **Excluded**: Formatting codes in `<ept>` (end paired tag) - e.g., `&lt;/b&gt;`, `&lt;/strong&gt;`
- ❌ **Excluded**: Placeholders in `<ph>` tags - e.g., `{username}`, `%s`

**Example**: In the trans-unit #3 above, the parser extracts `"Click here to continue"` and excludes the `&lt;b&gt;` and `&lt;/b&gt;` formatting codes.

## How It Works

### XLIFF Parsing

The parser intelligently extracts text from XLIFF files:

1. **Identifies trans-unit elements**: Finds all translation units in the file
2. **Extracts source/target text**: Gets the appropriate text based on the `extract_target` flag
3. **Handles inline elements**: Processes inline elements like `<g>`, `<x>`, `<bx>`, `<ex>`
4. **Excludes formatting codes**: Skips `<bpt>`, `<ept>`, and `<ph>` tags that contain HTML/XML codes and placeholders
5. **Normalizes whitespace**: Cleans up extra spaces for clean text

### Frequency-based Extraction

1. Parses the XLIFF file and extracts all text segments
2. Tokenizes the text and removes stop words
3. Counts term frequencies
4. Returns the top N most frequent terms (configurable via `--max-terms`, default: 50)

### LLM-based Extraction

1. Parses the XLIFF file and extracts all text segments
2. Chunks the text to fit within token limits (~3000 tokens per chunk)
3. For each chunk, sends the text to GPT-4 with a prompt to identify significant terms
   - The prompt explicitly instructs the LLM to return a maximum of N terms (configurable via `--max-terms`, default: 50)
   - The LLM is instructed to prioritize the most important and frequently occurring domain-specific terminology
4. Aggregates terms from all chunks
5. Returns a deduplicated list of terms

The LLM is specifically prompted to identify:
- Domain-specific and technical vocabulary
- Product names, brand names, and proper nouns
- Key concepts and recurring phrases
- Terms requiring consistent translation
- Industry jargon and specialized terminology

## Output Format

Both methods produce a CSV file with two columns:

```csv
term,translation
API,
authentication,
database,
machine learning,
microservices,
```

The `translation` column is empty for monolingual extraction (XLIFF source text or plain text files). You can fill in translations manually or use a translation service.

## Integration with Translation Workflow

The generated glossary can be used directly in the translation workflow:

```bash
# 1. Extract glossary from XLIFF
python cli.py extract-glossary \
  -i source.xliff \
  -sl English \
  -tl Spanish \
  -o glossary.csv \
  --use-llm

# 2. Add translations to the glossary manually or programmatically

# 3. Use the glossary in translation
python cli.py translate-file \
  -i input.txt \
  -sl English \
  -tl Spanish \
  -g glossary.csv \
  -s style_guide.md
```

## Examples

### Example 1: Extract from Technical Documentation

```bash
python cli.py extract-glossary \
  -i docs/technical-manual.xliff \
  -sl English \
  -tl French \
  -o glossaries/tech-terms.csv \
  --use-llm
```

### Example 2: Extract from Software UI Strings

```bash
python cli.py extract-glossary \
  -i app/strings.xliff \
  -sl English \
  -tl German \
  -o glossaries/ui-terms.csv
```

### Example 3: Extract a Limited Set of Key Terms

Extract only the top 20 most important terms:

```bash
python cli.py extract-glossary \
  -i data.xliff \
  -sl English \
  -tl Spanish \
  -o top-terms.csv \
  --use-llm \
  --max-terms 20
```

### Example 4: Compare Methods

Extract using both methods and compare results:

```bash
# Frequency-based
python cli.py extract-glossary \
  -i data.xliff \
  -sl English \
  -tl Spanish \
  -o freq-glossary.csv

# LLM-based
python cli.py extract-glossary \
  -i data.xliff \
  -sl English \
  -tl Spanish \
  -o llm-glossary.csv \
  --use-llm
```

## Limitations

- XLIFF 2.0 support is limited to basic structure (advanced features may not be supported)
- Very large XLIFF files (>10MB) may take a long time to process with LLM extraction
- LLM extraction requires an internet connection and incurs OpenAI API costs
- The parser assumes UTF-8 encoding

## Testing

Comprehensive tests are available in `tests/test_xliff_glossary_extraction.py`:

```bash
uv run pytest tests/test_xliff_glossary_extraction.py -v
```

## API Reference

### Python API

You can also use the functionality directly in Python:

```python
from nodes.document_parsers import parse_xliff
from nodes.extract_glossary import extract_glossary_with_llm

# Parse XLIFF file
segments = parse_xliff("data/sample.xliff", extract_target=False)

# Extract terms using LLM (default: 50 terms per chunk)
terms = extract_glossary_with_llm(segments, "English")

# Extract with custom limit (20 terms per chunk)
terms = extract_glossary_with_llm(
    segments, 
    "English",
    max_terms_per_chunk=20
)

print(terms)
```

## Troubleshooting

### Error: "No text segments found in XLIFF file"

This usually means:
- The file doesn't contain `<trans-unit>` elements
- The XML structure doesn't match XLIFF format
- The source elements are empty

### Error: "OPENAI_API_KEY is not set"

Set your OpenAI API key in a `.env` file:

```bash
echo "OPENAI_API_KEY=your-key-here" >> .env
```

### Poor Term Quality with Frequency-based Extraction

Try using `--use-llm` for better results. The LLM can understand context and identify domain-specific terms more accurately than frequency analysis.

## Future Enhancements

Potential future improvements:
- Support for extracting from both source and target to create bilingual glossaries
- Custom stop word lists for different languages
- Adjustable token limits for chunking
- Support for XLIFF 2.0 advanced features
- Integration with term bases (TBX format)

