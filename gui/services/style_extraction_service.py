"""
Style extraction service for the Translation GUI.
Provides interface to the CLI backend for style guide extraction.
"""
import subprocess
import threading
import json
import os
from typing import Dict, Any, Optional, Callable, List
import sys

from gui.components.error_handler import ErrorHandler


class StyleExtractionService:
    """Service for style guide extraction operations."""
    
    def __init__(self):
        """Initialize the style extraction service."""
        # Get the root directory of the application
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Path to CLI script
        self.cli_script = os.path.join(self.root_dir, "cli.py")
    
    def extract_style(self, config: Dict[str, Any], 
                     progress_callback: Optional[Callable[[int], None]] = None,
                     status_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Run style guide extraction using the CLI backend.
        
        Args:
            config: Style extraction configuration
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            Dictionary with extraction results
        """
        try:
            if status_callback:
                status_callback("Starting style guide extraction...")
            
            # Build command
            cmd = [sys.executable, self.cli_script, "extract-style"]
            
            # Add arguments
            if config.get("input_file"):
                cmd.extend(["--input", config["input_file"]])
            
            if config.get("file_type") and config["file_type"] != "auto":
                cmd.extend(["--type", config["file_type"]])
            
            if config.get("source_language"):
                cmd.extend(["--source-lang", config["source_language"]])
            
            if config.get("target_language"):
                cmd.extend(["--target-lang", config["target_language"]])
            
            if config.get("output_file"):
                cmd.extend(["--output", config["output_file"]])
            
            # Add output format
            cmd.extend(["--output-format", "json"])
            
            # Run command
            if status_callback:
                status_callback("Running style guide extraction...")
            
            if progress_callback:
                progress_callback(10)
            
            # This is a placeholder - in task 4 we'll implement actual subprocess execution
            # For now, just simulate the process
            
            if progress_callback:
                progress_callback(100)
            
            if status_callback:
                status_callback("Style guide extraction completed")
            
            # Return dummy result
            return {
                "style_guide": "# Sample Style Guide\n\n## Tone and Voice\n\n* Use active voice\n* Be concise\n* Be professional but friendly",
                "output_file": config.get("output_file", "")
            }
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "extracting style guide")
            return {"error": str(e)}
    
    def run_async(self, func: Callable, *args, **kwargs) -> threading.Thread:
        """Run a function asynchronously in a separate thread.
        
        Args:
            func: Function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Thread object
        """
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread