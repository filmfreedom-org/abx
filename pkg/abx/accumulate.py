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

def merge_slices(slices):
    """
    Given a list of slice objects, merge into minimum list of new slices to cover same elements.
    
    The idea is to catch contiguous or overlapping slices and reduce them to a single slice.
    
    Arguments:
        slices (list(slice)):    List of slices to be merged.
    """
    if isinstance(slices, slice):
        slices = [slices]
    slices = list(slices)
    ordered = sorted(slices, key = lambda a: a.start)
    merged = []
    while ordered:
        s = ordered.pop(0)
        while ordered and ordered[0].start <= s.stop:
            r = ordered.pop(0)
            s = slice(s.start, max(s.stop,r.stop))
        merged.append(s)
    return tuple(merged)

def update_slices(old_slices, new):
    if isinstance(old_slices, slice):
        old_slices = [old_slices]
    
    new_slices = []
    for old in old_slices:        
        if (old.start < new.start <= old.stop) and (new.stop >= old.stop):
            # Leading overlap Old:  |-----|
            #                 New:     |-----|
            new_slices.append(slice(old.start, new.start))
        elif  (old.start <= new.stop < old.stop) and (new.start <= old.start):
            # Trailing overlap Old:     |-----|
            #                  New: |-----|
            new_slices.append(slice(new.stop, old.stop))
        elif  (new.start <= old.start) and (new.stop >= old.stop):
            # Contains         Old:   |--|
            #                  New: |------|
            pass
        elif (new.start > old.stop) or (new.stop < old.start):
            # No overlap       Old: |---|
            #                  New:        |---|
            new_slices.append(old)
        elif (old.start < new.start) and (new.stop < old.stop):
            # Split            Old: |-------|
            #                  New:    |--|
            new_slices.append(slice(old.start,new.start))
            new_slices.append(slice(new.stop, old.stop))
            
    if len(new_slices)==1:
        new_slices = new_slices[0]
    elif len(new_slices)==0:
        new_slices = None
    else:
        new_slices = tuple(new_slices)
        
    return new_slices
            
def listable(val):
    """
    Can val be coerced to UnionList?
    """
    return ((isinstance(val, collections.abc.Sequence) or
             isinstance(val, collections.abc.Set))
                and not
            (type(val) in (bytes, str)) )
    
def dictable(val):
    """
    Can val be coerced to RecursiveDict?
    """
    return isinstance(val, collections.abc.Mapping)
        

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
    
    Attributes:
        source:    A dictionary mapping source objects to slice objects
                   according to which union (or original definition) they
                   come from.    
    """
    def __init__(self, data, source=None, override=True):
        self.source = {}
        super().__init__(data)
        
        if hasattr(data, 'source') and not override:
            self.source = data.source.copy()
            if source is not None and None in self.source:
                self.source[source] = self.source[None]
                del self.source[None]
        else:          
            self.source[source] = slice(0,len(self))
            
        # if source is None and hasattr(data, 'source'):
        #     self.source = data.source.copy()
        # else:
        #     self.source[source] = slice(0,len(self))
            
    def __repr__(self):
        return "UnionList(%s)" % super().__repr__()
        
    def __getitem__(self, query):
        if isinstance(query, int) or isinstance(query, slice):
            return super().__getitem__(query)
        elif isinstance(query, tuple):
            result = []
            for element in query:
                result.extend(super().__getitem__(element))
            return result
        elif query in self.source:
            return self[self.source[query]]
        else:
            raise ValueError("No source %s, " % repr(query) +
                             "not a direct int, slice, or tuple of same.") 
        
    def union(self, other, source=None):
        """
        Returns a combination of the current list with unique new options added.
        
        Arguments:
            other (list):   
                The other list from which new options will be taken.
            
            source(hashable):
                A provided object identifying the source of the new
                information (can be any type -- will be stored in
                the 'source' dictionary, along with the slice to
                which it applies).
            
        Returns:
            A list with the original options and any unique new options from the
            other list. This is intentionally asymmetric behave which results
            in the union operation being idempotent, retaining the original order,
            and emulating the set 'union' behavior, except that non-unique entries
            in the original list will be unharmed.
        """
        combined = UnionList(self)
        combined.source = {}
        
        old_len = len(combined)
                
        # This is the actual union operation
        j = old_len
        new_elements = []
        for element in other:
            if element not in self:
                new_elements.append(element)
                    
        combined.extend(new_elements)
        
        combined.source = self.source.copy()
        
        if source is None and hasattr(other, 'source'):
            # Other is a UnionList and may have complex source information
            for j, element in enumerate(new_elements):
                for src in other.source:
                    if src not in self.source:
                        combined.source[src] = []
                    elif isinstance(self.source[src], slice):
                        combined.source[src] = [self.source[src]]
                    elif isinstance(self.source[src], tuple):
                        combined.source[src] = list(self.source[src])
                    if element in other[other.source[src]]:
                        combined.source[src].append(slice(old_len,old_len+j+1))                
                
            for src in combined.source:
                combined.source[src] = merge_slices(combined.source[src])
                if len(combined.source[src]) == 0:
                    del combined.source[src]
                elif len(combined.source[src]) == 1:
                    combined.source[src] = combined.source[src][0]
                    
        else:
            # Source-naive list, only explicitly provided source:
            new_slice = slice(old_len, len(combined))
        
            for src in self.source:
                upd = update_slices(self.source[src], new_slice)
                if upd:
                    combined.source[src] = upd
                
            if source in self.source:
                # If a source is used twice, we have to merge it
                # into the existing slices for that source
                if isinstance(self.source[source], slice):
                    new_slices = (self.source[source], new_slice)
            
                elif isinstance(self.source[source], collections.Sequence):
                    new_slices = self.source[source] + (new_slice,)
            
                new_slices = tuple(merge_slices(new_slices))
            
                if len(new_slices) == 1:
                    combined.source[source] = new_slices[0]
                else:
                    combined.source[source] = tuple(new_slices)
            else:
                combined.source[source] = new_slice
                    
        return combined
    
class RecursiveDict(collections.OrderedDict):
    """
    A dictionary which updates recursively, updating any values which are
    themselves dictionaries when the replacement value is a dictionary, rather
    than replacing them, and treating any values which are themselves lists
    as UnionLists and applying the union operation to combine them
    (when the replacement value is also a list).
    """
    def __init__(self, data=None, source=None, active_source=None):
        self.active_source = active_source
        self.source = {}
        super().__init__()
        if isinstance(data, collections.abc.Mapping):
            self.update(data, source=source)

    def clear(self):
        """
        Clear the dictionary to an empty state.
        """
        for key in self:
            del self[key]
        self.source = {}
            
    def update(self, other, source=None):
        """
        Load information from another dictionary / mapping object.
        
        mapping (dict):
            The dictionary (or any mapping object) from which the update
            is made. It does not matter if the object is a RecursiveDict
            or not, it will result in the same behavior.
            
        Unlike an ordinary dictionary update, this version works recursively.
        
        If a key exists in both this dictionary and the dictionary from
        which the update is being made, and that key is itself a dictionary,
        it will be combined in the same way, rather than simply being
        overwritten at the top level.
        
        If the shared key represents a list in both dictionaries, then it
        will be combined using the list's union operation.
        
        This behavior allows multiple, deeply-nested dictionary objects to
        be overlaid one on top of the other in a idempotent way, without
        clobbering most content.
        
        There are issues that can happen if a dictionary value is replaced
        with a list or a scalar in the update source.
        """
        if source is None and hasattr(other, 'source'):
            def get_source(key):
                return other.source[key]
        else:
            def get_source(key):
                return source
            
        for key in other:
            if key in self:
                old = self[key]
                new = other[key]
                
                if dictable(old) and dictable(new):   
                    old.update(RecursiveDict(new), source=get_source(key))
                    
                elif listable(old) and listable(new):
                    self.__setitem__(key, old.union(new), source=self.source[key])
                    #self.__setitem__(key, old.union(UnionList(new)),
                    #                    source=self.source[key])

                    # self.__setitem__(key, old.union(UnionList(new), 
                    #                     source=get_source(key)),
                    #                     source=self.source[key])                
                else: # scalar
                    self.__setitem__(key, other[key], source=get_source(key))
                    
            else: # new key
                self.__setitem__(key, other[key], source=get_source(key))
                
    def copy(self):
        copy = RecursiveDict()
        for key in self:
            copy[key] = self[key]
        for key in self.source:
            copy.source[key] = self.source[key]
        return copy
                
    def get_data(self):
        """
        Returns the contents stripped down to an ordinary Python dictionary.
        """
        new = {}
        for key in self:
            if isinstance(self[key], RecursiveDict):
                new[key]=dict(self[key].get_data())
            elif isinstance(self[key], UnionList):
                new[key]=list(self[key])
            else:
                new[key]=self[key]
        return new
    
    def __setitem__(self, key, value, source=None):
        if not source:
            source = self.active_source
            
        self.source[key] = source
            
        if dictable(value):
            super().__setitem__(key, RecursiveDict(value, source=source))
        elif listable(value):
            super().__setitem__(key, UnionList(value, source=source, override=False))
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
    
    def from_yaml(self, yaml_string, source=None):
        """
        Initialize dictionary from YAML contained in a string.
        """
        self.update(yaml.safe_load(yaml_string), source=source)
        return self
    
    def from_yaml_file(self, path):
        """
        Initialize dictionary from a separate YAML file on disk.
        """
        with open(path, 'rt') as yamlfile:
            self.update(yaml.safe_load(yamlfile), source=path)
        return self
            
    def to_yaml(self):
        """
        Serialize dictionary contents into a YAML string.
        """
        return yaml.dump(self.get_data())
    
    def to_yaml_file(self, path):
        """
        Serialize dictionary contents to a YAML file on disk.
        """
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
    
    Arguments:
        path:      The starting point, typically the antecedent filename.
        stems:     File stem (or sequence of stems) we recognize (in priority order).
        dirmatch:  Also search for stems matching the containing directory name?
        sidecar:   Also search for stems matching the antecedent filename's stem?
        root:      Top level directory to consider (do not search above this).
    
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
    """
    Does the YAML file contain the 'project_root' key?
    
    Arguments:
        yaml_path (str): Filepath to the current YAML file being processed.
        
    Returns:
        Whether or not the file contains the 'project_root' key defining its
        containing folder as the root folder for this project.
    """
    with open(yaml_path, 'rt') as yaml_file:
        data = yaml.safe_load(yaml_file)
    if 'project_root' in data:
        return True
    else:
        return False
    
def trim_to_project_root(yaml_paths):
    """
    Trim the path to the project root location.
    
    Arguments:
        yaml_paths (list[str]): The list of YAML file paths.
        
    Returns:
        Same list, but with any files above the project root removed.
    """
    for i in range(len(yaml_paths)-1,-1,-1):
        if has_project_root(yaml_paths[i]):
            return yaml_paths[i:]
    return yaml_paths

def get_project_root(yaml_paths):
    """
    Get the absolute file system path to the root folder.
    
    Arguments:
        yaml_paths (list[str]): The list of YAML file paths.
        
    Returns:
        The absolute path to the top of the project.
    """
    trimmed = trim_to_project_root(yaml_paths)
    if trimmed:
        return os.path.dirname(trimmed[0])
    else:
        # No project root was found!
        return '/'

def combine_yaml(yaml_paths):
    """
    Merge a list of YAML texts into a single dictionary object.
    
    Arguments:
        yaml_paths (list[str]): The list of YAML file paths to be combined.
        
    Returns:
        A RecursiveDict containing the collected data.
    """
    data = RecursiveDict()
    for path in yaml_paths:
        with open(path, 'rt') as yaml_file:
            data.update(yaml.safe_load(yaml_file), source=path)
    return data
            
def get_project_data(filepath):
    """
    Collect the project data from the file system.
    
    Arguments:
        filepath (str): Path to the file.
        
    Returns:
        Data collected from YAML files going up the
        tree to the project root.
    """
    # First, get the KitCAT data.
    kitcat_paths = collect_yaml_files(filepath,
        ('kitcat', 'project'), dirmatch=True, sidecar=True)
    
    kitcat_data = combine_yaml(trim_to_project_root(kitcat_paths))
    
    kitcat_root = get_project_root(kitcat_paths)
    
    abx_data = combine_yaml([ABX_YAML])['abx']
    
    abx_data.update(combine_yaml(collect_yaml_files(filepath,
        'abx', root=kitcat_root)))
    
    return kitcat_root, kitcat_data, abx_data


    