"""
Translation tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui.components.base_tab import BaseTabController
from gui.components.utils import (
    create_file_browser_row,
    create_dropdown_row,
    create_collapsible_section
)


class TranslationTabController(BaseTabController):
    """Controller for the translation tab."""
    
    def __init__(self, parent_frame: ttk.Frame, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the translation tab controller.
        
        Args:
            parent_frame: The parent frame for this tab
            status_callback: Callback function to update status bar
            progress_callback: Callback function to update progress bar
        """
        super().__init__(parent_frame, status_callback, progress_callback)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the translation tab UI."""
        # File selection section
        file_section = self.create_section_frame("File Selection")
        self.input_file_entry, _ = create_file_browser_row(
            file_section, 
            "Input File:", 
            [("All Files", "*.*"), ("Text Files", "*.txt"), ("HTML Files", "*.html"), ("Markdown", "*.md")]
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
        
        # Optional resources section (collapsible)
        resources_content, _ = create_collapsible_section(self.container, "Optional Resources")
        
        self.glossary_entry, _ = create_file_browser_row(
            resources_content,
            "Glossary:",
            [("CSV Files", "*.csv")]
        )
        
        self.style_guide_entry, _ = create_file_browser_row(
            resources_content,
            "Style Guide:",
            [("Markdown Files", "*.md")]
        )
        
        self.tmx_entry, _ = create_file_browser_row(
            resources_content,
            "TMX Memory:",
            [("TMX Files", "*.tmx")]
        )
        
        # Buttons section
        button_section = self.create_button_row(self.container)
        
        self.translate_button = ttk.Button(
            button_section,
            text="Translate",
            command=self.translate,
            style="Primary.TButton"
        )
        self.translate_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(
            button_section,
            text="Clear",
            command=self.clear_form,
            style="Secondary.TButton"
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # Results section (placeholder)
        results_section = self.create_section_frame("Results")
        ttk.Label(results_section, text="Translation results will appear here").pack(pady=10)
    
    def translate(self) -> None:
        """Handle translation button click."""
        self.update_status("Translation functionality will be implemented in task 3")
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.input_file_entry.delete(0, tk.END)
        self.glossary_entry.delete(0, tk.END)
        self.style_guide_entry.delete(0, tk.END)
        self.tmx_entry.delete(0, tk.END)
        self.source_lang_combo.set("en")
        self.target_lang_combo.set("es")
        self.update_status("Form cleared")