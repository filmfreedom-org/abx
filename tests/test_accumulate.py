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

import unittest, os, collections

import yaml

# This is the most ridiculous work-around, but it seems to be necessary to
# get Python 3 to import the modules for testing 
import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import accumulate

class SourceTracking_UnionList(unittest.TestCase):
    """
    Test that source-tracking of UnionList elements is working.
    """
       
    def test_merge_slices(self):
        slices = [slice(0,3), slice(2,4), slice(3,5), slice(6,10), 
                  slice(8,9), slice(10,12), slice(14,16)]
        
        self.assertEqual(accumulate.merge_slices(slices),
            (slice(0,5), slice(6,12), slice(14,16)))
        
    def test_update_slices_two_overlaps(self):
        old = [slice(0,3), slice(5,7)]
        new = slice(2,6)
        self.assertEqual(accumulate.update_slices(
                old,   new),
                (slice(0,2), slice(6,7)))
        
    def test_update_slices_single_overlap_leading(self):
        self.assertEqual(accumulate.update_slices(
            slice(0,4),     slice(3,7)),
            slice(0,3))
        
    def test_update_slices_single_overlap_trailing(self):
        self.assertEqual(accumulate.update_slices(
            slice(3,7),     slice(0,4)),
            slice(4,7))
        
    def test_update_slices_contains(self):
        self.assertEqual(accumulate.update_slices(
            slice(2,4),     slice(2,7)),
            None)
    
    def test_update_slices_split(self):
        self.assertEqual(accumulate.update_slices(
            slice(0,8),     slice(3,5)),
            (slice(0,3), slice(5,8)))
        
    
    def test_union_list_def_no_source(self):
        A = accumulate.UnionList([1,2,3])
        
        self.assertEqual(len(A), 3)
        self.assertEqual(A.source[None], slice(0,3))
        
    def test_union_list_def_with_source(self):
        A = accumulate.UnionList([1,2,3], source='MySource')
        
        self.assertEqual(len(A), 3)
        self.assertEqual(A.source['MySource'], slice(0,3))
        self.assertDictEqual(A.source, {'MySource':slice(0,3)})
        
    def test_union_list_union_no_source(self):
        # I start out with a UnionList containing a simple list:
        A = accumulate.UnionList([1,2,3])
        
        # I then union it with a new list with some shared and some
        # new elements:
        C = A.union([3,4,5])
        
        # The new list should have the original elements plus the
        # the new elements that don't repeat existing elements:
        self.assertEqual(C, [1,2,3,4,5])
        
    def test_union_list_union_no_source_to_source(self):
        A = accumulate.UnionList([1,2,3])
        C = A.union([3,4,5], source='New')
        self.assertDictEqual(C.source,
                {None:slice(0,3), 'New':slice(3,5)})
        self.assertListEqual(C[C.source['New']], [4,5])
        
    def test_union_list_union_source_to_source(self):
        A = accumulate.UnionList([1,2,3], source='Old')
        C = A.union([3,4,5], source='New')
        self.assertDictEqual(C.source,
                {'Old':slice(0,3), 'New':slice(3,5)})
        self.assertListEqual(C[C.source['New']], [4,5])
        
    def test_union_list_union_w_union_list(self):
        A = accumulate.UnionList([1,2,3], source='A')
        B = accumulate.UnionList([3,4,5], source='B')
        
        C = A.union(B)
        D = B.union(A)
        
        self.assertListEqual(C, [1,2,3,4,5])
        self.assertDictEqual(C.source,
            {'A':slice(0,3), 'B':slice(3,5)})
        
        self.assertListEqual(D, [3,4,5,1,2])
        self.assertDictEqual(D.source,
            {'B':slice(0,3), 'A':slice(3,5)})    
        
    def test_union_list_union_source_to_source_twice(self):
        A = accumulate.UnionList([1,2,3], source='Original')
        B = A.union([3,4,5], source = 'Old')
        C = B.union([6,4,8], source = 'New')
        self.assertListEqual(C, [1,2,3,4,5,6,8])
        self.assertDictEqual(C.source,
            {'Original':slice(0,3), 'Old':slice(3,5), 'New':slice(5,7)})
        self.assertListEqual(C[C.source['Old']], [4,5])
        
        
    def test_union_list_union_source_to_no_source(self):
        A = accumulate.UnionList([1,2,3], source='Original')
        B = A.union([3,4,5])
        C = B.union([6,4,8])
        self.assertListEqual(C, [1,2,3,4,5,6,8])
        self.assertDictEqual(C.source,
            {'Original':slice(0,3), None:slice(3,7)})
        self.assertListEqual(C[C.source[None]], [4,5,6,8])
        
    def test_union_list_union_noncontiguous_same_source(self):
        A = accumulate.UnionList([1,2,3], source='Original')
        B = A.union([3,4,5], source='A')
        C = B.union([4,6,8], source='B')
        D = C.union([6,12,18], source='A')
        self.assertListEqual(D, [1,2,3,4,5,6,8,12,18])
        self.assertDictEqual(D.source,
            {'Original':slice(0,3), 
             'B':slice(5,7),
             'A':(slice(3,5),slice(7,9)) })
        self.assertListEqual(D[D.source['A']], [4,5,12,18])
        
    def test_union_list_syntax_sweet(self):
        A = accumulate.UnionList([1,2,3], source='Original')
        B = A.union([3,4,5], source='A')
        C = B.union([4,6,8], source='B')
        D = C.union([6,12,18], source='A')
        self.assertListEqual(D['Original'], [1,2,3])
        self.assertListEqual(D['B'], [6,8])
        self.assertListEqual(D['A'], [4,5,12,18])
        
        
    def test_unionlist_sourced_union_wo_source(self):
        L = accumulate.UnionList([1,2,3], source='s1')
        M = accumulate.UnionList([4], source='s2')
        N = L.union(M)       
        self.assertDictEqual(N.source,
            {'s1': slice(0, 3, None), 's2': slice(3, 4, None)})
        
    def test_unionlist_source_union_w_source(self):
        L = accumulate.UnionList([1,2,3], source='s1')
        M = accumulate.UnionList([4], source='s2')
        N = L.union(M, source='s2')      
        self.assertDictEqual(N.source,
            {'s1': slice(0, 3, None), 's2': slice(3, 4, None)})
        
    def test_unionlist_override_source(self):
        L = accumulate.UnionList([1,2,3], source='s1')
        M = accumulate.UnionList(L, source='s2')
        self.assertDictEqual(M.source,
            {'s2':slice(0,3)})
        
    def test_unionlist_default_source(self):
        L = accumulate.UnionList([1,2,3], source='s1')
        M = accumulate.UnionList(L, source='s2', override=False)
        N = accumulate.UnionList([1,2,3], source='s2', override=False)
        self.assertDictEqual(M.source,
            {'s1':slice(0,3)})
        self.assertDictEqual(N.source,
            {'s2':slice(0,3)})
        
        


class SourceTracking_RecursiveDict(unittest.TestCase):
    """
    Test source-tracking of keys in RecursiveDict.
    """
    def test_recursive_dict_def_no_source(self):
        A = accumulate.RecursiveDict({'a':1, 'b':2, 'c':3})
        self.assertEqual(A.source['a'], None)
        self.assertEqual(A.source['b'], None)
        self.assertEqual(A.source['c'], None)
        
    def test_recursive_dict_def_source(self):
        A = accumulate.RecursiveDict({'a':1, 'b':2, 'c':3}, source='Old')
        self.assertEqual(A.source['a'], 'Old')
        self.assertEqual(A.source['b'], 'Old')
        self.assertEqual(A.source['c'], 'Old')
        
    def test_recursive_dict_update_sourced_w_sourced(self):
        A = accumulate.RecursiveDict({'a':1, 'b':2, 'c':3}, source='Old')
        A.update({'d':4, 'e':5}, source='New')
        
        self.assertEqual(A.source['a'], 'Old')
        self.assertEqual(A.source['b'], 'Old')        
        self.assertEqual(A.source['c'], 'Old')
        self.assertEqual(A.source['d'], 'New')   
        self.assertEqual(A.source['e'], 'New')    
        
    def test_copy_recursive_dict(self):
        A = accumulate.RecursiveDict({'a':1, 'b':2, 'c':3}, source='Old')
        B = A.copy()
        B.update({'d':4}, source='New')
        
        self.assertDictEqual(A, {'a':1, 'b':2, 'c':3})
        self.assertEqual(A.source['a'], 'Old')
        self.assertDictEqual(B, {'a':1, 'b':2, 'c':3, 'd':4})
        self.assertEqual(B.source['d'], 'New')
        
    def test_recursive_dict_source_inheritance(self):
        A = accumulate.RecursiveDict({'a':1}, source='A')
        B = accumulate.RecursiveDict({'b':2}, source='B')
        C = accumulate.RecursiveDict({'c':3}, source='C')
        B.update(C)
        A.update(B)        
        
        self.assertEqual(A.source, {'a':'A', 'b':'B', 'c':'C'})
        
    def test_unionlist_in_recursivedict_sourced_union(self):
        Q = accumulate.RecursiveDict({'A':[1,2,3]}, source='s1')
        R = accumulate.RecursiveDict({'A':[4]}, source='s2')
        Q.update(R)
        self.assertDictEqual(Q.source,
            {'A':'s1'})
        self.assertDictEqual(Q['A'].source,
            {'s1': slice(0, 3, None), 's2': slice(3, 4, None)})

    
class AccumulationTests(unittest.TestCase):
    """
    Test combination operations give correct results.
    """
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    MYPROJ_ABX_YAML = os.path.join(TESTDATA, 'myproject/abx.yaml')
    PILOT_ABX_YAML  = os.path.join(TESTDATA, 'myproject/Episodes/A.001-Pilot/abx.yaml')
    
    def setUp(self):
        with open(self.MYPROJ_ABX_YAML, 'rt') as myprog_f:
            self.myproj_abx = yaml.safe_load(myprog_f)
        with open(self.PILOT_ABX_YAML, 'rt') as pilot_f:
            self.pilot_abx = yaml.safe_load(pilot_f)
            
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
        
    
    def test_recursive_dict_load_w_source(self):
        A =accumulate.RecursiveDict(self.myproj_abx, source='myproj', active_source='live')
        
        print("A.get_data() = ", A.get_data())
        print("A.source = ", A.source)
        
        self.assertEqual(sorted(list(A.keys())), ['abx', 'testdict', 'testscalar'])
        
        self.assertEqual(sorted(list(A['testdict'].keys())), ['A', 'B', 'C', 'D'])
        self.assertEqual(sorted(list(A['testdict']['A'])), ['item1', 'item2', 'item3'])
        
        self.assertDictEqual(A.source, 
            {'abx':'myproj', 'testdict':'myproj', 'testscalar':'myproj'})
        
        
        self.assertDictEqual(A['testdict'].source, {
                'A':'myproj', 'B':'myproj', 'C':'myproj', 'D':'myproj'})
        
        self.assertDictEqual(A['testdict']['A'].source, {'myproj':slice(0,3)})
        self.assertDictEqual(A['testdict']['C'].source, {'a':'myproj', 'b':'myproj', 
                                             'c':'myproj', 'd':'myproj'})
        self.assertDictEqual(A['testdict'].get_data(), 
            {'A':['item1', 'item2', 'item3'],
             'B':1,
             'C':{'a':1, 'b':1, 'c':2, 'd':3},
             'D':[
                 {'a':1, 'b':2},
                 {'a':2, 'b':3}
                 ]})
        
    
    def test_recursive_dict_load_and_update_w_source(self):
        A = accumulate.RecursiveDict(self.myproj_abx, source='myproj', active_source='live')
        B = accumulate.RecursiveDict(self.pilot_abx, source='pilot')
        
        A.update(B)
        
        self.assertEqual(sorted(list(A.keys())), ['abx', 'testdict', 'testscalar'])
        
        self.assertEqual(sorted(list(A['testdict'].keys())), ['A', 'B', 'C', 'D'])
        self.assertEqual(sorted(list(A['testdict']['A'])), ['item1', 'item2', 'item3', 'item4'])
        
        self.assertDictEqual(A.source, 
            {'abx':'myproj', 'testdict':'myproj', 'testscalar':'pilot'})
        
        self.assertDictEqual(A['testdict'].source, {
            'A':'myproj', 'B':'pilot', 'C':'myproj', 'D':'myproj'})
                
        self.assertDictEqual(A['testdict']['A'].source, 
            {'myproj':slice(0,3), 'pilot':slice(3,4)}) 
        
        
         
        
    def test_recursive_dict_update_w_source(self):
        A = accumulate.RecursiveDict({'a':1}, source='A')
        B = accumulate.RecursiveDict({'b':2}, source='B')
        C = accumulate.RecursiveDict({'c':3}, source='C')
        B.update(C)
        A.update(B)
        self.assertDictEqual(A.get_data(), {'a':1, 'b':2, 'c':3})
        self.assertDictEqual(A.source, {'a':'A', 'b':'B', 'c':'C'})
        
        
    def test_recursive_dict_update_w_source_override_source(self):
        A = accumulate.RecursiveDict({'a':1}, source='A')
        B = accumulate.RecursiveDict({'b':2}, source='B')
        C = accumulate.RecursiveDict({'c':3}, source='C')
        B.update(C, source='D')        
        self.assertDictEqual(B.source, {'b':'B', 'c':'D'})        
        A.update(B, source='E')        
        self.assertDictEqual(A.source, {'a':'A', 'b':'E', 'c':'E'})
        
        
    def test_recursive_dict_and_union_list_correct_instances(self):
        A = accumulate.UnionList([1,2,3])
        B = accumulate.RecursiveDict({'A':'a', 'B':'b'})
        
        self.assertTrue(isinstance(A, collections.abc.MutableSequence))
        self.assertTrue(isinstance(B, collections.abc.Mapping))
        
    
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
        
        print("\ntestdata.get_data() = ", testdata.get_data())
        print("testdata['testdict'].source = ", testdata['testdict'].source)
        
        self.assertEqual(testdata['testscalar'], 'loweryaml')
        self.assertEqual(
            list(testdata['testdict']['A']),
            ['item1', 'item2', 'item3', 'item4'])
        
        self.assertEqual(
            testdata.source['testdict'], abx_files[0])
        self.assertEqual(
            testdata['testdict'].source['A'], abx_files[0])
        
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
        
        
        
