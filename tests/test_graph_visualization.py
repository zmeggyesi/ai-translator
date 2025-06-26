from pathlib import Path

from graph import export_graph_png

def test_export_graph_png_creates_file(tmp_path):
    """The function should create a non-empty PNG file at the requested path."""
    output_file = tmp_path / "graph.png"

    generated_path = export_graph_png(output_path=str(output_file))

    # Ensure the returned path matches the requested one (after resolution)
    assert Path(generated_path) == output_file.resolve()

    # The file should exist and be non-empty
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Clean-up is handled automatically by pytest's tmp_path fixture. 