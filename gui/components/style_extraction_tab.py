"""
Style extraction tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional
from pathlib import Path
import threading

from gui.components.base_tab import BaseTabController
from gui.components.utils import (
    create_file_browser_row,
    create_output_file_browser_row,
    create_dropdown_row
)
from gui.services.style_extraction_service import StyleExtractionService


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
        self.service = StyleExtractionService()
        self.current_thread = None
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the style extraction tab UI."""
        # File selection section
        file_section = self.create_section_frame("File Selection")
        self.input_file_entry, _ = create_file_browser_row(
            file_section, 
            "Input File:", 
            [("All Supported", "*.tmx;*.pdf;*.docx;*.doc"), 
             ("TMX Files", "*.tmx"), 
             ("PDF Files", "*.pdf"), 
             ("Word Documents", "*.docx;*.doc")]
        )
        
        # File type selection
        file_type_frame = ttk.Frame(file_section)
        file_type_frame.pack(fill=tk.X, expand=False, pady=2)
        
        ttk.Label(file_type_frame, text="File Type:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        self.file_type_var = tk.StringVar(value="tmx")
        
        # Use a frame to group radio buttons
        radio_frame = ttk.Frame(file_type_frame)
        radio_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tmx_radio = ttk.Radiobutton(radio_frame, text="TMX", variable=self.file_type_var, value="tmx", 
                                   command=self.on_file_type_changed)
        tmx_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        pdf_radio = ttk.Radiobutton(radio_frame, text="PDF", variable=self.file_type_var, value="pdf",
                                   command=self.on_file_type_changed)
        pdf_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        docx_radio = ttk.Radiobutton(radio_frame, text="DOCX", variable=self.file_type_var, value="docx",
                                    command=self.on_file_type_changed)
        docx_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        doc_radio = ttk.Radiobutton(radio_frame, text="DOC", variable=self.file_type_var, value="doc",
                                   command=self.on_file_type_changed)
        doc_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        # Language configuration section
        lang_section = self.create_section_frame("Language Configuration")
        
        # Source language (always required)
        self.source_lang_combo = create_dropdown_row(
            lang_section,
            "Source Language:",
            ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Chinese", "Japanese", "Korean"],
            "English"
        )
        
        # Target language (conditional - only for TMX files)
        self.target_lang_frame = ttk.Frame(lang_section)
        self.target_lang_frame.pack(fill=tk.X, expand=False, pady=2)
        
        self.target_lang_label = ttk.Label(self.target_lang_frame, text="Target Language:", width=15, anchor=tk.W)
        self.target_lang_label.pack(side=tk.LEFT, padx=5)
        
        self.target_lang_combo = ttk.Combobox(
            self.target_lang_frame, 
            values=["English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Chinese", "Japanese", "Korean"],
            state="readonly"
        )
        self.target_lang_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.target_lang_combo.set("Spanish")
        
        # Info label for target language
        self.target_lang_info = ttk.Label(self.target_lang_frame, text="(Required for TMX files)", 
                                         foreground="gray")
        self.target_lang_info.pack(side=tk.RIGHT, padx=5)
        
        # Output file section
        output_section = self.create_section_frame("Output")
        
        # Use the output file browser that allows creating new files
        self.output_file_entry, _ = create_output_file_browser_row(
            output_section, 
            "Output File:", 
            [("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            self.on_output_file_selected
        )
        
        # Add helpful text about output files
        output_info = ttk.Label(output_section, text="💡 You can enter a new filename that doesn't exist yet", 
                               foreground="gray", font=("TkDefaultFont", 8))
        output_info.pack(anchor=tk.W, padx=20, pady=(0, 5))
        
        # Auto-suggest output filename based on input
        self.input_file_entry.bind('<KeyRelease>', self.on_input_file_changed)
        self.input_file_entry.bind('<FocusOut>', self.on_input_file_changed)
        
        # Progress section (initially hidden)
        self.progress_section = self.create_section_frame("Extraction Progress")
        self.progress_section.pack_forget()  # Hide initially
        
        # Progress indicator frame
        progress_frame = ttk.Frame(self.progress_section)
        progress_frame.pack(fill=tk.X, pady=5)
        
        # Progress status label
        self.progress_status_label = ttk.Label(progress_frame, text="", foreground="blue")
        self.progress_status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Progress bar (determinate)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate', 
            length=400,
            style="Accent.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=2)
        
        # Indeterminate spinner (for unknown duration tasks)
        self.progress_spinner = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=400,
            style="Accent.Horizontal.TProgressbar"
        )
        # Don't pack the spinner initially
        
        # Progress percentage label
        self.progress_percent_label = ttk.Label(progress_frame, text="0%", foreground="gray")
        self.progress_percent_label.pack(anchor=tk.E, pady=(2, 0))
        
        # Cancel button for long operations
        self.cancel_button = ttk.Button(
            progress_frame,
            text="Cancel",
            command=self.cancel_extraction,
            state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
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
        
        # Preview section - will be populated after extraction
        self.preview_section = self.create_section_frame("Style Guide Preview")
        self.preview_text = tk.Text(self.preview_section, height=15, wrap=tk.WORD, state=tk.DISABLED)
        
        # Add scrollbar for preview
        preview_frame = ttk.Frame(self.preview_section)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(preview_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.preview_text = tk.Text(preview_frame, height=15, wrap=tk.WORD, state=tk.DISABLED,
                                   yscrollcommand=scrollbar.set)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preview_text.yview)
        
        # Initially show placeholder text
        self.show_preview_placeholder()
        
        # Preview control buttons
        preview_controls = ttk.Frame(self.preview_section)
        preview_controls.pack(fill=tk.X, pady=5)
        
        self.save_preview_button = ttk.Button(
            preview_controls, text="Save As...", command=self.save_preview_as, state=tk.DISABLED
        )
        self.save_preview_button.pack(side=tk.LEFT, padx=5)
        
        self.copy_preview_button = ttk.Button(
            preview_controls, text="Copy to Clipboard", command=self.copy_preview, state=tk.DISABLED
        )
        self.copy_preview_button.pack(side=tk.LEFT, padx=5)
        
        # Update UI based on initial file type
        self.on_file_type_changed()
    
    def show_progress(self, show: bool = True):
        """Show or hide the progress section."""
        if show:
            self.progress_section.pack(fill=tk.X, expand=False, pady=5, before=self.preview_section)
        else:
            self.progress_section.pack_forget()
    
    def set_progress_mode(self, mode: str):
        """Set progress indicator mode: 'determinate' or 'indeterminate'."""
        if mode == 'indeterminate':
            # Hide determinate progress bar and show spinner
            self.progress_bar.pack_forget()
            self.progress_percent_label.pack_forget()
            self.progress_spinner.pack(fill=tk.X, padx=5, pady=2)
            self.progress_spinner.start(10)  # Animation speed
        else:
            # Hide spinner and show determinate progress bar
            self.progress_spinner.stop()
            self.progress_spinner.pack_forget()
            self.progress_bar.pack(fill=tk.X, padx=5, pady=2)
            self.progress_percent_label.pack(anchor=tk.E, pady=(2, 0))
    
    def update_extraction_progress(self, value: int):
        """Update the local progress indicators."""
        if value <= 0:
            # Starting - show indeterminate progress
            self.set_progress_mode('indeterminate')
            self.progress_status_label.config(text="🔄 Initializing extraction...")
        elif value < 100:
            # In progress - switch to determinate if needed
            if self.progress_spinner.winfo_viewable():
                self.set_progress_mode('determinate')
            
            self.progress_bar['value'] = value
            self.progress_percent_label.config(text=f"{value}%")
            
            # Update status based on progress
            if value <= 20:
                self.progress_status_label.config(text="📋 Validating inputs...")
            elif value <= 40:
                self.progress_status_label.config(text="🚀 Starting extraction process...")
            elif value <= 80:
                self.progress_status_label.config(text="⚙️ Processing document...")
            else:
                self.progress_status_label.config(text="📝 Generating style guide...")
        else:
            # Complete
            self.progress_bar['value'] = 100
            self.progress_percent_label.config(text="100%")
            self.progress_status_label.config(text="✅ Extraction completed successfully!")
        
        # Also update the main app progress bar
        if self.progress_callback:
            self.progress_callback(value)
    
    def cancel_extraction(self):
        """Cancel the current extraction operation."""
        if self.current_thread and self.current_thread.is_alive():
            # Note: Python threads can't be forcibly terminated, but we can set a flag
            # For now, just provide user feedback
            self.progress_status_label.config(text="⚠️ Cancellation requested - please wait...")
            self.cancel_button.config(state=tk.DISABLED)
            # The extraction should complete soon anyway
    
    def on_file_type_changed(self):
        """Handle file type selection change."""
        file_type = self.file_type_var.get()
        
        # Show/hide target language based on file type
        if file_type == "tmx":
            self.target_lang_frame.pack(fill=tk.X, expand=False, pady=2, after=self.source_lang_combo.master)
        else:
            self.target_lang_frame.pack_forget()
    
    def on_input_file_changed(self, event=None):
        """Auto-suggest output filename when input file changes."""
        input_file = self.input_file_entry.get().strip()
        if input_file and not self.output_file_entry.get().strip():
            try:
                input_path = Path(input_file)
                if input_path.exists() or input_path.suffix:  # If file exists or has extension
                    suggested_output = input_path.parent / f"{input_path.stem}_style_guide.md"
                    self.output_file_entry.delete(0, tk.END)
                    self.output_file_entry.insert(0, str(suggested_output))
            except Exception:
                pass  # Ignore path errors
    
    def on_output_file_selected(self, filename: str):
        """Handle output file selection."""
        pass  # No special handling needed currently
    
    def show_preview_placeholder(self):
        """Show placeholder text in preview area."""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "Style guide preview will appear here after extraction completes.")
        self.preview_text.config(state=tk.DISABLED)
    
    def update_preview(self, style_guide_content: str):
        """Update the preview area with generated style guide."""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, style_guide_content)
        self.preview_text.config(state=tk.DISABLED)
        
        # Enable preview control buttons
        self.save_preview_button.config(state=tk.NORMAL)
        self.copy_preview_button.config(state=tk.NORMAL)
    
    def save_preview_as(self):
        """Save the preview content to a file."""
        content = self.preview_text.get(1.0, tk.END).strip()
        if not content:
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Style Guide",
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if filename:
            try:
                Path(filename).write_text(content, encoding='utf-8')
                self.update_status(f"Style guide saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def copy_preview(self):
        """Copy the preview content to clipboard."""
        content = self.preview_text.get(1.0, tk.END).strip()
        if content:
            self.preview_text.clipboard_clear()
            self.preview_text.clipboard_append(content)
            self.update_status("Style guide copied to clipboard")
    
    def extract_style(self) -> None:
        """Handle extract style button click."""
        # Validate inputs
        input_file = self.input_file_entry.get().strip()
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        
        if not Path(input_file).exists():
            messagebox.showerror("Error", f"Input file does not exist: {input_file}")
            return
        
        file_type = self.file_type_var.get()
        source_language = self.source_lang_combo.get()
        target_language = self.target_lang_combo.get() if file_type == "tmx" else None
        output_file = self.output_file_entry.get().strip()
        
        if not source_language:
            messagebox.showerror("Error", "Please select a source language")
            return
        
        if file_type == "tmx" and not target_language:
            messagebox.showerror("Error", "Target language is required for TMX files")
            return
        
        # Build configuration
        config = {
            "input_file": input_file,
            "file_type": file_type,
            "source_language": source_language,
            "output_file": output_file if output_file else None
        }
        
        if target_language:
            config["target_language"] = target_language
        
        # Validate configuration
        is_valid, error_msg = self.service.validate_config(config)
        if not is_valid:
            messagebox.showerror("Error", error_msg)
            return
        
        # Disable buttons and show progress during processing
        self.extract_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        
        # Show progress section
        self.show_progress(True)
        self.update_extraction_progress(0)  # Start with indeterminate progress
        
        # Clear preview during processing
        self.show_preview_placeholder()
        self.save_preview_button.config(state=tk.DISABLED)
        self.copy_preview_button.config(state=tk.DISABLED)
        
        def completion_callback(result):
            # Hide progress and re-enable buttons
            self.show_progress(False)
            self.extract_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            
            # Reset main app progress
            if self.progress_callback:
                self.progress_callback(0)
            
            if result.get("success"):
                style_guide = result.get("style_guide", "")
                self.update_preview(style_guide)
                if not output_file and result.get("output_file"):
                    # Update output field with generated filename
                    self.output_file_entry.delete(0, tk.END)
                    self.output_file_entry.insert(0, result["output_file"])
            else:
                error_msg = result.get("error", "Unknown error occurred")
                messagebox.showerror("Extraction Failed", f"Style guide extraction failed:\n\n{error_msg}")
                self.show_preview_placeholder()
        
        # Start async extraction
        self.current_thread = self.service.extract_style_async(
            config=config,
            progress_callback=self.update_extraction_progress,
            status_callback=self.update_status,
            completion_callback=completion_callback
        )
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.input_file_entry.delete(0, tk.END)
        self.output_file_entry.delete(0, tk.END)
        self.file_type_var.set("tmx")
        self.source_lang_combo.set("English")
        self.target_lang_combo.set("Spanish")
        self.on_file_type_changed()  # Update UI visibility
        self.show_preview_placeholder()
        self.save_preview_button.config(state=tk.DISABLED)
        self.copy_preview_button.config(state=tk.DISABLED)
        
        # Hide progress section
        self.show_progress(False)
        
        self.update_status("Form cleared")
        if self.progress_callback:
            self.progress_callback(0)