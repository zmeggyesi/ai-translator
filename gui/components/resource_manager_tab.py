"""
Resource management tab controller for the Translation GUI.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Optional, Dict, List
import os
import shutil

from gui.components.base_tab import BaseTabController
from gui.components.utils import create_file_browser_row
from gui.components.error_handler import ErrorHandler


class ResourceManagerTabController(BaseTabController):
    """Controller for the resource management tab."""
    
    RESOURCE_TYPES = {
        "glossary": {
            "display_name": "Glossary",
            "extensions": [("CSV Files", "*.csv")],
            "default_dir": "glossaries"
        },
        "style_guide": {
            "display_name": "Style Guide",
            "extensions": [("Markdown Files", "*.md")],
            "default_dir": "style_guides"
        },
        "tmx": {
            "display_name": "Translation Memory",
            "extensions": [("TMX Files", "*.tmx")],
            "default_dir": "tmx"
        }
    }
    
    def __init__(self, parent_frame: ttk.Frame, status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None):
        """Initialize the resource manager tab controller.
        
        Args:
            parent_frame: The parent frame for this tab
            status_callback: Callback function to update status bar
            progress_callback: Callback function to update progress bar
        """
        super().__init__(parent_frame, status_callback, progress_callback)
        
        # Initialize resource directory
        self.resource_dir = os.path.join(os.path.expanduser("~"), ".translation-gui", "resources")
        os.makedirs(self.resource_dir, exist_ok=True)
        
        # Create subdirectories for each resource type
        for resource_type in self.RESOURCE_TYPES:
            os.makedirs(os.path.join(self.resource_dir, self.RESOURCE_TYPES[resource_type]["default_dir"]), exist_ok=True)
        
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the resource management tab UI."""
        # Import section
        import_section = self.create_section_frame("Import Resource")
        
        # Resource type selection
        resource_type_frame = ttk.Frame(import_section)
        resource_type_frame.pack(fill=tk.X, expand=False, pady=2)
        
        ttk.Label(resource_type_frame, text="Resource Type:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        self.resource_type_var = tk.StringVar(value="glossary")
        
        for resource_type, info in self.RESOURCE_TYPES.items():
            radio = ttk.Radiobutton(
                resource_type_frame, 
                text=info["display_name"], 
                variable=self.resource_type_var, 
                value=resource_type
            )
            radio.pack(side=tk.LEFT, padx=5)
        
        # File selection
        self.resource_file_entry, _ = create_file_browser_row(
            import_section, 
            "Resource File:", 
            [ext for info in self.RESOURCE_TYPES.values() for ext in info["extensions"]]
        )
        
        # Name field
        name_frame = ttk.Frame(import_section)
        name_frame.pack(fill=tk.X, expand=False, pady=2)
        
        ttk.Label(name_frame, text="Resource Name:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        self.resource_name_entry = ttk.Entry(name_frame)
        self.resource_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Import button
        import_button_frame = self.create_button_row(import_section)
        
        self.import_button = ttk.Button(
            import_button_frame,
            text="Import Resource",
            command=self.import_resource,
            style="Primary.TButton"
        )
        self.import_button.pack(side=tk.RIGHT, padx=5)
        
        # Resource listing section
        listing_section = self.create_section_frame("Available Resources")
        
        # Create notebook for resource types
        self.resource_notebook = ttk.Notebook(listing_section)
        self.resource_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a tab for each resource type
        self.resource_frames = {}
        self.resource_trees = {}
        
        for resource_type, info in self.RESOURCE_TYPES.items():
            frame = ttk.Frame(self.resource_notebook)
            self.resource_notebook.add(frame, text=info["display_name"])
            self.resource_frames[resource_type] = frame
            
            # Create treeview for resources
            tree = ttk.Treeview(frame, columns=("name", "path", "size"), show="headings")
            tree.heading("name", text="Name")
            tree.heading("path", text="Path")
            tree.heading("size", text="Size")
            
            tree.column("name", width=150)
            tree.column("path", width=300)
            tree.column("size", width=100)
            
            tree.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=scrollbar.set)
            
            self.resource_trees[resource_type] = tree
            
            # Add right-click menu
            self.create_context_menu(tree, resource_type)
        
        # Refresh resources
        self.refresh_resources()
    
    def create_context_menu(self, tree: ttk.Treeview, resource_type: str) -> None:
        """Create right-click context menu for resource tree.
        
        Args:
            tree: The treeview widget
            resource_type: Type of resource
        """
        menu = tk.Menu(tree, tearoff=0)
        
        menu.add_command(label="Preview", command=lambda: self.preview_resource(tree, resource_type))
        menu.add_command(label="Set as Default", command=lambda: self.set_default_resource(tree, resource_type))
        menu.add_separator()
        menu.add_command(label="Delete", command=lambda: self.delete_resource(tree, resource_type))
        
        def show_menu(event):
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
                menu.post(event.x_root, event.y_root)
        
        tree.bind("<Button-3>", show_menu)
    
    def import_resource(self) -> None:
        """Handle import resource button click."""
        try:
            # Get values
            resource_type = self.resource_type_var.get()
            resource_file = self.resource_file_entry.get()
            resource_name = self.resource_name_entry.get()
            
            # Validate inputs
            if not ErrorHandler.validate_required_field(resource_file, "Resource File"):
                return
            
            if not ErrorHandler.validate_file_exists(resource_file, "Resource File"):
                return
            
            if not ErrorHandler.validate_required_field(resource_name, "Resource Name"):
                return
            
            # Create destination path
            type_info = self.RESOURCE_TYPES[resource_type]
            dest_dir = os.path.join(self.resource_dir, type_info["default_dir"])
            
            # Get file extension
            _, ext = os.path.splitext(resource_file)
            
            # Create destination file path
            dest_file = os.path.join(dest_dir, f"{resource_name}{ext}")
            
            # Check if file already exists
            if os.path.exists(dest_file):
                if not tk.messagebox.askyesno(
                    "File Exists", 
                    f"A resource with the name '{resource_name}' already exists. Overwrite?"
                ):
                    return
            
            # Copy file
            shutil.copy2(resource_file, dest_file)
            
            # Update status
            self.update_status(f"Resource '{resource_name}' imported successfully")
            
            # Refresh resources
            self.refresh_resources()
            
            # Clear form
            self.resource_file_entry.delete(0, tk.END)
            self.resource_name_entry.delete(0, tk.END)
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "importing resource")
    
    def refresh_resources(self) -> None:
        """Refresh the resource listings."""
        try:
            for resource_type, info in self.RESOURCE_TYPES.items():
                tree = self.resource_trees[resource_type]
                
                # Clear existing items
                for item in tree.get_children():
                    tree.delete(item)
                
                # Get resource directory
                resource_dir = os.path.join(self.resource_dir, info["default_dir"])
                
                # List files
                if os.path.exists(resource_dir):
                    for filename in os.listdir(resource_dir):
                        file_path = os.path.join(resource_dir, filename)
                        if os.path.isfile(file_path):
                            # Get file size
                            size = os.path.getsize(file_path)
                            size_str = f"{size / 1024:.1f} KB"
                            
                            # Get resource name (without extension)
                            name, _ = os.path.splitext(filename)
                            
                            # Add to tree
                            tree.insert("", tk.END, values=(name, file_path, size_str))
            
            self.update_status("Resources refreshed")
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "refreshing resources")
    
    def preview_resource(self, tree: ttk.Treeview, resource_type: str) -> None:
        """Preview the selected resource.
        
        Args:
            tree: The treeview widget
            resource_type: Type of resource
        """
        try:
            # Get selected item
            selection = tree.selection()
            if not selection:
                return
            
            # Get file path
            item = tree.item(selection[0])
            file_path = item["values"][1]
            
            # Preview based on resource type
            if resource_type == "glossary":
                self.preview_csv(file_path)
            elif resource_type == "style_guide":
                self.preview_markdown(file_path)
            elif resource_type == "tmx":
                self.preview_tmx(file_path)
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "previewing resource")
    
    def preview_csv(self, file_path: str) -> None:
        """Preview a CSV file.
        
        Args:
            file_path: Path to the CSV file
        """
        # This is a placeholder - will be implemented in task 6
        self.update_status("CSV preview will be implemented in task 6")
    
    def preview_markdown(self, file_path: str) -> None:
        """Preview a Markdown file.
        
        Args:
            file_path: Path to the Markdown file
        """
        # This is a placeholder - will be implemented in task 6
        self.update_status("Markdown preview will be implemented in task 6")
    
    def preview_tmx(self, file_path: str) -> None:
        """Preview a TMX file.
        
        Args:
            file_path: Path to the TMX file
        """
        # This is a placeholder - will be implemented in task 6
        self.update_status("TMX preview will be implemented in task 6")
    
    def set_default_resource(self, tree: ttk.Treeview, resource_type: str) -> None:
        """Set the selected resource as default.
        
        Args:
            tree: The treeview widget
            resource_type: Type of resource
        """
        try:
            # Get selected item
            selection = tree.selection()
            if not selection:
                return
            
            # Get file path
            item = tree.item(selection[0])
            file_path = item["values"][1]
            
            # This is a placeholder - will be implemented in task 6
            self.update_status(f"Setting default {resource_type} will be implemented in task 6")
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "setting default resource")
    
    def delete_resource(self, tree: ttk.Treeview, resource_type: str) -> None:
        """Delete the selected resource.
        
        Args:
            tree: The treeview widget
            resource_type: Type of resource
        """
        try:
            # Get selected item
            selection = tree.selection()
            if not selection:
                return
            
            # Get file path and name
            item = tree.item(selection[0])
            file_path = item["values"][1]
            name = item["values"][0]
            
            # Confirm deletion
            if not tk.messagebox.askyesno(
                "Confirm Deletion", 
                f"Are you sure you want to delete the resource '{name}'?"
            ):
                return
            
            # Delete file
            os.remove(file_path)
            
            # Update status
            self.update_status(f"Resource '{name}' deleted")
            
            # Refresh resources
            self.refresh_resources()
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "deleting resource")