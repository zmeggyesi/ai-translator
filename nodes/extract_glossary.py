import csv
import json
import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import List, Tuple, Set, Optional, Any, Dict

import numpy as np
import spacy
from spacy.lang.en import STOP_WORDS as EN_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompt_values import PromptValue
from langchain_openai import ChatOpenAI

from nodes.tmx_loader import parse_tmx_file
from nodes.document_parsers import parse_xliff
from nodes.utils import extract_response_content

logger = logging.getLogger(__name__)

# Cache for loaded SpaCy models
_SPACY_MODELS: Dict[str, Any] = {}

# Mapping of language names to SpaCy model names
LANGUAGE_TO_SPACY_MODEL = {
    "english": "en_core_web_sm",
    "spanish": "es_core_news_sm",
    "french": "fr_core_news_sm",
    "german": "de_core_news_sm",
    "italian": "it_core_news_sm",
    "portuguese": "pt_core_news_sm",
    "dutch": "nl_core_news_sm",
    "greek": "el_core_news_sm",
    "norwegian": "nb_core_news_sm",
    "polish": "pl_core_news_sm",
    "romanian": "ro_core_news_sm",
    "russian": "ru_core_news_sm",
    "chinese": "zh_core_web_sm",
    "japanese": "ja_core_news_sm",
    "danish": "da_core_news_sm",
    "finnish": "fi_core_news_sm",
    "swedish": "sv_core_news_sm",
    "catalan": "ca_core_news_sm",
}

# Fallback stopwords (English) if SpaCy model is not available
FALLBACK_STOPWORDS: Set[str] = set(EN_STOP_WORDS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_spacy_model(language: str) -> Optional[Any]:
    """Load SpaCy model for the given language.
    
    Args:
        language: Language name (e.g., "English", "Spanish")
    
    Returns:
        SpaCy language model or None if not available
    """
    lang_key = language.lower()
    
    # Check cache first
    if lang_key in _SPACY_MODELS:
        return _SPACY_MODELS[lang_key]
    
    # Try to load the model
    model_name = LANGUAGE_TO_SPACY_MODEL.get(lang_key)
    if not model_name:
        logger.warning(f"No SpaCy model mapping found for language: {language}")
        return None
    
    try:
        nlp = spacy.load(model_name)
        _SPACY_MODELS[lang_key] = nlp
        logger.info(f"Loaded SpaCy model: {model_name} for language: {language}")
        return nlp
    except OSError:
        logger.warning(
            f"SpaCy model '{model_name}' not found. "
            f"Install it with: python -m spacy download {model_name}"
        )
        _SPACY_MODELS[lang_key] = None
        return None


def _get_stopwords(language: str) -> Set[str]:
    """Get stopwords for the given language from SpaCy.
    
    Args:
        language: Language name (e.g., "English", "Spanish")
    
    Returns:
        Set of stopwords for the language
    """
    nlp = _get_spacy_model(language)
    
    if nlp is not None:
        stopwords = nlp.Defaults.stop_words
        logger.info(f"Using {len(stopwords)} stopwords from SpaCy model for {language}")
        return stopwords
    
    # Fallback to English stopwords
    logger.info(f"Using fallback English stopwords ({len(FALLBACK_STOPWORDS)} words)")
    return FALLBACK_STOPWORDS

def _canonical(code: str) -> str:
    return code.lower().split("-")[0].split("_")[0]


def _tokenise(text: str) -> List[str]:
    """A naive tokenizer that keeps diacritics and apostrophes."""
    return re.findall(r"[A-Za-zÀ-ÿ\u00f1\u00d1'-]+", text)


# ---------------------------------------------------------------------------
# TMX-based extraction
# ---------------------------------------------------------------------------

def _collect_tmx_entries(
    tmx_data: dict, source_language: str, target_language: str
) -> List[Tuple[str, str]]:
    src_base = _canonical(source_language)
    tgt_base = _canonical(target_language)
    entries: List[Tuple[str, str]] = []

    # 1) Exact key --------------------------------------------------------
    key = f"{src_base}->{tgt_base}"
    for entry in tmx_data.get(key, []):
        entries.append((entry["source"], entry["target"]))

    # 2) Fallback: aggregate over canonicalised pairs --------------------
    if not entries:
        for pair_key, pair_entries in tmx_data.items():
            try:
                src, tgt = pair_key.split("->", 1)
            except ValueError:
                continue
            if _canonical(src) == src_base and _canonical(tgt) == tgt_base:
                for entry in pair_entries:
                    entries.append((entry["source"], entry["target"]))

    return entries


def extract_glossary_from_tmx(
    tmx_path: str, source_language: str, target_language: str, max_len: int = 3
) -> List[Tuple[str, str]]:
    """Extract short source-target pairs from a TMX file as glossary terms."""
    if not Path(tmx_path).exists():
        raise FileNotFoundError(f"TMX file not found: {tmx_path}")

    logger.info("Parsing TMX for glossary extraction → %s", tmx_path)
    tmx_data = parse_tmx_file(tmx_path)
    pairs = _collect_tmx_entries(tmx_data, source_language, target_language)

    seen: Set[str] = set()
    glossary: List[Tuple[str, str]] = []

    for src, tgt in pairs:
        if 1 <= len(src.split()) <= max_len:
            key = src.lower()
            if key not in seen:
                seen.add(key)
                glossary.append((src.strip(), tgt.strip()))
    logger.info("Collected %d glossary term pairs from TMX", len(glossary))
    return glossary


# ---------------------------------------------------------------------------
# Monolingual extraction
# ---------------------------------------------------------------------------

def extract_terms_from_text(
    text: str, top_n: int = 50, language: str = "English"
) -> List[str]:
    """Extract terms from text using frequency analysis.
    
    Args:
        text: Input text
        top_n: Number of top terms to return
        language: Language of the text for stopword filtering
    
    Returns:
        List of top terms by frequency
    """
    stopwords = _get_stopwords(language)
    tokens = [tok.lower() for tok in _tokenise(text)]
    tokens = [tok for tok in tokens if tok not in stopwords and len(tok) > 3]
    freq = Counter(tokens)
    return [term for term, _ in freq.most_common(top_n)]


def _preprocess_for_tfidf(text: str, language: str) -> str:
    """Preprocess text for TF-IDF analysis.
    
    Args:
        text: Input text
        language: Language for stopword filtering
    
    Returns:
        Preprocessed text with stopwords removed
    """
    stopwords = _get_stopwords(language)
    tokens = [tok.lower() for tok in _tokenise(text)]
    tokens = [tok for tok in tokens if tok not in stopwords and len(tok) > 3]
    return " ".join(tokens)


def extract_terms_with_tfidf(
    text_segments: List[str],
    top_n: int = 50,
    language: str = "English",
    max_ngram_size: int = 3,
    min_df: int = 1,
) -> List[Tuple[str, float]]:
    """Extract terms from multiple text segments using TF-IDF analysis.
    
    TF-IDF (Term Frequency-Inverse Document Frequency) identifies terms that are
    important within documents while filtering out common terms that appear across
    many documents. Each text segment is treated as a separate document.
    
    Args:
        text_segments: List of text segments (each treated as a document)
        top_n: Number of top terms to return
        language: Language for stopword filtering
        max_ngram_size: Maximum n-gram size (1=unigrams, 2=bigrams, 3=trigrams, etc.)
        min_df: Minimum document frequency (terms must appear in at least this many documents)
    
    Returns:
        List of tuples containing (term, tfidf_score), sorted by score (highest first)
    
    Examples:
        >>> segments = ["Machine learning is powerful", "Deep learning is advanced"]
        >>> terms = extract_terms_with_tfidf(segments, top_n=5, max_ngram_size=2)
        >>> # Returns terms like: [("machine learning", 0.85), ("deep learning", 0.82), ...]
    """
    if not text_segments:
        logger.warning("No text segments provided for TF-IDF extraction")
        return []
    
    if len(text_segments) < 2:
        logger.warning(
            "TF-IDF works best with multiple documents. "
            "Consider using frequency-based extraction for single documents."
        )
    
    logger.info(f"Extracting terms using TF-IDF from {len(text_segments)} text segments")
    
    # Preprocess all segments
    preprocessed_segments = [
        _preprocess_for_tfidf(segment, language) for segment in text_segments
    ]
    
    # Filter out empty segments
    preprocessed_segments = [seg for seg in preprocessed_segments if seg.strip()]
    
    if not preprocessed_segments:
        logger.warning("All segments became empty after preprocessing")
        return []
    
    logger.info(f"Preprocessed {len(preprocessed_segments)} non-empty segments")
    
    # Collect terms across all n-gram sizes
    all_terms: Dict[str, float] = {}
    
    for n in range(1, max_ngram_size + 1):
        logger.info(f"Processing {n}-grams...")
        
        try:
            # Create TF-IDF vectorizer for this n-gram size
            vectorizer = TfidfVectorizer(
                ngram_range=(n, n),
                min_df=min_df,
                max_df=0.95,  # Ignore terms that appear in >95% of documents
                lowercase=True,
                token_pattern=r'\b\w+\b',
            )
            
            # Fit and transform the documents
            tfidf_matrix = vectorizer.fit_transform(preprocessed_segments)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calculate average TF-IDF score across all documents for each term
            # This gives us a single importance score per term
            avg_tfidf_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
            
            # Store terms with their scores
            for term, score in zip(feature_names, avg_tfidf_scores):
                if score > 0:  # Only include terms with non-zero scores
                    # If term already exists, keep the higher score
                    if term not in all_terms or score > all_terms[term]:
                        all_terms[term] = score
            
            logger.info(f"Found {len(feature_names)} {n}-grams")
            
        except ValueError as e:
            logger.warning(f"Could not extract {n}-grams: {e}")
            continue
    
    if not all_terms:
        logger.warning("No terms extracted with TF-IDF")
        return []
    
    # Sort by TF-IDF score (highest first) and return top N
    sorted_terms = sorted(all_terms.items(), key=lambda x: (-x[1], x[0]))
    result = sorted_terms[:top_n]
    
    logger.info(f"Extracted {len(result)} terms using TF-IDF")
    
    return result


# ---------------------------------------------------------------------------
# LLM-based glossary extraction
# ---------------------------------------------------------------------------

GLOSSARY_EXTRACTION_PROMPT = """You are a terminology extraction expert. Your task is to identify significant words or phrases from the provided text that should be included in a translation glossary.

Focus on:
- Domain-specific terms and technical vocabulary
- Product names, brand names, proper nouns, and other entity names
- Key concepts and recurring phrases
- Terms that require consistent translation
- Industry jargon and specialized terminology

Exclude:
- Common words and stop words
- Generic terms without specific domain meaning
- Articles, prepositions, and conjunctions

Text to analyze:
{text}

Source language: {source_language}

Please identify and extract the most significant terms and phrases. Return a maximum of {max_terms} terms, prioritizing the most important and frequently occurring domain-specific terminology. Synonyms and terms related to the same concept should be included and not counted against the {max_terms} limit.

For each term, assign a significance score from 0.0 to 1.0 based on:
- **1.0**: Critical domain-specific terms (e.g., product names, technical jargon, key concepts)
- **0.8-0.9**: Important specialized terms that require consistent translation
- **0.6-0.7**: Useful domain terms that appear frequently
- **0.4-0.5**: Moderately important terms
- **0.1-0.3**: Less critical but potentially useful terms

Only include a term in your final picks if its significance score is greater than {min_significance}.

Return your response as a JSON array of objects, where each object has "term" and "significance" fields.

Example format:
[
  {{"term": "API authentication", "significance": 0.95}},
  {{"term": "database connection", "significance": 0.85}},
  {{"term": "user credentials", "significance": 0.75}}
]

Your response (JSON array only):"""


def _chunk_text(segments: List[str], max_tokens: int = 128000) -> List[str]:
    """Split segments into chunks that fit within token limits.
    
    Args:
        segments: List of text segments
        max_tokens: Maximum tokens per chunk (rough estimate: ~4 chars = 1 token)
    
    Returns:
        List of text chunks
    """
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Rough estimate: 4 characters per token
    max_chars = max_tokens * 4
    
    for segment in segments:
        segment_length = len(segment)
        
        if current_length + segment_length > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        current_chunk.append(segment)
        current_length += segment_length + 1  # +1 for newline
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks


def extract_glossary_with_llm(
    text_segments: List[str],
    source_language: str,
    max_chunks: Optional[int] = None,
    max_terms_per_chunk: int = 50,
    min_significance: float = 0.6,
) -> List[Tuple[str, float]]:
    """Extract glossary terms from text using LLM analysis.
    
    Args:
        text_segments: List of text segments to analyze
        source_language: Source language of the text
        max_chunks: Maximum number of chunks to process (None = all)
        max_terms_per_chunk: Maximum number of terms to extract per chunk (default: 50)
        min_significance: Minimum significance score to include a term (default: 0.6)
            Significance levels:
            - 1.0: Critical domain-specific terms (product names, technical jargon, key concepts)
            - 0.8-0.9: Important specialized terms requiring consistent translation
            - 0.6-0.7: Useful domain terms appearing frequently
            - 0.4-0.5: Moderately important terms
            - 0.1-0.3: Less critical but potentially useful terms
    
    Returns:
        List of tuples containing (term, significance_score), sorted by significance
    
    Raises:
        ValueError: If OpenAI API key is not set
        RuntimeError: If LLM call fails
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set. Cannot perform LLM-based glossary extraction.")
    
    logger.info(f"Extracting glossary terms from {len(text_segments)} segments using LLM")
    
    # Chunk the text to fit within token limits
    chunks = _chunk_text(text_segments)
    
    if max_chunks:
        chunks = chunks[:max_chunks]
    
    logger.info(f"Processing {len(chunks)} text chunk(s)")
    
    # Store terms with their highest significance score
    terms_dict: Dict[str, float] = {}
    
    prompt = ChatPromptTemplate.from_template(GLOSSARY_EXTRACTION_PROMPT)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"Processing chunk {i}/{len(chunks)}")
        
        try:
            # Prepare the prompt
            prompt_messages: PromptValue = prompt.invoke({
                "text": chunk,
                "source_language": source_language,
                "max_terms": max_terms_per_chunk,
                "min_significance": min_significance,
            })
            
            # Call the LLM
            if hasattr(llm, "invoke"):
                response: Any = llm.invoke(prompt_messages)
            elif hasattr(llm, "__ror__"):
                # Fallback for mocked implementations in tests
                chain: Any = llm.__ror__(prompt_messages)  # type: ignore[operator]
                if hasattr(chain, "invoke"):
                    response = chain.invoke(None)  # type: ignore[assignment]
                else:
                    raise TypeError(
                        "Fallback glossary extraction chain produced by mocked LLM does not "
                        "expose an 'invoke' method as expected."
                    )
            else:
                raise TypeError(
                    "The provided language model must expose either an 'invoke' "
                    "method or support piping via the '|' operator."
                )
            
            # Extract and parse the response
            content = extract_response_content(response)
            
            # Try to parse as JSON
            try:
                terms_data = json.loads(content)
                if isinstance(terms_data, list):
                    for item in terms_data:
                        if isinstance(item, dict) and "term" in item and "significance" in item:
                            term = item["term"].strip()
                            significance = float(item["significance"])
                            # Filter by minimum significance threshold
                            if term and significance > min_significance:
                                # Keep the highest significance score for each term
                                if term not in terms_dict or significance > terms_dict[term]:
                                    terms_dict[term] = significance
                        elif isinstance(item, str):
                            # Fallback for old format (plain strings)
                            term = item.strip()
                            if term:
                                terms_dict[term] = 0.5  # Default significance
                else:
                    logger.warning(f"LLM response was not a list: {content}")
            except json.JSONDecodeError:
                # Try to extract JSON array from the response
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        terms_data = json.loads(json_match.group())
                        if isinstance(terms_data, list):
                            for item in terms_data:
                                if isinstance(item, dict) and "term" in item and "significance" in item:
                                    term = item["term"].strip()
                                    significance = float(item["significance"])
                                    # Filter by minimum significance threshold
                                    if term and significance > min_significance:
                                        if term not in terms_dict or significance > terms_dict[term]:
                                            terms_dict[term] = significance
                                elif isinstance(item, str):
                                    term = item.strip()
                                    if term:
                                        terms_dict[term] = 0.5
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse JSON from LLM response for chunk {i}")
                else:
                    logger.warning(f"No JSON array found in LLM response for chunk {i}")
        
        except Exception as exc:
            logger.error(f"Error processing chunk {i}: {exc}")
            continue
    
    logger.info(f"Extracted {len(terms_dict)} unique terms from {len(chunks)} chunk(s)")
    
    # Sort by significance (highest first), then alphabetically
    sorted_terms = sorted(terms_dict.items(), key=lambda x: (-x[1], x[0]))
    
    return sorted_terms


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def write_glossary_csv(rows: List[Tuple[str, str, Optional[float]]], output_path: str):
    """Write glossary to CSV file.
    
    Args:
        rows: List of tuples containing (term, translation, significance)
        output_path: Path to output CSV file
    """
    out_file = Path(output_path)
    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Check if we have significance scores
        has_significance = any(len(row) > 2 and row[2] is not None for row in rows)
        
        if has_significance:
            writer.writerow(["term", "translation", "significance"])
        else:
            writer.writerow(["term", "translation"])
        
        writer.writerows(rows)
    logger.info("Glossary written → %s", out_file)


def extract_glossary(
    *,
    tmx: Optional[str] = None,
    input_file: Optional[str] = None,
    file_type: Optional[str] = None,
    source_language: str = "English",
    target_language: str = "Spanish",
    output: str = "glossary.csv",
    use_llm: bool = False,
    use_tfidf: bool = False,
    max_terms: int = 50,
    min_significance: float = 0.6,
    max_ngram_size: int = 3,
):
    """Extract glossary terms from various file formats.
    
    Args:
        tmx: Path to TMX file (for bilingual extraction)
        input_file: Path to input file (for monolingual extraction)
        file_type: Type of input file ('text', 'xliff')
        source_language: Source language
        target_language: Target language
        output: Output CSV file path
        use_llm: Whether to use LLM for term extraction (for non-TMX files)
        use_tfidf: Whether to use TF-IDF for term extraction (for non-TMX files with multiple segments)
        max_terms: Maximum number of terms to extract per chunk (default: 50)
        min_significance: Minimum significance score threshold (default: 0.6)
            Only applies to LLM-based extraction. Significance levels:
            - 1.0: Critical domain-specific terms (product names, technical jargon)
            - 0.8-0.9: Important specialized terms requiring consistent translation
            - 0.6-0.7: Useful domain terms appearing frequently
            - 0.4-0.5: Moderately important terms
            - 0.1-0.3: Less critical but potentially useful terms
            Lower values include more terms; higher values are more selective.
        max_ngram_size: Maximum n-gram size for TF-IDF extraction (default: 3)
            1=unigrams only, 2=unigrams+bigrams, 3=unigrams+bigrams+trigrams
    
    Note:
        - If both use_llm and use_tfidf are True, BOTH algorithms run and results are merged
        - When merging, the union of terms is returned with the highest score for duplicates
        - TF-IDF works best with multiple text segments (e.g., XLIFF files)
        - For single text files, TF-IDF is less effective than frequency-based extraction
    """

    if not tmx and not input_file:
        raise ValueError("Either a TMX file or an input file must be provided.")

    if tmx:
        terms_pairs = extract_glossary_from_tmx(tmx, source_language, target_language)
        # TMX extraction returns (source, target) pairs without significance scores
        terms = [(src, tgt, None) for src, tgt in terms_pairs]
        write_glossary_csv(terms, output)
    else:
        # Type checker: input_file is guaranteed not None in this branch
        input_path = Path(str(input_file))
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Determine file type if not specified
        if not file_type:
            if input_path.suffix.lower() in ['.xlf', '.xliff']:
                file_type = 'xliff'
            else:
                file_type = 'text'
        
        # Extract text based on file type
        if file_type == 'xliff':
            logger.info("Processing XLIFF file for glossary extraction")
            text_segments = parse_xliff(str(input_path), extract_target=False)
            
            # Check if we should run both LLM and TF-IDF
            if use_llm and use_tfidf:
                logger.info("Using BOTH LLM and TF-IDF extraction for XLIFF content (union of results)")
                
                # Run LLM extraction
                llm_terms = extract_glossary_with_llm(
                    text_segments, 
                    source_language,
                    max_terms_per_chunk=max_terms,
                    min_significance=min_significance
                )
                
                # Run TF-IDF extraction
                tfidf_terms = extract_terms_with_tfidf(
                    text_segments,
                    top_n=max_terms,
                    language=source_language,
                    max_ngram_size=max_ngram_size
                )
                
                # Merge results: union of terms, keeping highest score for duplicates
                terms_dict: Dict[str, float] = {}
                for term, score in llm_terms:
                    terms_dict[term] = score
                for term, score in tfidf_terms:
                    if term not in terms_dict or score > terms_dict[term]:
                        terms_dict[term] = score
                
                # Sort by score (highest first), then alphabetically
                sorted_terms = sorted(terms_dict.items(), key=lambda x: (-x[1], x[0]))
                logger.info(f"Merged results: {len(llm_terms)} LLM terms + {len(tfidf_terms)} TF-IDF terms = {len(sorted_terms)} unique terms")
                
                # Convert to CSV format
                terms = [(term, "", score) for term, score in sorted_terms]
                
            elif use_llm:
                logger.info("Using LLM-based extraction for XLIFF content")
                terms_with_scores = extract_glossary_with_llm(
                    text_segments, 
                    source_language,
                    max_terms_per_chunk=max_terms,
                    min_significance=min_significance
                )
                # Convert to CSV format: (term, translation, significance)
                terms = [(term, "", significance) for term, significance in terms_with_scores]
            elif use_tfidf:
                logger.info("Using TF-IDF extraction for XLIFF content")
                terms_with_scores = extract_terms_with_tfidf(
                    text_segments,
                    top_n=max_terms,
                    language=source_language,
                    max_ngram_size=max_ngram_size
                )
                # Convert to CSV format: (term, translation, tfidf_score)
                terms = [(term, "", score) for term, score in terms_with_scores]
            else:
                # Combine segments and use frequency-based extraction
                combined_text = "\n".join(text_segments)
                terms_list = extract_terms_from_text(
                    combined_text, top_n=max_terms, language=source_language
                )
                # No significance scores for frequency-based extraction
                terms = [(term, "", None) for term in terms_list]
        else:
            # Plain text file
            txt = input_path.read_text(encoding="utf-8")
            
            # Check if we should run both LLM and TF-IDF
            if use_llm and use_tfidf:
                logger.info("Using BOTH LLM and TF-IDF extraction for text content (union of results)")
                
                # Run LLM extraction
                llm_terms = extract_glossary_with_llm(
                    [txt], 
                    source_language,
                    max_terms_per_chunk=max_terms,
                    min_significance=min_significance
                )
                
                # Run TF-IDF extraction (split into paragraphs)
                paragraphs = [p.strip() for p in txt.split('\n\n') if p.strip()]
                if not paragraphs:
                    paragraphs = [p.strip() for p in txt.split('\n') if p.strip()]
                
                logger.info(f"Split text into {len(paragraphs)} paragraphs for TF-IDF")
                
                tfidf_terms = extract_terms_with_tfidf(
                    paragraphs,
                    top_n=max_terms,
                    language=source_language,
                    max_ngram_size=max_ngram_size
                )
                
                # Merge results: union of terms, keeping highest score for duplicates
                terms_dict: Dict[str, float] = {}
                for term, score in llm_terms:
                    terms_dict[term] = score
                for term, score in tfidf_terms:
                    if term not in terms_dict or score > terms_dict[term]:
                        terms_dict[term] = score
                
                # Sort by score (highest first), then alphabetically
                sorted_terms = sorted(terms_dict.items(), key=lambda x: (-x[1], x[0]))
                logger.info(f"Merged results: {len(llm_terms)} LLM terms + {len(tfidf_terms)} TF-IDF terms = {len(sorted_terms)} unique terms")
                
                # Convert to CSV format
                terms = [(term, "", score) for term, score in sorted_terms]
                
            elif use_llm:
                logger.info("Using LLM-based extraction for text content")
                terms_with_scores = extract_glossary_with_llm(
                    [txt], 
                    source_language,
                    max_terms_per_chunk=max_terms,
                    min_significance=min_significance
                )
                # Convert to CSV format: (term, translation, significance)
                terms = [(term, "", significance) for term, significance in terms_with_scores]
            elif use_tfidf:
                logger.info("Using TF-IDF extraction for text content")
                # Split text into paragraphs for TF-IDF analysis
                # Each paragraph becomes a separate document
                paragraphs = [p.strip() for p in txt.split('\n\n') if p.strip()]
                if not paragraphs:
                    # Fallback: split by single newline
                    paragraphs = [p.strip() for p in txt.split('\n') if p.strip()]
                
                logger.info(f"Split text into {len(paragraphs)} paragraphs for TF-IDF")
                
                terms_with_scores = extract_terms_with_tfidf(
                    paragraphs,
                    top_n=max_terms,
                    language=source_language,
                    max_ngram_size=max_ngram_size
                )
                # Convert to CSV format: (term, translation, tfidf_score)
                terms = [(term, "", score) for term, score in terms_with_scores]
            else:
                terms_list = extract_terms_from_text(
                    txt, top_n=max_terms, language=source_language
                )
                # No significance scores for frequency-based extraction
                terms = [(term, "", None) for term in terms_list]
        
        write_glossary_csv(terms, output)