"""
Style extraction tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui.components.base_tab import BaseTabController
from gui.components.utils import (
    create_file_browser_row,
    create_dropdown_row
)


class StyleExtractionTabController(BaseTabController):
    """Controller for the style extraction tab."""
    
    def __init__(self, parent_frame: ttk.Frame, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the style extraction tab controller.
        
        Args:
            parent_frame: The parent frame for this tab
            status_callback: Callback function to update status bar
            progress_callback: Callback function to update progress bar
        """
        super().__init__(parent_frame, status_callback, progress_callback)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the style extraction tab UI."""
        # File selection section
        file_section = self.create_section_frame("File Selection")
        self.input_file_entry, _ = create_file_browser_row(
            file_section, 
            "Input File:", 
            [("All Files", "*.*"), ("TMX Files", "*.tmx"), ("PDF Files", "*.pdf"), 
             ("Word Documents", "*.docx;*.doc")]
        )
        
        # File type selection
        file_type_frame = ttk.Frame(file_section)
        file_type_frame.pack(fill=tk.X, expand=False, pady=2)
        
        ttk.Label(file_type_frame, text="File Type:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        self.file_type_var = tk.StringVar(value="auto")
        
        auto_radio = ttk.Radiobutton(file_type_frame, text="Auto-detect", variable=self.file_type_var, value="auto")
        auto_radio.pack(side=tk.LEFT, padx=5)
        
        tmx_radio = ttk.Radiobutton(file_type_frame, text="TMX", variable=self.file_type_var, value="tmx")
        tmx_radio.pack(side=tk.LEFT, padx=5)
        
        pdf_radio = ttk.Radiobutton(file_type_frame, text="PDF", variable=self.file_type_var, value="pdf")
        pdf_radio.pack(side=tk.LEFT, padx=5)
        
        docx_radio = ttk.Radiobutton(file_type_frame, text="DOCX/DOC", variable=self.file_type_var, value="docx")
        docx_radio.pack(side=tk.LEFT, padx=5)
        
        # Language configuration section
        lang_section = self.create_section_frame("Language Configuration")
        self.source_lang_combo = create_dropdown_row(
            lang_section,
            "Source Language:",
            ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"]
        )
        self.target_lang_combo = create_dropdown_row(
            lang_section,
            "Target Language:",
            ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"]
        )
        
        # Output file section
        output_section = self.create_section_frame("Output")
        self.output_file_entry, _ = create_file_browser_row(
            output_section, 
            "Output File:", 
            [("Markdown Files", "*.md")]
        )
        
        # Buttons section
        button_section = self.create_button_row(self.container)
        
        self.extract_button = ttk.Button(
            button_section,
            text="Extract Style Guide",
            command=self.extract_style,
            style="Primary.TButton"
        )
        self.extract_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(
            button_section,
            text="Clear",
            command=self.clear_form,
            style="Secondary.TButton"
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # Preview section (placeholder)
        preview_section = self.create_section_frame("Style Guide Preview")
        ttk.Label(preview_section, text="Style guide preview will appear here").pack(pady=10)
    
    def extract_style(self) -> None:
        """Handle extract style button click."""
        self.update_status("Style extraction functionality will be implemented in task 4")
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.input_file_entry.delete(0, tk.END)
        self.output_file_entry.delete(0, tk.END)
        self.file_type_var.set("auto")
        self.source_lang_combo.set("en")
        self.target_lang_combo.set("es")
        self.update_status("Form cleared")