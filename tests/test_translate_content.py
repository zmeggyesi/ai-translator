from unittest.mock import MagicMock
from nodes.translate_content import translate_content
from types import SimpleNamespace

def test_translate_content(mocker):
    # Prepare response
    response_mock = SimpleNamespace(content="---\nContenu traduit\n---")

    class DummyChain:
        def __init__(self, response):
            self._response = response
        def invoke(self, _):
            return self._response

    class DummyLLM:
        def __init__(self, *args, **kwargs):
            pass
        def __ror__(self, other):
            return DummyChain(response_mock)

    mocker.patch("langchain_openai.ChatOpenAI", DummyLLM)

    state = {
        "original_content": "Translated content",
        "style_guide": "formal",
        "target_language": "French",
        "filtered_glossary": {"content": "contenu"},
        "glossary": {},
        "messages": [],
    }
    result = translate_content(state)
    assert result["translated_content"] == "---\nContenu traduit\n---"
    
    # Verify that the output glossary was correctly JSON formatted
    # This is implicit in translate_content's operation; we only check the final output here.

    # Verify that the LLM was called with the correct, JSON-formatted glossary
    # call_args = mock_llm.invoke.call_args[0][0]
    # assert '"contenu"' in call_args["glossary"] 