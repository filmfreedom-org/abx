# file_context.py
"""
Contextual metadata acquired from the file system, file name, directory structure, and
sidecar data files.

Data is acquired from file and directory names and also from yaml files in the tree.
The yaml files are loaded in increasing priority from metadata.yaml, abx.yaml, <dirname>.yaml.
They are also loaded from the top of the tree to the bottom, with the most local Values
overriding the top-level ones.

@author:     Terry Hancock

@copyright:  2019 Anansi Spaceworks. 

@license:    GNU General Public License, version 2.0 or later. (Python code)
             Creative Commons Attribution-ShareAlike, version 3.0 or later. (Website Templates).

@contact:    digitante@gmail.com

"""

import os, re, copy, string, collections
import yaml

DEFAULT_YAML = {}
with open(os.path.join(os.path.dirname(__file__), 'abx.yaml')) as def_yaml_file:
    DEFAULT_YAML.update(yaml.safe_load(def_yaml_file)) 


TESTPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testdata', 'myproject', 'Episodes', 'A.001-Pilot', 'Seq', 'LP-LastPoint', 'A.001-LP-1-BeginningOfEnd-anim.txt'))

from . import accumulate
    
from .accumulate import RecursiveDict
from .enum import Enum
from .ranks import RankNotFound

from abx.parsers import NameParsers


log_level = Enum('DEBUG', 'INFO', 'WARNING', 'ERROR')
        
from .name_schema import FieldSchema

from .name_context import NameContext

#from .render_profile import RenderProfileMap
            
class FileContext(NameContext):
    """
    Collected information about a file's storage location on disk.
    
    Collects name and path information from a filepath, used to identify
    the file's role in a project. In order to do this correctly, the
    FileContext object needs a schema defined for the project, which
    explains how to read and parse project file names, to determine what
    unit, name, or role they might have in the project.
    
    For this, you will need to have a <project>.yaml file which defines
    the 'project_schema' (a list of dictionaries used to initialize a list
    of FieldSchema objects). Examples of <project>.yaml are provided in the
    'myproject.yaml' file in the test data in the source distribution of
    ABX, and you can also see a "live" example in the "Lunatics!" project.
    
    Subclass from NameContext, so please read more information there.
    
    Attributes:
        root (filepath):
            The root directory of the project as an absolute operating system
            filepath. This should be used for finding the root where it is
            currently, not stored for permanent use, as it will be wrong if
            the project is relocated.
            
        render_root (filepath):
            The root directory for rendering. We often have this symlinked to
            a large drive to avoid congestion. Usually just <root>/Renders.
            
        filetype (str):
            Filetype code or extension for this file. Usually identifies what
            sort of file it is and may imply how it is used in some cases.
            
        role (str):
            Explicit definition of file's role in the project, according to
            roles specified in <project>.yaml. For a default, see 'abx.yaml'
            in the ABX source code. Derived from the file name.
            
        title (str):
            Title derived from the filename.
            The relationship between this and the NameContext title is unclear
            at present -- probably we should be setting the NameContext.title
            property from here (?)
            
        comment (str):
            Comment field from the filename. This is a free field generally
            occurring after the role, using a special delimiter and meant to
            be readable by humans. It may indicate an informal backup or
            saved version of the file outside of the VCS, as opposed to
            a main, VCS-tracked copy. Or it may indicate some variant version
            of the file.
            
        name_contexts (list[NameContext]):
            A list of NameContext objects contained in this file, typically
            one-per-scene in a Blender file.
            
        filepath (str):
            O/S and location dependent absolute path to the file.
            
        filename (str):
            Unaltered filename from disk.
            
        file_exists (bool):
            Does the file exist on disk (yet)?
            This may be false if the filename has been determined inside
            the application, but the file has not been written to disk yet.
        
        folder_exists (bool):
            Does the containing folder exist (yet)?
            
        folders (list(str)):
            List of folder names from the project root to the current file,
            forming a relative path from the root to this file.
        
        omit_ranks (dict[str:int]):
            How many ranks are omitted from the beginning of filename
            fields? (Implementation).
            
        provided_data (RecursiveDict):
            The pile of data from project YAML files. This is a special
            dictionary object that does "deep updates" in which sub-dictionaries
            and sub-lists are updated recursively rather than simply being
            replaced at the top level. This allows the provided_data to
            accumulate information as it looks up the project tree to the
            project root. It is not recommended to directly access this data.
            (Implementation)
            
        abx_fields (RecursiveDict):
            A pile of 'abx.yaml' file with directives affecting how ABX should
            behave with this file. This can be used to set custom behavior in
            different project units. For example, we use it to define different
            render profiles for different project units.
        
        notes (list(str)):
            A primitive logging facility. This stores warning and information
            messages about the discovery process to aid the production designer
            in setting up the project correctly.
            NOTE that the clear method does not clear the notes! There is a
            separate clear_notes() method.
            
        parsers (list):
            A list of registered parser implementations for analyzing file
            names. FileContext tries them all, and picks the parser which
            reports the best score -- that is, parser score themselves on
            how likely their parse is to be correct. So if a parser hits a
            problem, it demerits its score, allowing another parser to take
            over.
            
            Currently there are only three parsers provided: a custom one,
            originally written to be specific to "Lunatics!" episodes
            ('abx_episode', now obsolete?), a parser using the project_schema
            system ('abx_schema', now the preferred choice), and a "dumb"
            parser design to fallback on if no schema is provided, which reads
            only the filetype and possible role, title, and comment fields,
            guessing from common usage with no explicit schema
            ('abx_fallback').
    
    This implementation could probably benefit from some more application of
    computer science and artificial intelligence, but I've settled on a
    "good enough" solution and the assumption that production designers would
    probably rather just learn how to use the YAML schemas correctly, than
    to try to second-guess a sloppy AI system.
    
    As of v0.2.6, FileContext does NOT support getting any information
    directly from the operating system path for the file (i.e. by reading
    directory names), although this would seem to be a good idea.
    
    Therefore, project units have to be specified by additional unit-level
    YAML documents (these can be quite small), explicitly setting the
    unit-level information for directories above the current object, and
    by inference from the project schema and the filename (which on "Lunatics!"
    conveys all the necessary information for shot files, but perhaps not
    for library asset files).
    """
    
    # IMMUTABLE DEFAULTS:
    filepath = None
    root = None
    folders = ()
    #ranks = ()
    project_units = ()
    
    filename = None
    
    fields = None
    #subunits = ()
    
    code = '_'
    
#     defaults = {
#         'filetype': None,   'role': None,       'hierarchy': None,  'project': None,
#         'series': None,     'episode': None,    'seq': None,        'block': None,
#         'camera': None,     'shot': None,       'title': None                }
    
    def __init__(self, path=None):
        """
        Collect path context information from a given filepath.
        (Searches the filesystem for context information).
        """
        NameContext.__init__(self, None, {})
        self.clear()
        self.clear_notes()
        if path:
            self.update(path)

    def clear(self):
        """
        Clear the contents of the FileContext object.
        
        Nearly the same as reinitializing, but the notes
        attribute is left alone, to preserve the log history.
        """
        NameContext.clear(self)
                
        # Identity
        self.root = os.path.abspath(os.environ['HOME'])
        self.render_root = os.path.join(self.root, 'Renders')
        self.filetype = ''
        self.role     = ''
        self.title    = ''
        self.comment  = ''    
            
        # Containers
        #self.notes = []
        self.name_contexts = {}
                
        # Status / Settings
        self.filepath = None
        self.filename = None
        self.file_exists = False
        self.folder_exists = False
        self.omit_ranks = {
                'edit': 0,
                'render': 0,
                'filename': 0,
                'scene': 0}
        
        # Defaults
        self.provided_data = RecursiveDict(DEFAULT_YAML, source='default')
        self.abx_fields = DEFAULT_YAML['abx']
        self.render_profiles = {} #RenderProfileMap()
                     
    def clear_notes(self):
        """
        Clear the log history in the notes attribute.
        """
        # We use this for logging, so it doesn't get cleared by the
        # normal clear process.
        self.notes = []
            
    def update(self, path):
        """
        Update the FileContext based on a new file path.
        """
        # Basic File Path Info
        self.filepath = os.path.abspath(path)
        self.filename = os.path.basename(path)
        
        # Does the file path exist?
        if os.path.exists(path):
            self.file_exists = True
            self.folder_exists = True
        else:
            self.file_exists = False
            if os.path.exists(os.path.dirname(path)):
                self.folder_exists = True
            else:
                self.folder_exists = False
            
        #     - Should we create it? / Are we creating it?
        
        # We should add a default YAML file in the ABX software to guarantee
        # necessary fields are in place, and to document the configuration for
        # project developers.

        # Data from YAML Files                 
        #self._collect_yaml_data()
        self.provided_data = RecursiveDict(DEFAULT_YAML, source='default')
        
        kitcat_root, kitcat_data, abx_data = accumulate.get_project_data(self.filepath)
        self.root = kitcat_root
        self.provided_data.update(kitcat_data)
        path = os.path.abspath(os.path.normpath(self.filepath))
        root = os.path.abspath(self.root)
        self.folders = [os.path.basename(self.root)]
        self.folders.extend(os.path.normpath(os.path.relpath(path, root)).split(os.sep)[:-1])
        
        self.abx_fields = abx_data            
        # Did we find the YAML data for the project?
        # Did we find the project root?
        
        self.render_profiles = self.abx_fields['render_profiles']        
        #self.render_profiles = RenderProfileMap(self.abx_fields['render_profiles'])
        
        # TODO: Bug?
        # Note that 'project_schema' might not be correct if overrides are given.
        # As things are, I think it will simply append the overrides, and this
        # may lead to odd results. We'd need to actively compress the list by
        # overwriting according to rank
        #
        try:
            self._load_schemas(self.provided_data['project_schema'])            
            self.namepath_segment = [d['code'] for d in self.provided_data['project_unit']]
            self.code = self.namepath[-1]
        except:
            print("Can't find Name Path. Missing <project>.yaml file?")
            pass
            # print("\n(899) filename = ", self.filename)
            # if 'project_schema' in self.provided_data:
            #     print("(899) project_schema: ", self.provided_data['project_schema'])
            # else:
            #     print("(899) project schema NOT DEFINED")
            #
            # print("(904) self.namepath_segment = ", self.namepath_segment)
                
        
        # Was there a "project_schema" section?
        #    - if not, do we fall back to a default?
        
        # Was there a "project_unit" section?
        #    - if not, can we construct what we need from project_root & folders?
        
        # Is there a definitions section?
        # Do we provide defaults?
        
        try:
            self.render_root = os.path.join(self.root, 
                            self.provided_data['definitions']['render_root'])
        except KeyError:
            self.render_root = os.path.join(self.root, 'Renders') 
        
        self.omit_ranks = {}
        try:
            for key, val in self.provided_data['definitions']['omit_ranks'].items():
                self.omit_ranks[key] = int(val)
        except KeyError:
            self.omit_ranks.update({
                'edit': 0,
                'render': 1,
                'filename': 1,
                'scene': 3})
                           
        # Data from Parsing the File Name
        if ( 'parser' in self.provided_data['definitions'] and
             self.provided_data['definitions']['parser'] in NameParsers):
            # If project has defined what parser it wants (and it is registered),
            # then restrict to that parser:
            parser_selection = [self.provided_data['definitions']['parser']]
        else:
            parser_selection = NameParsers.keys()
            
        if 'parser_options' in self.provided_data['definitions']:
            parser_options = self.provided_data['definitions']['parser_options']
        else:
            parser_options = {}
            
        # TESTING:
        # Previous code locked-in the schema parser, so I'm starting with that:
        parser_selection = ['abx_schema']
            
        self.parsers = [NameParsers[p](
                            schemas = self.schemas,
                            definitions = self.provided_data['definitions'],
                            **parser_options)
                                for p in parser_selection]

            
        parser_chosen, parser_score = self._parse_filename()
        self.log(log_level.INFO, "Parsed with %s, score: %d" % 
                    (parser_chosen, parser_score))
        

        
        # TODO:
        # We don't currently consider the information from the folder names,
        # though we could get some additional information this way


            
    def __repr__(self):
        s = '{0}(data='.format(self.__class__.__name__)
        #s = s + super().__repr__()
        s = s + str(self.code) + '(' + str(self.rank) + ')'
        s = s + ')'
        return s
    
    def log(self, level, msg):
        """
        Log a message to the notes attribute.
        
        This is a simple facility for tracking issues with the production
        source tree layout, schemas, and file contexts.
        """
        if type(level) is str:
            level = log_level.index(level)
        self.notes.append((level, msg))
        
    def get_log_text(self, level=log_level.INFO):
        """
        Returns the notes attribute as a block of text.
        """
        level = log_level.number(level)
        return '\n'.join([
                    ': '.join((log_level.name(note[0]), note[1])) 
                        for note in self.notes
                            if log_level.number(note[0]) >= level])
        
    def _parse_filename(self):
        """
        Try available fuzzy data parsers on the filename, and pick the one
        that returns the best score.
        """
        fields = {}
        best_score = 0.0     
        best_parser_name = None
        for parser in self.parsers:
            score, fielddata = parser(self.filename, self.namepath)
            if score > best_score:
                fields = fielddata
                best_parser_name = parser.name
                best_score = score
        self.fields.update(fields)
        self._pull_up_last_rank_fields()
        return best_parser_name, best_score
    
    def _pull_up_last_rank_fields(self):
        if (    'rank' in self.fields and 
                self.fields['rank'] in self.fields and
                isinstance(self.fields[self.fields['rank']], collections.Mapping) ):
            for key, val in self.fields[self.fields['rank']].items():
                self.fields[key] = val
            
    
#     def _collect_yaml_data(self):

    @property
    def filetype(self):
        """
        Filetype suffix for the file (usually identifies format).
        """
        if 'filetype' in self.fields:
            return self.fields['filetype']
        else:
            return ''
        
    @filetype.setter
    def filetype(self, filetype):
        self.fields['filetype'] = filetype
        
    @property
    def role(self):
        """
        Role field from the filename, or guessed from filetype.
        """
        if 'role' in self.fields:
            return self.fields['role']
        else:
            return ''
        
    @role.setter
    def role(self, role):
        self.fields['role'] = role
        
    @property
    def title(self):
        """
        Title field parsed from the file name.
        """
        if 'title' in self.fields:
            return self.fields['title']
        else:
            return ''
    
    @title.setter
    def title(self, title):
        self.fields['title'] = title
        
    @property
    def comment(self):
        """
        Comment field parsed from the filename.
        
        Meant to be a human-readable extension to the filename, often used to
        represent an informal version, date, or variation on the file.
        """
        if 'comment' in self.fields:        
            return self.fields['comment']
        else:
            return ''
        
    @comment.setter
    def comment(self, comment):
        self.fields['comment'] = comment
        
    @classmethod    
    def deref_implications(cls, values, matchfields):
        """
        NOT USED: Interpret information from reading folder names.
        """
        subvalues = {}
        for key in values:
            # TODO: is it safe to use type tests here instead of duck tests?
            if type(values[key])==int and values[key] < len(matchfields):
                subvalues[key]=matchfields[values[key]]
            elif type(values[key]==dict):
                subvalues[key]=cls.deref_implications(values[key], matchfields)
            elif type(values[key]==list):
                vals = []
                for val in values[key]:
                    vals.append(cls.deref_implications(val, matchfields))
        return subvalues        
    
    def get_path_implications(self, path):
        """
        NOT USED: Extract information from folder names.
        """
        data = {}
        prefix = r'(?:.*/)?'
        suffix = r'(?:/.*)?'
        for implication in self.schema['path_implications']:
            matched = re.compile(prefix + implication['match'] + suffix).match(path)
            if matched and matched.groups:
                data.update(self.deref_implications(implication['values'], matched.groups()))
        return data
    
    def new_name_context(self, rank=None, **kwargs):
        """
        Get a NameContext object representing a portion of this file.
        
        In Blender, generally in a 1:1 relationship with locally-defined
        scenes.
        """
        fields = {}
        fields.update(self.fields)
        
        namepath_segment = []                      
        ranks = [s.rank for s in self.schemas]        
        i_rank = len(self.namepath) 
        if i_rank == 0:
            old_rank = None       
        else:
            old_rank = ranks[i_rank -1]
        
        # The new rank will be the highest rank mentioned, or the
        # explicitly requested rank or
        # one rank past the namepath
        #
        new_rank = self.schemas[i_rank].rank
        
        for schema in self.schemas[i_rank:]:
            if schema.rank in kwargs:
                fields[schema.rank] = {'code':kwargs[schema.rank]}
                new_rank = schema.rank
                namepath_segment.append(kwargs[schema.rank])
            elif rank is not None:
                namepath_segment.append(schema.default)
                if ranks.index(schema.rank) <= ranks.index(rank):
                    new_rank = schema.rank
                    
        if old_rank:
            delta_rank = ranks.index(new_rank) - ranks.index(old_rank)
        else:
            # I think in this case, it's as if the old_rank number is -1?
            delta_rank = ranks.index(new_rank) + 1
                
        # Truncate to the new rank:
        namepath_segment = namepath_segment[:delta_rank]
        
        fields['rank'] = new_rank
        fields['code'] = namepath_segment[-1]
        
        name_context = NameContext(self, fields, 
                                   namepath_segment=namepath_segment)
        
        self.name_contexts[str(id(name_context))] = name_context
        
        return name_context
    






    