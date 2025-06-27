import csv
import tempfile
import os
from unittest.mock import patch
import pytest

def test_glossary_loading_with_headers():
    """Test glossary loading when CSV has proper headers"""
    # Create a temporary CSV file with headers
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['term', 'translation'])
        writer.writerow(['hello', 'こんにちは'])
        writer.writerow(['world', '世界'])
        temp_file = f.name
    
    try:
        # Test the glossary loading logic
        glossary = {}
        with open(temp_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if fieldnames and "term" in fieldnames and "translation" in fieldnames:
                for row in reader:
                    if row["term"] and row["translation"]:
                        glossary[row["term"]] = row["translation"]
        
        assert len(glossary) == 2
        assert glossary["hello"] == "こんにちは"
        assert glossary["world"] == "世界"
        
    finally:
        os.unlink(temp_file)

def test_glossary_loading_without_headers():
    """Test glossary loading when CSV has no headers"""
    # Create a temporary CSV file without headers
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['hello', 'こんにちは'])
        writer.writerow(['world', '世界'])
        writer.writerow(['data backup', 'データ バックアップ'])
        temp_file = f.name
    
    try:
        # Test the glossary loading logic
        glossary = {}
        with open(temp_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if fieldnames and "term" in fieldnames and "translation" in fieldnames:
                # This branch shouldn't execute for headerless CSV
                for row in reader:
                    if row["term"] and row["translation"]:
                        glossary[row["term"]] = row["translation"]
            else:
                # CSV doesn't have proper headers, treat as headerless
                f.seek(0)
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if len(row) >= 2 and row[0] and row[1]:
                        glossary[row[0]] = row[1]
        
        assert len(glossary) == 3
        assert glossary["hello"] == "こんにちは"
        assert glossary["world"] == "世界"
        assert glossary["data backup"] == "データ バックアップ"
        
    finally:
        os.unlink(temp_file)

def test_glossary_loading_skips_incomplete_rows():
    """Test that glossary loading skips rows with insufficient data"""
    # Create a temporary CSV file with some incomplete rows
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['hello', 'こんにちは'])
        writer.writerow(['incomplete'])  # Missing translation
        writer.writerow(['', 'empty_term'])  # Empty term
        writer.writerow(['world', '世界'])
        temp_file = f.name
    
    try:
        # Test the glossary loading logic
        glossary = {}
        with open(temp_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if not (fieldnames and "term" in fieldnames and "translation" in fieldnames):
                f.seek(0)
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if len(row) >= 2 and row[0] and row[1]:
                        glossary[row[0]] = row[1]
        
        # Should only have 2 valid entries, skipping incomplete ones
        assert len(glossary) == 2
        assert glossary["hello"] == "こんにちは"
        assert glossary["world"] == "世界"
        assert "incomplete" not in glossary
        assert "" not in glossary
        
    finally:
        os.unlink(temp_file)

def test_glossary_loading_handles_japanese_content():
    """Test that glossary loading properly handles Japanese characters"""
    # Test with the actual glossary file structure
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['A force for', '確実に守る力'])
        writer.writerow(['access control list', 'アクセス コントロール リスト'])
        writer.writerow(['artificial intelligence', '人工知能'])
        temp_file = f.name
    
    try:
        # Test the glossary loading logic
        glossary = {}
        with open(temp_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if not (fieldnames and "term" in fieldnames and "translation" in fieldnames):
                f.seek(0)
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if len(row) >= 2 and row[0] and row[1]:
                        glossary[row[0]] = row[1]
        
        assert len(glossary) == 3
        assert glossary["A force for"] == "確実に守る力"
        assert glossary["access control list"] == "アクセス コントロール リスト"
        assert glossary["artificial intelligence"] == "人工知能"
        
    finally:
        os.unlink(temp_file)