"""
Test script for the Translation GUI framework.
This script tests the basic functionality of the GUI framework.
"""
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Add parent directory to path to allow importing from gui package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.app import TranslationGUI


def test_gui_framework():
    """Test the basic functionality of the GUI framework."""
    print("Testing GUI framework...")
    
    # Create the application
    app = TranslationGUI()
    
    # Update status to show test is running
    app.update_status("Testing framework...")
    
    # Test progress bar
    for i in range(0, 101, 10):
        app.set_progress(i)
        app.root.update()
        app.root.after(100)  # Short delay to see progress
    
    # Reset progress
    app.set_progress(0)
    
    # Test theme toggle
    app.toggle_theme()
    app.root.update()
    app.root.after(500)  # Delay to see theme change
    
    # Toggle back
    app.toggle_theme()
    app.root.update()
    
    # Test tab switching
    for i in range(app.notebook.index('end')):
        app.notebook.select(i)
        app.root.update()
        app.root.after(300)  # Delay to see tab change
    
    # Show test completion message
    app.update_status("Framework test completed successfully")
    messagebox.showinfo("Test Complete", "GUI framework test completed successfully!")
    
    # Close the application
    app.root.destroy()


if __name__ == "__main__":
    test_gui_framework()