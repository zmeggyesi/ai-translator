# XLIFF Style Extraction Feature Summary

## Overview

Added the ability to extract style guides from XLIFF (XML Localization Interchange File Format) files using the `extract-style` command. Content for creating the style guide is extracted from the `<source>` elements within XLIFF files, following the same pattern as glossary extraction.

## Changes Made

### 1. Core Functionality (`nodes/extract_style.py`)

#### New Function: `extract_style_guide_from_xliff()`
- **Location**: Lines 334-395
- **Purpose**: Extract style guide from XLIFF files by parsing source elements
- **Parameters**:
  - `xliff_path`: Path to the XLIFF file
  - `source_language`: Language of the source text
  - `output_path`: Output path for the style guide (default: "extracted_style.md")
  - `template_path`: Optional template for rewriting (default: None)
- **Process**:
  1. Validates XLIFF file exists
  2. Parses XLIFF using `parse_xliff()` with `extract_target=False` to get source segments
  3. Creates TMX-like entries using `create_document_entries()`
  4. Generates style guide using existing `infer_style_guide_from_tmx()` or `rewrite_style_guide_template()`
  5. Writes output to specified path

#### Updated Function: `extract_style_guide_unified()`
- **Location**: Lines 462-510
- **Changes**:
  - Added `'xlf'` and `'xliff'` to supported file types
  - Updated docstring to mention XLIFF support
  - Added conditional branch to call `extract_style_guide_from_xliff()` for XLIFF files
  - Updated error message to list all supported types including XLIFF

#### New Import
- Added `parse_xliff` to imports from `nodes.document_parsers`

### 2. Command-Line Interface (`cli.py`)

#### Updated: `_add_style_parser()`
- **Location**: Lines 276-293
- **Changes**:
  - Updated help text: "...document (PDF, DOCX, DOC), XLIFF file, or URLs"
  - Added `"xlf"` and `"xliff"` to `--file-type` choices
  - File type choices now: `["tmx", "pdf", "docx", "doc", "xlf", "xliff", "urls"]`

### 3. Tests (`tests/test_document_style_extraction.py`)

#### New Test Class: `TestXLIFFParsing`
- **Tests**: 2 tests
- **Coverage**:
  - `test_parse_xliff_source_extraction`: Verifies XLIFF parsing extracts source text correctly
  - `test_parse_xliff_file_not_found`: Tests error handling for missing files

#### New Test Class: `TestStyleExtractionFromXLIFF`
- **Tests**: 4 tests
- **Coverage**:
  - `test_extract_style_guide_from_xliff_success`: Happy path with mocked LLM
  - `test_extract_style_guide_from_xliff_with_template`: Template rewriting functionality
  - `test_extract_style_guide_from_xliff_file_not_found`: File not found error handling
  - `test_extract_style_guide_from_xliff_empty_file`: Empty XLIFF file error handling

#### Updated Test Class: `TestStyleExtractionFromDocuments`
- **New Tests**: 2 additional tests
- **Coverage**:
  - `test_extract_style_guide_unified_xliff`: Tests unified API with .xlf extension
  - `test_extract_style_guide_unified_xliff_variant`: Tests unified API with .xliff extension

**Total New Tests**: 8 tests
**All Tests Status**: 37/37 passing ✓

### 4. Documentation

#### Updated: `README.md`
- **Section**: "3b. Extract a Style Guide from TMX, Documents, XLIFF, or URLs"
- **Changes**:
  - Updated section title to include XLIFF
  - Added example command for XLIFF extraction:
    ```bash
    python cli.py extract-style \
      --input data/translations.xlf \
      --file-type xlf \
      --source-language English \
      --output extracted_style.md
    ```

#### New: `demo_xliff_style.py`
- **Purpose**: Demonstration script showing XLIFF style extraction
- **Features**:
  - Three demo scenarios (basic, unified API, real file)
  - Uses mocked LLM to avoid API key requirements
  - Shows usage with both `.xlf` and `.xliff` extensions
  - Includes example with real `data/urschel.xlf` file

## Usage Examples

### Command Line

Extract style from XLIFF using `.xlf` extension:
```bash
python cli.py extract-style \
  --input data/urschel.xlf \
  --file-type xlf \
  --source-language English \
  --output style_guide.md
```

Extract style from XLIFF using `.xliff` extension:
```bash
python cli.py extract-style \
  --input data/translations.xliff \
  --file-type xliff \
  --source-language Spanish \
  --output style_guide.md
```

With template rewriting:
```bash
python cli.py extract-style \
  --input data/translations.xlf \
  --file-type xlf \
  --source-language English \
  --output adapted_style.md \
  --template data/sample-style-guide.md
```

### Programmatic

```python
from nodes.extract_style import extract_style_guide_from_xliff, extract_style_guide_unified

# Direct function call
style_guide = extract_style_guide_from_xliff(
    xliff_path="data/translations.xlf",
    source_language="English",
    output_path="style_guide.md"
)

# Using unified API
style_guide = extract_style_guide_unified(
    file_path="data/translations.xlf",
    file_type="xlf",
    source_language="English",
    output_path="style_guide.md"
)

# With template rewriting
style_guide = extract_style_guide_unified(
    file_path="data/translations.xlf",
    file_type="xlf",
    source_language="English",
    output_path="style_guide.md",
    template_path="template.md"
)
```

## Integration with Existing System

The XLIFF style extraction seamlessly integrates with the existing architecture:

1. **Reuses XLIFF Parser**: Leverages existing `parse_xliff()` from `document_parsers.py`
2. **Compatible Data Structures**: Uses `create_document_entries()` to create TMX-like entries
3. **Same Style Generation**: Uses existing `infer_style_guide_from_tmx()` function
4. **Template Support**: Supports template rewriting like other file types
5. **Unified Interface**: Works through `extract_style_guide_unified()` for consistency
6. **No Breaking Changes**: All existing functionality remains unchanged

## Technical Details

### XLIFF Processing Flow

1. **Parse XLIFF**: Use `parse_xliff(file_path, extract_target=False)` to extract source text
2. **Create Entries**: Convert text segments to TMX-like entries with metadata
3. **Build Memory**: Create TMX memory structure with special flags:
   - `xliff_source: True` - Indicates XLIFF origin
   - `xliff_path: <path>` - Original file path
   - `language_pair: <lang>-><lang>` - Same source and target language
4. **Generate Style**: Use LLM analysis via `infer_style_guide_from_tmx()`
5. **Write Output**: Save markdown style guide to specified path

### TMX Memory Structure for XLIFF

```python
tmx_memory = {
    "entries": [
        {
            "source": "text",
            "target": "text",  # Same as source for style extraction
            "source_lang": "English",
            "target_lang": "English",
            "usage_count": 1,
            "document_sentence": True,
            "sentence_index": 0
        },
        # ... more entries
    ],
    "language_pair": "English->English",
    "xliff_source": True,
    "xliff_path": "/path/to/file.xlf"
}
```

### Key Design Decisions

1. **Source Elements Only**: Extract from `<source>` elements (not `<target>`) to analyze the original writing style
2. **Monolingual Processing**: Treat as monolingual content (source_lang == target_lang)
3. **Reuse Infrastructure**: Leverage existing document processing pipeline
4. **Both Extensions**: Support both `.xlf` and `.xliff` file extensions
5. **No Target Language Required**: Unlike TMX, XLIFF style extraction doesn't need target language

## Testing

### Test Coverage
- ✓ XLIFF parsing with source extraction
- ✓ File not found error handling
- ✓ Empty XLIFF file handling
- ✓ Basic style extraction (mocked LLM)
- ✓ Template rewriting support
- ✓ Unified API with .xlf extension
- ✓ Unified API with .xliff extension
- ✓ Integration with existing test suite

### Demo Script
Run `python demo_xliff_style.py` to see:
- Basic XLIFF style extraction
- Unified API usage
- Real file processing (with data/urschel.xlf)

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `nodes/extract_style.py` | +63 lines | Added XLIFF extraction function and updated unified API |
| `cli.py` | +2 lines | Added xlf/xliff to file type choices |
| `tests/test_document_style_extraction.py` | +170 lines | Added 8 new tests for XLIFF functionality |
| `README.md` | +8 lines | Added XLIFF usage example |
| `demo_xliff_style.py` | +261 lines | New demo script |
| `XLIFF_STYLE_EXTRACTION_SUMMARY.md` | +267 lines | This summary document |

**Total**: ~771 lines added/modified

## Dependencies

No new dependencies required. Uses existing:
- `xml.etree.ElementTree` (built-in)
- `nodes.document_parsers.parse_xliff`
- `nodes.style_guide.infer_style_guide_from_tmx`
- `nodes.style_guide.rewrite_style_guide_template`

## Backward Compatibility

✓ All existing functionality preserved
✓ No breaking changes to APIs
✓ All 37 tests passing
✓ No linter errors

## Future Enhancements (Optional)

Potential improvements for future consideration:
1. Support extracting from `<target>` elements (for analyzing translated content style)
2. Bilingual style comparison (source vs target style differences)
3. XLIFF 2.0 namespace support (currently handles 1.2)
4. Batch processing of multiple XLIFF files
5. Style guide merging from multiple XLIFF sources

## Conclusion

XLIFF style extraction is now fully integrated into the AI Translator system, providing users with another powerful source for style guide generation. The implementation follows established patterns, maintains backward compatibility, and includes comprehensive test coverage.

