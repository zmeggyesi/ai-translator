# Template Rewriting Feature

## Overview

The template rewriting feature allows you to adapt an existing style guide template to match the tone, vocabulary, and patterns found in your actual content. Instead of generating a completely new style guide from scratch, you can provide a template that has the structure and format you want, and the system will rewrite it based on analysis of your source material.

## Use Case

This feature is particularly useful when you:
- Have a preferred style guide structure or format
- Want to maintain consistency with existing documentation
- Need to adapt a generic template to specific brand or domain characteristics
- Have template placeholders (like `{{targetLanguage}}`) that should be preserved

## How It Works

1. **Provide a Template**: Supply an existing style guide in Markdown format
2. **Analyze Content**: Extract content from URLs, documents, or TMX files
3. **Rewrite Template**: The LLM analyzes the actual content patterns and rewrites the template sections to reflect what it finds
4. **Preserve Structure**: The template's structure, format, and placeholders are maintained

## Usage

### Basic Command

```bash
python cli.py extract-style \
  --input data/urls.txt \
  --file-type urls \
  --source-language English \
  --output adapted_style.md \
  --template data/sample-style-guide.md
```

### Works with All Input Types

**From URLs:**
```bash
python cli.py extract-style \
  --input data/company_urls.txt \
  --file-type urls \
  --source-language English \
  --template data/template.md \
  --output brand_style.md
```

**From Documents:**
```bash
python cli.py extract-style \
  --input data/brand_doc.pdf \
  --file-type pdf \
  --source-language English \
  --template data/template.md \
  --output adapted_style.md
```

**From TMX:**
```bash
python cli.py extract-style \
  --input data/translations.tmx \
  --file-type tmx \
  --source-language en \
  --target-language es \
  --template data/template.md \
  --output translation_style.md
```

## Example

### Input Template (`data/sample-style-guide.md`)

```markdown
## Tone of Voice
- Professional
- Friendly
- Engaging

## Writing Guidelines
- Use clear language
- Be concise
- Active voice preferred

## Terminology
- Use industry-standard terms
- Define technical concepts
```

### Analyzed Content (from URLs)

The system fetches content from your URLs and finds patterns like:
- Technical and precise language
- Direct communication style
- Extensive use of technical terminology
- Formal tone

### Output (Adapted Style Guide)

```markdown
## Tone of Voice
- Technical and precise
- Professional and authoritative
- Direct and concise

## Writing Guidelines
- Use technical terminology appropriately
- Favor brief, specific sentences
- Maintain active voice in technical descriptions

## Terminology
- Use domain-specific technical terms (e.g., "API", "endpoint", "authentication")
- Define acronyms on first use
- Prefer industry-standard nomenclature
```

## Python API

```python
from nodes.extract_style import extract_style_guide_unified

# Rewrite template based on URL content
style_guide = extract_style_guide_unified(
    file_path="data/urls.txt",
    file_type="urls",
    source_language="english",
    output_path="adapted_style.md",
    template_path="data/template.md"
)
```

Or use the direct function:

```python
from nodes.extract_style import extract_style_guide_from_urls

style_guide = extract_style_guide_from_urls(
    urls_file_path="data/urls.txt",
    source_language="english",
    output_path="adapted_style.md",
    template_path="data/template.md"
)
```

## Core Function

The underlying implementation is in `nodes/style_guide.py`:

```python
from nodes.style_guide import rewrite_style_guide_template

# Direct template rewriting
style_guide = rewrite_style_guide_template(
    tmx_memory=tmx_memory,  # Dict with 'entries' list
    template_path="data/template.md"
)
```

## Template Requirements

### What Makes a Good Template

1. **Clear Structure**: Use well-defined sections with headers
2. **Markdown Format**: Standard Markdown formatting
3. **Placeholder Support**: Include placeholders like `{{targetLanguage}}`
4. **Comprehensive Coverage**: Include all aspects you want analyzed (tone, style, terminology, etc.)

### Template Placeholders

The system preserves template placeholders:
- `{{targetLanguage}}` - Target language
- `{{audience}}` - Target audience
- `{{brandName}}` - Brand or product name
- Any other custom placeholders

### Example Template

```markdown
## **Translation Guide for {{brandName}}**

You are translating content for {{brandName}}, targeting {{audience}}.

### **Tone of Voice**
- [Template will be rewritten based on actual content]
- [Maintains this structure]

### **Target Language: {{targetLanguage}}**
- Use {{targetLanguage}} conventions
- [Specific guidelines will be adapted]

### **Terminology**
- [Domain-specific terms will be identified]
- [Usage patterns will be documented]
```

## Technical Details

### Analysis Process

1. **Content Sampling**: Reservoir sampling selects representative content within token budget (100K tokens)
2. **Pattern Analysis**: LLM analyzes:
   - Tone and voice patterns
   - Vocabulary and terminology
   - Sentence structure and pacing
   - Formality level
   - Domain-specific characteristics
3. **Template Rewriting**: LLM rewrites template sections while:
   - Preserving structure
   - Maintaining placeholders
   - Matching analyzed patterns

### LLM Requirements

- **Required**: OpenAI API key (`OPENAI_API_KEY` environment variable)
- **Model**: GPT-4o
- **Temperature**: 0 (deterministic)
- **Token Budget**: 100,000 tokens for content sampling

### Error Handling

```python
from nodes.style_guide import rewrite_style_guide_template

try:
    result = rewrite_style_guide_template(tmx_memory, "template.md")
except FileNotFoundError:
    print("Template file not found")
except RuntimeError as e:
    if "API key" in str(e):
        print("OpenAI API key required")
    else:
        print(f"LLM error: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
```

## Testing

Comprehensive tests are available in `tests/test_template_rewrite.py`:

```bash
# Run template rewriting tests
uv run pytest tests/test_template_rewrite.py -v

# Run all tests
uv run pytest -v
```

Test coverage includes:
- Template rewriting with various input types
- Error handling (missing files, no API key, LLM failures)
- Placeholder preservation
- Integration with URL, document, and TMX extraction

## Best Practices

### 1. Template Design
- Create templates that cover all aspects you care about
- Use clear section headers
- Include examples where helpful
- Add placeholders for dynamic content

### 2. Content Selection
- Choose representative URLs or documents
- Ensure sufficient content volume (multiple pages/documents)
- Verify content is accessible and text-heavy

### 3. Iterative Refinement
- Start with a draft template
- Review the adapted output
- Refine the template structure based on results
- Re-run with adjusted template

### 4. Quality Assurance
- Review the adapted style guide for accuracy
- Verify that critical guidelines are properly adapted
- Check that placeholders are preserved
- Ensure technical terminology is correctly identified

## Limitations

1. **LLM Dependency**: Requires OpenAI API key (no offline fallback for template rewriting)
2. **Token Limits**: Content sampling limited to 100K tokens
3. **Template Structure**: Works best with well-structured Markdown templates
4. **Language Support**: Template rewriting quality depends on LLM's language capabilities

## Comparison: Template Rewriting vs. Generation

| Aspect | Template Rewriting | New Generation |
|--------|-------------------|----------------|
| Structure | Preserves template structure | Creates new structure |
| Consistency | Maintains format | May vary in format |
| Placeholders | Preserved | Not applicable |
| Customization | High (start with your template) | Low (standard output) |
| Use Case | Brand-specific, structured guides | General-purpose guides |

## Files Modified/Created

**Modified:**
- `nodes/style_guide.py` - Added `rewrite_style_guide_template()` function
- `nodes/extract_style.py` - Added `template_path` parameter to all extraction functions
- `cli.py` - Added `--template` CLI argument
- `README.md` - Added template rewriting documentation

**Created:**
- `tests/test_template_rewrite.py` - 15 tests for template rewriting
- `TEMPLATE_REWRITE_FEATURE.md` - This documentation

## See Also

- [URL Style Extraction](docs/URL_STYLE_EXTRACTION.md)
- [Document Style Extraction](docs/DOCUMENT_STYLE_EXTRACTION.md)
- [TMX Integration](docs/TMX_INTEGRATION.md)
- [README](README.md)

