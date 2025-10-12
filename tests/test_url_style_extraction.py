"""Tests for URL-based style guide extraction functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from nodes.extract_style import (
    _extract_text_from_html,
    _fetch_url_content,
    _load_urls_from_file,
    extract_style_guide_from_urls,
    extract_style_guide_unified,
)


# Sample HTML content for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <script>console.log('test');</script>
    <style>body { color: red; }</style>
</head>
<body>
    <header>Navigation Menu</header>
    <nav>Home | About | Contact</nav>
    <main>
        <h1>Welcome to Our Site</h1>
        <p>This is a sample paragraph with some content.</p>
        <p>Another paragraph with more information about our services.</p>
        <p>We provide high-quality solutions for your business needs.</p>
    </main>
    <footer>Copyright 2024</footer>
</body>
</html>
"""

EXPECTED_TEXT = "Welcome to Our Site This is a sample paragraph with some content. Another paragraph with more information about our services. We provide high-quality solutions for your business needs."


class TestHTMLTextExtraction:
    """Tests for HTML text extraction."""

    def test_extract_text_from_html_basic(self):
        """Test basic HTML text extraction."""
        text = _extract_text_from_html(SAMPLE_HTML)
        assert "Welcome to Our Site" in text
        assert "sample paragraph" in text
        assert "high-quality solutions" in text
        # Script and style content should be removed
        assert "console.log" not in text
        assert "color: red" not in text

    def test_extract_text_from_html_removes_navigation(self):
        """Test that navigation elements are removed."""
        text = _extract_text_from_html(SAMPLE_HTML)
        # Header, nav, and footer should be removed
        assert "Navigation Menu" not in text
        assert "Home | About | Contact" not in text
        assert "Copyright 2024" not in text

    def test_extract_text_from_html_empty(self):
        """Test extraction from empty HTML."""
        html = "<html><body></body></html>"
        text = _extract_text_from_html(html)
        assert text == ""

    def test_extract_text_from_html_no_beautifulsoup(self):
        """Test error when BeautifulSoup is not available."""
        with patch('nodes.extract_style.BeautifulSoup', None):
            with pytest.raises(ImportError, match="beautifulsoup4 is required"):
                _extract_text_from_html(SAMPLE_HTML)


class TestURLFetching:
    """Tests for URL fetching functionality."""

    @patch('nodes.extract_style.requests')
    def test_fetch_url_content_success(self, mock_requests):
        """Test successful URL content fetching."""
        # Mock the response
        mock_response = Mock()
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        text = _fetch_url_content("https://example.com")
        
        assert "Welcome to Our Site" in text
        assert "sample paragraph" in text
        mock_requests.get.assert_called_once()
        
        # Check that User-Agent header was set
        call_kwargs = mock_requests.get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'User-Agent' in call_kwargs['headers']

    @patch('nodes.extract_style.requests')
    def test_fetch_url_content_with_timeout(self, mock_requests):
        """Test URL fetching with timeout parameter."""
        mock_response = Mock()
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        _fetch_url_content("https://example.com", timeout=30)
        
        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs['timeout'] == 30

    @patch('nodes.extract_style.requests')
    def test_fetch_url_content_empty_html(self, mock_requests):
        """Test fetching URL with no text content."""
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        text = _fetch_url_content("https://example.com")
        assert text == ""

    @patch('nodes.extract_style.requests')
    def test_fetch_url_content_http_error(self, mock_requests):
        """Test URL fetching with HTTP error."""
        mock_requests.get.side_effect = Exception("HTTP 404 Not Found")

        with pytest.raises(Exception, match="HTTP 404"):
            _fetch_url_content("https://example.com/notfound")

    def test_fetch_url_content_no_requests(self):
        """Test error when requests library is not available."""
        with patch('nodes.extract_style.requests', None):
            with pytest.raises(ImportError, match="requests is required"):
                _fetch_url_content("https://example.com")


class TestURLFileLoading:
    """Tests for loading URLs from file."""

    def test_load_urls_from_file_basic(self, tmp_path):
        """Test loading URLs from a basic file."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://example.com/page1\n"
            "https://example.com/page2\n"
            "https://example.com/page3\n"
        )

        urls = _load_urls_from_file(str(urls_file))
        assert len(urls) == 3
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        assert "https://example.com/page3" in urls

    def test_load_urls_from_file_with_comments(self, tmp_path):
        """Test loading URLs with comments."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "# This is a comment\n"
            "https://example.com/page1\n"
            "# Another comment\n"
            "https://example.com/page2\n"
        )

        urls = _load_urls_from_file(str(urls_file))
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    def test_load_urls_from_file_with_empty_lines(self, tmp_path):
        """Test loading URLs with empty lines."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://example.com/page1\n"
            "\n"
            "https://example.com/page2\n"
            "\n\n"
            "https://example.com/page3\n"
        )

        urls = _load_urls_from_file(str(urls_file))
        assert len(urls) == 3

    def test_load_urls_from_file_http_urls(self, tmp_path):
        """Test loading both HTTP and HTTPS URLs."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "http://example.com/page1\n"
            "https://example.com/page2\n"
        )

        urls = _load_urls_from_file(str(urls_file))
        assert len(urls) == 2
        assert "http://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    def test_load_urls_from_file_invalid_urls(self, tmp_path):
        """Test that invalid URLs are skipped."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://example.com/valid\n"
            "not-a-url\n"
            "ftp://example.com/invalid\n"
            "https://example.com/valid2\n"
        )

        urls = _load_urls_from_file(str(urls_file))
        assert len(urls) == 2
        assert "https://example.com/valid" in urls
        assert "https://example.com/valid2" in urls

    def test_load_urls_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError, match="URLs file not found"):
            _load_urls_from_file("/nonexistent/urls.txt")

    def test_load_urls_from_file_no_valid_urls(self, tmp_path):
        """Test file with no valid URLs."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "# Only comments\n"
            "# And invalid URLs\n"
            "not-a-url\n"
            "ftp://example.com\n"
        )

        with pytest.raises(ValueError, match="No valid URLs found"):
            _load_urls_from_file(str(urls_file))


class TestStyleGuideFromURLs:
    """Tests for complete style guide extraction from URLs."""

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_success(
        self, mock_load_urls, mock_fetch, mock_infer, tmp_path
    ):
        """Test successful style guide extraction from URLs."""
        # Mock URL loading
        mock_load_urls.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]

        # Mock content fetching
        mock_fetch.side_effect = [
            "This is the first page content. It has multiple sentences. "
            "Each sentence contributes to the style.",
            "This is the second page content. It also has sentences. "
            "Together they form a comprehensive corpus.",
        ]

        # Mock style guide inference
        mock_infer.return_value = "# Style Guide\n\nThis is a generated style guide."

        output_path = tmp_path / "style.md"
        result = extract_style_guide_from_urls(
            "urls.txt",
            "english",
            str(output_path)
        )

        assert result == "# Style Guide\n\nThis is a generated style guide."
        assert output_path.exists()
        assert output_path.read_text() == "# Style Guide\n\nThis is a generated style guide."

        # Verify calls
        mock_load_urls.assert_called_once_with("urls.txt")
        assert mock_fetch.call_count == 2
        mock_infer.assert_called_once()

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_with_max_urls(
        self, mock_load_urls, mock_fetch, mock_infer, tmp_path
    ):
        """Test style guide extraction with URL limit."""
        mock_load_urls.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4",
        ]

        mock_fetch.return_value = "Sample content with sentences. More content here."
        mock_infer.return_value = "# Style Guide"

        output_path = tmp_path / "style.md"
        extract_style_guide_from_urls(
            "urls.txt",
            "english",
            str(output_path),
            max_urls=2
        )

        # Should only fetch first 2 URLs
        assert mock_fetch.call_count == 2

    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_partial_failure(
        self, mock_load_urls, mock_fetch, tmp_path
    ):
        """Test handling of partial URL fetch failures."""
        mock_load_urls.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        # First URL succeeds, second fails, third succeeds
        def fetch_side_effect(url):
            if "page2" in url:
                raise Exception("Connection error")
            return "Sample content with multiple sentences here."

        mock_fetch.side_effect = fetch_side_effect

        # Should not raise error as long as at least one URL succeeds
        with patch('nodes.extract_style.infer_style_guide_from_tmx') as mock_infer:
            mock_infer.return_value = "# Style Guide"
            output_path = tmp_path / "style.md"
            result = extract_style_guide_from_urls(
                "urls.txt",
                "english",
                str(output_path)
            )
            assert result == "# Style Guide"

    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_all_failures(
        self, mock_load_urls, mock_fetch
    ):
        """Test error when all URL fetches fail."""
        mock_load_urls.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]

        mock_fetch.side_effect = Exception("Connection error")

        with pytest.raises(ValueError, match="Failed to extract content from any URLs"):
            extract_style_guide_from_urls("urls.txt", "english")

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_no_sentences(
        self, mock_load_urls, mock_fetch, mock_infer
    ):
        """Test error when no sentences can be extracted."""
        mock_load_urls.return_value = ["https://example.com/page1"]
        # Return content that won't produce sentences
        mock_fetch.return_value = ""

        with pytest.raises(ValueError, match="Failed to extract content from any URLs"):
            extract_style_guide_from_urls("urls.txt", "english")

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style._fetch_url_content')
    @patch('nodes.extract_style._load_urls_from_file')
    def test_extract_style_guide_from_urls_inference_failure(
        self, mock_load_urls, mock_fetch, mock_infer
    ):
        """Test error when style guide inference fails."""
        mock_load_urls.return_value = ["https://example.com/page1"]
        mock_fetch.return_value = "Sample content with sentences."
        mock_infer.return_value = ""  # Empty result

        with pytest.raises(ValueError, match="Failed to generate style guide"):
            extract_style_guide_from_urls("urls.txt", "english")


class TestUnifiedExtraction:
    """Tests for unified style guide extraction with URLs support."""

    @patch('nodes.extract_style.extract_style_guide_from_urls')
    def test_unified_extraction_urls(self, mock_extract_urls):
        """Test unified extraction with 'urls' file type."""
        mock_extract_urls.return_value = "# Style Guide from URLs"

        result = extract_style_guide_unified(
            "urls.txt",
            "urls",
            "english",
            output_path="style.md"
        )

        assert result == "# Style Guide from URLs"
        mock_extract_urls.assert_called_once_with(
            "urls.txt",
            "english",
            "style.md",
            None,  # max_urls
            None   # template_path
        )

    @patch('nodes.extract_style.extract_style_guide_from_urls')
    def test_unified_extraction_urls_with_max_urls(self, mock_extract_urls):
        """Test unified extraction with max_urls parameter."""
        mock_extract_urls.return_value = "# Style Guide"

        result = extract_style_guide_unified(
            "urls.txt",
            "urls",
            "english",
            max_urls=5
        )

        assert result == "# Style Guide"
        # Check that max_urls was passed correctly
        call_args = mock_extract_urls.call_args[0]
        assert call_args[3] == 5  # max_urls is the 4th positional arg

    def test_unified_extraction_invalid_file_type(self):
        """Test error with invalid file type."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_style_guide_unified(
                "file.xyz",
                "xyz",
                "english"
            )

    def test_unified_extraction_urls_case_insensitive(self):
        """Test that file type matching is case insensitive."""
        with patch('nodes.extract_style.extract_style_guide_from_urls') as mock_extract:
            mock_extract.return_value = "# Style Guide"
            
            # Test uppercase
            extract_style_guide_unified("urls.txt", "URLS", "english")
            mock_extract.assert_called_once()


class TestIntegration:
    """Integration tests with actual file operations (mocked network)."""

    @patch('nodes.extract_style.infer_style_guide_from_tmx')
    @patch('nodes.extract_style.requests')
    def test_full_workflow_with_real_files(
        self, mock_requests, mock_infer, tmp_path
    ):
        """Test complete workflow with file I/O."""
        # Create URLs file
        urls_file = tmp_path / "test_urls.txt"
        urls_file.write_text(
            "# Sample URLs for testing\n"
            "https://example.com/page1\n"
            "https://example.com/page2\n"
        )

        # Mock HTTP responses
        def get_response(url, **kwargs):
            response = Mock()
            if "page1" in url:
                response.text = """
                    <html><body>
                        <p>Professional services with attention to detail.</p>
                        <p>We ensure quality and reliability.</p>
                    </body></html>
                """
            else:
                response.text = """
                    <html><body>
                        <p>Our commitment to excellence drives results.</p>
                        <p>Customer satisfaction is our priority.</p>
                    </body></html>
                """
            response.raise_for_status = Mock()
            return response

        mock_requests.get.side_effect = get_response

        # Mock style guide inference
        mock_infer.return_value = (
            "# Professional Style Guide\n\n"
            "- Use formal tone\n"
            "- Focus on quality and reliability\n"
        )

        # Execute
        output_path = tmp_path / "extracted_style.md"
        result = extract_style_guide_from_urls(
            str(urls_file),
            "english",
            str(output_path)
        )

        # Verify
        assert "Professional Style Guide" in result
        assert output_path.exists()
        assert output_path.read_text() == result
        assert mock_requests.get.call_count == 2

