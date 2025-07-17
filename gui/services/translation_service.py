"""
Translation service for the Translation GUI.
Provides interface to the CLI backend for translation operations.
"""
import subprocess
import threading
import json
import os
from typing import Dict, Any, Optional, Callable, List
import sys

from gui.components.error_handler import ErrorHandler


class TranslationService:
    """Service for translation operations."""
    
    def __init__(self):
        """Initialize the translation service."""
        # Get the root directory of the application
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Path to CLI script
        self.cli_script = os.path.join(self.root_dir, "cli.py")
    
    def translate(self, config: Dict[str, Any], 
                 progress_callback: Optional[Callable[[int], None]] = None,
                 status_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Run translation using the CLI backend.
        
        Args:
            config: Translation configuration
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            Dictionary with translation results
        """
        try:
            if status_callback:
                status_callback("Starting translation...")
            
            # Build command
            cmd = [sys.executable, self.cli_script, "translate"]
            
            # Add arguments
            if config.get("input_file"):
                cmd.extend(["--input", config["input_file"]])
            
            if config.get("source_language"):
                cmd.extend(["--source-lang", config["source_language"]])
            
            if config.get("target_language"):
                cmd.extend(["--target-lang", config["target_language"]])
            
            if config.get("glossary_file"):
                cmd.extend(["--glossary", config["glossary_file"]])
            
            if config.get("style_guide_file"):
                cmd.extend(["--style-guide", config["style_guide_file"]])
            
            if config.get("tmx_file"):
                cmd.extend(["--tmx", config["tmx_file"]])
            
            if config.get("enable_review", False):
                cmd.append("--review")
            
            if config.get("generate_visualizations", False):
                cmd.append("--visualize")
            
            # Add output format
            cmd.extend(["--output-format", "json"])
            
            # Run command
            if status_callback:
                status_callback("Running translation...")
            
            if progress_callback:
                progress_callback(10)
            
            # This is a placeholder - in task 3 we'll implement actual subprocess execution
            # For now, just simulate the process
            
            if progress_callback:
                progress_callback(100)
            
            if status_callback:
                status_callback("Translation completed")
            
            # Return dummy result
            return {
                "original": "Sample source text",
                "translated": "Sample translated text",
                "review_scores": {
                    "grammar": 0.95,
                    "style": 0.85,
                    "faithfulness": 0.90
                }
            }
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "running translation")
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