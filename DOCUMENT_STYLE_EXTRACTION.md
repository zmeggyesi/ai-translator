# Document Style Extraction Feature

This document describes the new document style extraction feature that extends the AI translator to support PDF, DOCX, and DOC files for style guide generation.

## Overview

The style extraction subsystem has been extended to parse and utilize PDF, DOCX, and DOC files in addition to TMX files. The system uses specific parsers for each file type, splits the content into sentences, and applies the same sampling logic used for TMX files to create comprehensive style guides.

## Features

### Supported File Types
- **PDF**: Parses PDF files using PyPDF2
- **DOCX**: Parses DOCX files using python-docx
- **DOC**: Basic DOC file support (limited, converts via python-docx)
- **TMX**: Existing TMX file support (unchanged)

### Key Capabilities
- **Sentence Splitting**: Uses NLTK for intelligent sentence tokenization with regex fallback
- **Unified Sampling**: Applies the same reservoir sampling logic used for TMX files
- **Token Budget**: Maintains 120k token limit for LLM processing
- **Language Support**: Supports multiple languages for sentence tokenization
- **Style Guide Generation**: Creates comprehensive style guides using the existing LLM-based system

## Architecture

### New Components

#### 1. Document Parsers (`nodes/document_parsers.py`)
- **Sentence Splitting**: NLTK-based tokenization with regex fallback
- **PDF Parser**: Extracts text from PDF files using PyPDF2
- **DOCX Parser**: Extracts text from DOCX files including paragraphs and tables
- **DOC Parser**: Basic DOC file support
- **Unified Interface**: Common `parse_document()` function for all file types

#### 2. Extended Style Extraction (`nodes/extract_style.py`)
- **Document Style Extraction**: New function for document-based style guide generation
- **Unified Interface**: Single function that handles both TMX and document files
- **TMX-like Entries**: Converts document sentences to TMX-compatible format

#### 3. Updated CLI (`cli.py`)
- **File Type Selection**: New `--file-type` argument with choices: tmx, pdf, docx, doc
- **Flexible Arguments**: Target language is optional for documents, required for TMX
- **Enhanced Help**: Updated help text and argument descriptions

### Integration with Existing System

The new functionality integrates seamlessly with the existing style extraction pipeline:

1. **Same Sampling Logic**: Uses existing reservoir sampling and token budget system
2. **Compatible with LLM**: Generates TMX-like entries for consistent processing
3. **Backward Compatibility**: Existing TMX functionality unchanged
4. **Unified Style Guide**: Uses the same `infer_style_guide_from_tmx()` function

## Usage

### Command Line Interface

#### Extract style from PDF:
```bash
python cli.py extract-style \
  --input document.pdf \
  --file-type pdf \
  --source-language English \
  --output style_guide.md
```

#### Extract style from DOCX:
```bash
python cli.py extract-style \
  --input document.docx \
  --file-type docx \
  --source-language Spanish \
  --output style_guide.md
```

#### Extract style from TMX (unchanged):
```bash
python cli.py extract-style \
  --input translation_memory.tmx \
  --file-type tmx \
  --source-language English \
  --target-language French \
  --output style_guide.md
```

### Programmatic Usage

```python
from nodes.extract_style import extract_style_guide_unified

# Extract from PDF
style_guide = extract_style_guide_unified(
    file_path="document.pdf",
    file_type="pdf",
    source_language="English",
    output_path="style_guide.md"
)

# Extract from DOCX
style_guide = extract_style_guide_unified(
    file_path="document.docx",
    file_type="docx",
    source_language="Spanish",
    output_path="style_guide.md"
)

# Extract from TMX
style_guide = extract_style_guide_unified(
    file_path="memory.tmx",
    file_type="tmx",
    source_language="English",
    target_language="French",
    output_path="style_guide.md"
)
```

## Dependencies

New dependencies added to `pyproject.toml`:
- `pypdf2`: PDF parsing
- `python-docx`: DOCX parsing
- `nltk`: Sentence tokenization

## Error Handling

The system includes comprehensive error handling:
- **Missing Dependencies**: Clear error messages when required libraries are not installed
- **File Not Found**: Proper error handling for missing files
- **Parse Errors**: Graceful handling of corrupted or unreadable documents
- **Empty Content**: Validation for documents with no extractable text
- **Unsupported Types**: Clear error messages for unsupported file formats

## Testing

Comprehensive test suite (`tests/test_document_style_extraction.py`) covers:
- **Unit Tests**: All parsing functions and utilities
- **Integration Tests**: End-to-end style extraction workflows
- **Error Handling**: Edge cases and error conditions
- **Mocking**: Proper mocking of external dependencies

Test coverage includes:
- 25 test cases covering all major functionality
- Sentence splitting with both NLTK and regex fallback
- PDF, DOCX, and DOC parsing
- Style guide generation from documents
- Unified interface testing
- Error condition handling

## Performance Considerations

- **Token Budget**: 120k token limit prevents memory issues with large documents
- **Reservoir Sampling**: Efficient sampling of large documents
- **Graceful Fallbacks**: NLTK failures don't break the system
- **Streaming**: PDF parsing processes pages individually

## Future Enhancements

Potential improvements for future versions:
- **Better DOC Support**: Enhanced DOC file parsing
- **OCR Integration**: Support for scanned PDFs
- **Additional Formats**: Support for RTF, HTML, etc.
- **Language Detection**: Automatic language detection for documents
- **Parallel Processing**: Multi-threaded document parsing

## Backward Compatibility

The changes maintain full backward compatibility:
- **Existing TMX Functionality**: No changes to TMX processing
- **API Compatibility**: All existing functions remain unchanged
- **CLI Compatibility**: Old TMX-based commands still work
- **Test Suite**: All existing tests continue to pass

## Migration Guide

For users upgrading from previous versions:

1. **Install Dependencies**: Run `uv add pypdf2 python-docx nltk`
2. **Update CLI Usage**: Use new `--file-type` argument instead of `--tmx`
3. **Optional Target Language**: Target language is now optional for documents
4. **Same Output Format**: Style guides maintain the same markdown format