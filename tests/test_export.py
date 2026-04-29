"""MemoMind Export Service Tests"""

import unittest
import sys
import json
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.export_service import ExportService
from core.version_service import VersionService


class TestExportService(unittest.TestCase):
    """Export Service Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.export = ExportService(self.db)
        self.versions = VersionService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Insert test data"""
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Test Note", "This is test content", json.dumps(["test", "MemoMind"])))
        self.db.commit()
        self.note_id = 1
    
    def test_export_to_markdown(self):
        """Test export to Markdown"""
        markdown = self.export.export_note_to_markdown(self.note_id)
        
        self.assertIn("---", markdown)
        self.assertIn("title: Test Note", markdown)
        self.assertIn("tags:", markdown)
        self.assertIn("This is test content", markdown)
    
    def test_export_to_markdown_with_versions(self):
        """Test export to Markdown with version history"""
        self.versions.save_version(self.note_id, "V1 Title", "V1 Content", ["v1"])
        
        markdown = self.export.export_note_to_markdown(self.note_id, include_versions=True)
        
        # Check version history section (in Chinese)
        self.assertIn("版本历史", markdown)
        self.assertIn("V1 Content", markdown)
    
    def test_export_to_dict(self):
        """Test export to dictionary"""
        note = self.export.export_note_to_dict(self.note_id)
        
        self.assertEqual(note['title'], "Test Note")
        self.assertEqual(note['content'], "This is test content")
        self.assertEqual(note['tags'], ["test", "MemoMind"])
        self.assertIn('id', note)
    
    def test_export_to_dict_with_versions(self):
        """Test export to dictionary with version history"""
        self.versions.save_version(self.note_id, "V1 Title", "V1 Content", ["v1"])
        
        note = self.export.export_note_to_dict(self.note_id, include_versions=True)
        
        self.assertIn('versions', note)
        self.assertEqual(len(note['versions']), 1)
    
    def test_export_all_to_markdown_files(self):
        """Test batch export to Markdown files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = self.export.export_all_to_markdown_files(tmpdir)
            
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith('.md'))
            
            with open(files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("Test Note", content)
    
    def test_export_all_to_json(self):
        """Test export to JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmpfile:
            tmpfilepath = tmpfile.name
        
        try:
            output_file = self.export.export_all_to_json(tmpfilepath)
            
            self.assertTrue(os.path.exists(output_file))
            
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                self.assertIn('version', data)
                self.assertIn('notes', data)
                self.assertEqual(len(data['notes']), 1)
                self.assertEqual(data['notes'][0]['title'], "Test Note")
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)
    
    def test_export_nonexistent_note(self):
        """Test export nonexistent note"""
        with self.assertRaises(ValueError):
            self.export.export_note_to_markdown(999)
    
    def test_safe_filename(self):
        """Test safe filename generation"""
        safe = self.export._safe_filename("Test/Note:Important")
        self.assertNotIn('/', safe)
        self.assertNotIn(':', safe)
        self.assertLessEqual(len(safe), 50)
    
    def test_escape_yaml(self):
        """Test YAML escaping"""
        escaped = self.export._escape_yaml("Title: Content")
        self.assertTrue(escaped.startswith('"') and escaped.endswith('"'))
        
        escaped = self.export._escape_yaml("Normal Title")
        self.assertEqual(escaped, "Normal Title")


class TestExportServiceWithMultipleNotes(unittest.TestCase):
    """Export Service Tests with Multiple Notes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.export = ExportService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Insert multiple test notes"""
        notes = [
            ("Note 1", "Content 1", json.dumps(["Tag A"])),
            ("Note 2", "Content 2", json.dumps(["Tag B"])),
            ("Note 3", "Content 3", json.dumps(["Tag A", "Tag B"])),
        ]
        
        for title, content, tags in notes:
            self.db.execute("""
                INSERT INTO notes (title, content, tags)
                VALUES (?, ?, ?)
            """, (title, content, tags))
        
        self.db.commit()
    
    def test_export_all_count(self):
        """Test export all notes count"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = self.export.export_all_to_markdown_files(tmpdir)
            self.assertEqual(len(files), 3)
    
    def test_export_all_json_count(self):
        """Test JSON export all notes count"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmpfile:
            tmpfilepath = tmpfile.name
        
        try:
            output_file = self.export.export_all_to_json(tmpfilepath)
            
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(len(data['notes']), 3)
        finally:
            if os.path.exists(tmpfilepath):
                os.unlink(tmpfilepath)


if __name__ == '__main__':
    unittest.main()
