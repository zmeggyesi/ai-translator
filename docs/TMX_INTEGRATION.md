# TMX (Translation Memory eXchange) Integration

This document describes the TMX (Translation Memory eXchange) functionality integrated into the AI translator project.

## Overview

TMX files are XML-based translation memory files that store source and target text segments in multiple languages. This integration allows the AI translator to:

1. **Use exact TMX matches verbatim** during translation when source segments match exactly
2. **Use fuzzy TMX matches as style guidance** when no exact matches exist
3. **Validate translation faithfulness** against TMX entries during review
4. **Ensure consistency** with established translation patterns

## Features

### TMX File Parsing
- Parses TMX 1.4+ format files
- Extracts source-target segment pairs for all language combinations
- Handles multiple translation units and variants
- Supports usage counts and creation dates

### Translation Integration
- **Exact Matches**: Uses TMX translations verbatim when source text matches exactly (100% similarity)
- **Fuzzy Matches**: Provides top 3 similar TMX entries as style guidance for the LLM (80%+ similarity)
- **Fallback**: Uses regular translation with glossary and style guide when no matches exist

### Review Integration
- **TMX Faithfulness Review**: New review dimension that validates TMX compliance
- **Exact Match Validation**: Ensures exact TMX matches were used when available
- **Style Consistency**: Checks translation style consistency with similar TMX entries
- **Weighted Scoring**: TMX faithfulness contributes 20% to the overall review score

## File Structure

### New Files
- `nodes/tmx_loader.py` - TMX parsing and loading functionality
- `nodes/review_tmx_faithfulness.py` - TMX faithfulness review node
- `data/sample.tmx` - Sample TMX file for testing
- `tests/test_tmx_functionality.py` - Comprehensive TMX tests
- `TMX_INTEGRATION.md` - This documentation

### Modified Files
- `state.py` - Added TMX memory fields and TMX faithfulness scores
- `nodes/translate_content.py` - Integrated TMX matching for translation
- `nodes/review_aggregator.py` - Included TMX faithfulness in review scoring

## Usage

### 1. Prepare TMX File

Create or obtain a TMX file with your translation memory. Example format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header
    creationtool="AI-Translator"
    creationtoolversion="1.0"
    datatype="PlainText"
    segtype="sentence"
    adminlang="en-us"
    srclang="en"
    o-tmf="TMX"
  />
  <body>
    <tu tuid="1" usagecount="5" creationdate="20240101T120000Z">
      <tuv xml:lang="en">
        <seg>Hello world</seg>
      </tuv>
      <tuv xml:lang="fr">
        <seg>Bonjour le monde</seg>
      </tuv>
    </tu>
    <!-- More translation units... -->
  </body>
</tmx>
```

### 2. Load TMX Memory

```python
from nodes.tmx_loader import load_tmx_memory

# Load TMX memory for a specific language pair
state = {
    "source_language": "en",
    "target_language": "fr"
}

tmx_result = load_tmx_memory(state, "path/to/your/file.tmx")
state.update(tmx_result)
```

### 3. Translation with TMX

The translation process automatically uses TMX data:

```python
from nodes.translate_content import translate_content

# Translation will use exact TMX matches or fuzzy matches for guidance
translation_result = translate_content(state)
state.update(translation_result)
```

### 4. Review with TMX Validation

```python
from nodes.review_tmx_faithfulness import evaluate_tmx_faithfulness

# Review TMX faithfulness
review_result = evaluate_tmx_faithfulness(state)
state.update(review_result.update)
```

## API Reference

### TMX Loader Functions

#### `parse_tmx_file(tmx_file_path: str) -> Dict[str, List[Dict]]`
Parses a TMX file and extracts translation memory entries.

**Returns:**
```python
{
    "en->fr": [
        {
            "source": "Hello world",
            "target": "Bonjour le monde", 
            "source_lang": "en",
            "target_lang": "fr",
            "creation_date": "20240101T120000Z",
            "usage_count": 5
        }
    ]
}
```

#### `find_tmx_matches(source_text: str, tmx_entries: List[Dict], threshold: float = 100.0) -> List[Dict]`
Finds matching translation memory entries for the given source text.

**Parameters:**
- `source_text`: Text to find matches for
- `tmx_entries`: List of TMX entries for the language pair
- `threshold`: Minimum similarity score (0-100) for matches

**Returns:** List of matching entries sorted by similarity score (highest first)

#### `load_tmx_memory(state: TranslationState, tmx_file_path: str) -> dict`
Loads TMX translation memory for the current language pair.

### State Fields

The following fields are added to `TranslationState`:

```python
class TranslationState(TypedDict):
    # ... existing fields ...
    
    # TMX fields
    tmx_memory: Optional[dict]  # Loaded TMX translation memory entries
    tmx_faithfulness_score: Optional[float]  # Score for TMX compliance
    tmx_faithfulness_explanation: Optional[str]  # Explanation for TMX issues
```

## Translation Behavior

### Exact Matches (100% similarity)
When the source text exactly matches a TMX entry:
- The TMX target translation is used verbatim
- No LLM call is made
- Provides fastest and most consistent translation

### Fuzzy Matches (80%+ similarity)
When similar TMX entries exist:
- Top 3 matches are provided as style guidance to the LLM
- LLM generates translation considering TMX patterns
- Balances consistency with flexibility

### No Matches
When no TMX matches exist above threshold:
- Standard translation process with glossary and style guide
- TMX has no impact on translation

## Review Scoring

### TMX Faithfulness Dimension
- **Weight**: 20% of overall review score
- **Perfect Score (1.0)**: TMX matches used correctly or no TMX available
- **Good Score (0.7-0.9)**: Style consistent with TMX patterns
- **Poor Score (0.2-0.6)**: Style inconsistent with TMX patterns
- **Negative Score (-0.5)**: Exact TMX match available but not used

### Overall Review Impact
TMX faithfulness is combined with other dimensions:
- Glossary Faithfulness: 30%
- Grammar Correctness: 30%
- Style Adherence: 20%
- TMX Faithfulness: 20%

## Testing

Run the comprehensive TMX test suite:

```bash
pytest tests/test_tmx_functionality.py -v
```

Tests cover:
- TMX file parsing (valid/invalid files)
- TMX matching (exact/fuzzy/no matches)
- Translation integration (exact matches, fuzzy guidance)
- Review integration (faithfulness validation)
- End-to-end workflow

## Error Handling

The implementation gracefully handles:
- **Missing TMX files**: Continues without TMX functionality
- **Invalid TMX format**: Provides clear error messages
- **Malformed XML**: Safe parsing with error reporting
- **Language pair mismatches**: Logs available language pairs
- **Empty TMX files**: No impact on translation quality

## Performance Considerations

- **TMX Parsing**: Done once per session, cached in state
- **Exact Matching**: Very fast string comparison
- **Fuzzy Matching**: Uses rapidfuzz for efficient similarity scoring
- **Memory Usage**: TMX entries loaded only for current language pair

## Best Practices

1. **TMX File Quality**: Ensure high-quality, reviewed translations in TMX
2. **Language Codes**: Use consistent language codes (e.g., "en", "fr", "de")
3. **File Organization**: Organize TMX files by domain or project
4. **Regular Updates**: Keep TMX files updated with new approved translations
5. **Testing**: Validate TMX integration with representative content

## Limitations

- Currently supports TMX 1.4+ format only
- Fuzzy matching uses simple text similarity (could be enhanced with semantic similarity)
- Style consistency checks are basic (could be more sophisticated)
- No support for TMX inline tags (focuses on plain text segments)

## Future Enhancements

- **Semantic Matching**: Use embeddings for better fuzzy matching
- **Learning Integration**: Update TMX files with approved translations
- **Advanced Style Analysis**: More sophisticated style consistency checking
- **TMX Generation**: Export approved translations to TMX format
- **Multi-file Support**: Handle multiple TMX files simultaneously