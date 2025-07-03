#!/usr/bin/env python3
"""
TMX CLI Test Script
===================

Simple test script to demonstrate the TMX CLI functionality.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a command and return its output"""
    print(f"\n🔄 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Success")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print("stdout:", e.stdout)
        if e.stderr:
            print("stderr:", e.stderr)
        return None

def test_tmx_functionality():
    """Test TMX functionality with the CLI"""
    print("🌍 Testing TMX CLI Functionality")
    print("=" * 50)
    
    # Check that TMX file exists
    tmx_file = Path("data/sample.tmx")
    if not tmx_file.exists():
        print(f"❌ TMX file not found: {tmx_file}")
        return
    
    # Test 1: Translation with TMX (should use exact match)
    print("\n📚 Test 1: Translation with exact TMX match")
    cmd = [
        "uv", "run", "python", "cli.py", "translate-file",
        "--source-language", "en",
        "--target-language", "fr", 
        "--input", "data/input.txt",
        "--glossary", "data/glossary.csv",
        "--style-guide", "data/style_guide.md",
        "--tmx", "data/sample.tmx",
        "--review"
    ]
    
    output = run_command(cmd)
    
    if output and "Hello world" in output:
        if "Bonjour le monde" in output:
            print("✅ TMX exact match appears to be working")
        else:
            print("⚠️  Expected TMX translation 'Bonjour le monde' not found")
    
    # Test 2: Show help with TMX option
    print("\n📖 Test 2: Check CLI help includes TMX option")
    cmd = ["uv", "run", "python", "cli.py", "translate-file", "--help"]
    output = run_command(cmd)
    
    if output and "--tmx" in output:
        print("✅ TMX option found in help text")
    else:
        print("❌ TMX option not found in help text")
    
    # Test 3: Run tests to verify functionality
    print("\n🧪 Test 3: Running TMX unit tests")
    cmd = ["uv", "run", "python", "-m", "pytest", "tests/test_tmx_functionality.py", "-v", "--tb=short"]
    output = run_command(cmd)
    
    if output and "passed" in output:
        print("✅ TMX unit tests appear to be passing")
    else:
        print("⚠️  Some TMX unit tests may have issues")

if __name__ == "__main__":
    test_tmx_functionality()