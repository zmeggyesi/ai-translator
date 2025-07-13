"""Tests for document parsing and style extraction functionality.

This module tests the new document parsing capabilities for PDF, DOCX, and DOC files,
as well as the integrated style extraction functionality.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import tempfile
import os

from nodes.document_parsers import (
    split_into_sentences,
    parse_document,
    create_document_entries,
    _basic_sentence_split,
)
from nodes.extract_style import (
    extract_style_guide_from_document,
    extract_style_guide_unified,
)


class TestSentenceSplitting:
    """Tests for sentence splitting functionality."""

    def test_basic_sentence_split(self):
        """Test basic regex sentence splitting."""
        text = "This is the first sentence. This is the second! Is this a question?"
        sentences = _basic_sentence_split(text)
        
        assert len(sentences) == 3
        assert sentences[0] == "This is the first sentence"
        assert sentences[1] == "This is the second"
        assert sentences[2] == "Is this a question"

    def test_split_into_sentences_with_nltk(self):
        """Test sentence splitting with NLTK."""
        text = "Dr. Smith went to the U.S.A. He met Mr. Jones. They discussed A.I. technology."
        
        with patch('nodes.document_parsers.sent_tokenize') as mock_tokenize:
            mock_tokenize.return_value = [
                "Dr. Smith went to the U.S.A.",
                "He met Mr. Jones.",
                "They discussed A.I. technology."
            ]
            
            with patch('nodes.document_parsers._ensure_nltk_data'):
                sentences = split_into_sentences(text)
                
                assert len(sentences) == 3
                assert sentences[0] == "Dr. Smith went to the U.S.A."
                assert sentences[1] == "He met Mr. Jones."
                assert sentences[2] == "They discussed A.I. technology."

    def test_split_into_sentences_fallback(self):
        """Test fallback to basic splitting when NLTK fails."""
        text = "Sentence one. Sentence two! Sentence three?"
        
        with patch('nodes.document_parsers.sent_tokenize', side_effect=Exception("NLTK error")):
            sentences = split_into_sentences(text)
            
            assert len(sentences) == 3
            assert sentences[0] == "Sentence one"
            assert sentences[1] == "Sentence two"
            assert sentences[2] == "Sentence three"

    def test_split_empty_text(self):
        """Test splitting empty text."""
        sentences = split_into_sentences("")
        assert sentences == []
        
        sentences = split_into_sentences("   ")
        assert sentences == []


class TestDocumentParsing:
    """Tests for document parsing functionality."""

    def test_parse_document_pdf(self):
        """Test parsing PDF documents."""
        with patch('nodes.document_parsers.parse_pdf') as mock_parse:
            mock_parse.return_value = ["Sentence one.", "Sentence two."]
            
            sentences = parse_document("test.pdf", "pdf")
            
            assert sentences == ["Sentence one.", "Sentence two."]
            mock_parse.assert_called_once_with("test.pdf", "english")

    def test_parse_document_docx(self):
        """Test parsing DOCX documents."""
        with patch('nodes.document_parsers.parse_docx') as mock_parse:
            mock_parse.return_value = ["DOCX sentence one.", "DOCX sentence two."]
            
            sentences = parse_document("test.docx", "docx", "french")
            
            assert sentences == ["DOCX sentence one.", "DOCX sentence two."]
            mock_parse.assert_called_once_with("test.docx", "french")

    def test_parse_document_doc(self):
        """Test parsing DOC documents."""
        with patch('nodes.document_parsers.parse_doc') as mock_parse:
            mock_parse.return_value = ["DOC sentence one.", "DOC sentence two."]
            
            sentences = parse_document("test.doc", "doc")
            
            assert sentences == ["DOC sentence one.", "DOC sentence two."]
            mock_parse.assert_called_once_with("test.doc", "english")

    def test_parse_document_unsupported_type(self):
        """Test parsing unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type: txt"):
            parse_document("test.txt", "txt")

    def test_create_document_entries(self):
        """Test creating TMX-like entries from document sentences."""
        sentences = ["First sentence.", "Second sentence.", "Third sentence."]
        entries = create_document_entries(sentences, "English")
        
        assert len(entries) == 3
        
        # Check first entry
        assert entries[0]["source"] == "First sentence."
        assert entries[0]["target"] == "First sentence."
        assert entries[0]["source_lang"] == "English"
        assert entries[0]["target_lang"] == "English"
        assert entries[0]["usage_count"] == 1
        assert entries[0]["document_sentence"] is True
        assert entries[0]["sentence_index"] == 0
        
        # Check second entry
        assert entries[1]["source"] == "Second sentence."
        assert entries[1]["sentence_index"] == 1
        
        # Check third entry
        assert entries[2]["source"] == "Third sentence."
        assert entries[2]["sentence_index"] == 2

    def test_create_document_entries_empty_sentences(self):
        """Test creating entries with empty sentences."""
        sentences = ["First sentence.", "", "   ", "Second sentence."]
        entries = create_document_entries(sentences, "English")
        
        # Should skip empty sentences
        assert len(entries) == 2
        assert entries[0]["source"] == "First sentence."
        assert entries[1]["source"] == "Second sentence."
        assert entries[1]["sentence_index"] == 3  # Original index preserved


class TestPDFParsing:
    """Tests for PDF parsing functionality."""

    def test_parse_pdf_missing_dependency(self):
        """Test PDF parsing without PyPDF2."""
        with patch('nodes.document_parsers.PyPDF2', None):
            with pytest.raises(ImportError, match="PyPDF2 is required"):
                from nodes.document_parsers import parse_pdf
                parse_pdf("test.pdf")

    def test_parse_pdf_file_not_found(self):
        """Test PDF parsing with non-existent file."""
        with patch('nodes.document_parsers.PyPDF2', MagicMock()):
            from nodes.document_parsers import parse_pdf
            
            with pytest.raises(FileNotFoundError):
                parse_pdf("nonexistent.pdf")

    def test_parse_pdf_success(self):
        """Test successful PDF parsing."""
        mock_pdf_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is a sentence. This is another sentence."
        mock_pdf_reader.pages = [mock_page]
        
        with patch('nodes.document_parsers.PyPDF2') as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_pdf_reader
            
            with patch('nodes.document_parsers.split_into_sentences') as mock_split:
                mock_split.return_value = ["This is a sentence.", "This is another sentence."]
                
                with patch('builtins.open', mock_open()):
                    with patch('pathlib.Path.exists', return_value=True):
                        from nodes.document_parsers import parse_pdf
                        
                        sentences = parse_pdf("test.pdf")
                        
                        assert sentences == ["This is a sentence.", "This is another sentence."]
                        mock_split.assert_called_once()

    def test_parse_pdf_no_content(self):
        """Test PDF parsing with no extractable content."""
        mock_pdf_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf_reader.pages = [mock_page]
        
        with patch('nodes.document_parsers.PyPDF2') as mock_pypdf:
            mock_pypdf.PdfReader.return_value = mock_pdf_reader
            
            with patch('builtins.open', mock_open()):
                with patch('pathlib.Path.exists', return_value=True):
                    from nodes.document_parsers import parse_pdf
                    
                    with pytest.raises(ValueError, match="No text content found"):
                        parse_pdf("test.pdf")


class TestDOCXParsing:
    """Tests for DOCX parsing functionality."""

    def test_parse_docx_missing_dependency(self):
        """Test DOCX parsing without python-docx."""
        with patch('nodes.document_parsers.Document', None):
            with pytest.raises(ImportError, match="python-docx is required"):
                from nodes.document_parsers import parse_docx
                parse_docx("test.docx")

    def test_parse_docx_file_not_found(self):
        """Test DOCX parsing with non-existent file."""
        with patch('nodes.document_parsers.Document', MagicMock()):
            from nodes.document_parsers import parse_docx
            
            with pytest.raises(FileNotFoundError):
                parse_docx("nonexistent.docx")

    def test_parse_docx_success(self):
        """Test successful DOCX parsing."""
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "First paragraph."
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "Second paragraph."
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc.tables = []
        
        with patch('nodes.document_parsers.Document') as mock_document:
            mock_document.return_value = mock_doc
            
            with patch('nodes.document_parsers.split_into_sentences') as mock_split:
                mock_split.return_value = ["First paragraph.", "Second paragraph."]
                
                with patch('pathlib.Path.exists', return_value=True):
                    from nodes.document_parsers import parse_docx
                    
                    sentences = parse_docx("test.docx")
                    
                    assert sentences == ["First paragraph.", "Second paragraph."]
                    mock_split.assert_called_once()


class TestStyleExtractionFromDocuments:
    """Tests for style extraction from document files."""

    def test_extract_style_guide_from_document_success(self):
        """Test successful style guide extraction from document."""
        mock_sentences = ["Sentence one.", "Sentence two.", "Sentence three."]
        mock_style_guide = "# Style Guide\n\nThis is a generated style guide."
        
        with patch('nodes.extract_style.parse_document') as mock_parse:
            mock_parse.return_value = mock_sentences
            
            with patch('nodes.extract_style.infer_style_guide_from_tmx') as mock_infer:
                mock_infer.return_value = mock_style_guide
                
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.write_text') as mock_write:
                        result = extract_style_guide_from_document(
                            "test.pdf", "pdf", "English", "output.md"
                        )
                        
                        assert result == mock_style_guide
                        mock_parse.assert_called_once_with("test.pdf", "pdf", "English")
                        mock_infer.assert_called_once()
                        mock_write.assert_called_once_with(mock_style_guide, encoding="utf-8")

    def test_extract_style_guide_from_document_no_sentences(self):
        """Test style extraction with no sentences found."""
        with patch('nodes.extract_style.parse_document') as mock_parse:
            mock_parse.return_value = []
            
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(ValueError, match="No sentences found"):
                    extract_style_guide_from_document("test.pdf", "pdf", "English")

    def test_extract_style_guide_from_document_file_not_found(self):
        """Test style extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_style_guide_from_document("nonexistent.pdf", "pdf", "English")

    def test_extract_style_guide_unified_tmx(self):
        """Test unified style extraction with TMX file."""
        with patch('nodes.extract_style.extract_style_guide') as mock_extract:
            mock_extract.return_value = "TMX style guide"
            
            result = extract_style_guide_unified(
                "test.tmx", "tmx", "English", "French", "output.md"
            )
            
            assert result == "TMX style guide"
            mock_extract.assert_called_once_with("test.tmx", "English", "French", "output.md")

    def test_extract_style_guide_unified_tmx_no_target_language(self):
        """Test unified style extraction with TMX but no target language."""
        with pytest.raises(ValueError, match="Target language is required for TMX files"):
            extract_style_guide_unified("test.tmx", "tmx", "English")

    def test_extract_style_guide_unified_document(self):
        """Test unified style extraction with document file."""
        with patch('nodes.extract_style.extract_style_guide_from_document') as mock_extract:
            mock_extract.return_value = "Document style guide"
            
            result = extract_style_guide_unified(
                "test.pdf", "pdf", "English", None, "output.md"
            )
            
            assert result == "Document style guide"
            mock_extract.assert_called_once_with("test.pdf", "pdf", "English", "output.md")

    def test_extract_style_guide_unified_unsupported_type(self):
        """Test unified style extraction with unsupported file type."""
        with pytest.raises(ValueError, match="Unsupported file type: txt"):
            extract_style_guide_unified("test.txt", "txt", "English")


def mock_open(content=""):
    """Helper function to create mock file open."""
    return MagicMock()


# Integration tests would go here if we had actual test documents
class TestIntegration:
    """Integration tests for document parsing and style extraction."""
    
    def test_end_to_end_mock(self):
        """Test end-to-end workflow with mocked components."""
        # This would be expanded with actual test documents in a real scenario
        pass