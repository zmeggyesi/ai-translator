#!/usr/bin/env python3
"""
TMX Integration Demo
====================

Demonstrates the TMX (Translation Memory eXchange) functionality 
integrated into the AI translator project.
"""

from nodes.tmx_loader import load_tmx_memory, find_tmx_matches
from nodes.translate_content import translate_content
from nodes.review_tmx_faithfulness import evaluate_tmx_faithfulness
from nodes.review_aggregator import aggregate_review_scores

def demo_tmx_functionality():
    """Demonstrates TMX loading, translation, and review"""
    
    print("🌍 TMX Integration Demo")
    print("=" * 50)
    
    # Step 1: Load TMX memory
    print("\n📚 Step 1: Loading TMX memory...")
    state = {
        "source_language": "en",
        "target_language": "fr",
        "original_content": "Hello world",
        "style_guide": "Use formal language",
        "filtered_glossary": {}
    }
    
    tmx_result = load_tmx_memory(state, "data/sample.tmx")
    state.update(tmx_result)
    
    if "tmx_memory" in state and state["tmx_memory"]:
        entries = state["tmx_memory"].get("entries", [])
        print(f"✅ Loaded {len(entries)} TMX entries for en->fr")
        if entries:
            print("📝 Sample entries:")
            for i, entry in enumerate(entries[:3], 1):
                print(f"   {i}. '{entry['source']}' → '{entry['target']}'")
    else:
        print("❌ No TMX entries loaded")
        return
    
    # Step 2: Demonstrate exact matching
    print("\n🎯 Step 2: Testing exact TMX matching...")
    exact_matches = find_tmx_matches("Hello world", entries, threshold=100.0)
    
    if exact_matches:
        print(f"✅ Found exact match!")
        match = exact_matches[0]
        print(f"   Source: '{match['source']}'")
        print(f"   Target: '{match['target']}'")
        print(f"   Similarity: {match.get('similarity', 100)}%")
        
        # Simulate using exact match in translation
        state["translated_content"] = match["target"]
        print(f"🔄 Using exact TMX match: '{match['target']}'")
    else:
        print("❌ No exact matches found")
    
    # Step 3: Demonstrate fuzzy matching
    print("\n🔍 Step 3: Testing fuzzy TMX matching...")
    fuzzy_matches = find_tmx_matches("Hello there", entries, threshold=70.0)
    
    if fuzzy_matches:
        print(f"✅ Found {len(fuzzy_matches)} fuzzy matches!")
        for i, match in enumerate(fuzzy_matches[:2], 1):
            print(f"   {i}. '{match['source']}' → '{match['target']}' ({match.get('similarity', 0):.1f}%)")
    else:
        print("❌ No fuzzy matches found")
    
    # Step 4: Review TMX faithfulness
    print("\n🔍 Step 4: Reviewing TMX faithfulness...")
    if "translated_content" in state:
        review_result = evaluate_tmx_faithfulness(state)
        state.update(review_result.update)
        
        score = state.get("tmx_faithfulness_score", 0)
        explanation = state.get("tmx_faithfulness_explanation", "")
        
        print(f"📊 TMX Faithfulness Score: {score:.2f}")
        if explanation:
            print(f"💬 Explanation: {explanation}")
        else:
            print("✅ No issues found")
    
    # Step 5: Demonstrate complete review aggregation
    print("\n📈 Step 5: Complete review scoring...")
    
    # Add some sample scores for other dimensions
    state.update({
        "glossary_faithfulness_score": 0.9,
        "glossary_faithfulness_explanation": "",
        "grammar_correctness_score": 0.85,
        "grammar_correctness_explanation": "",
        "style_adherence_score": 0.8,
        "style_adherence_explanation": ""
    })
    
    aggregated_result = aggregate_review_scores(state)
    
    final_score = aggregated_result["review_score"]
    final_explanation = aggregated_result["review_explanation"]
    
    print(f"🏆 Final Review Score: {final_score:.2f}")
    print(f"📋 Review Breakdown:")
    print(f"   • Glossary Faithfulness: {state.get('glossary_faithfulness_score', 'N/A')}")
    print(f"   • Grammar Correctness: {state.get('grammar_correctness_score', 'N/A')}")
    print(f"   • Style Adherence: {state.get('style_adherence_score', 'N/A')}")
    print(f"   • TMX Faithfulness: {state.get('tmx_faithfulness_score', 'N/A')}")
    
    if final_explanation:
        print(f"💬 Issues: {final_explanation}")
    else:
        print("✅ No significant issues found")
    
    print("\n🎉 TMX Demo Complete!")
    print("\n📖 Key Benefits:")
    print("   • Exact matches provide 100% consistency")
    print("   • Fuzzy matches guide style and terminology")
    print("   • Automated validation ensures TMX compliance")
    print("   • Integrated scoring provides comprehensive quality assessment")

if __name__ == "__main__":
    demo_tmx_functionality()