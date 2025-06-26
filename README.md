# Translation Pipeline – LangGraph × LangChain

This project is a **minimal yet production-grade** example of how to combine [LangGraph](https://github.com/langchain-ai/langgraph) with [LangChain](https://github.com/langchain-ai/langchain) to build a translation workflow that enforces both a *style guide* and a *domain-specific glossary*.

The pipeline is intentionally small (two nodes) so the focus stays on the architecture and testing discipline rather than on lavish prompt engineering.

---
## Workflow Overview

```
      ┌───────────────────┐        ┌───────────────────┐
      │  glossary_filter  │──▶──▶──│    translator     │──▶──▶── END
      └───────────────────┘        └───────────────────┘
           (RapidFuzz)                  (OpenAI LLM)
```

1. **Glossary Filter** – Scans the source text and keeps **only** the glossary terms that actually appear (RapidFuzz fuzzy-matching, score ≥ 75).
2. **Translator** – Crafts a prompt embedding the style guide & the filtered glossary, then calls `gpt-4o` (or a mocked model during tests) to obtain the translated content.

Both nodes return *partial* state updates which LangGraph merges into the global `TranslationState` object, keeping the nodes completely decoupled.

---
## Repository Layout

```
translation/
├── data/                 # Example input, glossary and style guide
│   ├── glossary.csv
│   ├── input.txt
│   └── style_guide.md
├── nodes/                # Individual LangGraph nodes
│   ├── __init__.py
│   ├── filter_glossary.py
│   └── translate_content.py
├── tests/                # pytest unit tests with extensive mocking
│   ├── test_filter_glossary.py
│   └── test_translate_content.py
├── graph.py              # Graph wiring – defines the node topology
├── main.py               # Example CLI entry-point that runs the full graph
├── state.py              # TypedDict shared state definition
├── pyproject.toml        # Poetry-compatible metadata + dependencies
├── uv.lock               # Machine-generated lock-file (UV)
└── README.md             # You are here ✔
```

---
## Getting Started

### 1. Clone & create a virtual environment

```bash
# Install UV if you don't have it yet
pip install uv

# Inside the repo...
uv venv             # create .venv using uv
uv pip install -r pyproject.toml  # sync dependencies from pyproject
```

> **Why UV?** UV is a fast, modern Python packaging tool promoted for this project. Standard `pip` or `poetry` will work too, but the lock-file is optimised for UV.

### 2. Provide your OpenAI credentials

Create a `.env` file at the project root:

```ini
OPENAI_API_KEY=sk-...
```

The code automatically loads `.env` via `python-dotenv` on startup.

### 3. Run the example

```bash
python -m translation.main  # prints original & translated content
```

#### Command-line options:

```bash
# Specify target language (default: English)
python -m translation.main --language Spanish
python -m translation.main -l French

# Specify input file (default: data/input.txt)
python -m translation.main --input data/custom_input.txt
python -m translation.main -i data/another_file.txt

# Combine options
python -m translation.main --language German --input data/technical_doc.txt
```

A Mermaid diagram of the graph will be written to `graph-visualization.md`.

### 4. Run the test-suite

```bash
pytest -q
```

The tests use a **dummy** LLM implementation so they are 100 % offline / free.

---
## Extending the Pipeline

* **Add quality-assurance nodes** – e.g. back-translation consistency check.
* **Persist history** – swap the in-memory `messages` list for a vector store.
* **Alternative models** – patch `ChatOpenAI` with Anthropic/LLM of choice; the fallback logic in `translate_content.py` keeps tests untouched.

PRs welcome 🎉
