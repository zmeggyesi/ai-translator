from nodes.filter_glossary import filter_glossary

def test_filter_glossary_finds_terms():
    state = {
        "original_content": "This text talks about Python and LangGraph.",
        "glossary": {"Python": "Python 3", "LangGraph": "LG", "Unrelated": "Term"},
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "English",
        "messages": [],
    }
    result = filter_glossary(state)
    assert "Python" in result["filtered_glossary"]
    assert "LangGraph" in result["filtered_glossary"]
    assert "Unrelated" not in result["filtered_glossary"]
    assert len(result["filtered_glossary"]) == 2


def test_filter_glossary_chaos_engineering_case():
    """Test the specific case that was failing: chaos engineering should be found, not data backup."""
    state = {
        "original_content": "I will defer the detailed explanation of Chaos Engineering to this article, but in this session it's really about \"an approach to identify critical failures and get them fixed quickly\" – something similar to fire drills.",
        "glossary": {
            "chaos engineering": "カオス エンジニアリング",
            "data backup and retrieval technology": "データ バックアップおよび検索の技術",
            "application security": "アプリケーション セキュリティ",
            "fire drills": "火災訓練"
        },
        "style_guide": "formal",
        "source_language": "English", 
        "target_language": "Japanese",
        "messages": [],
    }
    result = filter_glossary(state)
    
    # Should find "chaos engineering" because it appears in the content
    assert "chaos engineering" in result["filtered_glossary"]
    assert result["filtered_glossary"]["chaos engineering"] == "カオス エンジニアリング"
    
    # Should NOT find "data backup and retrieval technology" 
    assert "data backup and retrieval technology" not in result["filtered_glossary"]
    
    # Could potentially find "fire drills" since it's mentioned
    # but not asserting this as it depends on fuzzy matching tolerance


def test_filter_glossary_case_insensitive():
    """Test that filtering works with different case variations."""
    state = {
        "original_content": "We use CHAOS ENGINEERING and Machine Learning in our systems.",
        "glossary": {
            "chaos engineering": "chaos testing",
            "machine learning": "ML",
            "artificial intelligence": "AI"
        },
        "style_guide": "formal",
        "source_language": "English",
        "target_language": "English", 
        "messages": [],
    }
    result = filter_glossary(state)
    
    # Should find terms despite case differences
    assert "chaos engineering" in result["filtered_glossary"]
    assert "machine learning" in result["filtered_glossary"]
    assert "artificial intelligence" not in result["filtered_glossary"] 