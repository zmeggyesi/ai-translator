"""
Error handling utilities for the Translation GUI.
Provides centralized error handling and user-friendly error messages.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, Any, Callable
import traceback
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.expanduser("~"), ".translation-gui", "error.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("translation-gui")


class ErrorHandler:
    """Centralized error handling and user notification."""
    
    # Common error messages with suggested solutions
    ERROR_MESSAGES = {
        "FileNotFoundError": {
            "title": "File Not Found",
            "message": "The specified file could not be found.",
            "solution": "Please check that the file exists and you have permission to access it."
        },
        "PermissionError": {
            "title": "Permission Denied",
            "message": "You don't have permission to access this file or directory.",
            "solution": "Try running the application with administrator privileges or check file permissions."
        },
        "ValueError": {
            "title": "Invalid Value",
            "message": "An invalid value was provided.",
            "solution": "Please check your input and try again."
        },
        "KeyError": {
            "title": "Missing Key",
            "message": "A required configuration key is missing.",
            "solution": "The application configuration may be corrupted. Try resetting to defaults."
        },
        "ConnectionError": {
            "title": "Connection Error",
            "message": "Could not connect to the required service.",
            "solution": "Please check your internet connection and try again."
        },
        "TimeoutError": {
            "title": "Operation Timeout",
            "message": "The operation took too long to complete.",
            "solution": "Please try again or try with a smaller input file."
        }
    }
    
    @staticmethod
    def handle_exception(exception: Exception, context: str = "") -> None:
        """Handle any exception with appropriate user feedback.
        
        Args:
            exception: The exception that was raised
            context: Additional context about where the error occurred
        """
        # Log the error
        logger.error(f"Error in {context}: {str(exception)}")
        logger.error(traceback.format_exc())
        
        # Get error type
        error_type = type(exception).__name__
        
        # Get error info or use generic message
        error_info = ErrorHandler.ERROR_MESSAGES.get(error_type, {
            "title": "Application Error",
            "message": str(exception),
            "solution": "Please try again or restart the application."
        })
        
        # Show error dialog
        ErrorHandler.show_error_dialog(
            error_info["title"],
            f"{error_info['message']}\n\n{context}\n\n{error_info['solution']}"
        )
    
    @staticmethod
    def handle_file_error(error: Exception, file_path: str) -> None:
        """Handle file-related errors with user-friendly messages.
        
        Args:
            error: The exception that was raised
            file_path: Path to the file that caused the error
        """
        context = f"Error accessing file: {file_path}"
        ErrorHandler.handle_exception(error, context)
    
    @staticmethod
    def handle_validation_error(field_name: str, message: str) -> None:
        """Handle validation errors for form fields.
        
        Args:
            field_name: Name of the field with validation error
            message: Validation error message
        """
        ErrorHandler.show_error_dialog(
            "Validation Error",
            f"Invalid {field_name}: {message}"
        )
    
    @staticmethod
    def handle_processing_error(error: Exception, operation: str) -> None:
        """Handle processing errors with retry options.
        
        Args:
            error: The exception that was raised
            operation: Description of the operation that failed
        """
        context = f"Error during {operation}"
        ErrorHandler.handle_exception(error, context)
    
    @staticmethod
    def show_error_dialog(title: str, message: str, details: Optional[str] = None) -> None:
        """Display error dialog with optional details.
        
        Args:
            title: Dialog title
            message: Error message
            details: Optional technical details
        """
        if details:
            full_message = f"{message}\n\nDetails:\n{details}"
        else:
            full_message = message
        
        messagebox.showerror(title, full_message)
    
    @staticmethod
    def validate_required_field(value: str, field_name: str) -> bool:
        """Validate that a required field is not empty.
        
        Args:
            value: Field value
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if not value or value.strip() == "":
            ErrorHandler.handle_validation_error(field_name, "This field is required")
            return False
        return True
    
    @staticmethod
    def validate_file_exists(file_path: str, field_name: str) -> bool:
        """Validate that a file exists.
        
        Args:
            file_path: Path to the file
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if not file_path or file_path.strip() == "":
            return True  # Empty is allowed, will be caught by required field validation if needed
        
        if not os.path.isfile(file_path):
            ErrorHandler.handle_validation_error(field_name, f"File does not exist: {file_path}")
            return False
        return True
    
    @staticmethod
    def validate_language_code(code: str, field_name: str) -> bool:
        """Validate that a language code is valid.
        
        Args:
            code: Language code
            field_name: Name of the field for error messages
            
        Returns:
            True if valid, False otherwise
        """
        # Simple validation - could be expanded with a proper list of language codes
        if not code or len(code) < 2:
            ErrorHandler.handle_validation_error(field_name, "Invalid language code")
            return False
        return True