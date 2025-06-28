# ---------------------------------------------------------------------------
# LangGraph **definition** – glue code that wires individual nodes into a
# coherent translation workflow.
# ---------------------------------------------------------------------------
#
# The graph has the following topology:
#
#   [glossary_filter]  →  [translator]  →  [review] (optional)  →  END
#
# Each node implements the `Callable[[TranslationState], dict]` protocol and
# returns a *partial* state update which LangGraph merges into the global
# `TranslationState` object. This keeps nodes loosely-coupled and easy to test
# in isolation.
# ---------------------------------------------------------------------------

from langgraph.graph import StateGraph, END
from state import TranslationState
from nodes.filter_glossary import filter_glossary
from nodes.translate_content import translate_content
from nodes.human_review import human_review
from nodes.review_agent import review_translation_multi_agent, create_review_agent
from langgraph.checkpoint.base import BaseCheckpointSaver

def create_translator(checkpointer: BaseCheckpointSaver, include_review: bool = False):
    """
    Creates and compiles the translation LangGraph.
    
    Args:
        checkpointer: The checkpoint saver for state persistence
        include_review: Whether to include the translation review node
    """
    graph = StateGraph(TranslationState)

    graph.add_node("glossary_filter", filter_glossary)
    graph.add_node("human_review", human_review)
    graph.add_node("translator", translate_content)
    
    if include_review:
        # Multi-agent review is now the default
        graph.add_node("review", review_translation_multi_agent)

    graph.set_entry_point("glossary_filter")
    graph.add_edge("glossary_filter", "human_review")
    graph.add_edge("human_review", "translator")
    
    if include_review:
        graph.add_edge("translator", "review")
        graph.add_edge("review", END)
    else:
        graph.add_edge("translator", END)

    return graph.compile(checkpointer=checkpointer)

def export_graph_png(output_path: str = "translator_graph.png", include_review: bool = False) -> str:
    """Generate a PNG image that visualises the LangGraph network.

    Parameters
    ----------
    output_path : str, optional
        Filesystem path where the PNG should be written. Defaults to
        ``translator_graph.png`` in the current working directory.
    include_review : bool, optional
        Whether to include the review node in the visualization.

    Returns
    -------
    str
        The *absolute* path to the written PNG file. This is convenient for
        callers that want to log or further process the artefact.

    Notes
    -----
    The function relies on **NetworkX** – a transitive dependency of
    LangGraph – and **matplotlib** (declared as a direct dependency in
    ``pyproject.toml``) for the actual rendering. We intentionally avoid
    Graphviz/pygraphviz to keep the external system dependencies minimal and
    fully Python-level.
    """

    # First, try the *built-in* helper exposed by LangGraph which directly
    # renders a Mermaid diagram to PNG.  This path requires no heavy
    # third-party plotting libraries and is therefore preferred when
    # available.
    from pathlib import Path
    # This is a bit of a hack, but we need a checkpointer to create the graph.
    # We'll use a dummy one for visualization purposes.
    from langgraph.checkpoint.memory import InMemorySaver
    compiled_graph = create_translator(checkpointer=InMemorySaver(), include_review=include_review)

    try:
        mermaid_png = compiled_graph.get_graph().draw_mermaid_png()  # type: ignore[attr-defined]
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(mermaid_png)
        return str(output_path.resolve())
    except Exception:
        # Fall back to the legacy matplotlib + networkx pipeline below.
        pass

    # Lazy imports keep the cost of adding this utility near-zero for users
    # that never call it.
    import os
    from pathlib import Path

    # ``Agg`` is a non-interactive backend that works in headless CI
    # environments and inside containers.
    try:
        import matplotlib
        matplotlib.use("Agg")  # type: ignore
        import matplotlib.pyplot as plt  # noqa: E402 – after backend selection
    except ModuleNotFoundError:
        # ``matplotlib`` is an optional dependency. If it's not available we
        # fall back to generating a *very* small placeholder PNG so the
        # calling code does not error out.
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        _MINIMAL_PNG = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe"
            b"\x02\xfeA\x8b k\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        output_path.write_bytes(_MINIMAL_PNG)
        return str(output_path.resolve())

    # Ensure the parent directory exists (the user may specify a nested path).
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import networkx as nx  # Local import to allow graceful degradation

        # Compile (or retrieve) the graph to obtain its *NetworkX* representation.
        # This is a bit of a hack, but we need a checkpointer to create the graph.
        # We'll use a dummy one for visualization purposes.
        from langgraph.checkpoint.memory import InMemorySaver
        compiled_graph = create_translator(checkpointer=InMemorySaver())

        try:
            nx_graph = compiled_graph.get_graph()  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback for older versions of LangGraph where ``get_graph`` was not
            # available. The compiled object itself is already a NetworkX graph.
            nx_graph = compiled_graph  # type: ignore[assignment]
        
        # Handle different LangGraph graph representations
        if hasattr(nx_graph, 'to_networkx'):
            # Newer LangGraph versions have a to_networkx method
            nx_graph = nx_graph.to_networkx()
        elif hasattr(nx_graph, 'nodes') and hasattr(nx_graph, 'edges'):
            # It's already a NetworkX-compatible graph
            pass
        else:
            # Create a simple graph manually if needed
            simple_graph = nx.DiGraph()
            # Add basic nodes based on what we know about the graph structure
            simple_graph.add_nodes_from(['glossary_filter', 'human_review', 'translator'])
            simple_graph.add_edges_from([
                ('glossary_filter', 'human_review'),
                ('human_review', 'translator')
            ])
            if include_review:
                simple_graph.add_node('review')
                simple_graph.add_edge('translator', 'review')
            nx_graph = simple_graph

        # Use a deterministic layout so that the image does not change between
        # runs (crucial for snapshot testing and clean version control diffs).
        pos = nx.spring_layout(nx_graph, seed=42)

        plt.figure(figsize=(8, 4))
        nx.draw_networkx(
            nx_graph,
            pos,
            with_labels=True,
            arrows=True,
            node_size=2000,
            node_color="#AED6F1",
            font_size=10,
            font_weight="bold",
            arrowstyle="-|>",
            arrowsize=20,
        )
        plt.axis("off")
        plt.tight_layout()
    except ModuleNotFoundError:
        # NetworkX is not available – create a placeholder image so that the
        # rest of the application can continue functioning.
        plt.figure(figsize=(6, 2))
        plt.text(0.5, 0.5, "Graph visualisation\nrequires 'networkx'", ha="center", va="center")
        plt.axis("off")

    # Save the figure regardless of whether it is a real graph or a placeholder.
    plt.savefig(output_path, format="png", dpi=150)
    plt.close()

    # Return the absolute path for convenience.
    return str(output_path.resolve())

def visualize_graph(output_file: str = "translator_workflow.png", *, open_file: bool = True, include_review: bool = False) -> str:
    """Visualise the **translation** LangGraph and persist the diagram.

    The function first attempts to leverage LangGraph's built-in
    ``draw_mermaid_png`` helper (fast and dependency-free) to emit a PNG.  If
    that capability is unavailable – e.g. because the underlying runtime lacks
    the optional *Pillow* dependency – it gracefully degrades to writing raw
    Mermaid text (``.mmd`` file).

    Parameters
    ----------
    output_file : str, optional
        Destination path for the rendered diagram.  The default is
        ``translator_workflow.png`` in the *current working directory*.
    open_file : bool, optional
        Whether to attempt opening the resulting file with the platform's
        default viewer.  Defaults to *True*.
    include_review : bool, optional
        Whether to include the review node in the visualization.

    Returns
    -------
    str
        Absolute path to the generated artefact (PNG **or** Mermaid file).
    """

    import os
    import platform
    import subprocess
    import time
    from pathlib import Path
    import logging

    logger = logging.getLogger(__name__)

    # Compile (or retrieve) the graph executor.  We reuse the helper so that
    # any future changes to the node topology are automatically reflected.
    # This is a bit of a hack, but we need a checkpointer to create the graph.
    # We'll use a dummy one for visualization purposes.
    from langgraph.checkpoint.memory import InMemorySaver
    app = create_translator(checkpointer=InMemorySaver(), include_review=include_review)

    # Normalise the user-supplied path.
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Preferred path: direct PNG generation via Mermaid → Pillow pipeline.
        start = time.time()
        png_bytes = app.get_graph().draw_mermaid_png()  # type: ignore[attr-defined]
        duration = round(time.time() - start, 2)
        output_path.write_bytes(png_bytes)
        logger.info(
            "LangGraph diagram exported to %s (%.2fs, PNG)", output_path, duration
        )
    except Exception as err:  # pragma: no cover – depends on optional deps
        logger.warning("PNG generation failed (%s). Falling back to Mermaid text.", err)
        try:
            mermaid_text = app.get_graph().draw_mermaid()  # type: ignore[attr-defined]
        except AttributeError:
            # Very old LangGraph versions – we cannot reasonably support them.
            raise RuntimeError(
                "Current LangGraph installation does not expose graph drawing "
                "helpers. Please upgrade to at least 0.0.39."
            ) from err

        # Swap extension to *.mmd* so callers can identify the content type.
        output_path = output_path.with_suffix(".mmd")
        output_path.write_text(mermaid_text, encoding="utf-8")
        logger.info("LangGraph diagram exported to %s (Mermaid text)", output_path)

    # Optionally show the image to the user for an improved DX.
    if open_file:
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(os.fspath(output_path))  # type: ignore[arg-type]
            elif system == "Darwin":
                subprocess.run(["open", os.fspath(output_path)], check=False)
            else:  # Linux and friends
                subprocess.run(["xdg-open", os.fspath(output_path)], check=False)
        except Exception as open_err:  # pragma: no cover – environment-specific
            logger.debug("Could not open generated diagram automatically: %s", open_err)

    return str(output_path.resolve())

def export_review_graph_png(output_path: str = "review_graph.png") -> str:
    """Generate a PNG image that visualizes the multi-agent review system.

    Parameters
    ----------
    output_path : str, optional
        Filesystem path where the PNG should be written. Defaults to
        ``review_graph.png`` in the current working directory.

    Returns
    -------
    str
        The *absolute* path to the written PNG file.

    Notes
    -----
    This function visualizes the internal structure of the multi-agent
    review system, showing how the specialized agents communicate via
    handoffs to evaluate translation quality.
    """
    from pathlib import Path
    from langgraph.checkpoint.memory import InMemorySaver
    
    # Create the review graph
    review_graph = create_review_agent(checkpointer=InMemorySaver())
    
    try:
        mermaid_png = review_graph.get_graph().draw_mermaid_png()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(mermaid_png)
        return str(output_path.resolve())
    except Exception:
        # Fall back to matplotlib + networkx
        pass

    # Lazy imports
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path
    
    # Ensure the parent directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import networkx as nx
        
        # Create a simplified representation of the review graph
        review_nx_graph = nx.DiGraph()
        
        # Add nodes with descriptive names
        nodes = [
            ("glossary_faithfulness", "Glossary\nFaithfulness\n(Non-LLM)"),
            ("grammar_correctness", "Grammar\nCorrectness\n(LLM)"),
            ("style_adherence", "Style\nAdherence\n(LLM)"),
            ("aggregator", "Score\nAggregator")
        ]
        
        for node_id, label in nodes:
            review_nx_graph.add_node(node_id, label=label)
        
        # Add edges showing the handoff flow
        edges = [
            ("glossary_faithfulness", "grammar_correctness"),
            ("glossary_faithfulness", "aggregator"),  # Early termination path
            ("grammar_correctness", "style_adherence"),
            ("grammar_correctness", "aggregator"),    # Early termination path
            ("style_adherence", "aggregator")
        ]
        
        review_nx_graph.add_edges_from(edges)
        
        # Use a hierarchical layout to show the flow
        pos = {}
        pos["glossary_faithfulness"] = (0, 3)
        pos["grammar_correctness"] = (1, 2)
        pos["style_adherence"] = (2, 1)
        pos["aggregator"] = (3, 0)
        
        plt.figure(figsize=(12, 8))
        
        # Draw nodes with different colors for different types
        node_colors = {
            "glossary_faithfulness": "#FFE6CC",  # Orange for non-LLM
            "grammar_correctness": "#CCE5FF",    # Blue for LLM
            "style_adherence": "#CCE5FF",        # Blue for LLM
            "aggregator": "#E6CCFF"              # Purple for aggregator
        }
        
        for node in review_nx_graph.nodes():
            nx.draw_networkx_nodes(
                review_nx_graph, pos, 
                nodelist=[node],
                node_color=node_colors[node],
                node_size=3000,
                alpha=0.9
            )
        
        # Draw edges with different styles
        # Main flow edges (solid)
        main_edges = [("glossary_faithfulness", "grammar_correctness"),
                     ("grammar_correctness", "style_adherence"),
                     ("style_adherence", "aggregator")]
        
        nx.draw_networkx_edges(
            review_nx_graph, pos,
            edgelist=main_edges,
            edge_color="black",
            arrows=True,
            arrowsize=20,
            arrowstyle="->",
            width=2
        )
        
        # Early termination edges (dashed)
        early_edges = [("glossary_faithfulness", "aggregator"),
                      ("grammar_correctness", "aggregator")]
        
        nx.draw_networkx_edges(
            review_nx_graph, pos,
            edgelist=early_edges,
            edge_color="gray",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            style="dashed",
            width=1
        )
        
        # Draw labels
        labels = {node_id: data["label"] for node_id, data in review_nx_graph.nodes(data=True)}
        nx.draw_networkx_labels(review_nx_graph, pos, labels, font_size=9, font_weight="bold")
        
        # Add title and legend
        plt.title("Multi-Agent Translation Review System", fontsize=16, fontweight="bold", pad=20)
        
        # Create legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#FFE6CC", label="Non-LLM Agent"),
            Patch(facecolor="#CCE5FF", label="LLM Agent"),
            Patch(facecolor="#E6CCFF", label="Aggregator"),
        ]
        plt.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(0, 1))
        
        # Add text annotations
        plt.text(0.5, -0.8, "Solid arrows: Main evaluation flow\nDashed arrows: Early termination paths", 
                ha="center", transform=plt.gca().transAxes, fontsize=10, style="italic")
        
        plt.axis("off")
        plt.tight_layout()
        
    except ModuleNotFoundError:
        # NetworkX not available
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, "Multi-Agent Review System\nVisualization requires 'networkx'", 
                ha="center", va="center", fontsize=14)
        plt.axis("off")

    # Save the figure
    plt.savefig(output_path, format="png", dpi=150, bbox_inches="tight")
    plt.close()

    return str(output_path.resolve())

def export_combined_graph_png(output_path: str = "combined_graph.png") -> str:
    """Generate a PNG showing both the main translation workflow and review system.

    Parameters
    ----------
    output_path : str, optional
        Filesystem path where the PNG should be written. Defaults to
        ``combined_graph.png`` in the current working directory.

    Returns
    -------
    str
        The *absolute* path to the written PNG file.

    Notes
    -----
    This function creates a comprehensive visualization showing how the
    main translation pipeline integrates with the multi-agent review system.
    """
    from pathlib import Path
    
    # Lazy imports
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    # Ensure the parent directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import networkx as nx
        
        # Create combined graph
        combined_graph = nx.DiGraph()
        
        # Main workflow nodes
        main_nodes = [
            ("glossary_filter", "Glossary\nFilter"),
            ("human_review", "Human\nReview"),
            ("translator", "Translator"),
        ]
        
        # Review system nodes (grouped)
        review_nodes = [
            ("review_start", "Review\nSystem"),
            ("glossary_check", "Glossary\nCheck"),
            ("grammar_check", "Grammar\nCheck"),
            ("style_check", "Style\nCheck"),
            ("score_aggregator", "Score\nAggregator")
        ]
        
        # Add all nodes
        for node_id, label in main_nodes + review_nodes:
            combined_graph.add_node(node_id, label=label)
        
        # Main workflow edges
        main_edges = [
            ("glossary_filter", "human_review"),
            ("human_review", "translator"),
            ("translator", "review_start"),
        ]
        
        # Review system edges
        review_edges = [
            ("review_start", "glossary_check"),
            ("glossary_check", "grammar_check"),
            ("grammar_check", "style_check"),
            ("style_check", "score_aggregator"),
        ]
        
        combined_graph.add_edges_from(main_edges + review_edges)
        
        # Position nodes in a clear layout
        pos = {}
        # Main workflow (top row)
        pos["glossary_filter"] = (0, 2)
        pos["human_review"] = (2, 2)
        pos["translator"] = (4, 2)
        
        # Review system (bottom section)
        pos["review_start"] = (6, 2)
        pos["glossary_check"] = (6, 1)
        pos["grammar_check"] = (7, 0.5)
        pos["style_check"] = (8, 0)
        pos["score_aggregator"] = (9, 0.5)
        
        plt.figure(figsize=(16, 10))
        
        # Draw main workflow nodes
        main_node_ids = [node_id for node_id, _ in main_nodes] + ["review_start"]
        nx.draw_networkx_nodes(
            combined_graph, pos,
            nodelist=main_node_ids,
            node_color="#AED6F1",
            node_size=2500,
            alpha=0.9
        )
        
        # Draw review system nodes
        review_node_ids = [node_id for node_id, _ in review_nodes[1:]]  # Exclude review_start
        nx.draw_networkx_nodes(
            combined_graph, pos,
            nodelist=review_node_ids,
            node_color="#F9E79F",
            node_size=2000,
            alpha=0.9
        )
        
        # Draw main workflow edges
        nx.draw_networkx_edges(
            combined_graph, pos,
            edgelist=main_edges,
            edge_color="blue",
            arrows=True,
            arrowsize=20,
            arrowstyle="->",
            width=2
        )
        
        # Draw review system edges  
        nx.draw_networkx_edges(
            combined_graph, pos,
            edgelist=review_edges,
            edge_color="orange",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            width=1.5
        )
        
        # Draw labels
        labels = {node_id: data["label"] for node_id, data in combined_graph.nodes(data=True)}
        nx.draw_networkx_labels(combined_graph, pos, labels, font_size=9, font_weight="bold")
        
        # Add title
        plt.title("Complete Translation Pipeline with Multi-Agent Review", 
                 fontsize=18, fontweight="bold", pad=30)
        
        # Create legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#AED6F1", label="Main Translation Pipeline"),
            Patch(facecolor="#F9E79F", label="Multi-Agent Review System"),
        ]
        plt.legend(handles=legend_elements, loc="upper left", bbox_to_anchor=(0, 1))
        
        # Add section labels
        plt.text(2, 2.5, "Translation Pipeline", ha="center", fontsize=14, fontweight="bold", color="blue")
        plt.text(7.5, 1.2, "Multi-Agent Review", ha="center", fontsize=14, fontweight="bold", color="orange")
        
        plt.axis("off")
        plt.tight_layout()
        
    except ModuleNotFoundError:
        # NetworkX not available
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "Combined Graph Visualization\nrequires 'networkx'", 
                ha="center", va="center", fontsize=14)
        plt.axis("off")

    # Save the figure
    plt.savefig(output_path, format="png", dpi=150, bbox_inches="tight")
    plt.close()

    return str(output_path.resolve())

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Export LangGraph visualizations to PNG files.")
    parser.add_argument("-o", "--output", help="Output PNG file path")
    parser.add_argument("--review", action="store_true", help="Include review node in main graph visualization")
    
    # Visualization type options
    viz_group = parser.add_mutually_exclusive_group()
    viz_group.add_argument("--main-only", action="store_true", default=True,
                          help="Export only the main translation graph (default)")
    viz_group.add_argument("--review-only", action="store_true", 
                          help="Export only the multi-agent review system")
    viz_group.add_argument("--combined", action="store_true",
                          help="Export combined view of main graph and review system")
    viz_group.add_argument("--all", action="store_true",
                          help="Export all visualization types")
    
    args = parser.parse_args()

    if args.all:
        # Export all types with default names
        main_path = export_graph_png("main_graph.png", include_review=args.review)
        review_path = export_review_graph_png("review_system.png")
        combined_path = export_combined_graph_png("combined_workflow.png")
        
        print(f"Main graph saved to {Path(main_path).resolve()}")
        print(f"Review system saved to {Path(review_path).resolve()}")
        print(f"Combined view saved to {Path(combined_path).resolve()}")
        
    elif args.review_only:
        output = args.output or "review_system.png"
        path = export_review_graph_png(output)
        print(f"Review system graph saved to {Path(path).resolve()}")
        
    elif args.combined:
        output = args.output or "combined_workflow.png"
        path = export_combined_graph_png(output)
        print(f"Combined workflow graph saved to {Path(path).resolve()}")
        
    else:  # main-only (default)
        output = args.output or "main_graph.png"
        path = export_graph_png(output, include_review=args.review)
        print(f"Main graph saved to {Path(path).resolve()}") 