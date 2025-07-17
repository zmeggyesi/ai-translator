"""
Glossary management tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui.components.base_tab import BaseTabController
from gui.components.utils import (
    create_file_browser_row,
    create_dropdown_row
)


class GlossaryTabController(BaseTabController):
    """Controller for the glossary management tab."""
    
    def __init__(self, parent_frame: ttk.Frame, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the glossary tab controller.
        
        Args:
            parent_frame: The parent frame for this tab
            status_callback: Callback function to update status bar
            progress_callback: Callback function to update progress bar
        """
        super().__init__(parent_frame, status_callback, progress_callback)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the glossary management tab UI."""
        # Source selection section
        source_section = self.create_section_frame("Glossary Source")
        
        source_type_frame = ttk.Frame(source_section)
        source_type_frame.pack(fill=tk.X, expand=False, pady=2)
        
        ttk.Label(source_type_frame, text="Extract From:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        self.source_type_var = tk.StringVar(value="tmx")
        
        tmx_radio = ttk.Radiobutton(source_type_frame, text="TMX File", variable=self.source_type_var, value="tmx")
        tmx_radio.pack(side=tk.LEFT, padx=5)
        
        text_radio = ttk.Radiobutton(source_type_frame, text="Text File", variable=self.source_type_var, value="text")
        text_radio.pack(side=tk.LEFT, padx=5)
        
        self.input_file_entry, _ = create_file_browser_row(
            source_section, 
            "Input File:", 
            [("All Files", "*.*"), ("TMX Files", "*.tmx"), ("Text Files", "*.txt")]
        )
        
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
            [("CSV Files", "*.csv")]
        )
        
        # Buttons section
        button_section = self.create_button_row(self.container)
        
        self.extract_button = ttk.Button(
            button_section,
            text="Extract Glossary",
            command=self.extract_glossary,
            style="Primary.TButton"
        )
        self.extract_button.pack(side=tk.RIGHT, padx=5)
        
        self.load_button = ttk.Button(
            button_section,
            text="Load Existing",
            command=self.load_glossary,
            style="Secondary.TButton"
        )
        self.load_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(
            button_section,
            text="Clear",
            command=self.clear_form,
            style="Secondary.TButton"
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # Glossary editor section (placeholder)
        editor_section = self.create_section_frame("Glossary Editor")
        ttk.Label(editor_section, text="Glossary editor will be implemented in task 5").pack(pady=10)
    
    def extract_glossary(self) -> None:
        """Handle extract glossary button click."""
        self.update_status("Glossary extraction functionality will be implemented in task 5")
    
    def load_glossary(self) -> None:
        """Handle load glossary button click."""
        self.update_status("Glossary loading functionality will be implemented in task 5")
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.input_file_entry.delete(0, tk.END)
        self.output_file_entry.delete(0, tk.END)
        self.source_type_var.set("tmx")
        self.source_lang_combo.set("en")
        self.target_lang_combo.set("es")
        self.update_status("Form cleared")