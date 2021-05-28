# accumulate.py
"""
Data structures for accumulating tree-structured data from multiple sources.

Data is acquired from file and directory names and also from yaml files in the
tree. The yaml files are loaded in increasing priority from upper directories
to the local one, starting from the highest level file to contain a "project_root"
key.

The files named for their parent directory are assumed to be KitCAT files (i.e.
"kitcat.yaml" and "<dirname>.yaml" are treated the same way). Only files named
"abx.yaml" are assumed to be configuration files specific to ABX. 

We collect these by going up the file path, and then load them coming down. If
we find a "project_root" key, we ditch the previous data and start over. This way
any project files found above the project root will be ignored.

As a use case: if we were to store a new project inside of another project, the
new project's project_root would make it blind to the settings in the containing
project. Other directories in the parent project would still go to the parent
project's root. This avoids having the location the project is stored affect
the project data.

The overall structure is a dictionary. When updating with new data, any element
that is itself a dictionary is treated recursively (that is, it is updated with
directory data when another dictionary is provided for the same key). If an
element is a list, then data from successively-higher directories extends the
list (see UnionList, below). If a scalar replaces a dictionary or list value in
a more specific entry, then it clobbers it and any updated information in it.

@author:     Terry Hancock

@copyright:  2019 Anansi Spaceworks. 

@license:    GNU General Public License, version 2.0 or later. (Python code)

@contact:    digitante@gmail.com

Demo:

>>> import accumulate
>>> T1 = accumulate.RecursiveDict(accumulate.TEST_DICT_1)
>>> T2 = accumulate.RecursiveDict(accumulate.TEST_DICT_2)
>>> import copy
>>> Ta = copy.deepcopy(T1)
>>> Tb = copy.deepcopy(T2)
>>> Ta
RecursiveDict({'A': 1, 'B': [1, 2, 3], 'C': {'a': 1, 'b': 2, 'c': 3}, 'D': {}, 'E': None, 'F': {'h': {'i': {'j': {'k': 'abcdefghijk'}}}}})
>>> Tb
RecursiveDict({'C': {'d': 4, 'e': 5, 'f': 6}, 'D': (1, 2, 3), 'B': [4, 5, 6], 'E': 0})
>>> Ta.update(T2)
>>> Ta
RecursiveDict({'A': 1, 'B': [4, 5, 6, 1, 2, 3], 'C': {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6}, 'D': (1, 2, 3), 'E': 0, 'F': {'h': {'i': {'j': {'k': 'abcdefghijk'}}}}})
>>> Tb.update(T1)
>>> Tb
RecursiveDict({'C': {'d': 4, 'e': 5, 'f': 6, 'a': 1, 'b': 2, 'c': 3}, 'D': {}, 'B': [1, 2, 3, 4, 5, 6], 'E': None, 'A': 1, 'F': {'h': {'i': {'j': {'k': 'abcdefghijk'}}}}})
>>>

"""

TEST_DICT_1 = { 'A':1,
                'B':[1,2,3],
                'C':{'a':1, 'b':2, 'c':3},
                'D':{},
                'E':None,
                'F':{'h':{'i':{'j':{'k':'abcdefghijk'}}}},
                }

TEST_DICT_2 = { 'C':{'d':4, 'e':5, 'f':6},
                'D':(1,2,3),
                'B':[4,5,6],
                'E':0
                }

YAML_TEST = """
A: 1
B:
    - 4
    - 5
    - 6
    - 1
    - 2
    - 3
C:
    a: 1
    b: 2
    c: 3
    d: 4
    e: 5
    f: 6
D: (1, 2, 3)
E: 0
F:
    h:
        i:
            j:
                k: abcdefghijk
"""

import os, collections.abc, re
import yaml

wordre = re.compile(r'([A-Z]+[a-z]*|[a-z]+|[0-9]+)')

class OrderedSet(collections.abc.Set):
    """
    List-based set from Python documentation example.
    """
    def __init__(self, iterable):
        self.elements = lst = []
        for value in iterable:
            if value not in lst:
                lst.append(value)

    def __iter__(self):
        return iter(self.elements)

    def __contains__(self, value):
        return value in self.elements

    def __len__(self):
        return len(self.elements)
    
    def __repr__(self):
        return repr(list(self))
    
    def union(self, other):
        return self.__or__(other)
    
    def intersection(self, other):
        return self.__and__(other)
    
class UnionList(list):
    """
    Special list-based collection, which implements a "union" operator similar
    to the one defined for sets. It only adds options from the other list
    which are not already in the current list.
    
    Note that it is intentionally asymmetric. The initial list may repeat values
    and they will be kept, so it does not require the list to consist only of
    unique entries (unlike Set collections).
    
    This allows us to use this type for loading list-oriented data from data
    files, which may or may not contain repetitions for different uses, but
    also makes accumulation idempotent (running the union twice will not
    increase the size of the result, because no new values will be found).
    """
    def union(self, other):
        combined = UnionList(self)
        for element in other:
            if element not in self:
                combined.append(element)
        return combined
    
class RecursiveDict(collections.OrderedDict):
    """
    A dictionary which updates recursively, updating any values which are
    themselves dictionaries when the replacement value is a dictionary, rather
    than replacing them, and treating any values which are themselves lists
    as UnionLists and applying the union operation to combine them
    (when the replacement value is also a list).
    """
    def clear(self):
        for key in self:
            del self[key]
            
    def update(self, mapping):
        for key in mapping:
            if key in self:
                if   (isinstance(self[key], collections.abc.Mapping) and
                      isinstance(mapping[key], collections.abc.Mapping)):
                    # Subdictionary
                    newvalue = RecursiveDict(self[key])
                    newvalue.update(RecursiveDict(mapping[key]))
                    self[key] = newvalue
                    
                elif ((isinstance(self[key], collections.abc.MutableSequence) or
                       isinstance(self[key], collections.abc.Set)) and 
                      (isinstance(mapping[key], collections.abc.MutableSequence) or
                       isinstance(mapping[key], collections.abc.Set))):
                    # Sublist
                    self[key] = UnionList(self[key]).union(UnionList(mapping[key]))
                    
                else: # scalar
                    self[key] = mapping[key]
                    
            else: # new key
                self[key] = mapping[key]
                
    def get_data(self):
        new = {}
        for key in self:
            if isinstance(self[key], RecursiveDict):
                new[key]=dict(self[key].get_data())
            elif isinstance(self[key], UnionList):
                new[key]=list(self[key])
            else:
                new[key]=self[key]
        return new
    
    def __setitem__(self, key, value):
        if isinstance(value, collections.abc.Mapping):
            super().__setitem__(key, RecursiveDict(value))
            
        elif isinstance(value, collections.abc.MutableSequence):
            super().__setitem__(key, UnionList(value))
            
        else:
            super().__setitem__(key,value)
            
    def __repr__(self, compact=False):
        s = ''
        if not compact:
            s = s + '%s(' % self.__class__.__name__
        s = s + '{'
        for key in self:
            if isinstance(self[key], RecursiveDict):
                s = s+"'%s'"%key + ': ' + "%s" % self[key].__repr__(compact=True) + ', '
            else:
                s = s+ "'%s'"%key + ': ' + "%s" % repr(self[key]) + ', '
        if s.endswith(', '): s= s[:-2]
        s = s + '}'
        if not compact:
            s = s + ')'
        return s
    
    def from_yaml(self, yaml_string):
        self.update(yaml.safe_load(yaml_string))
        return self
    
    def from_yaml_file(self, path):
        with open(path, 'rt') as yamlfile:
            self.update(yaml.safe_load(yamlfile))
        return self
            
    def to_yaml(self):
        return yaml.dump(self.get_data())
    
    def to_yaml_file(self, path):
        with open(path, 'wt') as yamlfile:
            yamlfile.write(yaml.dump(self.get_data()))


#--------
# Code for collecting the YAML files we need

ABX_YAML = os.path.join(os.path.dirname(
                os.path.abspath(os.path.join(__file__))),
                'abx.yaml')


def collect_yaml_files(path, stems, dirmatch=False, sidecar=False, root='/'):
    """
    Collect a list of file paths to YAML files.
    
    Does not attempt to read or interpret the files.
    
    @path: The starting point, typically the antecedent filename.
    @stems: File stem (or sequence of stems) we recognize (in priority order).
    @dirmatch: Also search for stems matching the containing directory name?
    @sidecar: Also search for stems matching the antecent filename's stem?
    @root: Top level directory to consider (do not search above this).
    
    "Stem" means the name with any extension after "." removed (typically,
    the filetype).
    """
    yaml_paths = []
    if type(stems) is str:
        stems = (stems,)
        
    path = os.path.abspath(path)
    path, filename = os.path.split(path)
    if sidecar:
        filestem = os.path.splitext(filename)[0]
        sidecar_path = os.path.join(path, filestem + '.yaml')
        if os.path.isfile(sidecar_path):
            yaml_paths.append(sidecar_path)
    
    while not os.path.abspath(path) == os.path.dirname(root):     
        path, base = os.path.split(path)
        
        if dirmatch:
            yaml_path = os.path.join(path, base, base + '.yaml')
            if os.path.isfile(yaml_path):
                yaml_paths.append(yaml_path)
        
        for stem in stems:
            yaml_path = os.path.join(path, base, stem + '.yaml')
            if os.path.isfile(yaml_path):
                yaml_paths.append(yaml_path)
        
    yaml_paths.reverse()
    return yaml_paths
        
        
def has_project_root(yaml_path):
    with open(yaml_path, 'rt') as yaml_file:
        data = yaml.safe_load(yaml_file)
    if 'project_root' in data:
        return True
    else:
        return False
    
def trim_to_project_root(yaml_paths):
    for i in range(len(yaml_paths)-1,-1,-1):
        if has_project_root(yaml_paths[i]):
            return yaml_paths[i:]
    return yaml_paths

def get_project_root(yaml_paths):
    trimmed = trim_to_project_root(yaml_paths)
    if trimmed:
        return os.path.dirname(trimmed[0])
    else:
        # No project root was found!
        return '/'

def combine_yaml(yaml_paths):
    data = RecursiveDict()
    for path in yaml_paths:
        with open(path, 'rt') as yaml_file:
            data.update(yaml.safe_load(yaml_file))
    return data
            
def get_project_data(filepath):
    # First, get the KitCAT data.
    kitcat_paths = collect_yaml_files(filepath,
        ('kitcat', 'project'), dirmatch=True, sidecar=True)
    
    kitcat_data = combine_yaml(trim_to_project_root(kitcat_paths))
    
    kitcat_root = get_project_root(kitcat_paths)
    
    abx_data = combine_yaml([ABX_YAML])['abx']
    
    abx_data.update(combine_yaml(collect_yaml_files(filepath,
        'abx', root=kitcat_root)))
    
    return kitcat_root, kitcat_data, abx_data


    