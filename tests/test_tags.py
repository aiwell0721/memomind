"""MemoMind Tag Service Tests"""

import unittest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.tag_service import TagService


class TestTagService(unittest.TestCase):
    """Tag Service Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.tags = TagService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Insert test data"""
        # Create test notes
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Note 1", "Content 1", json.dumps(["tag1"])))
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Note 2", "Content 2", json.dumps(["tag2"])))
        self.db.commit()
        
        self.note1_id = 1
        self.note2_id = 2
    
    def test_create_tag(self):
        """Test create tag"""
        tag_id = self.tags.create_tag("Test Tag")
        
        tag = self.tags.get_tag(tag_id)
        self.assertIsNotNone(tag)
        self.assertEqual(tag.name, "Test Tag")
        self.assertIsNone(tag.parent_id)
    
    def test_create_tag_with_parent(self):
        """Test create tag with parent"""
        parent_id = self.tags.create_tag("Parent")
        child_id = self.tags.create_tag("Child", parent_id)
        
        child = self.tags.get_tag(child_id)
        self.assertEqual(child.parent_id, parent_id)
    
    def test_get_or_create_tag(self):
        """Test get or create tag"""
        # First call creates
        tag_id1 = self.tags.get_or_create_tag("New Tag")
        
        # Second call gets existing
        tag_id2 = self.tags.get_or_create_tag("New Tag")
        
        self.assertEqual(tag_id1, tag_id2)
    
    def test_update_tag(self):
        """Test update tag"""
        tag_id = self.tags.create_tag("Old Name")
        
        # Update name
        success = self.tags.update_tag(tag_id, name="New Name")
        self.assertTrue(success)
        
        tag = self.tags.get_tag(tag_id)
        self.assertEqual(tag.name, "New Name")
    
    def test_delete_tag(self):
        """Test delete tag"""
        tag_id = self.tags.create_tag("To Delete")
        
        success = self.tags.delete_tag(tag_id)
        self.assertTrue(success)
        
        tag = self.tags.get_tag(tag_id)
        self.assertIsNone(tag)
    
    def test_get_all_tags(self):
        """Test get all tags"""
        self.tags.create_tag("Tag A")
        self.tags.create_tag("Tag B")
        
        all_tags = self.tags.get_all_tags()
        
        self.assertGreaterEqual(len(all_tags), 2)
        names = [t.name for t in all_tags]
        self.assertIn("Tag A", names)
        self.assertIn("Tag B", names)
    
    def test_get_tag_tree(self):
        """Test get tag tree"""
        root_id = self.tags.create_tag("Root")
        child1_id = self.tags.create_tag("Child 1", root_id)
        child2_id = self.tags.create_tag("Child 2", root_id)
        grandchild_id = self.tags.create_tag("Grandchild", child1_id)
        
        tree = self.tags.get_tag_tree()
        
        # Should have one root
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]['name'], "Root")
        
        # Root should have 2 children
        self.assertEqual(len(tree[0]['children']), 2)
        
        # Child 1 should have 1 child
        child1 = [c for c in tree[0]['children'] if c['name'] == "Child 1"][0]
        self.assertEqual(len(child1['children']), 1)
    
    def test_set_tag_alias(self):
        """Test set tag alias"""
        main_id = self.tags.create_tag("Main Tag")
        alias_id = self.tags.set_tag_alias(main_id, "Alias Tag")
        
        alias = self.tags.get_tag(alias_id)
        self.assertEqual(alias.alias_for, main_id)
    
    def test_resolve_alias(self):
        """Test resolve alias"""
        main_id = self.tags.create_tag("Main Tag")
        self.tags.set_tag_alias(main_id, "Alias Tag")
        
        # Resolve alias
        resolved = self.tags.resolve_alias("Alias Tag")
        
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.id, main_id)
        self.assertEqual(resolved.name, "Main Tag")
    
    def test_merge_tags(self):
        """Test merge tags"""
        # Create tags and associate with notes
        tag1_id = self.tags.create_tag("Tag 1")
        tag2_id = self.tags.create_tag("Tag 2")
        target_id = self.tags.create_tag("Target")
        
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note1_id, tag1_id))
        
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note2_id, tag2_id))
        
        self.db.commit()
        
        # Merge tag1 and tag2 into target
        merged = self.tags.merge_tags([tag1_id, tag2_id], target_id)
        
        self.assertEqual(merged, 2)
        
        # Target should now have 2 notes
        target_tags = self.tags.get_note_tags(self.note1_id)
        target_tag_names = [t.name for t in target_tags]
        self.assertIn("Target", target_tag_names)
    
    def test_get_popular_tags(self):
        """Test get popular tags"""
        tag1_id = self.tags.create_tag("Popular")
        tag2_id = self.tags.create_tag("Less Popular")
        
        # Associate tag1 with 2 notes
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note1_id, tag1_id))
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note2_id, tag1_id))
        
        # Associate tag2 with 1 note
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note1_id, tag2_id))
        
        self.db.commit()
        
        popular = self.tags.get_popular_tags(limit=2)
        
        self.assertEqual(len(popular), 2)
        self.assertEqual(popular[0].name, "Popular")
        self.assertEqual(popular[0].note_count, 2)
    
    def test_get_unused_tags(self):
        """Test get unused tags"""
        used_id = self.tags.create_tag("Used")
        unused_id = self.tags.create_tag("Unused")
        
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note1_id, used_id))
        self.db.commit()
        
        unused = self.tags.get_unused_tags()
        
        unused_names = [t.name for t in unused]
        self.assertIn("Unused", unused_names)
        self.assertNotIn("Used", unused_names)
    
    def test_suggest_tags(self):
        """Test tag suggestion"""
        self.tags.create_tag("Python")
        self.tags.create_tag("JavaScript")
        self.tags.create_tag("PyTorch")
        
        suggestions = self.tags.suggest_tags("Py", limit=10)
        
        self.assertEqual(len(suggestions), 2)
        names = [t.name for t in suggestions]
        self.assertIn("Python", names)
        self.assertIn("PyTorch", names)
    
    def test_tag_note(self):
        """Test tag note"""
        tag_ids = self.tags.tag_note(self.note1_id, ["Test Tag", "Another Tag"])
        
        self.assertEqual(len(tag_ids), 2)
        
        note_tags = self.tags.get_note_tags(self.note1_id)
        self.assertEqual(len(note_tags), 2)
    
    def test_tag_note_with_alias(self):
        """Test tag note with alias"""
        main_id = self.tags.create_tag("Main")
        self.tags.set_tag_alias(main_id, "Alias")
        
        # Use alias to tag
        self.tags.tag_note(self.note1_id, ["Alias"])
        
        # Should resolve to main tag
        note_tags = self.tags.get_note_tags(self.note1_id)
        self.assertEqual(len(note_tags), 1)
        self.assertEqual(note_tags[0].name, "Main")
    
    def test_remove_note_tag(self):
        """Test remove note tag"""
        tag_id = self.tags.create_tag("To Remove")
        
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
        """, (self.note1_id, tag_id))
        self.db.commit()
        
        success = self.tags.remove_note_tag(self.note1_id, tag_id)
        
        self.assertTrue(success)
        
        note_tags = self.tags.get_note_tags(self.note1_id)
        tag_ids = [t.id for t in note_tags]
        self.assertNotIn(tag_id, tag_ids)
    
    def test_get_note_tags(self):
        """Test get note tags"""
        tag1_id = self.tags.create_tag("Tag 1")
        tag2_id = self.tags.create_tag("Tag 2")
        
        self.db.execute("""
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?), (?, ?)
        """, (self.note1_id, tag1_id, self.note1_id, tag2_id))
        self.db.commit()
        
        note_tags = self.tags.get_note_tags(self.note1_id)
        
        self.assertEqual(len(note_tags), 2)
        names = [t.name for t in note_tags]
        self.assertIn("Tag 1", names)
        self.assertIn("Tag 2", names)


class TestTagServiceWithHierarchy(unittest.TestCase):
    """Tag Service Hierarchy Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.tags = TagService(self.db)
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def test_deep_hierarchy(self):
        """Test deep tag hierarchy"""
        # Create: Tech > Programming > Python > Frameworks > Django
        tech_id = self.tags.create_tag("Tech")
        prog_id = self.tags.create_tag("Programming", tech_id)
        python_id = self.tags.create_tag("Python", prog_id)
        frameworks_id = self.tags.create_tag("Frameworks", python_id)
        django_id = self.tags.create_tag("Django", frameworks_id)
        
        tree = self.tags.get_tag_tree()
        
        # Navigate tree
        tech_node = tree[0]
        self.assertEqual(tech_node['name'], "Tech")
        
        prog_node = tech_node['children'][0]
        self.assertEqual(prog_node['name'], "Programming")
        
        python_node = prog_node['children'][0]
        self.assertEqual(python_node['name'], "Python")
        
        frameworks_node = python_node['children'][0]
        self.assertEqual(frameworks_node['name'], "Frameworks")
        
        django_node = frameworks_node['children'][0]
        self.assertEqual(django_node['name'], "Django")
    
    def test_move_tag_to_different_parent(self):
        """Test move tag to different parent"""
        old_parent = self.tags.create_tag("Old Parent")
        new_parent = self.tags.create_tag("New Parent")
        child = self.tags.create_tag("Child", old_parent)
        
        # Move child
        success = self.tags.update_tag(child, parent_id=new_parent)
        
        self.assertTrue(success)
        
        tree = self.tags.get_tag_tree(new_parent)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]['name'], "Child")


if __name__ == '__main__':
    unittest.main()
