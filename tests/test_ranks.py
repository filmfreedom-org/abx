# test_ranks
"""
Test the ranks module, which implements the branch and rank semantics and math.
"""
import unittest, os

import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import ranks

class BranchTests(unittest.TestCase):
    def test_trunk_branch(self):
        t = ranks.trunk.rank('')
        f = ranks.trunk.rank('file')
        s = ranks.trunk.rank('scene')
        self.assertEqual(repr(ranks.trunk), "<branch 'trunk': file, scene>")
        self.assertIn(t, ranks.trunk)
        self.assertIn(f, ranks.trunk)
        self.assertIn(s, ranks.trunk)
        
    
    def test_defining_branch(self):
        b = ranks.Branch(ranks.trunk, 'myproject', 1,
            ('project', 'series', 'episode', 'sequence',
             'block', 'shot', 'element'))
        
        self.assertEqual(len(b._ranks), 8)

class RanksTests(unittest.TestCase):
    def setUp(self):
        self.b = ranks.Branch(ranks.trunk, 'myproject', 1,
            ('project', 'series', 'episode', 'sequence',
             'block', 'shot', 'element'))
        
    def test_rank_knows_branch(self):
        sh = self.b.rank('shot')
        self.assertIs(sh.branch, self.b)
        self.assertEqual(sh.num, 6)
        
    def test_rank_representation(self):
        ep = self.b.rank('episode')
        self.assertEqual(repr(ep), '<myproject:3-episode>')
        self.assertEqual(int(ep), 3)
        self.assertEqual(str(ep), 'episode')
        
        sq = self.b.rank(4)
        self.assertEqual(repr(sq), '<myproject:4-sequence>')
        self.assertEqual(int(sq), 4)
        self.assertEqual(str(sq), 'sequence')
        
    def test_rank_addition(self):
        ep = self.b.rank('episode')
        sq = self.b.rank(4)
        
        self.assertEqual(sq, ep + 1)
        self.assertEqual(sq, 1 + ep)
        
    def test_rank_subtraction(self):
        ep = self.b.rank('episode')
        sq = self.b.rank(4)
        
        self.assertEqual(ep, sq - 1)
        self.assertEqual(sq, ep - (-1))
        self.assertEqual(sq - ep, 1)
        self.assertEqual(ep - sq, -1)
        
    def test_rank_increment_decrement(self):
        ep = self.b.rank('episode')
        sq = self.b.rank(4)
        
        r = ep
        r += 1
        self.assertEqual(r, sq)
        
        r = sq
        r -= 1
        self.assertEqual(r, ep)
        
    def test_rank_comparisons_direct(self):
        sh = self.b.rank('shot')
        se = self.b.rank('series')
        s1 = self.b.rank(2)
        
        self.assertEqual(se, s1)
        self.assertGreater(sh, se)
        self.assertLess(se, sh)
    
    def test_rank_comparisons_compound(self):
        sh = self.b.rank('shot')
        se = self.b.rank('series')
        s1 = self.b.rank(2)
        
        self.assertNotEqual(sh, se)
        self.assertGreaterEqual(sh, se)
        self.assertLessEqual(se, sh)
        self.assertLessEqual(s1, se)
        self.assertGreaterEqual(se, s1)
    
    def test_rank_too_high(self):
        sh = self.b.rank('shot')
        el = self.b.rank('element')
        
        r = sh + 1
        s = sh + 2
        t = sh + 3
        
        self.assertEqual(r, el)
        self.assertEqual(s, None)
        self.assertEqual(t, None)
        
    def test_rank_too_low(self):
        se = self.b.rank('series')
        pr = self.b.rank('project')
        
        r = se - 1  # Normal - 'project' is one below 'series'
        s = se - 2  # ? Should this be 'project' or 'trunk'/None?
        t = se - 3  #      "`            "
        
        self.assertEqual(r, pr)
        self.assertEqual(s, ranks.trunk)
        self.assertEqual(t, ranks.trunk)
        
    
    def test_rank_slices_from_branch(self):
        ranks = self.b.ranks
        self.assertEqual(
            ranks[1:4],
            ranks[self.b.rank('project'):self.b.rank('sequence')])

        self.assertEqual(
            ranks[:],
            ranks)
        
    def test_ranklist_slice_access(self):
        ranks = self.b.ranks
        
        self.assertEqual(
            ranks[1:4],
            ranks['project':'sequence'])
        
        self.assertEqual(
            ranks[:'sequence'],
            ranks[0:4])
        
        self.assertEqual(
            ranks[1:'shot'],
            ranks['project':6])
        
        self.assertEqual(
            ranks[self.b.ranks['sequence']:7],
            ranks['sequence':7])
        
        self.assertEqual(
            ranks.branch,
            self.b)

    