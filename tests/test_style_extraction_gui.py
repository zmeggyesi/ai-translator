"""
Tests for the style extraction GUI functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
from tkinter import ttk
import threading
import tempfile
from pathlib import Path

from gui.components.style_extraction_tab import StyleExtractionTabController
from gui.services.style_extraction_service import StyleExtractionService


class TestStyleExtractionTab(unittest.TestCase):
    """Test suite for style extraction tab functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window during tests
        
        # Create test frame
        self.parent_frame = ttk.Frame(self.root)
        
        # Mock callbacks
        self.status_callback = Mock()
        self.progress_callback = Mock()
        
        # Create controller
        self.controller = StyleExtractionTabController(
            self.parent_frame,
            self.status_callback,
            self.progress_callback
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.root.destroy()
    
    def test_initialization(self):
        """Test that the controller initializes correctly."""
        self.assertIsInstance(self.controller.service, StyleExtractionService)
        self.assertIsNone(self.controller.current_thread)
        
        # Check that UI elements exist
        self.assertIsNotNone(self.controller.input_file_entry)
        self.assertIsNotNone(self.controller.output_file_entry)
        self.assertIsNotNone(self.controller.file_type_var)
        self.assertIsNotNone(self.controller.source_lang_combo)
        self.assertIsNotNone(self.controller.target_lang_combo)
        self.assertIsNotNone(self.controller.preview_text)
        
        # Check that progress elements exist
        self.assertIsNotNone(self.controller.progress_section)
        self.assertIsNotNone(self.controller.progress_bar)
        self.assertIsNotNone(self.controller.progress_spinner)
        self.assertIsNotNone(self.controller.progress_status_label)
        self.assertIsNotNone(self.controller.cancel_button)
    
    def test_progress_visibility(self):
        """Test progress section show/hide functionality."""
        # Initially hidden
        self.assertFalse(self.controller.progress_section.winfo_viewable())
        
        # Show progress
        self.controller.show_progress(True)
        self.root.update()
        
        # Should be visible now
        slaves = self.controller.container.pack_slaves()
        self.assertIn(self.controller.progress_section, slaves)
        
        # Hide progress
        self.controller.show_progress(False)
        self.root.update()
        
        # Should be hidden again
        slaves = self.controller.container.pack_slaves()
        self.assertNotIn(self.controller.progress_section, slaves)
    
    def test_progress_mode_switching(self):
        """Test switching between indeterminate and determinate progress modes."""
        # Show progress first
        self.controller.show_progress(True)
        self.root.update()
        
        # Get the progress frame (parent of progress widgets)
        progress_frame = self.controller.progress_bar.master
        
        # Start with indeterminate
        self.controller.set_progress_mode('indeterminate')
        self.root.update()
        
        # Check which widgets are packed in the progress frame
        progress_slaves = progress_frame.pack_slaves()
        spinner_packed = self.controller.progress_spinner in progress_slaves
        bar_packed = self.controller.progress_bar in progress_slaves
        
        # Spinner should be packed, progress bar should not be
        self.assertTrue(spinner_packed, "Spinner should be visible in indeterminate mode")
        self.assertFalse(bar_packed, "Progress bar should be hidden in indeterminate mode")
        
        # Switch to determinate
        self.controller.set_progress_mode('determinate')
        self.root.update()
        
        # Check layout again
        progress_slaves = progress_frame.pack_slaves()
        spinner_packed = self.controller.progress_spinner in progress_slaves
        bar_packed = self.controller.progress_bar in progress_slaves
        
        # Progress bar should be packed, spinner should not be
        self.assertTrue(bar_packed, "Progress bar should be visible in determinate mode")
        self.assertFalse(spinner_packed, "Spinner should be hidden in determinate mode")
    
    def test_progress_updates(self):
        """Test progress update functionality."""
        # Show progress
        self.controller.show_progress(True)
        
        # Test indeterminate start (0%)
        self.controller.update_extraction_progress(0)
        self.assertEqual(self.controller.progress_status_label.cget("text"), "🔄 Initializing extraction...")
        
        # Test determinate progress (50%)
        self.controller.update_extraction_progress(50)
        self.assertEqual(self.controller.progress_bar['value'], 50)
        self.assertEqual(self.controller.progress_percent_label.cget("text"), "50%")
        
        # Test completion (100%)
        self.controller.update_extraction_progress(100)
        self.assertEqual(self.controller.progress_bar['value'], 100)
        self.assertEqual(self.controller.progress_percent_label.cget("text"), "100%")
        self.assertEqual(self.controller.progress_status_label.cget("text"), "✅ Extraction completed successfully!")
        
        # Verify main app progress callback was called
        self.progress_callback.assert_called_with(100)
    
    def test_file_type_change_tmx(self):
        """Test UI behavior when TMX file type is selected."""
        self.controller.file_type_var.set("tmx")
        self.controller.on_file_type_changed()
        
        # Force update of the GUI
        self.root.update()
        
        # Target language frame should be visible for TMX
        # Check if frame is packed (visible in layout)
        slaves = self.controller.target_lang_frame.master.pack_slaves()
        self.assertIn(self.controller.target_lang_frame, slaves)
    
    def test_file_type_change_document(self):
        """Test UI behavior when document file type is selected."""
        # First make target language visible
        self.controller.file_type_var.set("tmx")
        self.controller.on_file_type_changed()
        self.root.update()
        
        # Verify it's visible first
        slaves = self.controller.target_lang_frame.master.pack_slaves()
        self.assertIn(self.controller.target_lang_frame, slaves)
        
        # Then change to document type
        self.controller.file_type_var.set("pdf")
        self.controller.on_file_type_changed()
        self.root.update()
        
        # Target language frame should be hidden for documents
        slaves = self.controller.target_lang_frame.master.pack_slaves()
        self.assertNotIn(self.controller.target_lang_frame, slaves)
    
    def test_input_file_suggestion(self):
        """Test automatic output file suggestion."""
        # Set input file
        self.controller.input_file_entry.insert(0, "/path/to/document.pdf")
        self.controller.on_input_file_changed()
        
        # Check that output file is suggested
        output_file = self.controller.output_file_entry.get()
        self.assertIn("document_style_guide.md", output_file)
    
    def test_clear_form(self):
        """Test form clearing functionality."""
        # Set some values
        self.controller.input_file_entry.insert(0, "test.tmx")
        self.controller.output_file_entry.insert(0, "output.md")
        self.controller.file_type_var.set("pdf")
        
        # Show progress
        self.controller.show_progress(True)
        
        # Clear form
        self.controller.clear_form()
        
        # Check that values are reset
        self.assertEqual(self.controller.input_file_entry.get(), "")
        self.assertEqual(self.controller.output_file_entry.get(), "")
        self.assertEqual(self.controller.file_type_var.get(), "tmx")
        self.assertEqual(self.controller.source_lang_combo.get(), "English")
        self.assertEqual(self.controller.target_lang_combo.get(), "Spanish")
        
        # Progress should be hidden
        slaves = self.controller.container.pack_slaves()
        self.assertNotIn(self.controller.progress_section, slaves)
    
    def test_preview_update(self):
        """Test preview area update functionality."""
        test_content = "# Test Style Guide\n\nThis is a test style guide."
        
        self.controller.update_preview(test_content)
        
        # Check that content is displayed
        preview_content = self.controller.preview_text.get(1.0, tk.END).strip()
        self.assertEqual(preview_content, test_content)
        
        # Check that buttons are enabled
        self.assertEqual(str(self.controller.save_preview_button['state']), 'normal')
        self.assertEqual(str(self.controller.copy_preview_button['state']), 'normal')
    
    def test_cancel_extraction(self):
        """Test extraction cancellation."""
        # Mock a running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.controller.current_thread = mock_thread
        
        # Show progress first
        self.controller.show_progress(True)
        
        # Test cancel
        self.controller.cancel_extraction()
        
        # Should update status and disable cancel button
        self.assertIn("Cancellation requested", self.controller.progress_status_label.cget("text"))
        self.assertEqual(str(self.controller.cancel_button['state']), 'disabled')
    
    def test_extract_style_validation_no_input(self):
        """Test validation when no input file is provided."""
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.controller.extract_style()
            mock_error.assert_called_with("Error", "Please select an input file")
    
    def test_extract_style_validation_tmx_no_target(self):
        """Test validation for TMX files without target language."""
        # Set up form for TMX extraction
        self.controller.input_file_entry.insert(0, "test.tmx")
        self.controller.file_type_var.set("tmx")
        self.controller.source_lang_combo.set("English")
        self.controller.target_lang_combo.set("")  # No target language
        
        with patch('tkinter.messagebox.showerror') as mock_error:
            with patch.object(Path, 'exists', return_value=True):
                self.controller.extract_style()
                mock_error.assert_called_with("Error", "Target language is required for TMX files")
    
    @patch('gui.components.style_extraction_tab.Path')
    def test_extract_style_success(self, mock_path):
        """Test successful style extraction with progress updates."""
        # Mock file existence
        mock_path.return_value.exists.return_value = True
        
        # Set up form
        self.controller.input_file_entry.insert(0, "test.pdf")
        self.controller.file_type_var.set("pdf")
        self.controller.source_lang_combo.set("English")
        
        # Mock service
        mock_result = {
            "success": True,
            "style_guide": "# Test Style Guide",
            "output_file": "test_style_guide.md"
        }
        
        with patch.object(self.controller.service, 'validate_config', return_value=(True, "")):
            with patch.object(self.controller.service, 'extract_style_async') as mock_async:
                # Mock the async method to call completion callback immediately
                def mock_extract_async(*args, **kwargs):
                    completion_callback = kwargs.get('completion_callback')
                    if completion_callback:
                        completion_callback(mock_result)
                    return Mock()
                
                mock_async.side_effect = mock_extract_async
                
                self.controller.extract_style()
                
                # Verify service was called
                mock_async.assert_called_once()
                
                # Verify progress was shown during extraction
                # (Note: In the mock, completion_callback is called immediately,
                # so progress section will be hidden again)


class TestStyleExtractionService(unittest.TestCase):
    """Test suite for style extraction service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = StyleExtractionService()
    
    def test_validate_config_missing_input(self):
        """Test config validation with missing input file."""
        config = {"file_type": "pdf", "source_language": "English"}
        is_valid, error = self.service.validate_config(config)
        
        self.assertFalse(is_valid)
        self.assertIn("Input file is required", error)
    
    def test_validate_config_invalid_file_type(self):
        """Test config validation with invalid file type."""
        config = {
            "input_file": "test.txt",
            "file_type": "invalid",
            "source_language": "English"
        }
        is_valid, error = self.service.validate_config(config)
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid file type", error)
    
    def test_validate_config_tmx_missing_target(self):
        """Test config validation for TMX without target language."""
        config = {
            "input_file": "test.tmx",
            "file_type": "tmx",
            "source_language": "English"
        }
        is_valid, error = self.service.validate_config(config)
        
        self.assertFalse(is_valid)
        self.assertIn("Target language is required for TMX files", error)
    
    @patch('gui.services.style_extraction_service.Path')
    def test_validate_config_valid_tmx(self, mock_path):
        """Test config validation for valid TMX configuration."""
        mock_path.return_value.exists.return_value = True
        
        config = {
            "input_file": "test.tmx",
            "file_type": "tmx",
            "source_language": "English",
            "target_language": "Spanish"
        }
        is_valid, error = self.service.validate_config(config)
        
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    @patch('gui.services.style_extraction_service.Path')
    def test_validate_config_valid_document(self, mock_path):
        """Test config validation for valid document configuration."""
        mock_path.return_value.exists.return_value = True
        
        config = {
            "input_file": "test.pdf",
            "file_type": "pdf",
            "source_language": "English"
        }
        is_valid, error = self.service.validate_config(config)
        
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    @patch('subprocess.run')
    @patch('gui.services.style_extraction_service.Path')
    def test_extract_style_success_with_progress(self, mock_path, mock_subprocess):
        """Test successful style extraction with progress updates."""
        # Mock file operations
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "# Generated Style Guide"
        mock_path.return_value.parent = Path("/tmp")
        mock_path.return_value.stem = "test"
        
        # Mock subprocess success
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Style guide generated successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Mock progress callback to track calls
        progress_calls = []
        def mock_progress(value):
            progress_calls.append(value)
        
        config = {
            "input_file": "test.pdf",
            "file_type": "pdf",
            "source_language": "English"
        }
        
        result = self.service.extract_style(config, progress_callback=mock_progress)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["style_guide"], "# Generated Style Guide")
        self.assertIn("output_file", result)
        
        # Verify progress was called with expected values
        expected_progress = [0, 10, 15, 20, 25, 85, 90, 95, 100]
        self.assertEqual(progress_calls, expected_progress)
    
    @patch('subprocess.run')
    def test_extract_style_failure(self, mock_subprocess):
        """Test style extraction failure."""
        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: File not found"
        mock_subprocess.return_value = mock_result
        
        config = {
            "input_file": "nonexistent.pdf",
            "file_type": "pdf",
            "source_language": "English"
        }
        
        result = self.service.extract_style(config)
        
        self.assertFalse(result["success"])
        self.assertIn("Error: File not found", result["error"])


if __name__ == '__main__':
    unittest.main() 