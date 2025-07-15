# TMX CLI Usage Guide

This guide demonstrates how to use the TMX (Translation Memory eXchange) functionality with the AI translator CLI.

## Overview

The AI translator now supports TMX files for translation memory, providing:
- **Exact matches**: Use TMX translations verbatim when source text matches exactly
- **Fuzzy matches**: Provide TMX entries as style guidance for similar content
- **Review validation**: Validate translation faithfulness against TMX patterns
- **Integrated scoring**: Include TMX compliance in overall quality assessment

## CLI Syntax

```bash
python main.py [options] --tmx <tmx_file_path>
```

### New TMX Option

- `-t TMX, --tmx TMX`: TMX (Translation Memory eXchange) file path for translation memory

## Command Examples

### Basic Translation with TMX

```bash
# Translate using TMX memory
python main.py \
  --source-language en \
  --target-language fr \
  --input data/input.txt \
  --glossary data/glossary.csv \
  --style-guide data/style_guide.md \
  --tmx data/sample.tmx
```

### Translation with TMX and Review

```bash
# Include automatic review that validates TMX faithfulness
python main.py \
  --source-language en \
  --target-language fr \
  --input data/input.txt \
  --glossary data/glossary.csv \
  --style-guide data/style_guide.md \
  --tmx data/sample.tmx \
  --review
```

### Help and Options

```bash
# View all available options including TMX
python main.py --help
```

## TMX File Format

The translator supports TMX 1.4+ format files. Example TMX structure:

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

## Expected Behavior

### Exact Matches (100% similarity)
When input text exactly matches a TMX source segment:
- TMX target translation is used directly
- No LLM call is made (faster, more consistent)
- Perfect TMX faithfulness score in review

Example:
- Input: "Hello world"
- TMX match: "Hello world" → "Bonjour le monde"  
- Output: "Bonjour le monde" (exact TMX match used)

### Fuzzy Matches (80%+ similarity)
When input text is similar to TMX entries:
- Top 3 similar TMX entries provided as guidance to LLM
- LLM generates translation considering TMX patterns
- Good TMX faithfulness score if style is consistent

Example:
- Input: "Hello there"
- TMX entry: "Hello world" → "Bonjour le monde" (85% similarity)
- Output: LLM translation guided by TMX style

### No Matches
When no TMX matches exist above threshold:
- Standard translation with glossary and style guide
- TMX has no impact on translation
- Perfect TMX faithfulness score (no TMX to violate)

## Review Output with TMX

When `--review` is enabled, output includes TMX faithfulness:

```
--- Translation Review ---
Overall Review Score: 0.85 (on scale from -1.0 to 1.0)
Quality Assessment: Good to Excellent

--- Detailed Score Breakdown ---
Glossary Faithfulness: 0.90
Grammar Correctness: 0.85
Style Adherence: 0.80
TMX Faithfulness: 0.85

Review Explanation: None needed (score is sufficiently high)
```

### TMX Faithfulness Scoring

- **1.0**: Perfect (exact TMX match used correctly or no TMX available)
- **0.7-0.9**: Good (style consistent with TMX patterns)
- **0.2-0.6**: Poor (style inconsistent with TMX patterns)  
- **-0.5**: Very Poor (exact TMX match available but not used)

## Integration Details

### Workflow Integration
1. **TMX Loading**: Parse TMX file and extract entries for language pair
2. **Translation**: Check for exact matches, use fuzzy matches for guidance
3. **Review**: Validate TMX faithfulness as part of quality assessment
4. **Scoring**: Include TMX compliance (20% weight) in overall review score

### Review Weights (with TMX)
- Glossary Faithfulness: 30%
- Grammar Correctness: 30%
- Style Adherence: 20%
- TMX Faithfulness: 20%

## Error Handling

The system gracefully handles:
- **Missing TMX files**: Continues without TMX functionality
- **Invalid TMX format**: Clear error messages and termination
- **Language pair mismatches**: Logs available language pairs
- **Malformed XML**: Safe parsing with error reporting

## Performance Considerations

- **TMX Parsing**: Done once at startup, cached for session
- **Exact Matching**: Very fast string comparison
- **Fuzzy Matching**: Efficient similarity scoring using rapidfuzz
- **Memory Usage**: Only loads entries for current language pair

## Testing TMX Functionality

Run the comprehensive test suite:

```bash
# Test TMX parsing, matching, and integration
pytest tests/test_tmx_functionality.py -v

# Test specific TMX components
pytest tests/test_tmx_functionality.py::TestTMXParsing -v
pytest tests/test_tmx_functionality.py::TestTMXMatching -v
```

## Sample Files

The repository includes sample files for testing:

- `data/sample.tmx`: Sample TMX file with English-French translations
- `data/input.txt`: Sample input text ("Hello world")
- `data/glossary.csv`: Sample glossary terms
- `data/style_guide.md`: Sample style guidelines

## Troubleshooting

### Common Issues

1. **TMX file not found**
   ```
   Error: TMX file not found: path/to/file.tmx
   ```
   Solution: Verify the TMX file path is correct

2. **No TMX entries for language pair**
   ```
   Warning: No TMX entries found for language pair en->fr
   ```
   Solution: Check TMX file contains the required language pair

3. **Invalid TMX format**
   ```
   Error: Invalid TMX file format: XML parsing error
   ```
   Solution: Validate TMX file against TMX 1.4 specification

### Debug Information

Enable debug logging to see TMX processing details:

```bash
# Set logging level for detailed TMX information
export LOG_LEVEL=DEBUG
python main.py --tmx data/sample.tmx --review
```

## Future Enhancements

Planned improvements include:
- **Semantic Matching**: Use embeddings for better fuzzy matching
- **TMX Export**: Save approved translations to TMX format
- **Multi-file Support**: Handle multiple TMX files simultaneously
- **Advanced Analytics**: Detailed TMX usage statistics and reporting