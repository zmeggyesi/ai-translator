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
import time
from pathlib import Path

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
        self._cancel_requested = False
        self._current_process = None
    
    def translate(self, config: Dict[str, Any], 
                 progress_callback: Optional[Callable[[int], None]] = None,
                 status_callback: Optional[Callable[[str], None]] = None,
                 review_callback: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        """Run translation using the CLI backend.
        
        Args:
            config: Translation configuration
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            review_callback: Callback for human review interrupts
            
        Returns:
            Dictionary with translation results
        """
        try:
            self._cancel_requested = False
            
            if status_callback:
                status_callback("Validating configuration...")
            
            # Validate required fields
            if not config.get("input_file") or not os.path.exists(config["input_file"]):
                raise ValueError("Input file is required and must exist")
            
            if not config.get("source_language") or not config.get("target_language"):
                raise ValueError("Source and target languages are required")
            
            if progress_callback:
                progress_callback(10)
            
            # Build command
            cmd = [sys.executable, self.cli_script, "translate-file"]
            
            # Add required arguments
            cmd.extend(["--input", config["input_file"]])
            cmd.extend(["--source-language", config["source_language"]])
            cmd.extend(["--target-language", config["target_language"]])
            
            # Add optional arguments
            if config.get("glossary_file") and os.path.exists(config["glossary_file"]):
                cmd.extend(["--glossary", config["glossary_file"]])
            
            if config.get("style_guide_file") and os.path.exists(config["style_guide_file"]):
                cmd.extend(["--style-guide", config["style_guide_file"]])
            
            if config.get("tmx_file") and os.path.exists(config["tmx_file"]):
                cmd.extend(["--tmx", config["tmx_file"]])
            
            if config.get("enable_review", False):
                cmd.append("--review")
            
            if status_callback:
                status_callback("Starting translation...")
            
            if progress_callback:
                progress_callback(20)
            
            # Create a temporary output file for results
            output_file = Path(self.root_dir) / "temp_translation_output.json"
            
            # Run the translation process
            result = self._run_translation_process(
                cmd, output_file, progress_callback, status_callback, review_callback
            )
            
            # Clean up temporary file
            if output_file.exists():
                output_file.unlink()
            
            return result
            
        except Exception as e:
            ErrorHandler.handle_exception(e, "running translation")
            return {"error": str(e)}
    
    def _run_translation_process(self, cmd: List[str], output_file: Path,
                               progress_callback: Optional[Callable[[int], None]],
                               status_callback: Optional[Callable[[str], None]],
                               review_callback: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]]) -> Dict[str, Any]:
        """Run the translation process with proper interrupt handling."""
        
        # Start the process
        self._current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        result = {
            "original": "",
            "translated": "",
            "review_scores": {},
            "process_completed": False
        }
        
        try:
            # Read output line by line to handle interrupts
            output_lines = []
            error_lines = []
            
            if progress_callback:
                progress_callback(30)
            
            # Monitor the process
            while self._current_process.poll() is None:
                if self._cancel_requested:
                    self._current_process.terminate()
                    return {"error": "Translation cancelled by user"}
                
                # Check for output
                line = self._current_process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    
                    # Check for human review interrupt
                    if "Human Review Interrupt" in line and review_callback:
                        if status_callback:
                            status_callback("Waiting for human review...")
                        
                        # Parse the interrupt information
                        interrupt_data = self._parse_interrupt_output(output_lines)
                        
                        # Call the review callback
                        review_result = review_callback(interrupt_data)
                        
                        # Send the review result back to the process
                        if review_result:
                            self._current_process.stdin.write(json.dumps(review_result) + "\n")
                        else:
                            self._current_process.stdin.write("\n")
                        self._current_process.stdin.flush()
                        
                        if status_callback:
                            status_callback("Continuing translation...")
                
                time.sleep(0.1)
            
            # Get final output
            stdout, stderr = self._current_process.communicate()
            
            if stdout:
                output_lines.extend(stdout.strip().split('\n'))
            if stderr:
                error_lines.extend(stderr.strip().split('\n'))
            
            if progress_callback:
                progress_callback(80)
            
            # Parse the results from output
            result = self._parse_translation_output(output_lines, error_lines)
            
            if progress_callback:
                progress_callback(100)
            
            if status_callback:
                if result.get("error"):
                    status_callback(f"Translation failed: {result['error']}")
                else:
                    status_callback("Translation completed successfully")
            
            result["process_completed"] = True
            return result
            
        except Exception as e:
            if self._current_process:
                self._current_process.terminate()
            raise e
        finally:
            self._current_process = None
    
    def _parse_interrupt_output(self, output_lines: List[str]) -> Dict[str, Any]:
        """Parse human review interrupt information from CLI output."""
        interrupt_data = {
            "message": "Review the filtered glossary",
            "current_glossary": {}
        }
        
        # Look for glossary information in the output
        in_glossary_section = False
        for line in output_lines:
            if "Current filtered glossary:" in line:
                in_glossary_section = True
                continue
            elif "--------------------" in line and in_glossary_section:
                break
            elif in_glossary_section:
                # Try to parse glossary entries
                try:
                    if "{" in line and "}" in line:
                        glossary = json.loads(line)
                        interrupt_data["current_glossary"] = glossary
                        break
                except json.JSONDecodeError:
                    continue
        
        return interrupt_data
    
    def _parse_translation_output(self, output_lines: List[str], error_lines: List[str]) -> Dict[str, Any]:
        """Parse translation results from CLI output."""
        result = {
            "original": "",
            "translated": "",
            "review_scores": {},
            "error": None
        }
        
        # Check for errors first
        if error_lines:
            error_text = "\n".join(error_lines)
            if "Error" in error_text or "Exception" in error_text:
                result["error"] = error_text
                return result
        
        # Parse output sections
        current_section = None
        content_lines = []
        
        for line in output_lines:
            if "--- Original Content ---" in line:
                current_section = "original"
                content_lines = []
            elif "--- Translated Content" in line:
                current_section = "translated"
                content_lines = []
            elif "--- Translation Review ---" in line:
                current_section = "review"
                content_lines = []
            elif line.startswith("---") and current_section:
                # End of section
                if current_section == "original":
                    result["original"] = "\n".join(content_lines).strip()
                elif current_section == "translated":
                    result["translated"] = "\n".join(content_lines).strip()
                current_section = None
                content_lines = []
            elif current_section:
                content_lines.append(line)
            elif "Overall Review Score:" in line:
                # Parse review score
                try:
                    score_text = line.split(":")[-1].strip()
                    score = float(score_text.split()[0])
                    result["review_scores"]["overall"] = score
                except (ValueError, IndexError):
                    pass
        
        # Handle case where content continues to end of output
        if current_section and content_lines:
            if current_section == "original":
                result["original"] = "\n".join(content_lines).strip()
            elif current_section == "translated":
                result["translated"] = "\n".join(content_lines).strip()
        
        return result
    
    def cancel_translation(self) -> None:
        """Cancel the current translation process."""
        self._cancel_requested = True
        if self._current_process:
            self._current_process.terminate()
    
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