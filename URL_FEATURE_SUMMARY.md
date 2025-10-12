# URL-Based Style Extraction - Feature Summary

## Overview

Added the ability to extract translation style guides from web content by providing a file containing a list of URLs.

## What Was Added

### 1. Core Functionality (`nodes/extract_style.py`)

- **`_extract_text_from_html(html_content)`**: Extracts clean text from HTML, removing scripts, styles, navigation, headers, and footers
- **`_fetch_url_content(url, timeout)`**: Fetches and extracts text content from a URL
- **`_load_urls_from_file(file_path)`**: Loads and validates URLs from a text file
- **`extract_style_guide_from_urls(...)`**: Main function to extract style from multiple URLs
- **Updated `extract_style_guide_unified(...)`**: Added support for 'urls' file type and `max_urls` parameter

### 2. Dependencies (`pyproject.toml`)

Added two new required packages:
- `requests`: For fetching URL content
- `beautifulsoup4`: For parsing HTML and extracting text

### 3. CLI Integration (`cli.py`)

- Added 'urls' to the list of supported file types
- Added `--max-urls` optional parameter to limit number of URLs processed
- Updated help text to mention URL support

### 4. Comprehensive Tests (`tests/test_url_style_extraction.py`)

Created 27 tests covering:
- HTML text extraction
- URL content fetching
- File loading with comments and empty lines
- Error handling (HTTP errors, partial failures, invalid URLs)
- Style guide generation
- Integration tests
- Edge cases and validation

### 5. Documentation

- **`docs/URL_STYLE_EXTRACTION.md`**: Comprehensive guide on using the URL extraction feature
- **`README.md`**: Updated with URL extraction examples and CLI options
- **`data/sample_urls.txt`**: Sample URL file format

## Usage Example

```bash
# Create a file with URLs (one per line)
cat > urls.txt << EOF
# Blog Posts
https://www.example.com/blog/post1
https://www.example.com/blog/post2

# Documentation
https://docs.example.com/guide
EOF

# Extract style guide from URLs
python cli.py extract-style \
  --input urls.txt \
  --file-type urls \
  --source-language English \
  --output extracted_style.md \
  --max-urls 10
```

## Key Features

1. **Robust Error Handling**: Continues processing even if some URLs fail
2. **Comment Support**: URL files support comments (lines starting with #) and blank lines
3. **HTML Cleaning**: Automatically removes navigation, scripts, and other non-content elements
4. **URL Limiting**: Optional `max_urls` parameter to limit processing
5. **Comprehensive Logging**: Detailed logs of URL fetching and processing
6. **LLM Integration**: Uses GPT-4o to analyze aggregated content and generate style guides

## Technical Details

### HTML Parsing Strategy

- Uses BeautifulSoup4 for parsing
- Removes: `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`
- Extracts and normalizes whitespace
- Preserves main content only

### Content Aggregation

1. Load URLs from file
2. Fetch each URL (with error handling)
3. Extract text from HTML
4. Combine all text
5. Split into sentences using NLTK
6. Create TMX-like entries
7. Use existing style guide inference logic

### Error Scenarios Handled

- Invalid URL formats (skipped with warning)
- HTTP errors (404, 403, etc.) - skipped with warning
- Connection timeouts - skipped with warning
- Empty content - skipped with warning
- Partial failures - continues if at least one URL succeeds

## Testing

All 27 new tests pass, plus all existing tests (103 total passed):

```bash
uv run pytest tests/test_url_style_extraction.py -v
# 27 passed

uv run pytest -v
# 103 passed, 1 skipped
```

## Integration with Existing System

The URL extraction feature integrates seamlessly with:
- Existing style guide inference logic (`infer_style_guide_from_tmx`)
- Document parsing utilities (`split_into_sentences`, `create_document_entries`)
- Unified extraction interface (`extract_style_guide_unified`)
- CLI command structure
- Test infrastructure

## Files Modified

1. `nodes/extract_style.py` - Core functionality
2. `pyproject.toml` - Added dependencies
3. `cli.py` - CLI integration
4. `README.md` - Documentation updates
5. `tests/test_url_style_extraction.py` - New test suite (27 tests)
6. `docs/URL_STYLE_EXTRACTION.md` - Comprehensive documentation
7. `data/sample_urls.txt` - Example URL file

## Backwards Compatibility

All changes are backwards compatible:
- Existing TMX, PDF, DOCX, DOC extraction continues to work
- New parameters are optional
- No breaking changes to APIs or CLI
- All existing tests continue to pass

