# Translation Pipeline – LangGraph × LangChain

This project is a **minimal yet production-grade** example of how to combine [LangGraph](https://github.com/langchain-ai/langgraph) with [LangChain](https://github.com/langchain-ai/langchain) to build a translation workflow that enforces both a *style guide* and a *domain-specific glossary*.

The pipeline is intentionally small (three nodes) so the focus stays on the architecture and testing discipline rather than on lavish prompt engineering.

---
## Workflow Overview

```
      ┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
      │  glossary_filter  │──▶──▶──│   human_review    │──▶──▶──│    translator     │──▶──▶──│      review       │──▶──▶── END
      └───────────────────┘        └───────────────────┘        └───────────────────┘        └───────────────────┘
           (RapidFuzz)                (Human-in-the-loop)            (OpenAI LLM)               (Quality Assessment)
```

1. **Glossary Filter** – Scans the source text and keeps **only** the glossary terms that actually appear (RapidFuzz fuzzy-matching, score ≥ 75).
2. **Human Review** – Pauses execution to allow human review and modification of the filtered glossary before translation.
3. **Translator** – Crafts a prompt embedding the style guide & the filtered glossary, then calls `gpt-4o` (or a mocked model during tests) to obtain the translated content.
4. **Review** (optional) – Evaluates translation quality, glossary faithfulness, and style guide adherence with a score from -1.0 to 1.0.

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
│   ├── human_review.py
│   ├── translate_content.py
│   └── review_translation.py
├── tests/                # pytest unit tests with extensive mocking
│   ├── test_filter_glossary.py
│   ├── test_translate_content.py
│   └── test_graph_visualization.py
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
python main.py  # Default: English to Spanish translation
```

#### Command-line options:

```bash
# Basic usage with custom languages
python main.py --source-language English --target-language French
python main.py -sl German -tl English

# Custom file locations
python main.py --input data/my_document.txt --glossary data/my_glossary.csv --style-guide data/my_style.md
python main.py -i data/doc.txt -g data/terms.csv -s data/guide.md

# Combine all options
python main.py -sl English -tl Spanish -i data/technical_doc.txt -g data/tech_glossary.csv -s data/technical_style.md

# Enable automatic translation review
python main.py --review
python main.py -sl English -tl French --review

# Backward compatibility (deprecated)
python main.py --language French  # Same as --target-language French
python main.py -l German          # Same as -tl German
```

#### Available command-line arguments:

- `-sl, --source-language`: Source language of the input text (default: English)
- `-tl, --target-language`: Target language for translation (default: Spanish)
- `-i, --input`: Input file path (default: data/input.txt)
- `-g, --glossary`: Glossary CSV file path (default: data/glossary.csv)  
- `-s, --style-guide`: Style guide file path (default: data/style_guide.md)
- `--review`: Enable automatic translation review and scoring
- `-l, --language`: **Deprecated** - use `--target-language` instead

#### Human-in-the-loop Review

The pipeline includes a human review step that:
1. Shows you the filtered glossary terms found in your text
2. Allows you to modify the glossary before translation
3. Accepts JSON input to update glossary terms, or Enter to continue unchanged

Example interaction:
```
--- Human Review ---
Current filtered glossary:
{'Python': 'Python 3', 'LangGraph': 'LG'}
--------------------

--- Waiting for human input ---
To provide a new glossary, enter a JSON string. Otherwise, press Enter to continue.
> {"Python": "Python 3.11", "LangGraph": "LangGraph Framework"}
```

A Mermaid diagram of the graph will be written to `graph-visualization.md`.

#### Translation Review (Optional)

The pipeline includes an optional automatic review system that evaluates translation quality on three key dimensions:

1. **Overall Quality**: Grammar, fluency, and naturalness in the target language
2. **Faithfulness to Glossary**: Correct usage of specified terminology
3. **Adherence to Style Guide**: Following the prescribed tone and style

**Scoring System:**
- **1.0**: Excellent - Perfect translation with flawless quality, terminology, and style
- **0.7-0.9**: Good - High quality with minor issues
- **0.3-0.6**: Acceptable - Average quality with some noticeable issues  
- **0.0-0.2**: Poor - Significant issues requiring revision
- **-1.0 to -0.1**: Very poor - Major errors, incorrect terminology, or wrong style

**Usage:**
```bash
# Enable review as part of the main pipeline
python main.py --review

# Standalone review of existing translation
python -m nodes.review_translation \
  --original data/input.txt \
  --translation data/my_translation.txt \
  --glossary data/glossary.csv \
  --style-guide data/style_guide.md
```

When the review score is ≥ 0.7, only the score is provided. For lower scores, a detailed explanation is included to guide improvements.

### 4. Run the test-suite

```bash
pytest -q
```

The tests use a **dummy** LLM implementation so they are 100 % offline / free.

---
## File Formats

### Glossary CSV Format
The glossary file should be a CSV with `term` and `translation` columns:
```csv
term,translation
Python,Python 3
LangGraph,LangGraph
API,Interface de Programmation
```

### Style Guide Format
The style guide can be any text file (Markdown recommended) containing translation instructions:
```markdown
# Translation Style Guide

- Use formal tone
- Preserve technical terms in original language when appropriate
- Use active voice
- Be concise but clear
```

---
## Extending the Pipeline

* **Add quality-assurance nodes** – e.g. back-translation consistency check.
* **Persist history** – swap the in-memory `messages` list for a vector store.
* **Alternative models** – patch `ChatOpenAI` with Anthropic/LLM of choice; the fallback logic in `translate_content.py` keeps tests untouched.
* **Custom glossary formats** – extend the loader in `main.py` to support JSON, YAML, or database sources.

PRs welcome 🎉
