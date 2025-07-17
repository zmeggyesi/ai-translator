"""
Glossary service for the Translation GUI.
Provides interface to the CLI backend for glossary operations.
"""
import subprocess
import threading
import json
import os
import csv
from typing import Dict, Any, Optional, Callable, List, Tuple
import sys

from gui.components.error_handler import ErrorHandler


class GlossaryService:
    """Service for glossary operations."""
    
    def __init__(self):
        """Initialize the glossary service."""
        # Get the root directory of the application
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Path to CLI script
        self.cli_script = os.path.join(self.root_dir, "cli.py")
    
    def extract_glossary(self, config: Dict[str, Any], 
                        progress_callback: Optional[Callable[[int], None]] = None,
                        status_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Run glossary extraction using the CLI backend.
        
        Args:
            config: Glossary extraction configuration
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            Dictionary with extraction results
        """
        try:
            if status_callback:
                status_callback("Starting glossary extraction...")
            
            # Build command
            cmd = [sys.executable, self.cli_script, "extract-glossary"]
            
            # Add arguments
            if config.get("input_file"):
                cmd.extend(["--input", config["input_file"]])
            
            if config.get("source_type"):
                cmd.extend(["--type", config["source_type"]])
            
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
                status_callback("Running glossary extraction...")
            
            if progress_callback:
                progress_callback(10)
            
            # This is a placeholder - in task 5 we'll implement actual subprocess execution
            # For now, just simulate the process
            
            if progress_callback:
                progress_callback(100)
            
            if status_callback:
                status_callback("Glossary extraction completed")
            
            # Return dummy result
            return {
                "glossary": [
                    {"source": "example", "target": "ejemplo"},
                    {"source": "translation", "target": "traducción"},
                    {"source": "glossary", "target": "glosario"}
                ],
                "output_file": config.get("output_file", "")
            }
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "extracting glossary")
            return {"error": str(e)}
    
    def load_glossary(self, file_path: str) -> List[Dict[str, str]]:
        """Load glossary from CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of term pairs
        """
        try:
            glossary = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        glossary.append({
                            "source": row[0],
                            "target": row[1]
                        })
            
            return glossary
            
        except Exception as e:
            ErrorHandler.handle_exception(e, f"loading glossary from {file_path}")
            return []
    
    def save_glossary(self, glossary: List[Dict[str, str]], file_path: str) -> bool:
        """Save glossary to CSV file.
        
        Args:
            glossary: List of term pairs
            file_path: Path to CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["source", "target"])
                
                for entry in glossary:
                    writer.writerow([entry["source"], entry["target"]])
            
            return True
            
        except Exception as e:
            ErrorHandler.handle_exception(e, f"saving glossary to {file_path}")
            return False
    
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