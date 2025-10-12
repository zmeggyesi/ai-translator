# URL-Based Style Guide Extraction

This document describes how to extract style guides from web content by providing a list of URLs.

## Overview

The URL-based style extraction feature allows you to generate translation style guides by analyzing content from multiple web pages. This is particularly useful when:

- Your brand content is primarily published online
- You want to extract style from blog posts, articles, or marketing pages
- You need to analyze style across multiple web resources
- You want to ensure consistency with existing online content

## Features

- **Batch Processing**: Analyze multiple URLs in one operation
- **Robust HTML Parsing**: Automatically extracts text content and removes navigation, scripts, and styles
- **Error Handling**: Continues processing even if some URLs fail to load
- **Flexible Limits**: Option to limit the number of URLs processed
- **Comment Support**: URL files can include comments and empty lines
- **Comprehensive Logging**: Detailed logs of URL fetching and processing

## Requirements

The URL extraction feature requires two additional dependencies:

```bash
uv pip install requests beautifulsoup4
```

These are automatically included in the project's `pyproject.toml`.

## Usage

### 1. Create a URLs File

Create a text file with one URL per line. The file supports comments (lines starting with `#`) and blank lines:

```text
# Company Blog Posts
https://www.example.com/blog/product-launch
https://www.example.com/blog/customer-success-story

# Marketing Pages
https://www.example.com/products/premium-service
https://www.example.com/about-us

# Support Documentation
https://docs.example.com/getting-started
https://docs.example.com/best-practices
```

### 2. Extract Style Guide

#### Using the Specific Function

```python
from nodes.extract_style import extract_style_guide_from_urls

style_guide = extract_style_guide_from_urls(
    urls_file_path="data/my_urls.txt",
    source_language="english",
    output_path="extracted_style.md",
    max_urls=10  # Optional: limit number of URLs
)

print(style_guide)
```

#### Using the Unified Interface

```python
from nodes.extract_style import extract_style_guide_unified

style_guide = extract_style_guide_unified(
    file_path="data/my_urls.txt",
    file_type="urls",
    source_language="english",
    output_path="extracted_style.md",
    max_urls=5  # Optional
)
```

### 3. Function Parameters

#### `extract_style_guide_from_urls`

- **`urls_file_path`** (str, required): Path to the text file containing URLs
- **`source_language`** (str, required): Language of the web content (e.g., "english", "spanish")
- **`output_path`** (str, optional): Where to save the generated style guide (default: "extracted_style.md")
- **`max_urls`** (int, optional): Maximum number of URLs to process (default: None = all URLs)

#### `extract_style_guide_unified`

- **`file_path`** (str, required): Path to the input file
- **`file_type`** (str, required): Type of file - use "urls" for URL lists
- **`source_language`** (str, required): Language of the content
- **`target_language`** (str, optional): Not used for URLs (only for TMX files)
- **`output_path`** (str, optional): Where to save the style guide
- **`max_urls`** (int, optional): Maximum number of URLs to process

## How It Works

1. **URL Loading**: Reads and validates URLs from the input file
2. **Content Fetching**: Downloads HTML content from each URL
3. **HTML Parsing**: Extracts text content while removing:
   - Navigation elements (`<nav>`, `<header>`, `<footer>`)
   - Scripts and styles (`<script>`, `<style>`)
   - Other non-content elements
4. **Text Aggregation**: Combines text from all successful URLs
5. **Sentence Extraction**: Splits the text into individual sentences
6. **Style Inference**: Uses LLM (GPT-4) to analyze patterns and generate a comprehensive style guide

## Example Output

The generated style guide will be a Markdown document similar to:

```markdown
# Translation Style Guide

## Tone and Voice
- Professional yet approachable
- Customer-focused language
- Use active voice

## Terminology
- "customers" not "users"
- "solution" not "product"
...
```

## Error Handling

The system is designed to be robust:

- **Invalid URLs**: Skipped with a warning (lines not starting with `http://` or `https://`)
- **Failed Fetches**: Individual URL failures don't stop the process
- **No Content**: URLs with no extractable text are logged and skipped
- **Partial Success**: As long as at least one URL succeeds, style guide generation proceeds

Example log output:

```
INFO: Loaded 5 URLs from data/urls.txt
INFO: Fetching content from URL: https://example.com/page1
INFO: Successfully extracted 2847 characters from https://example.com/page1
WARNING: Skipping URL https://example.com/page2 due to error: HTTP 404
INFO: Successfully extracted content from 4/5 URLs
INFO: Extracted 156 sentences from web content
INFO: Style guide written → extracted_style.md
```

## Best Practices

### Selecting URLs

1. **Content Quality**: Choose pages with substantial, well-written content
2. **Consistency**: Select URLs from the same brand/organization
3. **Variety**: Include different content types (blog posts, landing pages, documentation)
4. **Recency**: Use recent content that reflects current style preferences

### Processing Tips

1. **Start Small**: Test with 3-5 URLs first
2. **Use max_urls**: Limit processing during development/testing
3. **Check Accessibility**: Ensure URLs are publicly accessible (not behind paywalls/logins)
4. **Monitor Logs**: Watch for fetch errors and adjust URL list accordingly

### URL File Organization

```text
# Professional Services URLs - Use these for formal tone
https://www.company.com/enterprise-solutions
https://www.company.com/case-studies/fortune-500

# Blog Posts - Analyze for conversational elements
https://blog.company.com/expert-tips
https://blog.company.com/industry-insights

# Documentation - Technical writing style
https://docs.company.com/api-reference
https://docs.company.com/integration-guide
```

## Limitations

1. **JavaScript-Rendered Content**: Content rendered by JavaScript may not be captured
2. **Login-Protected Pages**: Authentication-required pages cannot be accessed
3. **Rate Limiting**: Excessive requests might trigger rate limiting
4. **Content Quality**: Style guide quality depends on source content quality
5. **Language Detection**: Assumes all URLs are in the specified language

## Troubleshooting

### "No valid URLs found in file"

- Check that URLs start with `http://` or `https://`
- Ensure file encoding is UTF-8
- Verify file path is correct

### "Failed to extract content from any URLs"

- Check internet connectivity
- Verify URLs are accessible in a browser
- Check for firewall/proxy restrictions
- Try with a smaller set of URLs

### "ImportError: requests is required"

```bash
uv pip install requests beautifulsoup4
```

### "HTTP 403 Forbidden" errors

Some websites block automated requests. Try:
- Using fewer URLs
- Adding delays between requests (not currently supported, may need custom solution)
- Ensuring URLs are publicly accessible

## Integration with Main Workflow

The URL extraction feature integrates seamlessly with the existing translation workflow:

```python
from nodes.extract_style import extract_style_guide_unified

# Extract style from URLs
style_guide = extract_style_guide_unified(
    file_path="data/brand_urls.txt",
    file_type="urls",
    source_language="english"
)

# Use in translation workflow
# ... (integrate with your LangGraph workflow)
```

## Testing

Comprehensive tests are available in `tests/test_url_style_extraction.py`:

```bash
uv run pytest tests/test_url_style_extraction.py -v
```

The test suite covers:
- HTML text extraction
- URL content fetching
- File loading with comments and empty lines
- Error handling and partial failures
- End-to-end integration

## See Also

- [TMX Integration Guide](TMX_INTEGRATION.md)
- [Document Style Extraction](DOCUMENT_STYLE_EXTRACTION.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

