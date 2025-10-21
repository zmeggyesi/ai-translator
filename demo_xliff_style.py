#!/usr/bin/env python3
"""Demo script for XLIFF style extraction.

This script demonstrates how to extract a style guide from an XLIFF file
using the new XLIFF support in the style extractor.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from nodes.extract_style import extract_style_guide_from_xliff, extract_style_guide_unified


def demo_basic_xliff_extraction():
    """Demo: Basic XLIFF style extraction with mocked LLM."""
    print("=" * 70)
    print("Demo: XLIFF Style Extraction")
    print("=" * 70)
    
    # Create a sample XLIFF file
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en" target-language="es" datatype="plaintext">
    <body>
      <trans-unit id="1">
        <source>Welcome to our professional services.</source>
        <target>Bienvenido a nuestros servicios profesionales.</target>
      </trans-unit>
      <trans-unit id="2">
        <source>We provide high-quality solutions for your business needs.</source>
        <target>Proporcionamos soluciones de alta calidad para sus necesidades comerciales.</target>
      </trans-unit>
      <trans-unit id="3">
        <source>Our team is dedicated to excellence and customer satisfaction.</source>
        <target>Nuestro equipo está dedicado a la excelencia y la satisfacción del cliente.</target>
      </trans-unit>
      <trans-unit id="4">
        <source>Contact us today for a free consultation.</source>
        <target>Contáctenos hoy para una consulta gratuita.</target>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    # Create temporary XLIFF file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xliff', delete=False, encoding='utf-8') as f:
        f.write(xliff_content)
        temp_xliff = f.name
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as out_f:
        temp_output = out_f.name
    
    try:
        print(f"\n1. Created sample XLIFF file: {temp_xliff}")
        print(f"2. Output will be written to: {temp_output}\n")
        
        # Mock the LLM to avoid needing API keys
        mock_style_guide = """# Style Guide

## Tone and Voice
- **Professional and welcoming**: The content uses formal language while maintaining a friendly, approachable tone
- **Service-oriented**: Focus on customer needs and satisfaction
- **Quality-focused**: Emphasis on high standards and excellence

## Key Characteristics
1. Direct and clear communication
2. Customer-centric messaging
3. Professional terminology
4. Action-oriented language (e.g., "Contact us today")

## Common Phrases
- "professional services"
- "high-quality solutions"
- "customer satisfaction"
- "business needs"

## Recommendations
- Maintain formal but approachable tone
- Use active voice and direct calls-to-action
- Emphasize quality and professionalism
- Focus on customer benefits
"""
        
        with patch('nodes.extract_style.infer_style_guide_from_tmx') as mock_infer:
            mock_infer.return_value = mock_style_guide
            
            print("3. Extracting style guide from XLIFF source elements...")
            result = extract_style_guide_from_xliff(
                temp_xliff,
                source_language="English",
                output_path=temp_output
            )
            
            print(f"✓ Style guide successfully extracted!")
            print(f"\n{'=' * 70}")
            print("Generated Style Guide:")
            print('=' * 70)
            print(result)
            print('=' * 70)
            
    finally:
        # Clean up temporary files
        if os.path.exists(temp_xliff):
            os.unlink(temp_xliff)
        if os.path.exists(temp_output):
            os.unlink(temp_output)


def demo_unified_api():
    """Demo: Using the unified API for XLIFF files."""
    print("\n" + "=" * 70)
    print("Demo: Unified API for XLIFF Style Extraction")
    print("=" * 70)
    
    # Create a sample XLIFF file
    xliff_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file source-language="en" datatype="plaintext">
    <body>
      <trans-unit id="1">
        <source>Our innovative technology drives industry-leading results.</source>
      </trans-unit>
      <trans-unit id="2">
        <source>Partner with us to transform your digital presence.</source>
      </trans-unit>
    </body>
  </file>
</xliff>'''
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xlf', delete=False, encoding='utf-8') as f:
        f.write(xliff_content)
        temp_xliff = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as out_f:
        temp_output = out_f.name
    
    try:
        print(f"\n1. Testing with .xlf extension: {temp_xliff}")
        
        mock_style_guide = """# Style Guide (Technology Focus)

## Tone
- Forward-thinking and innovative
- Professional and authoritative
- Partnership-oriented

## Language Patterns
- Industry terminology ("industry-leading", "digital presence")
- Action verbs ("drives", "transform")
- Collaborative language ("partner with us")
"""
        
        with patch('nodes.extract_style.infer_style_guide_from_tmx') as mock_infer:
            mock_infer.return_value = mock_style_guide
            
            # Test with 'xlf' file type
            result = extract_style_guide_unified(
                file_path=temp_xliff,
                file_type='xlf',
                source_language='English',
                output_path=temp_output
            )
            
            print("✓ Successfully extracted using 'xlf' file type")
            print(f"\n{result}")
            
    finally:
        # Clean up
        if os.path.exists(temp_xliff):
            os.unlink(temp_xliff)
        if os.path.exists(temp_output):
            os.unlink(temp_output)


def demo_with_real_file():
    """Demo: Extract style from the real urschel.xlf file (if available)."""
    print("\n" + "=" * 70)
    print("Demo: Extract from Real XLIFF File")
    print("=" * 70)
    
    xliff_path = Path("data/urschel.xlf")
    
    if not xliff_path.exists():
        print(f"\n⚠ Real XLIFF file not found: {xliff_path}")
        print("  Skipping this demo.")
        return
    
    print(f"\n1. Found XLIFF file: {xliff_path}")
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as out_f:
        temp_output = out_f.name
    
    try:
        # Mock the LLM
        mock_style_guide = """# Urschel Equipment Style Guide

## Industry Focus
- Food processing equipment
- Technical and specialized terminology
- Product-focused language

## Tone
- Professional and technical
- Detailed and precise
- Industry-specific

## Common Terms
- Equipment types: Slicers, Dicers, Milling Equipment, Shredders
- Technical specifications
- Product categories

## Style Characteristics
- Clear, technical descriptions
- Product categorization
- Industry-standard terminology
"""
        
        with patch('nodes.extract_style.infer_style_guide_from_tmx') as mock_infer:
            mock_infer.return_value = mock_style_guide
            
            print("2. Extracting style guide from urschel.xlf...")
            result = extract_style_guide_unified(
                file_path=str(xliff_path),
                file_type='xlf',
                source_language='English',
                output_path=temp_output
            )
            
            print(f"✓ Style guide extracted and saved to: {temp_output}")
            print(f"\n{result}")
            
    finally:
        # Clean up
        if os.path.exists(temp_output):
            os.unlink(temp_output)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("XLIFF Style Extraction Demonstration")
    print("=" * 70)
    print("\nThis demo shows how to extract style guides from XLIFF files.")
    print("The LLM calls are mocked to avoid needing API keys.\n")
    
    # Run demos
    demo_basic_xliff_extraction()
    demo_unified_api()
    demo_with_real_file()
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nTo use with a real LLM (requires OPENAI_API_KEY):")
    print("  python cli.py extract-style \\")
    print("    --input data/urschel.xlf \\")
    print("    --file-type xlf \\")
    print("    --source-language English \\")
    print("    --output style_guide.md")
    print()

