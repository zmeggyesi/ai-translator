#!/usr/bin/env python3
"""translation CLI
====================

A thin wrapper around the existing translation pipeline that introduces a
sub-command based interface.

Supported commands:

    • translate-file   – Translate a plain-text file using the LangGraph
      workflow (this maps 1-to-1 to the old *main.py* behaviour).

    • extract-style    – Infer a (very lightweight) style guide from an
      existing TMX file.

    • extract-glossary – Pull potential glossary term pairs from a TMX or
      monolingual text file.

The legacy interface is preserved: running ``python main.py`` directly still
works.  For all new work, however, prefer the explicit sub-command syntax.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, cast

from dotenv import load_dotenv
from state import TranslationState

# ---------------------------------------------------------------------------
# Local imports – these modules live in the repo
# ---------------------------------------------------------------------------
from nodes.extract_style import extract_style_guide_unified
from nodes.extract_glossary import extract_glossary
from graph import create_translator
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
import csv
import json
import uuid

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger(__name__).setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Sub-command: TRANSLATE-FILE
# ---------------------------------------------------------------------------

def _add_translate_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = subparsers.add_parser(
        "translate-file",
        help="Translate the specified input file.",
        description="Translate a text file, optionally applying a glossary, style guide, and/or TMX file.",
    )

    p.add_argument("-i", "--input", required=True, help="Input file path (plain text)")
    p.add_argument("-sl", "--source-language", required=True, help="Source language of the text")
    p.add_argument("-tl", "--target-language", required=True, help="Target language for translation")
    p.add_argument("-g", "--glossary", default="data/glossary.csv", help="Glossary CSV (term,translation)")
    p.add_argument("-s", "--style-guide", default="data/style_guide.md", help="Style-guide file (markdown)")
    p.add_argument("-t", "--tmx", help="TMX file providing translation memory")
    p.add_argument("--review", action="store_true", help="Run automatic translation review")
    p.add_argument(
        "--visualize",
        action="store_true",
        help="Generate workflow visualisation diagrams (PNG)",
    )
    p.add_argument(
        "--viz-type",
        choices=["main", "review", "combined", "all"],
        default="combined",
        help="Diagram type to generate when --visualize is enabled.",
    )
    # Deprecated flag – kept for backwards compatibility
    p.add_argument("-l", "--language", help="DEPRECATED. Use --target-language instead.")
    return p


def _run_translation(args: argparse.Namespace) -> None:  # noqa: C901 – complexity comes from exhaustive error handling
    """Re-implementation of the old *main.py* logic but parameterised."""

    load_dotenv()
    _setup_logging()
    logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Handle deprecated aliases
    # ------------------------------------------------------------------
    target_language = args.target_language
    if getattr(args, "language", None):
        target_language = args.language
        print("Warning: -l/--language is deprecated. Use -tl/--target-language instead.")

    logger.info("Starting translation: %s → %s", args.source_language, target_language)
    if args.review:
        logger.info("Automatic review ENABLED")

    # ------------------------------------------------------------------
    # Load input text
    # ------------------------------------------------------------------
    try:
        original_content = Path(args.input).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)
    except Exception as exc:
        logger.error("Error reading input file: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load glossary (CSV) – supports headerless fallback
    # ------------------------------------------------------------------
    glossary: dict[str, str] = {}
    try:
        with Path(args.glossary).open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "term" in reader.fieldnames and "translation" in reader.fieldnames:
                for row in reader:
                    if row.get("term") and row.get("translation"):
                        glossary[row["term"]] = row["translation"]
                logger.info("Loaded glossary with headers → %s", args.glossary)
            else:
                f.seek(0)
                reader2 = csv.reader(f)
                for row_num, row in enumerate(reader2, 1):
                    if len(row) >= 2 and row[0] and row[1]:
                        glossary[row[0]] = row[1]
                    elif len(row) < 2:
                        logger.warning("Skipping glossary row %d – insufficient columns", row_num)
                logger.info("Loaded headerless glossary → %s", args.glossary)
    except FileNotFoundError:
        logger.error("Glossary file not found: %s", args.glossary)
        sys.exit(1)
    except Exception as exc:
        logger.error("Error reading glossary: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load style guide (optional) – no failure if missing
    # ------------------------------------------------------------------
    style_guide = ""
    try:
        style_guide = Path(args.style_guide).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Style guide not found – proceeding without it: %s", args.style_guide)
    except Exception as exc:
        logger.error("Error reading style guide: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # TMX preparation (optional)
    # ------------------------------------------------------------------
    tmx_memory = None
    if args.tmx:
        try:
            from nodes.tmx_loader import load_tmx_memory

            temp_state = cast(
                "TranslationState",  # type: ignore[name-defined]
                {
                    "source_language": args.source_language,
                    "target_language": target_language,
                },
            )
            tmx_memory_state = load_tmx_memory(temp_state, args.tmx)  # type: ignore[arg-type]
            tmx_memory = tmx_memory_state.get("tmx_memory", {})

            entries_count = len(tmx_memory.get("entries", [])) if tmx_memory else 0
            lang_pair = tmx_memory.get(
                "language_pair", f"{args.source_language}->{target_language}"
            )
            logger.info(
                "TMX entries loaded: %d for %s", entries_count, lang_pair
            )
            if entries_count == 0:
                logger.warning("TMX contained no usable entries for this language pair.")
        except Exception as exc:
            logger.error("Error loading TMX file: %s", exc)
            sys.exit(1)

    # ------------------------------------------------------------------
    # Build and execute the LangGraph translator
    # ------------------------------------------------------------------
    checkpointer = InMemorySaver()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    translator_app = create_translator(
        checkpointer=checkpointer,
        include_review=args.review,
        include_tmx=bool(args.tmx),
    )

    state = {
        "original_content": original_content,
        "glossary": glossary,
        "style_guide": style_guide,
        "source_language": args.source_language,
        "target_language": target_language,
        "messages": [],
    }
    if tmx_memory:
        state["tmx_memory"] = tmx_memory

    result = translator_app.invoke(state, config=config)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Interactive review interruptions
    # ------------------------------------------------------------------
    while isinstance(result, dict) and "__interrupt__" in result:
        print("\n--- Human Review Interrupt ---")
        interrupt_info = result.get("__interrupt__", [])
        if interrupt_info:
            print(f"Interrupt payload: {interrupt_info}")
        user_input = input("Enter revised glossary as JSON (or press Enter to continue):\n> ")
        try:
            resume_val = json.loads(user_input) if user_input.strip() else ""
        except json.JSONDecodeError:
            print("Invalid JSON. Resuming with no changes.")
            resume_val = ""
        result = translator_app.invoke(Command(resume=resume_val), config=config)  # type: ignore[arg-type]

    final_state = result  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    print("\n--- Original Content ---\n", original_content)
    print(f"\n--- Translated Content ({args.source_language} → {target_language}) ---")
    print(final_state.get("translated_content"))

    if args.review and final_state.get("review_score") is not None:
        print("\n--- Translation Review ---")
        score = final_state.get("review_score")
        print(f"Overall Review Score: {score:.2f} (-1.0 → 1.0)")

    # ------------------------------------------------------------------
    # Visualisation (optional)
    # ------------------------------------------------------------------
    if args.visualize:
        from graph import (
            export_graph_png,
            export_review_graph_png,
            export_combined_graph_png,
        )

        if args.viz_type in {"all", "main"}:
            print("Generating main workflow diagram …")
            export_graph_png("main_graph.png", include_review=args.review)
        if args.viz_type in {"all", "review"}:
            print("Generating review workflow diagram …")
            export_review_graph_png("review_system.png")
        if args.viz_type in {"all", "combined"}:
            print("Generating combined workflow diagram …")
            export_combined_graph_png("combined_workflow.png")


# ---------------------------------------------------------------------------
# Sub-command: EXTRACT-STYLE
# ---------------------------------------------------------------------------

def _add_style_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = subparsers.add_parser(
        "extract-style",
        help="Infer a style guide from a TMX file or document (PDF, DOCX, DOC).",
    )
    p.add_argument("-i", "--input", required=True, help="Input file path")
    p.add_argument("-ft", "--file-type", required=True, 
                   choices=["tmx", "pdf", "docx", "doc"],
                   help="Type of input file")
    p.add_argument("-sl", "--source-language", required=True, help="Source language code")
    p.add_argument("-tl", "--target-language", 
                   help="Target language code (required for TMX files)")
    p.add_argument("-o", "--output", required=True, help="Output markdown file path")
    return p


def _run_extract_style(args: argparse.Namespace) -> None:
    load_dotenv()
    _setup_logging()

    # Validate arguments based on file type
    if args.file_type == "tmx" and not args.target_language:
        print("Error: Target language is required for TMX files")
        return

    try:
        extract_style_guide_unified(
            file_path=args.input,
            file_type=args.file_type,
            source_language=args.source_language,
            target_language=args.target_language,
            output_path=args.output,
        )
        print(f"Style guide written to {args.output}")
    except Exception as e:
        print(f"Error: {e}")
        return


# ---------------------------------------------------------------------------
# Sub-command: EXTRACT-GLOSSARY
# ---------------------------------------------------------------------------

def _add_glossary_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = subparsers.add_parser(
        "extract-glossary",
        help="Extract glossary term pairs either from TMX or a monolingual text file.",
    )
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("-t", "--tmx", help="TMX file to analyse")
    source.add_argument("-i", "--input", help="Plain-text file to analyse")

    p.add_argument("-sl", "--source-language", required=True, help="Source language code")
    p.add_argument("-tl", "--target-language", required=True, help="Target language code")
    p.add_argument("-o", "--output", required=True, help="Output CSV file path")
    return p


def _run_extract_glossary(args: argparse.Namespace) -> None:
    load_dotenv()
    _setup_logging()

    extract_glossary(
        tmx=args.tmx,
        input_file=args.input,
        source_language=args.source_language,
        target_language=args.target_language,
        output=args.output,
    )
    print(f"Glossary written to {args.output}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="translate",
        description="Translation toolkit with multiple sub-commands.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_translate_parser(subparsers)
    _add_style_parser(subparsers)
    _add_glossary_parser(subparsers)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "translate-file":
        _run_translation(args)
    elif args.command == "extract-style":
        _run_extract_style(args)
    elif args.command == "extract-glossary":
        _run_extract_glossary(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()