"""
Utility functions for the Translation GUI components.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Optional, List, Tuple
import os


def create_file_browser_row(parent: ttk.Frame, label_text: str, file_types: List[Tuple[str, str]],
                           callback: Optional[Callable[[str], None]] = None) -> Tuple[ttk.Entry, ttk.Button]:
    """Create a row with a label, entry field, and browse button for file selection.
    
    Args:
        parent: Parent frame
        label_text: Text for the label
        file_types: List of file type tuples (description, extension)
        callback: Optional callback function when a file is selected
        
    Returns:
        Tuple of (entry_field, browse_button)
    """
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, expand=False, pady=2)
    
    label = ttk.Label(row, text=label_text, width=15, anchor=tk.W)
    label.pack(side=tk.LEFT, padx=5)
    
    entry = ttk.Entry(row)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_file():
        filename = filedialog.askopenfilename(
            title=f"Select {label_text}",
            filetypes=file_types
        )
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)
            if callback:
                callback(filename)
    
    browse_button = ttk.Button(row, text="Browse...", command=browse_file)
    browse_button.pack(side=tk.RIGHT, padx=5)
    
    return entry, browse_button


def create_directory_browser_row(parent: ttk.Frame, label_text: str,
                               callback: Optional[Callable[[str], None]] = None) -> Tuple[ttk.Entry, ttk.Button]:
    """Create a row with a label, entry field, and browse button for directory selection.
    
    Args:
        parent: Parent frame
        label_text: Text for the label
        callback: Optional callback function when a directory is selected
        
    Returns:
        Tuple of (entry_field, browse_button)
    """
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, expand=False, pady=2)
    
    label = ttk.Label(row, text=label_text, width=15, anchor=tk.W)
    label.pack(side=tk.LEFT, padx=5)
    
    entry = ttk.Entry(row)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    def browse_directory():
        directory = filedialog.askdirectory(
            title=f"Select {label_text}"
        )
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)
            if callback:
                callback(directory)
    
    browse_button = ttk.Button(row, text="Browse...", command=browse_directory)
    browse_button.pack(side=tk.RIGHT, padx=5)
    
    return entry, browse_button


def create_dropdown_row(parent: ttk.Frame, label_text: str, options: List[str], 
                      default: Optional[str] = None) -> ttk.Combobox:
    """Create a row with a label and dropdown selection.
    
    Args:
        parent: Parent frame
        label_text: Text for the label
        options: List of options for the dropdown
        default: Default selected option
        
    Returns:
        The combobox widget
    """
    row = ttk.Frame(parent)
    row.pack(fill=tk.X, expand=False, pady=2)
    
    label = ttk.Label(row, text=label_text, width=15, anchor=tk.W)
    label.pack(side=tk.LEFT, padx=5)
    
    combobox = ttk.Combobox(row, values=options, state="readonly")
    combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    if default and default in options:
        combobox.set(default)
    elif options:
        combobox.set(options[0])
    
    return combobox


def create_collapsible_section(parent: ttk.Frame, title: str) -> Tuple[ttk.Frame, Callable]:
    """Create a collapsible section with a toggle button.
    
    Args:
        parent: Parent frame
        title: Title for the section
        
    Returns:
        Tuple of (content_frame, toggle_function)
    """
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.X, expand=False, pady=5)
    
    header = ttk.Frame(frame)
    header.pack(fill=tk.X, expand=False)
    
    # Use Unicode characters for expand/collapse indicators
    expand_symbol = "▼"
    collapse_symbol = "▶"
    
    toggle_button = ttk.Label(header, text=f"{expand_symbol} {title}", cursor="hand2")
    toggle_button.pack(side=tk.LEFT, padx=5)
    
    separator = ttk.Separator(header, orient=tk.HORIZONTAL)
    separator.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    content_frame = ttk.Frame(frame, padding="5 0 5 10")
    content_frame.pack(fill=tk.X, expand=False)
    
    # Initial state is expanded
    is_expanded = True
    
    def toggle_section():
        nonlocal is_expanded
        is_expanded = not is_expanded
        
        if is_expanded:
            toggle_button.configure(text=f"{expand_symbol} {title}")
            content_frame.pack(fill=tk.X, expand=False)
        else:
            toggle_button.configure(text=f"{collapse_symbol} {title}")
            content_frame.pack_forget()
    
    toggle_button.bind("<Button-1>", lambda e: toggle_section())
    
    return content_frame, toggle_section