from nodes.filter_glossary import filter_glossary

def test_filter_glossary_finds_terms():
    state = {
        "original_content": "This text talks about Python and LangGraph.",
        "glossary": {"Python": "Python 3", "LangGraph": "LG", "Unrelated": "Term"},
        "style_guide": "formal",
        "target_language": "English",
        "messages": [],
    }
    result = filter_glossary(state)
    assert "Python" in result["filtered_glossary"]
    assert "LangGraph" in result["filtered_glossary"]
    assert "Unrelated" not in result["filtered_glossary"]
    assert len(result["filtered_glossary"]) == 2 