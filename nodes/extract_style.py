import logging
from pathlib import Path
from typing import List, Optional
import os
import re

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from nodes.tmx_loader import parse_tmx_file
from nodes.style_guide import infer_style_guide_from_tmx, rewrite_style_guide_template
from nodes.document_parsers import parse_document, create_document_entries, split_into_sentences

logger = logging.getLogger(__name__)


def _canonical(code: str) -> str:
    """Return base ISO language code (strip region / script variants)."""
    return code.lower().split("-")[0].split("_")[0]


def _flatten_target_segments(tmx_data: dict, source_language: str, target_language: str) -> List[dict]:
    """Return a list of *target* text segments for the requested language pair.

    Falls back gracefully to any segments that match the canonicalised
    language codes if no exact pair is found.
    """
    src_base = _canonical(source_language)
    tgt_base = _canonical(target_language)

    # 1) Exact key first -------------------------------------------------
    key = f"{src_base}->{tgt_base}"
    entries = tmx_data.get(key, [])

    # 2) Fallback: aggregate over keys whose canonicalised codes match ----
    if not entries:
        for pair_key, pair_entries in tmx_data.items():
            try:
                src, tgt = pair_key.split("->", 1)
            except ValueError:
                continue
            if _canonical(src) == src_base and _canonical(tgt) == tgt_base:
                entries.extend(pair_entries)

    # 3) Final fallback: ANY entry where target matches the requested ----
    if not entries:
        for pair_entries in tmx_data.values():
            for entry in pair_entries:
                if _canonical(entry.get("target_lang", "")) == tgt_base:
                    entries.append(entry)

    # Return the **full** entry dictionaries so that downstream consumers (e.g.
    # ``infer_style_guide_from_tmx``) have access to both *source* and *target*
    # as well as auxiliary metadata (usage_count, etc.).

    return [e for e in entries if isinstance(e, dict) and e.get("target")]


def _extract_text_from_html(html_content: str) -> str:
    """Extract readable text content from HTML.
    
    Args:
        html_content: Raw HTML content as a string
    
    Returns:
        Extracted plain text
    
    Raises:
        ImportError: If BeautifulSoup4 is not installed
    """
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator=' ')
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text


def _fetch_url_content(url: str, timeout: int = 10) -> str:
    """Fetch and extract text content from a URL.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Extracted text content
    
    Raises:
        ImportError: If requests is not installed
        requests.RequestException: If the request fails
    """
    if requests is None:
        raise ImportError("requests is required for URL fetching. Install with: pip install requests")
    
    logger.info(f"Fetching content from URL: {url}")
    
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; StyleExtractor/1.0)'
        })
        response.raise_for_status()
        
        # Extract text from HTML
        text = _extract_text_from_html(response.text)
        
        if not text.strip():
            logger.warning(f"No text content found in URL: {url}")
            return ""
        
        logger.info(f"Successfully extracted {len(text)} characters from {url}")
        return text
        
    except Exception as e:
        logger.error(f"Failed to fetch content from {url}: {e}")
        raise


def _load_urls_from_file(file_path: str) -> List[str]:
    """Load URLs from a text file (one URL per line).
    
    Args:
        file_path: Path to the file containing URLs
    
    Returns:
        List of valid URLs
    
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"URLs file not found: {file_path}")
    
    content = path.read_text(encoding='utf-8')
    
    # Extract URLs (one per line, ignoring empty lines and comments)
    urls = []
    for line in content.splitlines():
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        # Basic URL validation
        if line.startswith('http://') or line.startswith('https://'):
            urls.append(line)
        else:
            logger.warning(f"Skipping invalid URL: {line}")
    
    if not urls:
        raise ValueError(f"No valid URLs found in file: {file_path}")
    
    logger.info(f"Loaded {len(urls)} URLs from {file_path}")
    return urls


def extract_style_guide_from_urls(
    urls_file_path: str,
    source_language: str,
    output_path: str = "extracted_style.md",
    max_urls: Optional[int] = None,
    template_path: Optional[str] = None,
) -> str:
    """Generate a style guide from web content at URLs listed in a file.
    
    Args:
        urls_file_path: Path to a text file containing URLs (one per line)
        source_language: Language of the web content
        output_path: Path to write the style guide
        max_urls: Optional limit on number of URLs to process
        template_path: Optional path to a style guide template to rewrite based on the content
    
    Returns:
        The generated style guide as a markdown string
    
    Raises:
        FileNotFoundError: If the URLs file doesn't exist
        ValueError: If no valid URLs are found or no content is extracted
        ImportError: If required dependencies are not installed
    """
    # Load URLs from file
    urls = _load_urls_from_file(urls_file_path)
    
    if max_urls and max_urls > 0:
        urls = urls[:max_urls]
        logger.info(f"Limiting to first {max_urls} URLs")
    
    # Fetch and aggregate content from all URLs
    all_text = []
    successful_urls = 0
    
    for url in urls:
        try:
            text = _fetch_url_content(url)
            if text:
                all_text.append(text)
                successful_urls += 1
        except Exception as e:
            logger.warning(f"Skipping URL {url} due to error: {e}")
            continue
    
    if not all_text:
        raise ValueError(f"Failed to extract content from any URLs in {urls_file_path}")
    
    logger.info(f"Successfully extracted content from {successful_urls}/{len(urls)} URLs")
    
    # Combine all text
    combined_text = "\n\n".join(all_text)
    
    # Split into sentences
    sentences = split_into_sentences(combined_text, source_language)
    
    if not sentences:
        raise ValueError(f"No sentences found in content from URLs in {urls_file_path}")
    
    logger.info(f"Extracted {len(sentences)} sentences from web content")
    
    # Create TMX-like entries for the style guide generation
    entries = create_document_entries(sentences, source_language)
    
    # Create a TMX memory structure compatible with existing style guide logic
    tmx_memory = {
        "entries": entries,
        "language_pair": f"{source_language}->{source_language}",
        "url_source": True,  # Flag to indicate this is from URL parsing
        "urls_file": urls_file_path,
        "urls_count": len(urls),
        "successful_urls": successful_urls
    }
    
    # Use template rewriting if template is provided, otherwise generate new guide
    if template_path:
        logger.info("Rewriting template based on URL content: %s", template_path)
        style_guide_md = rewrite_style_guide_template(tmx_memory, template_path)
    else:
        style_guide_md = infer_style_guide_from_tmx(tmx_memory, use_llm=True)
    
    if not style_guide_md:
        raise ValueError("Failed to generate style guide from URL content.")

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s", out_path)

    return style_guide_md


def extract_style_guide_from_document(
    document_path: str,
    file_type: str,
    source_language: str,
    output_path: str = "extracted_style.md",
    template_path: Optional[str] = None,
) -> str:
    """Generate a style guide from a document file (PDF, DOCX, DOC).

    Args:
        document_path: Path to the document file
        file_type: Type of document ('pdf', 'docx', 'doc')
        source_language: Language of the document
        output_path: Path to write the style guide
        template_path: Optional path to a style guide template to rewrite based on the content

    Returns:
        The generated style guide as a markdown string

    Raises:
        FileNotFoundError: If the document file doesn't exist
        ValueError: If the document cannot be parsed or no content is found
        ImportError: If required dependencies are not installed
    """
    doc_path = Path(document_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"Document file not found: {document_path}")

    logger.info("Parsing document file for style extraction → %s", doc_path)
    
    # Parse the document to extract sentences
    sentences = parse_document(document_path, file_type, source_language)
    
    if not sentences:
        raise ValueError(f"No sentences found in document: {document_path}")
    
    # Create TMX-like entries for the style guide generation
    entries = create_document_entries(sentences, source_language)
    
    # Create a TMX memory structure compatible with existing style guide logic
    tmx_memory = {
        "entries": entries,
        "language_pair": f"{source_language}->{source_language}",
        "document_source": True,  # Flag to indicate this is from document parsing
        "document_path": document_path,
        "document_type": file_type
    }

    # Use template rewriting if template is provided, otherwise generate new guide
    if template_path:
        logger.info("Rewriting template based on document content: %s", template_path)
        style_guide_md = rewrite_style_guide_template(tmx_memory, template_path)
    else:
        style_guide_md = infer_style_guide_from_tmx(tmx_memory, use_llm=True)
    
    if not style_guide_md:
        raise ValueError("Failed to generate style guide from document sentences.")

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s", out_path)

    return style_guide_md


def extract_style_guide(
    tmx_path: str,
    source_language: str,
    target_language: str,
    output_path: str = "extracted_style.md",
    template_path: Optional[str] = None,
) -> str:
    """Generate a **comprehensive** style guide using TMX data.

    The function now follows a *hybrid* strategy:

    1. **Statistical Heuristics** – Fast, deterministic metrics such as
       average sentence length, punctuation frequency, and exclamation /
       question usage.  These numbers are included verbatim in the prompt so
       the LLM can reason with concrete evidence.

    2. **LLM Analysis** – If an `OPENAI_API_KEY` is configured the function
       uses `ChatOpenAI` (or the mock equivalent in the test-suite) to analyse
       stylistic patterns, domain-specific terminology, tone / formality, and
       brand voice.  The LLM returns a **Markdown** document that becomes the
       final style guide.

    3. **Graceful Fallback** – When no API key is available (e.g. in CI) we
       fall back to a purely heuristic guide similar to the previous
       implementation, ensuring offline determinism for tests.

    Args:
        tmx_path: Path to TMX file
        source_language: Source language
        target_language: Target language
        output_path: Path to write the style guide
        template_path: Optional path to a style guide template to rewrite based on the content
    """
    tmx_file = Path(tmx_path)
    if not tmx_file.exists():
        raise FileNotFoundError(f"TMX file not found: {tmx_path}")

    logger.info("Parsing TMX file for style extraction → %s", tmx_file)
    tmx_data = parse_tmx_file(str(tmx_file))

    # Leverage the shared TMX inference utility which already supports LLM + fallback
    tmx_memory = {
        "entries": _flatten_target_segments(tmx_data, source_language, target_language),
        "language_pair": f"{source_language}->{target_language}",
    }

    # Use template rewriting if template is provided, otherwise generate new guide
    if template_path:
        logger.info("Rewriting template based on TMX content: %s", template_path)
        style_guide_md = rewrite_style_guide_template(tmx_memory, template_path)
    else:
        style_guide_md = infer_style_guide_from_tmx(tmx_memory, use_llm=True)
    
    if not style_guide_md:
        raise ValueError("Failed to generate style guide from TMX entries.")

    # Write out ----------------------------------------------------------
    out_path = Path(output_path)
    out_path.write_text(style_guide_md, encoding="utf-8")
    logger.info("Style guide written → %s", out_path)

    return style_guide_md


def extract_style_guide_unified(
    file_path: str,
    file_type: str,
    source_language: str,
    target_language: Optional[str] = None,
    output_path: str = "extracted_style.md",
    max_urls: Optional[int] = None,
    template_path: Optional[str] = None,
) -> str:
    """Unified style guide extraction that handles TMX, document files, and URL lists.

    Args:
        file_path: Path to the input file
        file_type: Type of file ('tmx', 'pdf', 'docx', 'doc', 'urls')
        source_language: Source language
        target_language: Target language (required for TMX, optional for documents and URLs)
        output_path: Output path for the style guide
        max_urls: Optional limit on number of URLs to process (only for 'urls' file type)
        template_path: Optional path to a style guide template to rewrite based on the content

    Returns:
        The generated style guide as a markdown string

    Raises:
        ValueError: If file_type is not supported or required parameters are missing
        ImportError: If required dependencies are not installed
    """
    file_type = file_type.lower()
    
    if file_type == 'tmx':
        if target_language is None:
            raise ValueError("Target language is required for TMX files")
        return extract_style_guide(file_path, source_language, target_language, output_path, template_path)
    
    elif file_type in ['pdf', 'docx', 'doc']:
        # For document files, we use the source language as both source and target
        # since we're extracting style from monolingual content
        return extract_style_guide_from_document(file_path, file_type, source_language, output_path, template_path)
    
    elif file_type == 'urls':
        # For URL lists, fetch and aggregate content from web pages
        return extract_style_guide_from_urls(file_path, source_language, output_path, max_urls, template_path)
    
    else:
        raise ValueError(f"Unsupported file type: {file_type}. Supported types: tmx, pdf, docx, doc, urls")