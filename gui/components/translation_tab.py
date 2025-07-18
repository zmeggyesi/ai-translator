"""
Translation tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, Dict, Any
import threading
import os

from gui.components.base_tab import BaseTabController
from gui.components.utils import (
    create_file_browser_row,
    create_dropdown_row,
    create_collapsible_section
)
from gui.services.translation_service import TranslationService


class HumanReviewDialog:
    """Dialog for human review of translation with editing capabilities."""
    
    def __init__(self, parent: tk.Tk, interrupt_data: Dict[str, Any]) -> None:
        """Initialize the human review dialog.
        
        Args:
            parent: Parent window
            interrupt_data: Data from the translation interrupt
        """
        self.parent = parent
        self.interrupt_data = interrupt_data
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Human Review Required")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (800 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
        self.dialog.geometry(f"800x600+{x}+{y}")
        
        self.setup_ui()
        
    def setup_ui(self) -> None:
        """Set up the review dialog UI."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Translation Review - Glossary Modification",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Review and modify the glossary terms below. You can edit, add, or remove terms as needed.",
            wraplength=750
        )
        instructions.pack(pady=(0, 10))
        
        # Current glossary section
        glossary_frame = ttk.LabelFrame(main_frame, text="Current Glossary", padding="10")
        glossary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create glossary editor
        self.setup_glossary_editor(glossary_frame)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Accept Changes",
            command=self.accept_changes,
            style="Primary.TButton"
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Continue Without Changes",
            command=self.continue_without_changes
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel Translation",
            command=self.cancel_translation
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_translation)
        
    def setup_glossary_editor(self, parent: ttk.Frame) -> None:
        """Set up the glossary editing interface."""
        # Treeview for glossary terms
        self.tree_frame = ttk.Frame(parent)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL)
        h_scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.glossary_tree = ttk.Treeview(
            self.tree_frame,
            columns=("term", "translation"),
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Configure columns
        self.glossary_tree.heading("term", text="Source Term")
        self.glossary_tree.heading("translation", text="Translation")
        self.glossary_tree.column("term", width=300, minwidth=150)
        self.glossary_tree.column("translation", width=300, minwidth=150)
        
        # Pack treeview and scrollbars
        self.glossary_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.glossary_tree.yview)
        h_scrollbar.config(command=self.glossary_tree.xview)
        
        # Load current glossary
        self.load_glossary_data()
        
        # Edit controls
        edit_frame = ttk.Frame(parent)
        edit_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Term entry
        ttk.Label(edit_frame, text="Term:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.term_entry = ttk.Entry(edit_frame, width=30)
        self.term_entry.grid(row=0, column=1, padx=(0, 10))
        
        # Translation entry
        ttk.Label(edit_frame, text="Translation:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.translation_entry = ttk.Entry(edit_frame, width=30)
        self.translation_entry.grid(row=0, column=3, padx=(0, 10))
        
        # Buttons
        ttk.Button(edit_frame, text="Add/Update", command=self.add_update_term).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(edit_frame, text="Delete", command=self.delete_term).grid(row=0, column=5)
        
        # Bind selection event
        self.glossary_tree.bind("<<TreeviewSelect>>", self.on_term_select)
        
    def load_glossary_data(self) -> None:
        """Load glossary data into the treeview."""
        # Clear existing items
        for item in self.glossary_tree.get_children():
            self.glossary_tree.delete(item)
        
        # Load current glossary
        current_glossary = self.interrupt_data.get("current_glossary", {})
        for term, translation in current_glossary.items():
            self.glossary_tree.insert("", "end", values=(term, translation))
    
    def on_term_select(self, event) -> None:
        """Handle term selection in treeview."""
        selection = self.glossary_tree.selection()
        if selection:
            item = self.glossary_tree.item(selection[0])
            values = item["values"]
            if values:
                self.term_entry.delete(0, tk.END)
                self.term_entry.insert(0, values[0])
                self.translation_entry.delete(0, tk.END)
                self.translation_entry.insert(0, values[1])
    
    def add_update_term(self) -> None:
        """Add or update a glossary term."""
        term = self.term_entry.get().strip()
        translation = self.translation_entry.get().strip()
        
        if not term or not translation:
            messagebox.showwarning("Input Error", "Both term and translation are required.")
            return
        
        # Check if term already exists
        existing_item = None
        for item in self.glossary_tree.get_children():
            if self.glossary_tree.item(item)["values"][0] == term:
                existing_item = item
                break
        
        if existing_item:
            # Update existing term
            self.glossary_tree.item(existing_item, values=(term, translation))
        else:
            # Add new term
            self.glossary_tree.insert("", "end", values=(term, translation))
        
        # Clear entries
        self.term_entry.delete(0, tk.END)
        self.translation_entry.delete(0, tk.END)
    
    def delete_term(self) -> None:
        """Delete selected glossary term."""
        selection = self.glossary_tree.selection()
        if selection:
            self.glossary_tree.delete(selection[0])
        
        # Clear entries
        self.term_entry.delete(0, tk.END)
        self.translation_entry.delete(0, tk.END)
    
    def get_current_glossary(self) -> Dict[str, str]:
        """Get the current glossary from the treeview."""
        glossary = {}
        for item in self.glossary_tree.get_children():
            values = self.glossary_tree.item(item)["values"]
            if len(values) >= 2:
                glossary[values[0]] = values[1]
        return glossary
    
    def accept_changes(self) -> None:
        """Accept the glossary changes and continue."""
        self.result = self.get_current_glossary()
        self.dialog.destroy()
    
    def continue_without_changes(self) -> None:
        """Continue without making changes."""
        self.result = ""
        self.dialog.destroy()
    
    def cancel_translation(self) -> None:
        """Cancel the translation process."""
        self.result = None
        self.dialog.destroy()


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
        self.translation_service = TranslationService()
        self.current_translation_thread = None
        self.translation_results = None
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the translation tab UI."""
        # Create main container with scrollbar
        canvas = tk.Canvas(self.container)
        scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # File selection section
        file_section = self.create_labeled_frame(scrollable_frame, "File Selection")
        self.input_file_entry, self.input_browse_button = create_file_browser_row(
            file_section, 
            "Input File:", 
            [("All Files", "*.*"), ("Text Files", "*.txt"), ("HTML Files", "*.html"), ("Markdown", "*.md")]
        )
        
        # Language configuration section
        lang_section = self.create_labeled_frame(scrollable_frame, "Language Configuration")
        self.source_lang_combo = create_dropdown_row(
            lang_section,
            "Source Language:",
            ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ar", "hi", "ko", "th", "vi"]
        )
        self.target_lang_combo = create_dropdown_row(
            lang_section,
            "Target Language:",
            ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ar", "hi", "ko", "th", "vi"]
        )
        
        # Set default values
        self.source_lang_combo.set("en")
        self.target_lang_combo.set("es")
        
        # Optional resources section (collapsible)
        resources_content, self.resources_expanded = create_collapsible_section(scrollable_frame, "Optional Resources")
        
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
        
        # Translation options section
        options_section = self.create_labeled_frame(scrollable_frame, "Translation Options")
        
        self.enable_review_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_section,
            text="Enable automatic review",
            variable=self.enable_review_var
        ).pack(anchor="w", pady=2)
        
        # Translation execution section
        execution_section = self.create_labeled_frame(scrollable_frame, "Translation Execution")
        
        button_frame = ttk.Frame(execution_section)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.translate_button = ttk.Button(
            button_frame,
            text="Start Translation",
            command=self.start_translation,
            style="Primary.TButton"
        )
        self.translate_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_translation,
            state="disabled"
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_button = ttk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_form
        )
        self.clear_button.pack(side=tk.LEFT)
        
        # Results section
        self.results_section = self.create_labeled_frame(scrollable_frame, "Translation Results")
        self.setup_results_display()
        
    def create_labeled_frame(self, parent: ttk.Frame, title: str) -> ttk.LabelFrame:
        """Create a labeled frame section."""
        frame = ttk.LabelFrame(parent, text=title, padding="10")
        frame.pack(fill=tk.X, expand=False, pady=5)
        return frame
        
    def setup_results_display(self) -> None:
        """Set up the results display area."""
        # Create notebook for tabbed results
        self.results_notebook = ttk.Notebook(self.results_section)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Original text tab
        self.original_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.original_frame, text="Original Text")
        
        self.original_text = tk.Text(
            self.original_frame,
            wrap=tk.WORD,
            height=10,
            state="disabled"
        )
        original_scroll = ttk.Scrollbar(self.original_frame, orient="vertical", command=self.original_text.yview)
        self.original_text.configure(yscrollcommand=original_scroll.set)
        
        self.original_text.pack(side="left", fill="both", expand=True)
        original_scroll.pack(side="right", fill="y")
        
        # Translated text tab
        self.translated_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.translated_frame, text="Translated Text")
        
        self.translated_text = tk.Text(
            self.translated_frame,
            wrap=tk.WORD,
            height=10,
            state="disabled"
        )
        translated_scroll = ttk.Scrollbar(self.translated_frame, orient="vertical", command=self.translated_text.yview)
        self.translated_text.configure(yscrollcommand=translated_scroll.set)
        
        self.translated_text.pack(side="left", fill="both", expand=True)
        translated_scroll.pack(side="right", fill="y")
        
        # Side-by-side comparison tab
        self.comparison_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.comparison_frame, text="Side-by-Side")
        
        # Left pane (original)
        left_frame = ttk.LabelFrame(self.comparison_frame, text="Original", padding="5")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 2))
        
        self.comparison_original = tk.Text(
            left_frame,
            wrap=tk.WORD,
            height=10,
            state="disabled"
        )
        self.comparison_original.pack(fill="both", expand=True)
        
        # Right pane (translated)
        right_frame = ttk.LabelFrame(self.comparison_frame, text="Translated", padding="5")
        right_frame.pack(side="right", fill="both", expand=True, padx=(2, 0))
        
        self.comparison_translated = tk.Text(
            right_frame,
            wrap=tk.WORD,
            height=10,
            state="disabled"
        )
        self.comparison_translated.pack(fill="both", expand=True)
        
        # Review scores tab (if review enabled)
        self.review_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.review_frame, text="Review Scores")
        
        self.review_text = tk.Text(
            self.review_frame,
            wrap=tk.WORD,
            height=10,
            state="disabled"
        )
        review_scroll = ttk.Scrollbar(self.review_frame, orient="vertical", command=self.review_text.yview)
        self.review_text.configure(yscrollcommand=review_scroll.set)
        
        self.review_text.pack(side="left", fill="both", expand=True)
        review_scroll.pack(side="right", fill="y")
        
        # Results action buttons
        results_button_frame = ttk.Frame(self.results_section)
        results_button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.save_button = ttk.Button(
            results_button_frame,
            text="Save Translation",
            command=self.save_translation,
            state="disabled"
        )
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.copy_button = ttk.Button(
            results_button_frame,
            text="Copy to Clipboard",
            command=self.copy_translation,
            state="disabled"
        )
        self.copy_button.pack(side=tk.LEFT)
    
    def validate_inputs(self) -> bool:
        """Validate user inputs before starting translation."""
        # Check input file
        input_file = self.input_file_entry.get().strip()
        if not input_file:
            messagebox.showerror("Validation Error", "Please select an input file.")
            return False
        
        if not os.path.exists(input_file):
            messagebox.showerror("Validation Error", "Input file does not exist.")
            return False
        
        # Check languages
        source_lang = self.source_lang_combo.get().strip()
        target_lang = self.target_lang_combo.get().strip()
        
        if not source_lang or not target_lang:
            messagebox.showerror("Validation Error", "Please select source and target languages.")
            return False
        
        if source_lang == target_lang:
            messagebox.showerror("Validation Error", "Source and target languages must be different.")
            return False
        
        # Check optional files exist if specified
        optional_files = [
            ("Glossary", self.glossary_entry.get().strip()),
            ("Style Guide", self.style_guide_entry.get().strip()),
            ("TMX Memory", self.tmx_entry.get().strip())
        ]
        
        for name, path in optional_files:
            if path and not os.path.exists(path):
                result = messagebox.askyesno(
                    "File Not Found", 
                    f"{name} file '{path}' does not exist. Continue without it?"
                )
                if not result:
                    return False
        
        return True
    
    def start_translation(self) -> None:
        """Start the translation process."""
        if not self.validate_inputs():
            return
        
        # Prepare configuration
        config = {
            "input_file": self.input_file_entry.get().strip(),
            "source_language": self.source_lang_combo.get().strip(),
            "target_language": self.target_lang_combo.get().strip(),
            "enable_review": self.enable_review_var.get()
        }
        
        # Add optional files if they exist
        if self.glossary_entry.get().strip() and os.path.exists(self.glossary_entry.get().strip()):
            config["glossary_file"] = self.glossary_entry.get().strip()
        
        if self.style_guide_entry.get().strip() and os.path.exists(self.style_guide_entry.get().strip()):
            config["style_guide_file"] = self.style_guide_entry.get().strip()
        
        if self.tmx_entry.get().strip() and os.path.exists(self.tmx_entry.get().strip()):
            config["tmx_file"] = self.tmx_entry.get().strip()
        
        # Update UI state
        self.translate_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.save_button.config(state="disabled")
        self.copy_button.config(state="disabled")
        
        # Clear previous results
        self.clear_results()
        
        # Start translation in background thread
        self.current_translation_thread = threading.Thread(
            target=self._run_translation,
            args=(config,),
            daemon=True
        )
        self.current_translation_thread.start()
    
    def _run_translation(self, config: Dict[str, Any]) -> None:
        """Run translation in background thread."""
        try:
            result = self.translation_service.translate(
                config=config,
                progress_callback=self.update_progress,
                status_callback=self.update_status,
                review_callback=self._handle_human_review
            )
            
            # Update UI in main thread
            self.frame.after(0, lambda: self._handle_translation_complete(result))
            
        except Exception as e:
            # Handle errors in main thread
            self.frame.after(0, lambda: self._handle_translation_error(str(e)))
    
    def _handle_human_review(self, interrupt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle human review interrupt from translation process."""
        # This will be called from the background thread, so we need to
        # schedule the dialog creation in the main thread and wait for result
        result_container = [None]
        dialog_completed = threading.Event()
        
        def show_review_dialog():
            try:
                # Find the root window
                root = self.frame
                while root.master:
                    root = root.master
                
                dialog = HumanReviewDialog(root, interrupt_data)
                root.wait_window(dialog.dialog)
                result_container[0] = dialog.result
            except Exception as e:
                print(f"Error in review dialog: {e}")
                result_container[0] = ""
            finally:
                dialog_completed.set()
        
        # Schedule dialog in main thread
        self.frame.after(0, show_review_dialog)
        
        # Wait for dialog to complete
        dialog_completed.wait(timeout=300)  # 5 minute timeout
        
        return result_container[0]
    
    def _handle_translation_complete(self, result: Dict[str, Any]) -> None:
        """Handle translation completion in main thread."""
        self.translation_results = result
        
        # Update UI state
        self.translate_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        
        if result.get("error"):
            self.update_status(f"Translation failed: {result['error']}")
            messagebox.showerror("Translation Error", result["error"])
        else:
            self.update_status("Translation completed successfully")
            self.display_results(result)
            self.save_button.config(state="normal")
            self.copy_button.config(state="normal")
    
    def _handle_translation_error(self, error_message: str) -> None:
        """Handle translation error in main thread."""
        self.translate_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.update_status(f"Translation error: {error_message}")
        messagebox.showerror("Translation Error", error_message)
    
    def cancel_translation(self) -> None:
        """Cancel the current translation."""
        self.translation_service.cancel_translation()
        self.translate_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        self.update_status("Translation cancelled")
    
    def display_results(self, result: Dict[str, Any]) -> None:
        """Display translation results in the UI."""
        original = result.get("original", "")
        translated = result.get("translated", "")
        review_scores = result.get("review_scores", {})
        
        # Update original text displays
        self.original_text.config(state="normal")
        self.original_text.delete(1.0, tk.END)
        self.original_text.insert(1.0, original)
        self.original_text.config(state="disabled")
        
        self.comparison_original.config(state="normal")
        self.comparison_original.delete(1.0, tk.END)
        self.comparison_original.insert(1.0, original)
        self.comparison_original.config(state="disabled")
        
        # Update translated text displays
        self.translated_text.config(state="normal")
        self.translated_text.delete(1.0, tk.END)
        self.translated_text.insert(1.0, translated)
        self.translated_text.config(state="disabled")
        
        self.comparison_translated.config(state="normal")
        self.comparison_translated.delete(1.0, tk.END)
        self.comparison_translated.insert(1.0, translated)
        self.comparison_translated.config(state="disabled")
        
        # Update review scores display
        self.review_text.config(state="normal")
        self.review_text.delete(1.0, tk.END)
        
        if review_scores:
            review_content = "Translation Review Scores:\n\n"
            for key, value in review_scores.items():
                if isinstance(value, (int, float)):
                    review_content += f"{key.replace('_', ' ').title()}: {value:.2f}\n"
                else:
                    review_content += f"{key.replace('_', ' ').title()}: {value}\n"
        else:
            review_content = "No review scores available."
        
        self.review_text.insert(1.0, review_content)
        self.review_text.config(state="disabled")
        
        # Switch to translated text tab
        self.results_notebook.select(1)
    
    def clear_results(self) -> None:
        """Clear all result displays."""
        text_widgets = [
            self.original_text, self.translated_text,
            self.comparison_original, self.comparison_translated,
            self.review_text
        ]
        
        for widget in text_widgets:
            widget.config(state="normal")
            widget.delete(1.0, tk.END)
            widget.config(state="disabled")
    
    def save_translation(self) -> None:
        """Save the translation to a file."""
        if not self.translation_results:
            messagebox.showwarning("No Results", "No translation results to save.")
            return
        
        # Ask user for save location
        filename = filedialog.asksaveasfilename(
            title="Save Translation",
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.translation_results.get("translated", ""))
                
                self.update_status(f"Translation saved to {filename}")
                messagebox.showinfo("Save Complete", f"Translation saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save translation: {str(e)}")
    
    def copy_translation(self) -> None:
        """Copy the translation to clipboard."""
        if not self.translation_results:
            messagebox.showwarning("No Results", "No translation results to copy.")
            return
        
        translated_text = self.translation_results.get("translated", "")
        if translated_text:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(translated_text)
            self.update_status("Translation copied to clipboard")
            messagebox.showinfo("Copy Complete", "Translation copied to clipboard")
    
    def clear_form(self) -> None:
        """Clear all form fields."""
        self.input_file_entry.delete(0, tk.END)
        self.glossary_entry.delete(0, tk.END)
        self.style_guide_entry.delete(0, tk.END)
        self.tmx_entry.delete(0, tk.END)
        self.source_lang_combo.set("en")
        self.target_lang_combo.set("es")
        self.enable_review_var.set(True)
        self.clear_results()
        self.save_button.config(state="disabled")
        self.copy_button.config(state="disabled")
        self.translation_results = None
        self.update_status("Form cleared")