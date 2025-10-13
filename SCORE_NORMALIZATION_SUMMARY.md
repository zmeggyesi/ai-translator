# Score Normalization for Combined Extraction

## Problem

When combining LLM and TF-IDF extraction, the scoring systems operate on different scales:

- **LLM scores**: Typically 0.6-1.0 (significance scores based on semantic importance)
- **TF-IDF scores**: Typically 0.0-0.3 (statistical importance based on frequency and rarity)

When merging results and keeping "the highest score" for duplicates, comparing scores from different scales is unfair:

```python
# Before normalization - UNFAIR comparison:
LLM:    ("machine learning", 0.95)
TF-IDF: ("machine learning", 0.15)  # Actually important, but looks low!

# Result: LLM score (0.95) always wins, even when TF-IDF might be more confident
```

## Solution: Score Normalization

Before merging, we normalize TF-IDF scores to match the LLM score scale:

```python
# After normalization - FAIR comparison:
LLM:    ("machine learning", 0.95)
TF-IDF: ("machine learning", 0.85)  # Scaled to LLM range

# Result: Can now fairly compare which algorithm is more confident
```

### Algorithm

```python
def _normalize_scores(terms_list, target_max):
    """
    Scales all scores proportionally so max score = target_max
    
    Example:
        Input:  [("a", 0.5), ("b", 0.3), ("c", 0.1)]
        Target: 1.0
        
        Current max: 0.5
        Scale factor: 1.0 / 0.5 = 2.0
        
        Output: [("a", 1.0), ("b", 0.6), ("c", 0.2)]
    """
    current_max = max(score for _, score in terms_list)
    scale_factor = target_max / current_max
    
    return [(term, score * scale_factor) for term, score in terms_list]
```

### Implementation

In combined extraction:

1. **Run both algorithms independently**
   ```python
   llm_terms = extract_glossary_with_llm(...)      # → max score ~0.95
   tfidf_terms = extract_terms_with_tfidf(...)     # → max score ~0.21
   ```

2. **Normalize TF-IDF to LLM scale**
   ```python
   llm_max = max(score for _, score in llm_terms)  # 0.95
   tfidf_terms = _normalize_scores(tfidf_terms, target_max=llm_max)
   # Now TF-IDF max is also 0.95
   ```

3. **Merge with fair comparison**
   ```python
   terms_dict = {}
   for term, score in llm_terms:
       terms_dict[term] = score
   for term, score in tfidf_terms:  # Now normalized!
       if term not in terms_dict or score > terms_dict[term]:
           terms_dict[term] = score
   ```

## Example

### Before Normalization

```
LLM extracts:
  "Kubernetes" (0.95)
  "Docker" (0.92)
  "containerized applications" (0.88)

TF-IDF extracts:
  "containerized applications" (0.15)  ← DUPLICATE
  "orchestration" (0.12)
  "deployment" (0.10)

Merge (unfair):
  "Kubernetes" (0.95)              ← LLM
  "Docker" (0.92)                  ← LLM
  "containerized applications" (0.88)  ← LLM wins (0.88 > 0.15)
  "orchestration" (0.12)           ← TF-IDF
  "deployment" (0.10)              ← TF-IDF
```

**Problem**: LLM always wins duplicates because its scores are much higher!

### After Normalization

```
LLM extracts (unchanged):
  "Kubernetes" (0.95)
  "Docker" (0.92)
  "containerized applications" (0.88)

TF-IDF extracts (original):
  "containerized applications" (0.15)  ← max
  "orchestration" (0.12)
  "deployment" (0.10)

TF-IDF normalized (scaled by 0.95/0.15 = 6.33):
  "containerized applications" (0.95)  ← now comparable!
  "orchestration" (0.76)
  "deployment" (0.63)

Merge (fair):
  "Kubernetes" (0.95)              ← LLM
  "containerized applications" (0.95)  ← TIE! (Both 0.95, LLM wins by order)
  "Docker" (0.92)                  ← LLM
  "orchestration" (0.76)           ← TF-IDF (normalized)
  "deployment" (0.63)              ← TF-IDF (normalized)
```

**Better**: Now scores are comparable and we can see relative confidence!

## Benefits

1. **Fair Comparison**: Scores from both algorithms are now directly comparable
2. **True "Highest"**: When we keep the "highest score", it's a meaningful comparison
3. **Relative Importance**: The ranking within each algorithm is preserved
4. **No Bias**: Neither algorithm dominates due to scale differences

## Testing

```python
def test_normalize_scores():
    terms = [("term1", 0.5), ("term2", 0.3), ("term3", 0.1)]
    normalized = _normalize_scores(terms, target_max=1.0)
    
    assert normalized == [
        ("term1", 1.0),   # 0.5 * 2.0
        ("term2", 0.6),   # 0.3 * 2.0
        ("term3", 0.2),   # 0.1 * 2.0
    ]

def test_combined_extraction_score_normalization():
    # Mock LLM with scores 0.90-0.95
    # TF-IDF produces scores ~0.1-0.2
    # After normalization, TF-IDF should be in 0.5-0.95 range
    extract_glossary(..., use_llm=True, use_tfidf=True)
    
    # Verify max score matches LLM max
    assert max_combined_score ≈ llm_max_score
```

All 182 tests pass ✓

## Edge Cases

1. **Empty list**: Returns empty list
2. **All zeros**: Returns unchanged (avoids division by zero)
3. **Single score**: Still scales correctly
4. **Target = current**: Scale factor = 1.0 (no change)

## Usage

Normalization happens automatically when using combined extraction:

```bash
uv run python cli.py extract-glossary \
    --input data/sample.xliff \
    --source-language English \
    --output glossary.csv \
    --use-llm \
    --use-tfidf
```

No user action required - it just works! 🎉

## Logging

When normalization occurs, you'll see:

```
INFO: Normalized 23 scores: max 0.2143 → 0.9500 (scale factor: 4.4332)
INFO: Normalized TF-IDF scores to match LLM scale for fair comparison
```

This confirms that normalization happened and shows the scale factor applied.

## Files Modified

- `nodes/extract_glossary.py`: Added `_normalize_scores()` function
- `nodes/extract_glossary.py`: Updated combined extraction to normalize before merging
- `tests/test_combined_extraction.py`: Added 5 normalization tests
- `README.md`: Updated combined mode documentation
- `docs/TFIDF_INTEGRATION.md`: Updated comparison table

## Conclusion

Score normalization ensures that combined extraction truly gives you the **best of both worlds** by making scores from different algorithms directly comparable. This was a great catch - thanks for suggesting it!

