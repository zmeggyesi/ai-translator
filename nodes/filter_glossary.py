import logging
from rapidfuzz import process, fuzz
from state import TranslationState

# Configure logging
logger = logging.getLogger(__name__)

"""nodes.filter_glossary
+---------------------------------
This LangGraph *node* is responsible for reducing a potentially large, global
glossary down to the subset that is *actually* relevant to the piece of text
we are about to translate.

Why do we bother?
-----------------
Large glossaries slow down token-limited LLM calls because we need to embed the
whole glossary inside the prompt. By passing **only** the terms that appear in
the source content we:

1. Reduce prompt size → cheaper and faster calls.
2. Minimise the risk of the LLM hallucinating glossary terms that are not
   applicable to the current context.

Implementation details
----------------------
We use `rapidfuzz.process.extract` with the `WRatio` scorer, which is a robust
fuzzy-matching algorithm. A score cut-off of 75 has empirically been found to
strike a good balance between catching slight variations (e.g. "colour" vs
"color") while avoiding false positives.

The function returns a **partial** state update – exactly how LangGraph expects
node outputs to be shaped. Upstream nodes will merge this dict into the global
`TranslationState`.
"""

def filter_glossary(state: TranslationState) -> dict:
    """
    Filters the glossary to include only terms found in the original content.
    
    Parameters
    ----------
    state : TranslationState
        The current LangGraph state. We expect at least the following keys to
        be present:
        ``original_content`` – the string we are going to translate.
        ``glossary`` – a mapping from source-language terms to their desired
        translations.
    
    Returns
    -------
    dict
        Partial LangGraph state update containing a single key
        ``filtered_glossary``. This mimics the LangGraph convention that node
        outputs are merged into the global state.
    """
    logger.info("Filtering glossary...")
    # Extract inputs from the shared state -------------------------------
    original_content = state["original_content"]

    # ``state["glossary"]`` maps *term* → *preferred translation*.
    # We only need the keys for fuzzy matching.
    glossary_terms = list(state["glossary"].keys())
    
    # For each glossary term, check if it appears within the original content
    # using fuzzy matching. We want to find terms that appear IN the content,
    # not find which terms are similar TO the entire content.
    filtered_glossary = {}
    
    for term in glossary_terms:
        # Use extractOne to find the best match of this term within the content
        # This searches for the term within the content, not the other way around
        match = process.extractOne(
            term,
            [original_content],
            scorer=fuzz.partial_ratio,  # partial_ratio is better for finding substrings
            score_cutoff=75,
        )
        
        # If we found a good match, include this term in the filtered glossary
        if match is not None:
            filtered_glossary[term] = state["glossary"][term]
            logger.debug(f"Found term '{term}' in content with score {match[1]}")
    
    # Alternative approach: check each term against the content more directly
    # This approach tokenizes and uses word-level matching which can be more accurate
    additional_terms = {}
    content_lower = original_content.lower()
    
    for term in glossary_terms:
        term_lower = term.lower()
        
        # Direct substring match (most reliable)
        if term_lower in content_lower:
            additional_terms[term] = state["glossary"][term]
            logger.debug(f"Found exact term '{term}' in content")
        else:
            # Fuzzy match for individual words in the term
            term_words = term_lower.split()
            if len(term_words) > 1:
                # For multi-word terms, check if the words appear close together
                term_pattern = ' '.join(term_words)
                match = process.extractOne(
                    term_pattern,
                    [content_lower],
                    scorer=fuzz.partial_ratio,
                    score_cutoff=75,
                )
                if match is not None:
                    additional_terms[term] = state["glossary"][term]
                    logger.debug(f"Found multi-word term '{term}' in content with score {match[1]}")
    
    # Merge both approaches - prefer the more accurate one
    if additional_terms:
        filtered_glossary = additional_terms

    logger.info(f"Found {len(filtered_glossary)} relevant glossary terms.")
    logger.debug(f"Filtered glossary: {filtered_glossary}")

    # Return the partial state update for LangGraph to merge.
    return {"filtered_glossary": filtered_glossary} 