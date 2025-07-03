# Translation Pipeline – LangGraph × LangChain

This project is a **minimal yet production-grade** example of how to combine [LangGraph](https://github.com/langchain-ai/langgraph) with [LangChain](https://github.com/langchain-ai/langchain) to build a translation workflow that enforces a *style guide*, a *domain-specific glossary*, and leverages *TMX (Translation Memory eXchange)* files for consistency and quality.

The pipeline is intentionally small (three core nodes) so the focus stays on the architecture and testing discipline rather than on lavish prompt engineering, while providing enterprise-grade translation memory capabilities.

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
3. **Translator** – Integrates TMX translation memory, uses exact TMX matches verbatim when available, or leverages fuzzy TMX matches for style guidance. Crafts a prompt embedding the style guide, filtered glossary, and TMX guidance, then calls `gpt-4o` to obtain the translated content.
4. **Review** (optional) – Multi-agent evaluation of translation quality including glossary faithfulness, grammar correctness, style adherence, and TMX compliance with scores from -1.0 to 1.0.

Both nodes return *partial* state updates which LangGraph merges into the global `TranslationState` object, keeping the nodes completely decoupled.

---
## Repository Layout

```
translation/
├── data/                 # Example input, glossary, style guide, and TMX files
│   ├── glossary.csv
│   ├── input.txt
│   ├── sample.tmx        # Sample TMX translation memory file
│   └── style_guide.md
├── nodes/                # Individual LangGraph nodes
│   ├── __init__.py
│   ├── filter_glossary.py
│   ├── human_review.py
│   ├── review_aggregator.py
│   ├── review_glossary_faithfulness.py
│   ├── review_grammar_correctness.py
│   ├── review_style_adherence.py
│   ├── review_tmx_faithfulness.py  # TMX faithfulness evaluation
│   ├── review_agent.py   # Multi-agent review coordination
│   ├── tmx_loader.py     # TMX parsing and matching functionality
│   ├── translate_content.py
│   └── review_translation.py
├── tests/                # pytest unit tests with extensive mocking
│   ├── test_filter_glossary.py
│   ├── test_tmx_functionality.py  # Comprehensive TMX testing
│   ├── test_translate_content.py
│   └── test_graph_visualization.py
├── graph.py              # Graph wiring – defines the node topology
├── cli.py               # Unified CLI (translate-file / extract-style / extract-glossary)
├── main.py               # Legacy CLI entry-point (translate-file only, still supported)
├── state.py              # TypedDict shared state definition
├── pyproject.toml        # UV-compatible metadata + dependencies
├── uv.lock               # Machine-generated lock-file (UV)
├── TMX_INTEGRATION.md    # Technical TMX integration documentation
├── TMX_CLI_USAGE.md      # TMX CLI usage guide
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
python cli.py translate-file \
  --input data/input.txt \
  --source-language English \
  --target-language Spanish
```

#### Command-line options:

```bash
# Basic usage with custom languages (input file required)
python cli.py translate-file -i data/doc.txt -sl English -tl French
python cli.py translate-file --input data/doc.txt --source-language German --target-language English

# Custom file locations
python cli.py translate-file -i data/my_document.txt -sl English -tl Spanish \
  --glossary data/my_glossary.csv --style-guide data/my_style.md

# Translation with TMX memory
python cli.py translate-file -i data/input.txt -sl English -tl French \
  --tmx data/sample.tmx
python cli.py translate-file -i data/input.txt -sl en -tl fr \
  -t data/my_translations.tmx

# Combine all options with TMX
python cli.py translate-file -i data/technical_doc.txt -sl English -tl Spanish \
  -g data/tech_glossary.csv -s data/technical_style.md -t data/tech_memory.tmx

# Enable automatic translation review (multi-agent system)
python cli.py translate-file -i data/input.txt -sl English -tl French --review

# Generate workflow visualizations  
python cli.py translate-file -i data/input.txt -sl English -tl Spanish --visualize --viz-type all
python cli.py translate-file -i data/input.txt -sl English -tl French --review --visualize --viz-type combined

# Backward compatibility (deprecated)
python cli.py translate-file -i data/input.txt --source-language English --language French  # Same as --target-language French
python cli.py translate-file -i data/input.txt -sl English -l German          # Same as -tl German
```

#### Available command-line arguments (translate-file):

- `-i, --input` **(required)**: Input file path
- `-sl, --source-language` **(required)**: Source language of the input text
- `-tl, --target-language` **(required)**: Target language for translation
- `-g, --glossary`: Glossary CSV file path (default: data/glossary.csv)  
- `-s, --style-guide`: Style guide file path (default: data/style_guide.md)
- `-t, --tmx`: TMX (Translation Memory eXchange) file path for leveraging translation memory
- `--review`: Enable automatic translation review and scoring (uses multi-agent system by default)
- `--visualize`: Generate visualization diagrams of the workflow  
- `--viz-type {main,review,combined,all}`: Type of visualization to generate (default: combined when review is enabled)

### 3b. Extract a Style Guide from TMX

```bash
python cli.py extract-style \
  --tmx data/sample.tmx \
  --source-language English \
  --target-language French \
  --output extracted_style.md
```

### 3c. Extract Glossary Terms

```bash
python cli.py extract-glossary \
  --input data/input.txt \
  --output glossary.csv \
  --source-language English \
  --target-language Spanish
```

#### Available command-line arguments (extract-style):

- `-t, --tmx` **(required)**: TMX file to analyse
- `-sl, --source-language` **(required)**: Source language code
- `-tl, --target-language` **(required)**: Target language code
- `-o, --output` **(required)**: Output Markdown file

#### Available command-line arguments (extract-glossary):

- One of `-t/--tmx` *or* `-i/--input` **(required)**: Source to analyse 
- `-o, --output` **(required)**: Output CSV file path
- `-sl, --source-language` **(required)**: Source language
- `-tl, --target-language` **(required)**: Target language (needed for TMX extraction)

#### Translation Review (Optional)

The pipeline includes an optional **multi-agent review system** that evaluates translation quality using specialized agents for comprehensive assessment:

**Multi-Agent Architecture:**
- **Glossary Faithfulness Agent**: Non-LLM based evaluation using fuzzy matching to verify correct terminology usage
- **Grammar Correctness Agent**: LLM-based evaluation focused exclusively on grammatical accuracy and linguistic structure  
- **Style Adherence Agent**: LLM-based evaluation for tone, voice, and style guide compliance
- **Review Aggregator**: Combines individual scores using weighted averages

**Key Benefits:**
- **Performance**: Specialized agents with focused prompts are more efficient than monolithic evaluation
- **Token Efficiency**: Each agent has a specific scope, reducing token usage per evaluation
- **Modularity**: Individual agents can be tested, modified, and improved independently
- **Early Termination**: Poor scores in critical dimensions can trigger early completion for efficiency

**Evaluation Dimensions:**
1. **Glossary Faithfulness** (30% weight): Correct usage of specified terminology
2. **Grammar Correctness** (30% weight): Grammar, fluency, and naturalness in the target language
3. **Style Adherence** (20% weight): Following the prescribed tone and style guide
4. **TMX Faithfulness** (20% weight): Consistency with translation memory patterns and exact match usage (when TMX is provided)

**Scoring System:**
- **1.0**: Excellent - Perfect translation with flawless quality, terminology, and style
- **0.7-0.9**: Good - High quality with minor issues
- **0.3-0.6**: Acceptable - Average quality with some noticeable issues  
- **0.0-0.2**: Poor - Significant issues requiring revision
- **-1.0 to -0.1**: Very Poor - Major problems requiring substantial rework

**Usage:**
```bash
# Enable review as part of the main pipeline
python cli.py translate-file --review

# Standalone multi-agent review of existing translation
python -m nodes.review_agent \
  --original data/input.txt \
  --translation data/my_translation.txt \
  --glossary data/glossary.csv \
  --style-guide data/style_guide.md \
  --breakdown  # Show detailed score breakdown

# Legacy single-agent review (still available)
python -m nodes.review_translation \
  --original data/input.txt \
  --translation data/my_translation.txt
```

**Review Process:**
- Agent Communication Protocol (ACP) handoffs coordinate between specialized evaluators
- Only dimensions scoring below 0.7 receive detailed explanations
- Individual dimension scores and explanations are shown in the detailed breakdown
- The system prioritizes actionable feedback for improvement

### 4. Workflow Visualizations

The system can generate comprehensive visualizations of the translation workflow, including the multi-agent review system:

```bash
# Generate all visualization types
python graph.py --all

# Generate specific visualization types
python graph.py --review-only -o review_system.png
python graph.py --combined -o complete_workflow.png
python graph.py --main-only --review -o main_with_review.png

# Generate visualizations as part of translation
python cli.py translate-file --review --visualize --viz-type combined
```

**Available Visualization Types:**
- **Main Graph**: Shows the primary translation workflow (glossary filtering, human review, translation)
- **Review System**: Detailed view of the multi-agent review system with handoff flows
- **Combined View**: Comprehensive visualization showing both main workflow and review system integration
- **All Types**: Generates all three visualization types

**Generated Files:**
- `main_graph.png`: Main translation pipeline
- `review_system.png`: Multi-agent review system architecture  
- `combined_workflow.png`: Complete end-to-end process flow
- `workflow_with_review.png`: Auto-generated when review is enabled

### 5. Run the test-suite

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

### TMX File Format
TMX (Translation Memory eXchange) files follow the industry-standard XML format for sharing translation memories. The system supports TMX 1.4+ format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header>
    <prop type="x-filename">sample.tmx</prop>
  </header>
  <body>
    <tu tuid="1" usagecount="1">
      <tuv xml:lang="en">
        <seg>Hello world</seg>
      </tuv>
      <tuv xml:lang="fr">
        <seg>Bonjour le monde</seg>
      </tuv>
    </tu>
    <tu tuid="2" usagecount="5">
      <tuv xml:lang="en">
        <seg>Welcome to our application</seg>
      </tuv>
      <tuv xml:lang="fr">
        <seg>Bienvenue dans notre application</seg>
      </tuv>
    </tu>
  </body>
</tmx>
```

**TMX Integration Features:**
- **Exact Matches**: Segments with 100% similarity are used verbatim, bypassing LLM translation for maximum consistency
- **Fuzzy Matches**: Segments with 80%+ similarity provide style guidance to the LLM
- **Bidirectional Support**: Works with both source→target and target→source language pairs
- **Quality Validation**: TMX faithfulness evaluation ensures translations align with memory patterns

For more details, see `TMX_CLI_USAGE.md` and `TMX_INTEGRATION.md`.

---
## Extending the Pipeline

The system already includes enterprise-grade TMX (Translation Memory eXchange) support with exact matching, fuzzy matching, and quality validation. Additional extensions you could add:

* **Enhanced TMX features** – Add TMX writing capabilities, usage statistics tracking, or advanced fuzzy matching algorithms.
* **Additional quality-assurance nodes** – e.g. back-translation consistency check, readability analysis.
* **Persist history** – swap the in-memory `messages` list for a vector store or database.
* **Alternative models** – patch `ChatOpenAI` with Anthropic/LLM of choice; the fallback logic in `translate_content.py` keeps tests untouched.
* **Custom file format support** – extend loaders to support additional formats like XLIFF, JSON, YAML, or database sources.
* **Translation memory learning** – automatically build TMX files from high-scoring translations.

PRs welcome 🎉
