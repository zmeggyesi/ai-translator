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
    
    # Use RapidFuzz to fuzzy-match any glossary terms that appear in the
    # original text. The library returns a list of tuples in the form:
    #   (matched_term, similarity_score, index_in_glossary_terms)
    # ``score_cutoff`` ensures we only keep high-confidence matches.
    extracted_terms = process.extract(
        original_content,
        glossary_terms,
        scorer=fuzz.WRatio,
        score_cutoff=75,
    )

    # Re-assemble a mini glossary containing only the relevant terms. We use a
    # dict-comprehension for brevity.
    filtered_glossary = {
        term: state["glossary"][term]
        for term, score, index in extracted_terms
    }

    logger.info(f"Found {len(filtered_glossary)} relevant glossary terms.")
    logger.debug(f"Filtered glossary: {filtered_glossary}")

    # Return the partial state update for LangGraph to merge.
    return {"filtered_glossary": filtered_glossary} 