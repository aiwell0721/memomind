"""MemoMind API Tests"""

import unittest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memomind.api import MemoMind


class TestMemoMindAPI(unittest.TestCase):
    """MemoMind API Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.client = MemoMind(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.client.close()
        import os
        os.unlink(self.temp_db.name)
    
    def test_notes_create(self):
        """Test create note"""
        note_id = self.client.notes.create("Test Note", "Test content", tags=["test"])
        
        self.assertGreater(note_id, 0)
    
    def test_notes_get(self):
        """Test get note"""
        note_id = self.client.notes.create("Test Note", "Test content")
        
        note = self.client.notes.get(note_id)
        
        self.assertIsNotNone(note)
        self.assertEqual(note['title'], "Test Note")
    
    def test_notes_update(self):
        """Test update note"""
        note_id = self.client.notes.create("Old Title", "Old content")
        
        success = self.client.notes.update(note_id, title="New Title", content="New content")
        
        self.assertTrue(success)
        
        note = self.client.notes.get(note_id)
        self.assertEqual(note['title'], "New Title")
    
    def test_notes_delete(self):
        """Test delete note"""
        note_id = self.client.notes.create("To Delete", "Content")
        
        success = self.client.notes.delete(note_id)
        
        self.assertTrue(success)
        
        note = self.client.notes.get(note_id)
        self.assertIsNone(note)
    
    def test_notes_search(self):
        """Test search notes"""
        self.client.notes.create("AI Basics", "Artificial intelligence is great", tags=["AI"])
        self.client.notes.create("ML Guide", "Machine learning is subset of AI", tags=["AI", "ML"])
        
        results = self.client.notes.search("intelligence")
        
        self.assertGreater(len(results), 0)
    
    def test_notes_list(self):
        """Test list notes"""
        self.client.notes.create("Note 1", "Content 1")
        self.client.notes.create("Note 2", "Content 2")
        
        notes = self.client.notes.list(limit=10)
        
        self.assertEqual(len(notes), 2)
    
    def test_notes_versions(self):
        """Test note versions"""
        note_id = self.client.notes.create("Versioned Note", "Version 1", tags=["v1"])
        
        # Save versions
        v1 = self.client.versions.save(note_id, "Versioned Note", "Version 1", ["v1"])
        v2 = self.client.versions.save(note_id, "Versioned Note", "Version 2", ["v2"])
        
        # List versions
        versions = self.client.versions.list(note_id)
        self.assertEqual(len(versions), 2)
        
        # Restore
        self.client.versions.restore(v1)
        
        note = self.client.notes.get(note_id)
        self.assertEqual(note['content'], "Version 1")
    
    def test_tags_create(self):
        """Test create tag"""
        tag_id = self.client.tags.create("Test Tag")
        
        self.assertGreater(tag_id, 0)
    
    def test_tags_list(self):
        """Test list tags"""
        self.client.tags.create("Tag A")
        self.client.tags.create("Tag B")
        
        tags = self.client.tags.list()
        
        self.assertGreaterEqual(len(tags), 2)
    
    def test_tags_tree(self):
        """Test tag tree"""
        parent_id = self.client.tags.create("Parent")
        child_id = self.client.tags.create("Child", parent_id)
        
        tree = self.client.tags.get_tree()
        
        self.assertEqual(len(tree), 1)
        self.assertEqual(len(tree[0]['children']), 1)
    
    def test_links_create(self):
        """Test create link"""
        note1_id = self.client.notes.create("Note 1", "Content 1")
        note2_id = self.client.notes.create("Note 2", "Content 2")
        
        success = self.client.links.create(note1_id, note2_id)
        
        self.assertTrue(success)
    
    def test_links_incoming(self):
        """Test incoming links"""
        note1_id = self.client.notes.create("Note 1", "Content 1")
        note2_id = self.client.notes.create("Note 2", "Content 2")
        
        self.client.links.create(note1_id, note2_id)
        
        incoming = self.client.links.get_incoming(note2_id)
        
        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming[0]['source_note_id'], note1_id)
    
    def test_links_outgoing(self):
        """Test outgoing links"""
        note1_id = self.client.notes.create("Note 1", "Content 1")
        note2_id = self.client.notes.create("Note 2", "Content 2")
        
        self.client.links.create(note1_id, note2_id)
        
        outgoing = self.client.links.get_outgoing(note1_id)
        
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0]['target_note_id'], note2_id)
    
    def test_links_graph(self):
        """Test link graph"""
        note1_id = self.client.notes.create("Note 1", "[[Note 2]]")
        note2_id = self.client.notes.create("Note 2", "Content 2")
        
        self.client.links.create(note1_id, note2_id)
        
        graph = self.client.links.get_graph()
        
        self.assertIn('nodes', graph)
        self.assertIn('links', graph)
        self.assertGreater(len(graph['nodes']), 0)
    
    def test_versions_save(self):
        """Test save version"""
        note_id = self.client.notes.create("Note", "Content 1", tags=["v1"])
        
        version_id = self.client.versions.save(note_id, "Note", "Content 1", ["v1"], "Initial version")
        
        self.assertGreater(version_id, 0)
    
    def test_versions_tag(self):
        """Test tag version"""
        note_id = self.client.notes.create("Note", "Content")
        version_id = self.client.versions.save(note_id, "Note", "Content", [])
        
        success = self.client.versions.tag(version_id, "Important")
        
        self.assertTrue(success)
    
    def test_versions_cleanup(self):
        """Test cleanup versions"""
        note_id = self.client.notes.create("Note", "Content")
        
        # Create 15 versions
        for i in range(15):
            self.client.versions.save(note_id, "Note", f"Content {i}", [])
        
        # Cleanup, keep 10
        deleted = self.client.versions.cleanup(note_id, keep_count=10)
        
        self.assertEqual(deleted, 5)
    
    def test_export_markdown(self):
        """Test export to Markdown"""
        self.client.notes.create("Export Test", "Content to export", tags=["export"])
        
        with tempfile.TemporaryDirectory() as tmpdir:
            files = self.client.export.export_all_to_markdown_files(tmpdir)
            
            self.assertEqual(len(files), 1)
    
    def test_export_json(self):
        """Test export to JSON"""
        self.client.notes.create("Export Test", "Content to export")
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            tmpfile = f.name
        
        try:
            output = self.client.export.export_all_to_json(tmpfile)
            
            import os
            self.assertTrue(os.path.exists(output))
        finally:
            import os
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
    
    def test_import_json(self):
        """Test import from JSON"""
        import tempfile
        import json
        
        # Create test JSON
        test_data = {
            'version': '1.0',
            'notes': [
                {
                    'title': 'Imported Note',
                    'content': 'Imported content',
                    'tags': ['imported']
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            tmpfile = f.name
        
        try:
            result = self.client.importer.import_json_file(tmpfile)
            
            self.assertEqual(result.imported, 1)
        finally:
            import os
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
    
    def test_context_manager(self):
        """Test context manager"""
        with MemoMind(db_path=self.temp_db.name) as client:
            note_id = client.notes.create("Context Test", "Content")
            self.assertGreater(note_id, 0)
    
    def test_full_workflow(self):
        """Test full workflow"""
        # Create notes
        note1_id = self.client.notes.create("AI Guide", "AI is transforming the world", tags=["AI", "tech"])
        note2_id = self.client.notes.create("ML Basics", "Machine learning is a subset of AI", tags=["AI", "ML"])
        
        # Create link
        self.client.links.create(note1_id, note2_id)
        
        # Search
        results = self.client.notes.search("AI")
        self.assertGreater(len(results), 0)
        
        # Get backlinks
        incoming = self.client.links.get_incoming(note2_id)
        self.assertEqual(len(incoming), 1)
        
        # Export
        with tempfile.TemporaryDirectory() as tmpdir:
            files = self.client.export.export_all_to_markdown_files(tmpdir, include_versions=False)
            self.assertEqual(len(files), 2)


if __name__ == '__main__':
    unittest.main()
