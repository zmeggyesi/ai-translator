"""
Theme manager for the Translation GUI.
Provides consistent styling across the application.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any


class ThemeManager:
    """Manages application theming and styling."""
    
    # Color schemes
    LIGHT_THEME = {
        "bg_color": "#f5f5f5",
        "fg_color": "#333333",
        "accent_color": "#4a6ea9",
        "accent_light": "#6b8ec9",
        "accent_dark": "#395989",
        "success_color": "#4caf50",
        "warning_color": "#ff9800",
        "error_color": "#f44336",
        "border_color": "#dddddd",
    }
    
    DARK_THEME = {
        "bg_color": "#2d2d2d",
        "fg_color": "#e0e0e0",
        "accent_color": "#5c88c6",
        "accent_light": "#7ca3e6",
        "accent_dark": "#3c6aa6",
        "success_color": "#66bb6a",
        "warning_color": "#ffa726",
        "error_color": "#ef5350",
        "border_color": "#444444",
    }
    
    def __init__(self, use_dark_theme: bool = False):
        """Initialize the theme manager.
        
        Args:
            use_dark_theme: Whether to use dark theme
        """
        self.style = ttk.Style()
        self.current_theme = self.DARK_THEME if use_dark_theme else self.LIGHT_THEME
        self.apply_theme()
    
    def apply_theme(self) -> None:
        """Apply the current theme to the application."""
        # Use the built-in 'clam' theme as a base for a more modern look
        self.style.theme_use('clam')
        
        # Extract colors from current theme
        bg = self.current_theme["bg_color"]
        fg = self.current_theme["fg_color"]
        accent = self.current_theme["accent_color"]
        accent_light = self.current_theme["accent_light"]
        accent_dark = self.current_theme["accent_dark"]
        border = self.current_theme["border_color"]
        
        # Configure common elements
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("TNotebook", background=bg, tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", padding=[10, 2], font=("Segoe UI", 10))
        
        # Configure selected tab
        self.style.map("TNotebook.Tab",
                      background=[("selected", accent)],
                      foreground=[("selected", "white")])
        
        # Configure entry fields
        self.style.configure("TEntry", fieldbackground=bg, foreground=fg)
        
        # Configure combobox
        self.style.configure("TCombobox", fieldbackground=bg, foreground=fg)
        
        # Configure labelframe
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI", 10, "bold"))
        
        # Configure progressbar
        self.style.configure("TProgressbar", background=accent)
        
        # Configure buttons
        self.style.configure("Primary.TButton", background=accent, foreground="white")
        self.style.configure("Secondary.TButton", background=accent_light)
        
                # Configure button hover effects
        self.style.map("Primary.TButton",
                      background=[("active", accent_light), ("pressed", accent_dark)],
                      foreground=[("active", "white"), ("pressed", "white")])
        self.style.map("Secondary.TButton",
                      background=[("active", accent), ("pressed", accent_dark)])
        
        # Configure secondary buttons
        self.style.configure("Secondary.TButton", background=bg, foreground=fg)
        self.style.map("Secondary.TButton",
                     background=[("active", border), ("pressed", border)],
                     foreground=[("active", fg), ("pressed", fg)])
    
    def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        if self.current_theme == self.LIGHT_THEME:
            self.current_theme = self.DARK_THEME
        else:
            self.current_theme = self.LIGHT_THEME
        
        self.apply_theme()
    
    def get_color(self, color_name: str) -> str:
        """Get a color from the current theme.
        
        Args:
            color_name: Name of the color to get
            
        Returns:
            Hex color code
        """
        return self.current_theme.get(color_name, "#000000")