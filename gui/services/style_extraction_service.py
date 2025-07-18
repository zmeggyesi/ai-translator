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
import tempfile
from pathlib import Path
import logging

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
        
        # Setup logger for this service
        self.logger = logging.getLogger("style-extraction-service")
    
    def extract_style(self, config: Dict[str, Any], 
                     progress_callback: Optional[Callable[[int], None]] = None,
                     status_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Run style guide extraction using the CLI backend.
        
        Args:
            config: Style extraction configuration containing:
                - input_file: Path to input file
                - file_type: Type of file (tmx, pdf, docx, doc)
                - source_language: Source language code
                - target_language: Target language code (required for TMX)
                - output_file: Output file path (optional, will create temp file if not provided)
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            Dictionary with extraction results containing:
                - success: Boolean indicating success
                - style_guide: Generated style guide content
                - output_file: Path to output file
                - error: Error message if failed
        """
        try:
            self.logger.info("Starting style guide extraction")
            if status_callback:
                status_callback("Starting style guide extraction...")
            
            # Initial progress - start indeterminate
            if progress_callback:
                progress_callback(0)
            
            # Validate required fields
            if not config.get("input_file"):
                return {"success": False, "error": "Input file is required"}
            
            if not config.get("file_type"):
                return {"success": False, "error": "File type is required"}
            
            if not config.get("source_language"):
                return {"success": False, "error": "Source language is required"}
            
            # For TMX files, target language is required
            if config["file_type"] == "tmx" and not config.get("target_language"):
                return {"success": False, "error": "Target language is required for TMX files"}
            
            # Validation complete
            if progress_callback:
                progress_callback(10)
            
            # Handle output file - create directory if it doesn't exist
            output_file = config.get("output_file")
            if not output_file:
                # Create a temporary file in the same directory as input
                input_path = Path(config["input_file"])
                output_file = input_path.parent / f"{input_path.stem}_style_guide.md"
            
            output_path = Path(output_file)
            
            # Ensure the output directory exists
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Output directory ensured: {output_path.parent}")
            except Exception as e:
                return {"success": False, "error": f"Cannot create output directory: {str(e)}"}
            
            # Directory setup complete
            if progress_callback:
                progress_callback(15)
            
            # Build command - use 'uv run' to ensure dependencies are available
            cmd = [sys.executable, self.cli_script, "extract-style"]
            
            # Check if we should use uv run (if uv is available and we're not in a virtual env)
            try:
                import subprocess
                uv_result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
                if uv_result.returncode == 0:
                    # Use uv run for better dependency management
                    cmd = ["uv", "run", "python", self.cli_script, "extract-style"]
                    self.logger.info("Using 'uv run' for CLI execution")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.logger.info("Using regular python for CLI execution")
            
            # Add required arguments with correct CLI parameter names
            cmd.extend(["--input", config["input_file"]])
            cmd.extend(["--file-type", config["file_type"]])
            cmd.extend(["--source-language", config["source_language"]])
            cmd.extend(["--output", str(output_path)])
            
            # Add target language if provided (required for TMX)
            if config.get("target_language"):
                cmd.extend(["--target-language", config["target_language"]])
            
            self.logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Command preparation complete
            if progress_callback:
                progress_callback(20)
            
            if status_callback:
                status_callback("Running style guide extraction...")
            
            # Run the CLI command
            # Note: We capture output so it doesn't interfere with GUI,
            # but the GUI logs will still go to stdout via the main logger
            if progress_callback:
                progress_callback(25)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.root_dir  # Ensure we run from the correct directory
            )
            
            # CLI execution complete
            if progress_callback:
                progress_callback(85)
            
            # Log the CLI output for debugging
            if result.stdout:
                self.logger.debug(f"CLI stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"CLI stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error occurred"
                self.logger.error(f"CLI extraction failed with return code {result.returncode}: {error_msg}")
                if status_callback:
                    status_callback(f"Extraction failed: {error_msg}")
                return {
                    "success": False,
                    "error": f"Style extraction failed: {error_msg}",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            
            # CLI success, check output file
            if progress_callback:
                progress_callback(90)
            
            # Check if output file was created
            if not output_path.exists():
                self.logger.error(f"Output file was not created: {output_path}")
                return {
                    "success": False,
                    "error": "Style guide file was not created",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            
            # Read the generated style guide
            if progress_callback:
                progress_callback(95)
                
            try:
                style_guide_content = output_path.read_text(encoding='utf-8')
                self.logger.info(f"Successfully read style guide from {output_path} ({len(style_guide_content)} chars)")
            except Exception as e:
                self.logger.error(f"Failed to read generated style guide: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to read generated style guide: {str(e)}"
                }
            
            # Complete
            if progress_callback:
                progress_callback(100)
            
            if status_callback:
                status_callback("Style guide extraction completed successfully")
            
            self.logger.info("Style guide extraction completed successfully")
            
            return {
                "success": True,
                "style_guide": style_guide_content,
                "output_file": str(output_path),
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "Style extraction timed out after 5 minutes"
            self.logger.error(error_msg)
            if status_callback:
                status_callback(error_msg)
            return {"success": False, "error": error_msg}
        
        except Exception as e:
            self.logger.error(f"Unexpected error during style extraction: {str(e)}")
            ErrorHandler.handle_exception(e, "extracting style guide")
            return {"success": False, "error": str(e)}
    
    def extract_style_async(self, config: Dict[str, Any], 
                           progress_callback: Optional[Callable[[int], None]] = None,
                           status_callback: Optional[Callable[[str], None]] = None,
                           completion_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> threading.Thread:
        """Run style extraction asynchronously.
        
        Args:
            config: Style extraction configuration
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            completion_callback: Callback called when extraction completes
            
        Returns:
            Thread object
        """
        def worker():
            try:
                result = self.extract_style(config, progress_callback, status_callback)
                if completion_callback:
                    completion_callback(result)
            except Exception as e:
                self.logger.error(f"Error in async worker: {str(e)}")
                if completion_callback:
                    completion_callback({"success": False, "error": str(e)})
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        return thread
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate style extraction configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not config.get("input_file"):
            return False, "Input file is required"
        
        if not config.get("file_type"):
            return False, "File type is required"
        
        valid_file_types = ["tmx", "pdf", "docx", "doc"]
        if config["file_type"] not in valid_file_types:
            return False, f"Invalid file type. Must be one of: {', '.join(valid_file_types)}"
        
        if not config.get("source_language"):
            return False, "Source language is required"
        
        # For TMX files, target language is required
        if config["file_type"] == "tmx" and not config.get("target_language"):
            return False, "Target language is required for TMX files"
        
        # Check input file existence (but NOT output file - that should be created)
        input_path = Path(config["input_file"])
        if not input_path.exists():
            return False, f"Input file does not exist: {config['input_file']}"
        
        # Validate that we can write to the output directory if specified
        if config.get("output_file"):
            output_path = Path(config["output_file"])
            try:
                # Test if we can create the parent directory
                output_path.parent.mkdir(parents=True, exist_ok=True)
                # Test if we can write to the directory
                test_file = output_path.parent / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                return False, f"Cannot write to output directory {output_path.parent}: {str(e)}"
        
        return True, ""