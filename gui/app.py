"""
Main application module for the Translation GUI.
This module contains the main application class and entry point for the GUI.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from pathlib import Path
import logging

from gui.components.theme_manager import ThemeManager
from gui.components.translation_tab import TranslationTabController
from gui.components.style_extraction_tab import StyleExtractionTabController
from gui.components.glossary_tab import GlossaryTabController
from gui.components.resource_manager_tab import ResourceManagerTabController
from gui.components.error_handler import ErrorHandler
from gui.services.config_manager import ConfigurationManager


class TranslationGUI:
    """Main application window with tabbed interface"""
    
    def __init__(self):
        """Initialize the main application window."""
        # Ensure config directory exists
        config_dir = Path.home() / ".translation-gui"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        log_file = config_dir / "app.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("translation-gui")
        self.logger.info("Application starting")
        
        # Initialize configuration manager
        self.config_manager = ConfigurationManager()
        
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Translation Tool")
        
        # Set window icon if available
        try:
            # TODO: Add application icon in future tasks
            pass
        except Exception as e:
            self.logger.warning(f"Could not set application icon: {e}")
        
        # Get window geometry from config
        window_config = self.config_manager.get_window_geometry()
        window_width = window_config["width"]
        window_height = window_config["height"]
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Set window to maximized if configured
        if window_config["maximized"]:
            self.root.state('zoomed')
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Track tab changes
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Create status bar
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Create progress bar in status bar
        self.progress = ttk.Progressbar(self.status_bar, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.pack(side=tk.RIGHT, padx=5, pady=2)
        
        # Setup menu bar
        self.setup_menu()
        
        # Setup tabs
        self.setup_tabs()
        
        # Set last used tab from config
        last_tab = self.config_manager.get_last_tab()
        if 0 <= last_tab < self.notebook.index('end'):
            self.notebook.select(last_tab)
        
        # Setup window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Log initialization complete
        self.logger.info("Application initialized")
        self.update_status("Ready")
    
    def setup_menu(self):
        """Create the application menu bar."""
        menu_bar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New Project", command=self.not_implemented)
        file_menu.add_command(label="Open...", command=self.not_implemented)
        file_menu.add_command(label="Save", command=self.not_implemented)
        
        # Add recent files submenu
        self.recent_files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_files_menu)
        self.update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Preferences", command=self.not_implemented)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.not_implemented)
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.not_implemented)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def update_recent_files_menu(self):
        """Update the recent files submenu."""
        # Clear existing items
        self.recent_files_menu.delete(0, tk.END)
        
        # Add recent files
        recent_files = self.config_manager.get_recent_files()
        if recent_files:
            for file_path in recent_files:
                # Use lambda with default argument to avoid late binding issue
                self.recent_files_menu.add_command(
                    label=os.path.basename(file_path),
                    command=lambda path=file_path: self.open_recent_file(path)
                )
        else:
            self.recent_files_menu.add_command(label="No recent files", state=tk.DISABLED)
    
    def open_recent_file(self, file_path):
        """Open a file from the recent files list."""
        # This will be implemented in future tasks
        self.not_implemented()
    
    def setup_tabs(self):
        """Create the tabbed interface with tab controllers."""
        # Create tab frames
        translation_tab = ttk.Frame(self.notebook)
        style_tab = ttk.Frame(self.notebook)
        glossary_tab = ttk.Frame(self.notebook)
        resource_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(translation_tab, text="Translation")
        self.notebook.add(style_tab, text="Style Extraction")
        self.notebook.add(glossary_tab, text="Glossary Management")
        self.notebook.add(resource_tab, text="Resource Management")
        
        # Create tab controllers with status and progress callbacks
        # These will be fully implemented in future tasks
        # For now, we'll just add placeholder content
        ttk.Label(translation_tab, text="Translation tab content will be implemented in task 2").pack(pady=20)
        ttk.Label(style_tab, text="Style extraction tab content will be implemented in task 4").pack(pady=20)
        ttk.Label(glossary_tab, text="Glossary management tab content will be implemented in task 5").pack(pady=20)
        ttk.Label(resource_tab, text="Resource management tab content will be implemented in task 6").pack(pady=20)
        
        # Store tab references for future use
        self.tabs = {
            "translation": translation_tab,
            "style": style_tab,
            "glossary": glossary_tab,
            "resource": resource_tab
        }
    
    def on_tab_changed(self, event):
        """Handle tab change events."""
        selected_tab = self.notebook.index(self.notebook.select())
        self.config_manager.set_last_tab(selected_tab)
        self.logger.debug(f"Tab changed to {selected_tab}")
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.theme_manager.toggle_theme()
        self.update_status("Theme changed")
    
    def not_implemented(self):
        """Placeholder for not yet implemented functionality."""
        try:
            messagebox.showinfo("Not Implemented", "This feature is not yet implemented.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "showing not implemented message")
    
    def show_about(self):
        """Show the about dialog."""
        try:
            messagebox.showinfo("About Translation Tool", 
                              "Translation Tool GUI\n\n"
                              "A graphical interface for the translation pipeline.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "showing about dialog")
    
    def update_status(self, message):
        """Update the status bar message."""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def set_progress(self, value):
        """Update the progress bar value (0-100)."""
        self.progress["value"] = value
        self.root.update_idletasks()
    
    def on_close(self):
        """Handle window close event."""
        try:
            # Save window geometry
            if self.root.state() == 'zoomed':
                self.config_manager.set_window_geometry(
                    self.root.winfo_width(),
                    self.root.winfo_height(),
                    True
                )
            else:
                self.config_manager.set_window_geometry(
                    self.root.winfo_width(),
                    self.root.winfo_height(),
                    False
                )
            
            # Log application closing
            self.logger.info("Application closing")
            
            # Close the window
            self.root.destroy()
        except Exception as e:
            # If an error occurs during closing, just destroy the window
            self.logger.error(f"Error during application close: {e}")
            self.root.destroy()
    
    def run(self):
        """Run the main application loop."""
        try:
            self.root.mainloop()
        except Exception as e:
            ErrorHandler.handle_exception(e, "main application loop")


def main():
    """Main entry point for the GUI application."""
    try:
        app = TranslationGUI()
        app.run()
    except Exception as e:
        # Handle any uncaught exceptions
        ErrorHandler.handle_exception(e, "application startup")
        sys.exit(1)


if __name__ == "__main__":
    main()