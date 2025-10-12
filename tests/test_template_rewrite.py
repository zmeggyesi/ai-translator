"""Tests for style guide template rewriting functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from nodes.style_guide import rewrite_style_guide_template
from nodes.extract_style import (
    extract_style_guide_from_urls,
    extract_style_guide_from_document,
    extract_style_guide,
    extract_style_guide_unified,
)


SAMPLE_TEMPLATE = """# Style Guide Template

## Tone of Voice
- Professional
- Friendly
- Engaging

## Writing Guidelines
- Use clear language
- Be concise
- Active voice preferred

## Formatting
- Headers use title case
- Lists use bullets
"""


class TestTemplateRewriting:
    """Tests for rewrite_style_guide_template function."""

    def test_rewrite_template_success(self, tmp_path):
        """Test successful template rewriting."""
        # Create template file
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        # Mock TMX memory
        tmx_memory = {
            "entries": [
                {"source": "Hello world", "target": "Hola mundo", "usage_count": 5},
                {"source": "Good morning", "target": "Buenos días", "usage_count": 3},
                {"source": "Thank you", "target": "Gracias", "usage_count": 4},
            ]
        }

        # Mock LLM
        with patch('nodes.style_guide.os.getenv', return_value='fake-key'):
            with patch('nodes.style_guide.ChatOpenAI') as mock_llm_class:
                mock_llm = Mock()
                mock_response = Mock()
                mock_response.content = "# Rewritten Style Guide\n\nBased on analyzed content..."
                mock_llm.invoke.return_value = mock_response
                mock_llm_class.return_value = mock_llm

                result = rewrite_style_guide_template(
                    tmx_memory,
                    str(template_file)
                )

                assert "Rewritten Style Guide" in result
                assert mock_llm.invoke.called

    def test_rewrite_template_no_entries(self, tmp_path):
        """Test error when TMX memory has no entries."""
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        tmx_memory = {"entries": []}

        with pytest.raises(ValueError, match="does not contain any entries"):
            rewrite_style_guide_template(tmx_memory, str(template_file))

    def test_rewrite_template_invalid_tmx_memory(self, tmp_path):
        """Test error with invalid TMX memory."""
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        with pytest.raises(ValueError, match="must be a dictionary"):
            rewrite_style_guide_template(None, str(template_file))

        with pytest.raises(ValueError, match="must be a dictionary"):
            rewrite_style_guide_template("not a dict", str(template_file))

    def test_rewrite_template_file_not_found(self):
        """Test error when template file doesn't exist."""
        tmx_memory = {
            "entries": [
                {"source": "Test", "target": "Prueba", "usage_count": 1}
            ]
        }

        with pytest.raises(FileNotFoundError, match="Template file not found"):
            rewrite_style_guide_template(tmx_memory, "/nonexistent/template.md")

    def test_rewrite_template_no_api_key(self, tmp_path):
        """Test error when no API key is available."""
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        tmx_memory = {
            "entries": [
                {"source": "Test", "target": "Prueba", "usage_count": 1}
            ]
        }

        with patch('nodes.style_guide.os.getenv', return_value=None):
            with pytest.raises(RuntimeError, match="requires an OpenAI API key"):
                rewrite_style_guide_template(tmx_memory, str(template_file))

    def test_rewrite_template_llm_failure(self, tmp_path):
        """Test error handling when LLM call fails."""
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        tmx_memory = {
            "entries": [
                {"source": "Test", "target": "Prueba", "usage_count": 1}
            ]
        }

        with patch('nodes.style_guide.os.getenv', return_value='fake-key'):
            with patch('nodes.style_guide.ChatOpenAI') as mock_llm_class:
                mock_llm = Mock()
                mock_llm.invoke.side_effect = Exception("API Error")
                mock_llm_class.return_value = mock_llm

                with pytest.raises(RuntimeError, match="template rewriting failed"):
                    rewrite_style_guide_template(tmx_memory, str(template_file))

    def test_rewrite_template_preserves_placeholders(self, tmp_path):
        """Test that template placeholders are preserved."""
        template_with_placeholders = """# Translation Guide

Use {{targetLanguage}} language conventions.
Address {{audience}} appropriately.
"""
        template_file = tmp_path / "template.md"
        template_file.write_text(template_with_placeholders)

        tmx_memory = {
            "entries": [
                {"source": "Hello", "target": "Hola", "usage_count": 1}
            ]
        }

        with patch('nodes.style_guide.os.getenv', return_value='fake-key'):
            with patch('nodes.style_guide.ChatOpenAI') as mock_llm_class:
                mock_llm = Mock()
                mock_response = Mock()
                mock_response.content = template_with_placeholders  # Preserved
                mock_llm.invoke.return_value = mock_response
                mock_llm_class.return_value = mock_llm

                result = rewrite_style_guide_template(
                    tmx_memory,
                    str(template_file)
                )

                assert "{{targetLanguage}}" in result
                assert "{{audience}}" in result


class TestURLExtractionWithTemplate:
    """Tests for URL extraction with template rewriting."""

    @patch('nodes.extract_style.rewrite_style_guide_template')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_from_urls_with_template(
        self, mock_load_urls, mock_fetch, mock_rewrite, tmp_path
    ):
        """Test URL extraction with template rewriting."""
        # Setup
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)
        output_file = tmp_path / "output.md"

        mock_load_urls.return_value = ["https://example.com/page1"]
        mock_fetch.return_value = "Sample content with multiple sentences. More content here."
        mock_rewrite.return_value = "# Rewritten Style Guide"

        # Execute
        result = extract_style_guide_from_urls(
            "urls.txt",
            "english",
            str(output_file),
            template_path=str(template_file)
        )

        # Verify
        assert result == "# Rewritten Style Guide"
        mock_rewrite.assert_called_once()
        assert output_file.exists()
        assert output_file.read_text() == "# Rewritten Style Guide"

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_from_urls_without_template(
        self, mock_load_urls, mock_fetch, mock_infer, tmp_path
    ):
        """Test URL extraction without template (generates new guide)."""
        output_file = tmp_path / "output.md"

        mock_load_urls.return_value = ["https://example.com/page1"]
        mock_fetch.return_value = "Sample content with sentences."
        mock_infer.return_value = "# Generated Style Guide"

        result = extract_style_guide_from_urls(
            "urls.txt",
            "english",
            str(output_file)
        )

        assert result == "# Generated Style Guide"
        mock_infer.assert_called_once()


class TestDocumentExtractionWithTemplate:
    """Tests for document extraction with template rewriting."""

    @patch('nodes.extract_style.rewrite_style_guide_template')
    @patch('nodes.extract_style.parse_document')
    def test_extract_from_document_with_template(
        self, mock_parse, mock_rewrite, tmp_path
    ):
        """Test document extraction with template rewriting."""
        # Create dummy document and template
        doc_file = tmp_path / "doc.pdf"
        doc_file.write_text("dummy pdf content")
        
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)
        
        output_file = tmp_path / "output.md"

        mock_parse.return_value = [
            "First sentence from document.",
            "Second sentence from document.",
            "Third sentence from document."
        ]
        mock_rewrite.return_value = "# Rewritten Document Style Guide"

        result = extract_style_guide_from_document(
            str(doc_file),
            "pdf",
            "english",
            str(output_file),
            template_path=str(template_file)
        )

        assert result == "# Rewritten Document Style Guide"
        mock_rewrite.assert_called_once()
        assert output_file.exists()


class TestTMXExtractionWithTemplate:
    """Tests for TMX extraction with template rewriting."""

    @patch('nodes.extract_style.rewrite_style_guide_template')
    @patch('nodes.extract_style.parse_tmx_file')
    def test_extract_from_tmx_with_template(
        self, mock_parse_tmx, mock_rewrite, tmp_path
    ):
        """Test TMX extraction with template rewriting."""
        # Create dummy TMX and template files
        tmx_file = tmp_path / "sample.tmx"
        tmx_file.write_text("<tmx></tmx>")
        
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)
        
        output_file = tmp_path / "output.md"

        mock_parse_tmx.return_value = {
            "en->es": [
                {"source": "Hello", "target": "Hola", "usage_count": 5},
                {"source": "Goodbye", "target": "Adiós", "usage_count": 3}
            ]
        }
        mock_rewrite.return_value = "# Rewritten TMX Style Guide"

        result = extract_style_guide(
            str(tmx_file),
            "en",
            "es",
            str(output_file),
            template_path=str(template_file)
        )

        assert result == "# Rewritten TMX Style Guide"
        mock_rewrite.assert_called_once()


class TestUnifiedExtractionWithTemplate:
    """Tests for unified extraction with template support."""

    @patch('nodes.extract_style.extract_style_guide_from_urls')
    def test_unified_urls_with_template(self, mock_extract):
        """Test unified extraction for URLs with template."""
        mock_extract.return_value = "# Rewritten Style Guide"

        result = extract_style_guide_unified(
            "urls.txt",
            "urls",
            "english",
            output_path="output.md",
            template_path="template.md"
        )

        assert result == "# Rewritten Style Guide"
        # Verify template_path was passed (4th positional arg or keyword arg)
        mock_extract.assert_called_once()
        call_args, call_kwargs = mock_extract.call_args
        # Check positional args: (file_path, source_language, output_path, max_urls, template_path)
        assert call_args[4] == "template.md" or call_kwargs.get('template_path') == "template.md"

    @patch('nodes.extract_style.extract_style_guide_from_document')
    def test_unified_document_with_template(self, mock_extract):
        """Test unified extraction for documents with template."""
        mock_extract.return_value = "# Rewritten Style Guide"

        result = extract_style_guide_unified(
            "doc.pdf",
            "pdf",
            "english",
            output_path="output.md",
            template_path="template.md"
        )

        assert result == "# Rewritten Style Guide"
        # Verify template_path was passed (4th positional arg or keyword arg)
        mock_extract.assert_called_once()
        call_args, call_kwargs = mock_extract.call_args
        # Check positional args: (document_path, file_type, source_language, output_path, template_path)
        assert call_args[4] == "template.md" or call_kwargs.get('template_path') == "template.md"

    @patch('nodes.extract_style.extract_style_guide')
    def test_unified_tmx_with_template(self, mock_extract):
        """Test unified extraction for TMX with template."""
        mock_extract.return_value = "# Rewritten Style Guide"

        result = extract_style_guide_unified(
            "sample.tmx",
            "tmx",
            "en",
            target_language="es",
            output_path="output.md",
            template_path="template.md"
        )

        assert result == "# Rewritten Style Guide"
        # Verify template_path was passed (4th positional arg or keyword arg)
        mock_extract.assert_called_once()
        call_args, call_kwargs = mock_extract.call_args
        # Check positional args: (tmx_path, source_language, target_language, output_path, template_path)
        assert call_args[4] == "template.md" or call_kwargs.get('template_path') == "template.md"


class TestIntegration:
    """Integration tests for template rewriting."""

    @patch('nodes.style_guide.ChatOpenAI')
    @patch('nodes.style_guide.os.getenv', return_value='fake-key')
    @patch('nodes.extract_style.requests')
    def test_full_workflow_urls_with_template(
        self, mock_requests, mock_getenv, mock_llm_class, tmp_path
    ):
        """Test complete workflow: URLs -> analyze -> rewrite template -> output."""
        # Create URLs file
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://example.com/page1\n")

        # Create template file
        template_file = tmp_path / "template.md"
        template_file.write_text(SAMPLE_TEMPLATE)

        # Create output path
        output_file = tmp_path / "output.md"

        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = """
            <html><body>
                <p>Professional technical writing with precision.</p>
                <p>Clear and concise communication style.</p>
            </body></html>
        """
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        # Mock LLM for template rewriting
        mock_llm = Mock()
        mock_llm_response = Mock()
        mock_llm_response.content = """# Adapted Style Guide

## Tone of Voice
- Technical and precise
- Professional
- Clear and concise

## Writing Guidelines
- Use technical terminology appropriately
- Be direct and specific
- Focus on clarity
"""
        mock_llm.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        # Execute
        result = extract_style_guide_from_urls(
            str(urls_file),
            "english",
            str(output_file),
            template_path=str(template_file)
        )

        # Verify
        assert "Adapted Style Guide" in result
        assert output_file.exists()
        assert "Technical and precise" in output_file.read_text()

