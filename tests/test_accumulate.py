#!/usr/bin/env python3
"""
The 'accumulate' module implements mutable data structures, like Dictionary
and List, but which implement set operations that allow information from
additional dictionaries and lists (whether using the new data types or not),
to be combined with the existing information in a recursive way.

The problem it solves:

For various purposes, usually involving metadata, I'm going to want to
collect information from various sources around a project: YAML files,
INI files, JSON or YAML strings inside Blender documents, query responses
from a central database, and so on. Each will generally have an incomplete
picture of the information I want, and I want the data to be filled in.

Ordinary Python dictionaries and lists do not work well for this.

With the "update" method of standard Python dictionaries, if a key exists in
the new dictionary, its value will always REPLACE the value in the old
dictionary -- even if that value is itself a data structure, such as a
dictionary. There is no recursion into sub-dictionaries. This makes it poor at
combining nested data structures.

With the "extend" method of lists, if two source show the same information,
there will now be two copies with redundant information, and extending it
again will produce additional ones.

The accumulate module therefore provides RecursiveDict, with an update
method that will recurse into sub-dictionaries and combine sequence elements
using an idempotent "ordered-set-union" operation.

It also provides convenient conversions to YAML or JSON serializations of
the data for output to text files or text blocks.
"""

import unittest, os

# This is the most ridiculous work-around, but it seems to be necessary to
# get Python 3 to import the modules for testing 
import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import accumulate

class AccumulationTests(unittest.TestCase):
    """
    Test combination operations give correct results.
    """
    
    def setUp(self):
        # AFAIK, I don't need any setup
        # I'm only putting this in in case I need to add something to it.
        pass
    
    def tearDown(self):
        # AFAIK, I don't need any teardown
        pass
    
    def test_union_list_union(self):
        # I start out with a UnionList containing a simple list:
        A = accumulate.UnionList([1,2,3])
        
        # I then union it with a new list with some shared and some
        # new elements:
        C = A.union([3,4,5])
        
        # The new list should have the original elements plus the
        # the new elements that don't repeat existing elements:
        self.assertEqual(C, [1,2,3,4,5])
            
    def test_subdictionary_updates_instead_of_being_replaced(self):
        # I start out with a dictionary that contains a subdictionary
        # with some data, under key 'A':
        first = {'A': {'a':1}}
        
        # And another dictionary that has the same subdictionary, with
        # different information:
        second = {'A': {'b':2}}
        
        # I convert first to a RecursiveDict
        first_recursive = accumulate.RecursiveDict(first)
        
        # Then I update it with the second dictionary (it shouldn't
        # matter that it isn't a recursive dictionary)
        first_recursive.update(second)
        
        # The subdictionary should contain the new value:
        self.assertEqual(first_recursive['A']['b'], 2)
        
        # And it should still contain the old value:
        self.assertEqual(first_recursive['A']['a'], 1)
        
        
    def test_sublist_updates_as_an_ordered_set_union(self):
        # I start with a dictionary that contains a sublist under a key:
        first = {'L':[1,2,3,4]}
        
        # And a second dictionary with a different sublist under the
        # same key:
        second = {'L':[5,4,3,6]}
        
        # I convert first to a recursive dict:
        first_recursive = accumulate.RecursiveDict(first)
        
        # Then I update it with the second dictionary:
        first_recursive.update(second)
        
        # The resulting list should combine, but only with
        # the unique new elements:
        self.assertEqual(first_recursive['L'], [1,2,3,4,5,6])
        
        # Then I update it again:
        first_recursive.update(second)
        
        # This shouldn't make any difference!
        self.assertEqual(first_recursive['L'], [1,2,3,4,5,6])
        
    
class CollectYaml(unittest.TestCase):
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')
    
    TESTPATH_EMBEDDED_PROJ = os.path.join(TESTDATA, 'myproject/')
    
    def test_collect_yaml_files_w_abx_rules(self):
        files = accumulate.collect_yaml_files(self.TESTPATH, 'abx',
            root = os.path.join(self.TESTDATA, 'myproject'))
        
        self.assertEqual([os.path.abspath(f) for f in files],  
            [os.path.join(self.TESTDATA, 'myproject/abx.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/abx.yaml')])
        
    
    def test_collect_yaml_files_w_kitcat_rules(self):
        files = accumulate.collect_yaml_files(self.TESTPATH,
            ('kitcat', 'project'), dirmatch=True, sidecar=True,
            root = os.path.join(self.TESTDATA, 'myproject'))
        
        self.assertEqual([os.path.join(self.TESTDATA, f) for f in files],
            [os.path.join(self.TESTDATA, 'myproject/myproject.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/Episodes.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/A.001-Pilot.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/Seq/LP-LastPoint/' +
                             'LP-LastPoint.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/Seq/LP-LastPoint/' +
                             'A.001-LP-1-BeginningOfEnd-anim.yaml')
             ])
        
    def test_detecting_project_root(self):               
        self.assertFalse(accumulate.has_project_root(
            os.path.join(self.TESTDATA, 'kitcat.yaml')))
        self.assertTrue(accumulate.has_project_root(
            os.path.join(self.TESTDATA, 'myproject/myproject.yaml')))
        self.assertFalse(accumulate.has_project_root(
            os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/A.001-Pilot.yaml')))
        
    def test_trim_to_project_root(self):        
        trimmed = accumulate.trim_to_project_root(
            [os.path.join(self.TESTDATA, 'kitcat.yaml'),
             os.path.join(self.TESTDATA, 'myproject/myproject.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/A.001-Pilot.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/Seq/' +
                             'LP-LastPoint/A.001-LP-1-BeginningOfEnd-anim.yaml')]            
            )
        
        self.assertEqual([os.path.abspath(f) for f in trimmed],
            [os.path.join(self.TESTDATA, 'myproject/myproject.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/A.001-Pilot.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/Seq/' +
                             'LP-LastPoint/A.001-LP-1-BeginningOfEnd-anim.yaml')])
    
    def test_trim_to_project_under_project(self):
        trimmed = accumulate.trim_to_project_root(
            [os.path.join(self.TESTDATA, 'kitcat.yaml'),
             os.path.join(self.TESTDATA, 'myproject/myproject.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.002-Second/kitcat.yaml')])            
        
        self.assertEqual([os.path.abspath(f) for f in trimmed],
            [os.path.join(self.TESTDATA, 'myproject/Episodes/A.002-Second/kitcat.yaml')])
        
    def test_finding_project_root_dir_from_kitcat_files(self):
        rootdir = accumulate.get_project_root(
            accumulate.collect_yaml_files(
                os.path.abspath(self.TESTPATH),
                ('kitcat', 'project'), dirmatch=True, sidecar=True))

        self.assertEqual(os.path.abspath(rootdir),
                    os.path.join(self.TESTDATA, 'myproject'))
        
    def test_finding_abx_files_from_kitcat_root(self):
        rootdir = accumulate.get_project_root(
            accumulate.collect_yaml_files(
                os.path.abspath(self.TESTPATH),
                ('kitcat', 'project'), dirmatch=True, sidecar=True))
        
        abx_files = accumulate.collect_yaml_files(
                os.path.abspath(self.TESTPATH),
                'abx', root=rootdir)
        
        self.assertEqual([os.path.abspath(f) for f in abx_files],
            [os.path.join(self.TESTDATA, 'myproject/abx.yaml'),
             os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/abx.yaml')])
        
    def test_combining_abx_yaml_files(self):
        abx_files = [
            os.path.join(self.TESTDATA, 'myproject/abx.yaml'),
            os.path.join(self.TESTDATA, 'myproject/Episodes/A.001-Pilot/abx.yaml')]
        
        testdata = accumulate.combine_yaml(abx_files)
        
        self.assertEqual(testdata['testscalar'], 'loweryaml')
        self.assertEqual(
            list(testdata['testdict']['A']),
            ['item1', 'item2', 'item3', 'item4'])
        
    def test_collecting_yaml_from_empty_dir(self):
        files = accumulate.collect_yaml_files(
            os.path.join(self.TESTDATA, 'empty/'),
            'spam', root = self.TESTDATA)
        
        self.assertEqual(list(files), [])
        
    def test_collecting_yaml_from_nonexistent_file(self):
        files = accumulate.collect_yaml_files(
            os.path.join(self.TESTDATA, 'empty/no_such_file.txt'),
            'spam', root = self.TESTDATA)

        self.assertEqual(list(files), [])
    
    def test_combining_yamls_from_empty_list(self):
        data = accumulate.combine_yaml([])
        
        self.assertEqual(dict(data), {})
        
    def test_getting_project_data_from_path(self):
        root, kitcat_data, abx_data = accumulate.get_project_data(self.TESTPATH)
        
        self.assertEqual(
            os.path.abspath(root),
            os.path.join(self.TESTDATA, 'myproject'))
        
        self.assertEqual(kitcat_data['project_unit'][0]['code'], 'myproject')
        
        self.assertEqual(abx_data['testdict']['A'],
            ['item1', 'item2', 'item3', 'item4'])
        
        
        
