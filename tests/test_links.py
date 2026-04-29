"""MemoMind Link Service Tests"""

import unittest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.link_service import LinkService


class TestLinkService(unittest.TestCase):
    """Link Service Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.links = LinkService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Insert test data"""
        # Create test notes
        notes = [
            ("Note A", "This is note A with [[Note B]] link."),
            ("Note B", "This is note B with [[Note C|Note C Alias]] link."),
            ("Note C", "This is note C with no links."),
            ("Note D", "This is orphan note D."),
        ]
        
        for title, content in notes:
            self.db.execute("""
                INSERT INTO notes (title, content, tags)
                VALUES (?, ?, ?)
            """, (title, content, json.dumps([])))
        
        self.db.commit()
        
        # Update links
        self.links.update_note_links(1, notes[0][1])  # Note A
        self.links.update_note_links(2, notes[1][1])  # Note B
        self.links.update_note_links(3, notes[2][1])  # Note C
    
    def test_extract_links(self):
        """Test extract wiki links from content"""
        content = "This is [[Note A]] and [[Note B|Note B Alias]]."
        
        links = self.links.extract_links(content)
        
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], ("Note A", None))
        self.assertEqual(links[1], ("Note B", "Note B Alias"))
    
    def test_extract_links_no_alias(self):
        """Test extract links without alias"""
        content = "Link to [[Target Note]]."
        
        links = self.links.extract_links(content)
        
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0], ("Target Note", None))
    
    def test_extract_links_empty(self):
        """Test extract links from empty content"""
        links = self.links.extract_links("")
        self.assertEqual(len(links), 0)
        
        links = self.links.extract_links("No links here.")
        self.assertEqual(len(links), 0)
    
    def test_update_note_links(self):
        """Test update note links"""
        content = "Links to [[Note B]] and [[Note C]]."
        
        count = self.links.update_note_links(1, content)
        
        self.assertEqual(count, 2)
        
        # Verify links
        outgoing = self.links.get_outgoing_links(1)
        self.assertEqual(len(outgoing), 2)
    
    def test_get_outgoing_links(self):
        """Test get outgoing links"""
        outgoing = self.links.get_outgoing_links(1)  # Note A
        
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0].target_title, "Note B")
    
    def test_get_incoming_links(self):
        """Test get incoming links (backlinks)"""
        incoming = self.links.get_incoming_links(2)  # Note B
        
        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming[0].source_title, "Note A")
    
    def test_get_all_links(self):
        """Test get all links"""
        all_links = self.links.get_all_links(2)  # Note B
        
        self.assertIn('outgoing', all_links)
        self.assertIn('incoming', all_links)
        self.assertEqual(len(all_links['outgoing']), 1)  # Links to C
        self.assertEqual(len(all_links['incoming']), 1)  # Linked by A
    
    def test_get_link_count(self):
        """Test get link count"""
        count = self.links.get_link_count(2)  # Note B
        
        self.assertEqual(count['outgoing'], 1)
        self.assertEqual(count['incoming'], 1)
        self.assertEqual(count['total'], 2)
    
    def test_get_orphaned_notes(self):
        """Test get orphaned notes"""
        orphans = self.links.get_orphaned_notes()
        
        # Note D should be orphaned
        orphan_titles = [n['title'] for n in orphans]
        self.assertIn("Note D", orphan_titles)
        
        # Note A, B, C should not be orphaned
        self.assertNotIn("Note A", orphan_titles)
        self.assertNotIn("Note B", orphan_titles)
        self.assertNotIn("Note C", orphan_titles)
    
    def test_get_broken_links(self):
        """Test get broken links"""
        import json
        # Add a note with broken link
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Note E", "Links to [[NonExistent Note]].", json.dumps([])))
        self.db.commit()
        
        broken = self.links.get_broken_links()
        
        # Should find the broken link
        broken_titles = [b['target_title'] for b in broken]
        self.assertIn("NonExistent Note", broken_titles)
    
    def test_get_link_graph(self):
        """Test get link graph data"""
        graph = self.links.get_link_graph()
        
        self.assertIn('nodes', graph)
        self.assertIn('links', graph)
        
        # Should have nodes for A, B, C (linked notes)
        node_titles = [n['title'] for n in graph['nodes']]
        self.assertIn("Note A", node_titles)
        self.assertIn("Note B", node_titles)
        self.assertIn("Note C", node_titles)
        
        # Should have links
        self.assertGreater(len(graph['links']), 0)
    
    def test_suggest_links(self):
        """Test link suggestion"""
        suggestions = self.links.suggest_links("Note", limit=10)
        
        self.assertGreater(len(suggestions), 0)
        titles = [s['title'] for s in suggestions]
        self.assertIn("Note A", titles)
    
    def test_remove_link(self):
        """Test remove link"""
        # Add a link
        self.links.update_note_links(1, "Links to [[Note B]] and [[Note C]].")
        
        # Remove one link
        success = self.links.remove_link(1, 2)  # Remove A->B
        
        self.assertTrue(success)
        
        # Verify
        outgoing = self.links.get_outgoing_links(1)
        target_titles = [l.target_title for l in outgoing]
        self.assertNotIn("Note B", target_titles)
        self.assertIn("Note C", target_titles)
    
    def test_get_popular_links(self):
        """Test get popular links"""
        import json
        # Add more links to Note C
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Note E", "Links to [[Note C]].", json.dumps([])))
        self.db.execute("""
            INSERT INTO notes (title, content, tags)
            VALUES (?, ?, ?)
        """, ("Note F", "Links to [[Note C]].", json.dumps([])))
        self.db.commit()
        
        self.links.update_note_links(5, "Links to [[Note C]].")
        self.links.update_note_links(6, "Links to [[Note C]].")
        
        popular = self.links.get_popular_links(limit=5)
        
        self.assertGreater(len(popular), 0)
        # Note C should be most popular
        self.assertEqual(popular[0]['title'], "Note C")
        self.assertGreater(popular[0]['link_count'], 1)
    
    def test_no_self_link(self):
        """Test that self-links are not created"""
        content = "This note links to [[Note A]] itself."
        
        count = self.links.update_note_links(1, content)
        
        # Should not create self-link
        self.assertEqual(count, 0)
    
    def test_case_insensitive_link(self):
        """Test case insensitive link matching"""
        content = "Links to [[note b]] (lowercase)."
        
        count = self.links.update_note_links(1, content)
        
        # Should match "Note B" (case insensitive)
        self.assertEqual(count, 1)
        
        outgoing = self.links.get_outgoing_links(1)
        self.assertEqual(outgoing[0].target_title, "Note B")


class TestLinkServiceWithComplexGraph(unittest.TestCase):
    """Link Service Complex Graph Tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = Database(":memory:")
        self.links = LinkService(self.db)
        self._seed_data()
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.db.close()
    
    def _seed_data(self):
        """Create a more complex link graph"""
        import json
        
        # Create a graph: A -> B -> C -> D
        #                 \-> D
        notes = [
            ("Page A", "[[Page B]] and [[Page D]]."),
            ("Page B", "[[Page C]]."),
            ("Page C", "[[Page D]]."),
            ("Page D", "No outgoing links."),
        ]
        
        # First create all notes
        for title, content in notes:
            self.db.execute("""
                INSERT INTO notes (title, content, tags)
                VALUES (?, ?, ?)
            """, (title, content, json.dumps([])))
        
        self.db.commit()
        
        # Then update links (all notes exist now)
        for i, (title, content) in enumerate(notes, 1):
            self.links.update_note_links(i, content)
    
    def test_chain_links(self):
        """Test chain of links"""
        # A links to B and D
        outgoing_a = self.links.get_outgoing_links(1)
        self.assertEqual(len(outgoing_a), 2)
        
        # B links to C
        outgoing_b = self.links.get_outgoing_links(2)
        self.assertEqual(len(outgoing_b), 1)
        self.assertEqual(outgoing_b[0].target_title, "Page C")
        
        # D has no outgoing links
        outgoing_d = self.links.get_outgoing_links(4)
        self.assertEqual(len(outgoing_d), 0)
    
    def test_multiple_incoming(self):
        """Test multiple incoming links"""
        # D is linked by A and C
        incoming_d = self.links.get_incoming_links(4)
        
        self.assertEqual(len(incoming_d), 2)
        source_titles = [l.source_title for l in incoming_d]
        self.assertIn("Page A", source_titles)
        self.assertIn("Page C", source_titles)
    
    def test_graph_structure(self):
        """Test graph structure"""
        graph = self.links.get_link_graph()
        
        # Should have 4 nodes
        self.assertEqual(len(graph['nodes']), 4)
        
        # Should have 4 links (A->B, A->D, B->C, C->D)
        self.assertEqual(len(graph['links']), 4)


if __name__ == '__main__':
    unittest.main()
