"""
Base tab controller for the Translation GUI.
Provides common functionality for all tab controllers.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class BaseTabController:
    """Base class for tab controllers."""
    
    def __init__(self, parent_frame: ttk.Frame, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the base tab controller.
        
        Args:
            parent_frame: The parent frame for this tab
            status_callback: Callback function to update status bar
            progress_callback: Callback function to update progress bar
        """
        self.frame = parent_frame
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        
        # Create a main container frame with padding
        self.container = ttk.Frame(self.frame, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)
    
    def update_status(self, message: str) -> None:
        """Update the status bar message."""
        if self.status_callback:
            self.status_callback(message)
    
    def update_progress(self, value: int) -> None:
        """Update the progress bar value (0-100)."""
        if self.progress_callback:
            self.progress_callback(value)
    
    def create_section_frame(self, title: str = None) -> ttk.LabelFrame:
        """Create a framed section with an optional title.
        
        Args:
            title: Optional title for the section
            
        Returns:
            A new frame for content
        """
        if title:
            frame = ttk.LabelFrame(self.container, text=title, padding="5")
        else:
            frame = ttk.Frame(self.container, padding="5")
        
        frame.pack(fill=tk.X, expand=False, pady=5)
        return frame
    
    def create_button_row(self, parent_frame: ttk.Frame) -> ttk.Frame:
        """Create a button row at the bottom of the specified parent frame.
        
        Args:
            parent_frame: The parent frame to add the button row to
            
        Returns:
            A new frame for buttons
        """
        button_frame = ttk.Frame(parent_frame, padding="5")
        button_frame.pack(fill=tk.X, expand=False, pady=10)
        return button_frame
    
    def create_form_row(self, parent: ttk.Frame, label_text: str) -> ttk.Frame:
        """Create a form row with a label.
        
        Args:
            parent: Parent frame
            label_text: Text for the label
            
        Returns:
            A new frame containing the label and space for controls
        """
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, expand=False, pady=2)
        
        label = ttk.Label(row, text=label_text, width=15, anchor=tk.W)
        label.pack(side=tk.LEFT, padx=5)
        
        return row