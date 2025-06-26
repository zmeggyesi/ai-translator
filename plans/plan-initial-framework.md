# Plan: Initial Translation Framework

## Objective

Create the foundational LangGraph system for content translation, adhering to modular design principles and comprehensive testing. The system will take a piece of content, a glossary, and a style guide, and produce a translation. This version includes intelligent glossary filtering, verbose logging, and graph visualization capabilities.

## Step 1: Project Structure and Setup

1.  Create a `src` directory for all Python source code.
2.  Inside `src`, create a `nodes` directory. This will hold each graph node in its own file.
3.  Create a `tests` directory in the project root for all unit tests.
4.  Create a `data` directory for sample input files.
5.  Inside the `data` directory, create the following files:
    *   `glossary.csv`: A CSV file with "term" and "translation" columns for terminology.
        *   *Example*:
            ```csv
            term,translation
            LangGraph,LangGraph
            Python,Python
            ```
    *   `style_guide.md`: A markdown file outlining the desired tone and style.
        *   *Example*: "Translate in a formal and professional tone. Use active voice."
    *   `input.txt`: A simple text file with content to be translated.
        *   *Example*: "This is a test of the new translation system powered by LangGraph."
6.  Create a `.env` file in the project root and add your OpenAI API key: `OPENAI_API_KEY="your_key_here"`
7.  Update `pyproject.toml` to include the necessary packages. Add `pytest` and `pytest-mock` to a `[project.group.dev-dependencies]` section.
    ```toml
    [project.dependencies]
    dependencies = [
        "langgraph",
        "langchain-openai",
        "python-dotenv",
        "langchain",
        "rapidfuzz",
        "rich"
    ]

    [project.group.dev-dependencies]
    dependencies = [
        "pytest",
        "pytest-mock"
    ]
    ```
8.  After the file is updated, run `uv pip install -r requirements.txt` and `uv pip install --group dev` to install the dependencies.
9.  A `graph-visualization.md` file will be generated in the root directory, containing a Mermaid diagram of the graph.

## Step 2: Define Graph State

-   Create a new file: `src/state.py`
-   Define a `TypedDict` that will serve as the state for the LangGraph workflow.

```python
# src/state.py
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class TranslationState(TypedDict):
    original_content: str
    glossary: dict
    style_guide: str
    filtered_glossary: dict | None
    translated_content: str | None
    messages: Annotated[List[BaseMessage], add_messages]
```

## Step 3: Implement Graph Nodes

-   Each node will be implemented in its own file inside the `src/nodes/` directory.

#### 3.1. Glossary Filter Node

-   Create a new file: `src/nodes/filter_glossary.py`

```python
# src/nodes/filter_glossary.py
import logging
from rapidfuzz import process, fuzz
from ..state import TranslationState

# Configure logging
logger = logging.getLogger(__name__)

def filter_glossary(state: TranslationState) -> dict:
    """
    Filters the glossary to include only terms found in the original content.
    """
    logger.info("Filtering glossary...")
    original_content = state["original_content"]
    glossary_terms = list(state["glossary"].keys())
    
    extracted_terms = process.extract(
        original_content,
        glossary_terms,
        scorer=fuzz.token_set_ratio,
        score_cutoff=80,
    )

    filtered_glossary = {
        term: state["glossary"][term]
        for term, score, index in extracted_terms
    }

    logger.info(f"Found {len(filtered_glossary)} relevant glossary terms.")
    logger.debug(f"Filtered glossary: {filtered_glossary}")

    return {"filtered_glossary": filtered_glossary}
```

#### 3.2. Translator Node

-   Create a new file: `src/nodes/translate_content.py`

```python
# src/nodes/translate_content.py
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..state import TranslationState

# Configure logging
logger = logging.getLogger(__name__)

TRANSLATION_PROMPT = """
Translate the following content:

---
{original_content}
---

You MUST adhere to the following instructions:
1.  **Style Guide**: {style_guide}
2.  **Glossary**: Strictly use the translations provided in this JSON object for any applicable terms:
    {glossary}

Output only the translated text.
"""

def translate_content(state: TranslationState) -> dict:
    """
    Translates the original content based on the filtered glossary and style guide.
    """
    logger.info("Translating content...")
    prompt = ChatPromptTemplate.from_template(TRANSLATION_PROMPT)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    chain = prompt | llm

    glossary = state.get("filtered_glossary") or {}
    logger.debug(f"Using glossary for translation: {glossary}")

    response = chain.invoke({
        "original_content": state["original_content"],
        "style_guide": state["style_guide"],
        "glossary": json.dumps(glossary, ensure_ascii=False),
    })

    logger.info("Translation complete.")
    return {"translated_content": response.content}
```

#### 3.3. Nodes Package

- Create a new file: `src/nodes/__init__.py` to expose the nodes.

```python
# src/nodes/__init__.py
from .filter_glossary import filter_glossary
from .translate_content import translate_content
```

## Step 4: Build the Graph

-   Create a new file: `src/graph.py`
-   This file will be responsible for constructing and compiling the LangGraph workflow.

```python
# src/graph.py
from langgraph.graph import StateGraph, END
from .state import TranslationState
from .nodes import filter_glossary, translate_content

def create_translator():
    """
    Creates and compiles the translation LangGraph.
    """
    graph = StateGraph(TranslationState)

    graph.add_node("glossary_filter", filter_glossary)
    graph.add_node("translator", translate_content)

    graph.set_entry_point("glossary_filter")
    graph.add_edge("glossary_filter", "translator")
    graph.add_edge("translator", END)

    return graph.compile()
```

## Step 5: Create Main Application Entrypoint

-   Modify the existing `main.py` file to orchestrate the entire process.

```python
# main.py
import csv
import json
import logging
from dotenv import load_dotenv
from src.graph import create_translator

def setup_logging():
    """Configures the logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Set the logging level for this application's logger
    logger = logging.getLogger('src')
    logger.setLevel(logging.DEBUG)


def main():
    """
    Main function to run the translation process.
    """
    load_dotenv()
    setup_logging()

    # 1. Load data
    with open("data/input.txt", "r", encoding="utf-8") as f:
        original_content = f.read()

    glossary = {}
    with open("data/glossary.csv", "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            glossary[row["term"]] = row["translation"]

    with open("data/style_guide.md", "r", encoding="utf-8") as f:
        style_guide = f.read()

    # 2. Create and run the graph
    translator_app = create_translator()
    initial_state = {
        "original_content": original_content,
        "glossary": glossary,
        "style_guide": style_guide,
        "messages": [], # Initialize messages list
    }
    final_state = translator_app.invoke(initial_state)

    # 3. Generate graph visualization
    try:
        mermaid_diagram = translator_app.get_graph().draw_mermaid()
        with open("graph-visualization.md", "w", encoding="utf-8") as f:
            f.write("```mermaid\n")
            f.write(mermaid_diagram)
            f.write("\n```")
        logging.info("Graph visualization saved to graph-visualization.md")
    except Exception as e:
        logging.error(f"Could not generate graph visualization: {e}")


    # 4. Print results
    print("\n--- Original Content ---")
    print(original_content)
    print("\n--- Translated Content ---")
    print(final_state.get("translated_content"))

if __name__ == "__main__":
    main()
```

## Step 6: Implement Unit Tests

- Create a `tests` directory.
- Add tests for the graph nodes to ensure they work as expected.

#### 6.1. Test Glossary Filter Node

- Create a file: `tests/test_filter_glossary.py`

```python
# tests/test_filter_glossary.py
from src.nodes.filter_glossary import filter_glossary

def test_filter_glossary_finds_terms():
    state = {
        "original_content": "This text talks about Python and LangGraph.",
        "glossary": {"Python": "Python 3", "LangGraph": "LG", "Unrelated": "Term"}
    }
    result = filter_glossary(state)
    assert "Python" in result["filtered_glossary"]
    assert "LangGraph" in result["filtered_glossary"]
    assert "Unrelated" not in result["filtered_glossary"]
    assert len(result["filtered_glossary"]) == 2
```

#### 6.2. Test Translator Node

- Create a file: `tests/test_translate_content.py`

```python
# tests/test_translate_content.py
from unittest.mock import MagicMock
from src.nodes.translate_content import translate_content

def test_translate_content(mocker):
    # Mock the OpenAI call
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "Contenu traduit"
    mocker.patch(
        "src.nodes.translate_content.ChatOpenAI", return_value=mock_llm
    )

    state = {
        "original_content": "Translated content",
        "style_guide": "formal",
        "filtered_glossary": {"content": "contenu"},
    }
    result = translate_content(state)
    assert result["translated_content"] == "Contenu traduit"
    
    # Verify that the LLM was called with the correct, JSON-formatted glossary
    call_args = mock_llm.invoke.call_args[0][0]
    assert '"contenu"' in call_args["glossary"]
```

#### 6.3. Running Tests

- To run the tests, execute `pytest` in the terminal from the project root. 