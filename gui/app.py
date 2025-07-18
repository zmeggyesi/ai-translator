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
        self.root.title("Translation Tool - Multi-Agent Translation System")
        
        # Set window icon if available
        self.set_application_icon()
        
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
        file_menu.add_command(label="New Project", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        
        # Add recent files submenu
        self.recent_files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_files_menu)
        self.update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close, accelerator="Ctrl+Q")
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Preferences", command=self.show_preferences, accelerator="Ctrl+,")
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Recent Files", command=self.clear_recent_files)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.refresh_view, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme, accelerator="Ctrl+T")
        view_menu.add_command(label="Full Screen", command=self.toggle_fullscreen, accelerator="F11")
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.show_documentation, accelerator="F1")
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts, accelerator="Ctrl+?")
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        
        # Bind keyboard shortcuts
        self.bind_keyboard_shortcuts()
        
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
        try:
            # Style Extraction Tab - Task 4 completed
            self.style_controller = StyleExtractionTabController(
                style_tab, 
                status_callback=self.update_status,
                progress_callback=self.set_progress
            )
            self.logger.info("Style extraction tab initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize style extraction tab: {e}")
            ttk.Label(style_tab, text="Error loading style extraction tab").pack(pady=20)
        
        # Translation Tab - Task 3 completed
        try:
            self.translation_controller = TranslationTabController(
                translation_tab,
                status_callback=self.update_status,
                progress_callback=self.set_progress
            )
            self.logger.info("Translation tab initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize translation tab: {e}")
            ttk.Label(translation_tab, text="Error loading translation tab").pack(pady=20)
        
        # Placeholder content for other tabs (will be implemented in future tasks)
        ttk.Label(glossary_tab, text="Glossary management tab content will be implemented in task 5").pack(pady=20)
        ttk.Label(resource_tab, text="Resource management tab content will be implemented in task 6").pack(pady=20)
        
        # Store tab references for future use
        self.tabs = {
            "translation": translation_tab,
            "style": style_tab,
            "glossary": glossary_tab,
            "resource": resource_tab
        }
        
        # Store controller references for future use
        self.controllers = {
            "translation": getattr(self, 'translation_controller', None),
            "style": getattr(self, 'style_controller', None)
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
    
    def update_recent_files_menu(self):
        """Update the recent files menu with current files."""
        try:
            # Clear existing menu items
            self.recent_files_menu.delete(0, 'end')
            
            recent_files = self.config_manager.get_recent_files()
            
            if not recent_files:
                self.recent_files_menu.add_command(label="(No recent files)", state='disabled')
            else:
                for file_path in recent_files:
                    # Show only filename, but store full path
                    filename = os.path.basename(file_path)
                    self.recent_files_menu.add_command(
                        label=f"{filename}",
                        command=lambda path=file_path: self.open_recent_file(path)
                    )
                    
                # Add separator and clear option if there are files
                self.recent_files_menu.add_separator()
                self.recent_files_menu.add_command(
                    label="Clear Recent Files",
                    command=self.clear_recent_files
                )
        except Exception as e:
            ErrorHandler.handle_exception(e, "updating recent files menu")
    
    def open_recent_file(self, file_path):
        """Open a recent file."""
        try:
            if os.path.exists(file_path):
                self.update_status(f"Opened: {os.path.basename(file_path)}")
                self.logger.info(f"Recent file opened: {file_path}")
                # TODO: In future tasks, pass this file to the appropriate tab
            else:
                # File no longer exists, remove from recent files
                recent_files = self.config_manager.get_recent_files()
                if file_path in recent_files:
                    recent_files.remove(file_path)
                    self.config_manager.config["recent_files"] = recent_files
                    self.config_manager.save_config()
                    self.update_recent_files_menu()
                
                messagebox.showerror("File Not Found", 
                                   f"The file '{file_path}' no longer exists and has been removed from recent files.")
        except Exception as e:
            ErrorHandler.handle_exception(e, f"opening recent file {file_path}")
    
    def create_preferences_dialog(self):
        """Create and show the preferences dialog."""
        try:
            # Create preferences dialog
            prefs_dialog = tk.Toplevel(self.root)
            prefs_dialog.title("Preferences")
            prefs_dialog.geometry("500x400")
            prefs_dialog.resizable(True, True)
            
            # Center the dialog
            prefs_dialog.transient(self.root)
            prefs_dialog.grab_set()
            
            # Create notebook for preference categories
            prefs_notebook = ttk.Notebook(prefs_dialog)
            prefs_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # General preferences tab
            general_frame = ttk.Frame(prefs_notebook)
            prefs_notebook.add(general_frame, text="General")
            
            # Theme selection
            theme_section = ttk.LabelFrame(general_frame, text="Appearance", padding="10")
            theme_section.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(theme_section, text="Theme:").grid(row=0, column=0, sticky=tk.W, padx=5)
            theme_var = tk.StringVar(value="Light")
            theme_combo = ttk.Combobox(theme_section, textvariable=theme_var, 
                                     values=["Light", "Dark"], state="readonly")
            theme_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
            
            # Language preferences tab
            lang_frame = ttk.Frame(prefs_notebook)
            prefs_notebook.add(lang_frame, text="Languages")
            
            # Default languages section
            lang_section = ttk.LabelFrame(lang_frame, text="Default Languages", padding="10")
            lang_section.pack(fill=tk.X, padx=10, pady=5)
            
            default_langs = self.config_manager.get_default_languages()
            
            ttk.Label(lang_section, text="Source Language:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            source_lang_var = tk.StringVar(value=default_langs["source"])
            source_lang_combo = ttk.Combobox(lang_section, textvariable=source_lang_var,
                                           values=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"],
                                           state="readonly")
            source_lang_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(lang_section, text="Target Language:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            target_lang_var = tk.StringVar(value=default_langs["target"])
            target_lang_combo = ttk.Combobox(lang_section, textvariable=target_lang_var,
                                           values=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"],
                                           state="readonly")
            target_lang_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            # Advanced preferences tab
            advanced_frame = ttk.Frame(prefs_notebook)
            prefs_notebook.add(advanced_frame, text="Advanced")
            
            # Window settings
            window_section = ttk.LabelFrame(advanced_frame, text="Window Settings", padding="10")
            window_section.pack(fill=tk.X, padx=10, pady=5)
            
            remember_window_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(window_section, text="Remember window position and size", 
                          variable=remember_window_var).pack(anchor=tk.W, pady=2)
            
            remember_tabs_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(window_section, text="Remember last selected tab", 
                          variable=remember_tabs_var).pack(anchor=tk.W, pady=2)
            
            # Logging settings
            logging_section = ttk.LabelFrame(advanced_frame, text="Logging", padding="10")
            logging_section.pack(fill=tk.X, padx=10, pady=5)
            
            log_level_var = tk.StringVar(value="INFO")
            ttk.Label(logging_section, text="Log Level:").grid(row=0, column=0, sticky=tk.W, padx=5)
            log_level_combo = ttk.Combobox(logging_section, textvariable=log_level_var,
                                         values=["DEBUG", "INFO", "WARNING", "ERROR"],
                                         state="readonly")
            log_level_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
            
            # Button frame
            button_frame = ttk.Frame(prefs_dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def save_preferences():
                try:
                    # Save language preferences
                    self.config_manager.set_default_languages(
                        source_lang_var.get(),
                        target_lang_var.get()
                    )
                    
                    # TODO: Save other preferences when implemented
                    # For now, just show confirmation
                    self.update_status("Preferences saved")
                    prefs_dialog.destroy()
                    messagebox.showinfo("Preferences", "Preferences saved successfully!")
                except Exception as e:
                    ErrorHandler.handle_exception(e, "saving preferences")
            
            def cancel_preferences():
                prefs_dialog.destroy()
            
            ttk.Button(button_frame, text="Cancel", command=cancel_preferences).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Save", command=save_preferences).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "creating preferences dialog")
    
    def set_application_icon(self):
        """Set the application icon if available."""
        try:
            # Try to set icon from multiple possible locations
            possible_icon_paths = [
                "gui/assets/icon.ico",
                "assets/icon.ico", 
                "icon.ico",
                "gui/assets/icon.png",
                "assets/icon.png",
                "icon.png"
            ]
            
            for icon_path in possible_icon_paths:
                if os.path.exists(icon_path):
                    try:
                        # Try ICO format first (Windows preferred)
                        if icon_path.endswith('.ico'):
                            self.root.iconbitmap(icon_path)
                        else:
                            # For PNG files, create a PhotoImage
                            icon_photo = tk.PhotoImage(file=icon_path)
                            self.root.iconphoto(True, icon_photo)
                        self.logger.info(f"Application icon set from: {icon_path}")
                        return
                    except Exception as e:
                        self.logger.debug(f"Could not load icon from {icon_path}: {e}")
                        continue
            
            # If no icon file found, try to create a simple default icon
            self.create_default_icon()
            
        except Exception as e:
            self.logger.warning(f"Could not set application icon: {e}")
    
    def create_default_icon(self):
        """Create a simple default icon using Tkinter."""
        try:
            # Create a simple 32x32 icon using PhotoImage
            # This creates a blue square with "T" for Translation
            icon_data = '''
            R0lGODlhIAAgAPcAAAAAADMzMzNmZjOZmTO2tjPMzDPd3TP//wAAMwAAZgAAmQAAtgAAzAAA3QAA
            /wAzAAAzMwAzZgAzmQAztgAzzAAz3QAz/wBmAABmMwBmZgBmmQBmtgBmzABm3QBm/wCZAACZMwCZ
            ZgCZmQCZtgCZzACZ3QCZ/wC2AAC2MwC2ZgC2mQC2tgC2zAC23QC2/wDMAADMMwDMZgDMmQDMtgDM
            zADM3QDM/wDdAADdMwDdZgDdmQDdtgDdzADd3QDd/wD/AAD/MwD/ZgD/mQD/tgD/zAD/3QD//zMA
            ADMAMzMAZjMAmTMAtjMAzDMA3TMA/zMzADMzMzMzZjMzmTMztjMzzDMz3TMz/zNmADNmMzNmZjNm
            mTNmtjNmzDNm3TNm/zOZADOZMzOZZjOZmTOZtjOZzDOZ3TOZ/zO2ADO2MzO2ZjO2mTO2tjO2zDO2
            3TO2/zPMADPMMzPMZjPMmTPMtjPMzDPM3TPM/zPdADPdMzPdZjPdmTPdtjPdzDPd3TPd/zP/ADP/
            MzP/ZjP/mTP/tjP/zDP/3TP//2YAAGYAM2YAZmYAmWYAtmYAzGYA3WYA/2YzAGYzM2YzZmYzmWYz
            tmYzzGYz3WYz/2ZmAGZmM2ZmZmZmmWZmtmZmzGZm3WZm/2aZAGaZM2aZZmaZmWaZtmaZzGaZ3WaZ
            /2a2AGa2M2a2Zma2mWa2tma2zGa23Wa2/2bMAGbMM2bMZmbMmWbMtmbMzGbM3WbM/2bdAGbdM2bd
            ZmbdmWbdtmbdzGbd3Wbd/2b/AGb/M2b/Zmb/mWb/tmb/zGb/3Wb//5kAAJkAM5kAZpkAmZkAtpkA
            zJkA3ZkA/5kzAJkzM5kzZpkzmZkztpkzzJkz3Zkz/5lmAJlmM5lmZplmmZlmtpllmzJlm3Jlm/5m
            mAJmm8JmzJlm3Zlm/5mZAJmZM5mZZpmZmZmZtpmZzJmZ3ZmZ/5m2AJm2M5m2Zpm2mZm2tpm2zJm2
            3Zm2/5nMAJnMM5nMZpnMmZnMtpnMzJnM3ZnM/5ndAJndM5ndZpndmZndtpndzJnd3Znd/5n/AJn/
            M5n/Zpn/mZn/tpn/zJn/3Zn//7YAALYAAyH+EUNyZWF0ZWQgd2l0aCBHSU1QACwAAAAAIAAgAAAI
            /gD/CRxIsKDBgwgTKlzIsKHDhxAjSpxIsaLFixgzatzIsaPHjyBDihxJsqTJkyhTqlzJsqXLlzBj
            ypxJs6bNmzhz6tzJs6fPn0CDCh1KtKjRo0iTKl3KtKnTp1CjSp1KtarVq1izat3KtavXr2DDih1L
            tqzZs2jTql3Ltq3bt3Djyp1Lt67du3jz6t3Lt6/fv4ADCx5MuLDhw4gTK17MuLHjx5AjS55MubLl
            y5gza97MubPnz6BDix5NurTp06hTq17NurXr17Bjy55Nu7bt27hz697Nu7fv38CDCx9OvLjx48iTK1
            /OvLnz59CjS59Ovbr169iza9/Ovbv37+DDix9Pvrz58+jTq1/Pvr379/Djy59Pv779+/jz69/Pv7
            //gAYq6KCEFmrooYgmquijkEYq6aSUVmrppZhmqummnHbq6aeghirqqKSWauqpqKaq6qqsturq
            q7DGKuustNZq66245qrrrrkWEAA7
            '''
            
            import base64
            icon_bytes = base64.b64decode(icon_data)
            
            # Write temporary icon file
            temp_icon_path = os.path.join(os.path.expanduser("~"), ".translation-gui", "temp_icon.gif")
            with open(temp_icon_path, 'wb') as f:
                f.write(icon_bytes)
            
            # Set as icon
            icon_photo = tk.PhotoImage(file=temp_icon_path)
            self.root.iconphoto(True, icon_photo)
            
            # Clean up temp file
            try:
                os.remove(temp_icon_path)
            except:
                pass
                
            self.logger.info("Default application icon created and set")
            
        except Exception as e:
            self.logger.debug(f"Could not create default icon: {e}")
    
    def bind_keyboard_shortcuts(self):
        """Bind keyboard shortcuts to menu actions."""
        # File menu shortcuts
        self.root.bind_all("<Control-n>", lambda e: self.new_project())
        self.root.bind_all("<Control-o>", lambda e: self.open_file())
        self.root.bind_all("<Control-s>", lambda e: self.save_file())
        self.root.bind_all("<Control-Shift-S>", lambda e: self.save_as_file())
        self.root.bind_all("<Control-q>", lambda e: self.on_close())
        
        # Edit menu shortcuts
        self.root.bind_all("<Control-comma>", lambda e: self.show_preferences())
        
        # View menu shortcuts
        self.root.bind_all("<F5>", lambda e: self.refresh_view())
        self.root.bind_all("<Control-t>", lambda e: self.toggle_theme())
        self.root.bind_all("<F11>", lambda e: self.toggle_fullscreen())
        
        # Help menu shortcuts
        self.root.bind_all("<F1>", lambda e: self.show_documentation())
        self.root.bind_all("<Control-question>", lambda e: self.show_shortcuts())
        
        # Tab navigation shortcuts
        self.root.bind_all("<Control-Tab>", lambda e: self.next_tab())
        self.root.bind_all("<Control-Shift-Tab>", lambda e: self.previous_tab())
        
        # Number key tab shortcuts (Ctrl+1 through Ctrl+4)
        for i in range(1, 5):
            self.root.bind_all(f"<Control-Key-{i}>", lambda e, tab=i-1: self.select_tab(tab))
    
    def new_project(self):
        """Create a new project."""
        try:
            # Reset all tabs to default state
            self.logger.info("Creating new project")
            # For now, just clear any current data and reset to first tab
            self.notebook.select(0)
            self.update_status("New project created")
            messagebox.showinfo("New Project", "New project created. All tabs have been reset.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "creating new project")
    
    def open_file(self):
        """Open a file dialog to select a file."""
        try:
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Open File",
                filetypes=[
                    ("All Supported", "*.txt;*.md;*.html;*.tmx;*.csv"),
                    ("Text Files", "*.txt"),
                    ("Markdown Files", "*.md"),
                    ("HTML Files", "*.html"),
                    ("TMX Files", "*.tmx"),
                    ("CSV Files", "*.csv"),
                    ("All Files", "*.*")
                ]
            )
            if file_path:
                self.config_manager.add_recent_file(file_path)
                self.update_recent_files_menu()
                self.update_status(f"Opened: {os.path.basename(file_path)}")
                self.logger.info(f"File opened: {file_path}")
                # TODO: In future tasks, pass this file to the appropriate tab
        except Exception as e:
            ErrorHandler.handle_exception(e, "opening file")
    
    def save_file(self):
        """Save the current work."""
        try:
            # For now, this is a placeholder
            self.update_status("Save functionality will be implemented with individual tabs")
            messagebox.showinfo("Save", "Save functionality will be implemented when tab content is complete.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "saving file")
    
    def save_as_file(self):
        """Save the current work with a new name."""
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                title="Save As",
                defaultextension=".txt",
                filetypes=[
                    ("Text Files", "*.txt"),
                    ("Markdown Files", "*.md"),
                    ("HTML Files", "*.html"),
                    ("All Files", "*.*")
                ]
            )
            if file_path:
                self.update_status(f"Save As functionality will be implemented with individual tabs")
                messagebox.showinfo("Save As", "Save As functionality will be implemented when tab content is complete.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "saving file as")
    
    def show_preferences(self):
        """Show the preferences dialog."""
        try:
            self.create_preferences_dialog()
        except Exception as e:
            ErrorHandler.handle_exception(e, "showing preferences")
    
    def clear_recent_files(self):
        """Clear the recent files list."""
        try:
            self.config_manager.config["recent_files"] = []
            self.config_manager.save_config()
            self.update_recent_files_menu()
            self.update_status("Recent files cleared")
        except Exception as e:
            ErrorHandler.handle_exception(e, "clearing recent files")
    
    def refresh_view(self):
        """Refresh the current view."""
        try:
            # Refresh the current tab content
            current_tab = self.notebook.index(self.notebook.select())
            self.logger.info(f"Refreshing tab {current_tab}")
            self.update_status("View refreshed")
            # TODO: In future tasks, implement tab-specific refresh logic
        except Exception as e:
            ErrorHandler.handle_exception(e, "refreshing view")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        try:
            current_state = self.root.attributes("-fullscreen")
            self.root.attributes("-fullscreen", not current_state)
            status = "Entered fullscreen" if not current_state else "Exited fullscreen"
            self.update_status(status)
        except Exception as e:
            ErrorHandler.handle_exception(e, "toggling fullscreen")
    
    def show_documentation(self):
        """Show documentation."""
        try:
            import webbrowser
            # For now, show a message - in a real app this would open documentation
            messagebox.showinfo("Documentation", 
                              "Documentation will be available online.\n\n"
                              "For now, see the README.md file in the project directory.")
        except Exception as e:
            ErrorHandler.handle_exception(e, "showing documentation")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        try:
            shortcuts_text = """Keyboard Shortcuts:

File:
  Ctrl+N - New Project
  Ctrl+O - Open File
  Ctrl+S - Save
  Ctrl+Shift+S - Save As
  Ctrl+Q - Exit

Edit:
  Ctrl+, - Preferences

View:
  F5 - Refresh
  Ctrl+T - Toggle Theme
  F11 - Toggle Fullscreen

Navigation:
  Ctrl+Tab - Next Tab
  Ctrl+Shift+Tab - Previous Tab
  Ctrl+1-4 - Select Tab

Help:
  F1 - Documentation
  Ctrl+? - This Dialog"""
            
            # Create a custom dialog
            shortcuts_dialog = tk.Toplevel(self.root)
            shortcuts_dialog.title("Keyboard Shortcuts")
            shortcuts_dialog.geometry("400x500")
            shortcuts_dialog.resizable(False, False)
            
            # Center the dialog
            shortcuts_dialog.transient(self.root)
            shortcuts_dialog.grab_set()
            
            # Add text widget with scrollbar
            text_frame = ttk.Frame(shortcuts_dialog, padding="10")
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget.insert(tk.END, shortcuts_text)
            text_widget.config(state=tk.DISABLED)
            
            # Add close button
            button_frame = ttk.Frame(shortcuts_dialog, padding="10")
            button_frame.pack(fill=tk.X)
            
            close_button = ttk.Button(button_frame, text="Close", command=shortcuts_dialog.destroy)
            close_button.pack(side=tk.RIGHT)
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "showing shortcuts dialog")
    
    def next_tab(self):
        """Switch to next tab."""
        try:
            current = self.notebook.index(self.notebook.select())
            next_tab = (current + 1) % self.notebook.index('end')
            self.notebook.select(next_tab)
        except Exception as e:
            ErrorHandler.handle_exception(e, "switching to next tab")
    
    def previous_tab(self):
        """Switch to previous tab."""
        try:
            current = self.notebook.index(self.notebook.select())
            prev_tab = (current - 1) % self.notebook.index('end')
            self.notebook.select(prev_tab)
        except Exception as e:
            ErrorHandler.handle_exception(e, "switching to previous tab")
    
    def select_tab(self, tab_index):
        """Select a specific tab by index."""
        try:
            if 0 <= tab_index < self.notebook.index('end'):
                self.notebook.select(tab_index)
        except Exception as e:
            ErrorHandler.handle_exception(e, f"selecting tab {tab_index}")
    
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