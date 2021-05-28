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

Demo:
>>>
>>> fc = FileContext(TESTPATH)

>>> fc.notes
['Data from implicit + explicit sources']

>>> fc['project']['name']
'My Project'

>>> fc['episode']['code']
1

>>> fc['rank']
'block'

>>> fc['block']['title']
'Beginning Of End'

>>> fc['seq']['title']
'LastPoint'

>>> fc['episode']['title']
'Pilot'
>>> fc['hierarchy']
'episode'

>>> fc['filename']
'A.001-LP-1-BeginningOfEnd-anim.txt'

>>> fc['path']
'/project/terry/Dev/eclipse-workspace/ABX/testdata/myproject/Episodes/A.001-Pilot/Seq/LP-LastPoint/A.001-LP-1-BeginningOfEnd-anim.txt'

>>> fc.root
'/project/terry/Dev/eclipse-workspace/ABX/testdata/myproject'

"""

import os, re, copy, string, collections
import yaml

DEFAULT_YAML = {}
with open(os.path.join(os.path.dirname(__file__), 'abx.yaml')) as def_yaml_file:
    DEFAULT_YAML.update(yaml.safe_load(def_yaml_file)) 


TESTPATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testdata', 'myproject', 'Episodes', 'A.001-Pilot', 'Seq', 'LP-LastPoint', 'A.001-LP-1-BeginningOfEnd-anim.txt'))

from . import accumulate
    
from .accumulate import RecursiveDict

wordre = re.compile(r'([A-Z][a-z]+|[a-z]+|[0-9]+|[A-Z][A-Z]+)')

class Enum(dict):
    def __init__(self, *options):        
        for i, option in enumerate(options):
            if isinstance(option, list) or isinstance(option, tuple):
                name = option[0]
                self[i] = tuple(option)
            else:
                name = str(option)
                self[i] = (option, option, option)
            self[name] = i
            if name not in ('name', 'number', 'options'):
                setattr(self, name, i)
                
    @property
    def options(self):
        """
        This gives the options in a Blender-friendly format, with
        tuples of three strings for initializing bpy.props.Enum().
        
        If the Enum was initialized with strings, the options will
        contain the same string three times. If initialized with
        tuples of strings, they will be used unaltered.
        """
        options = []
        number_keys = sorted([k for k in self.keys() if type(k) is int])
        return [self[i] for i in number_keys]
    
    def name(self, n):
        if type(n) is int:
            return self[n][0]
        elif type(n) is str:
            return n
        else:
            return None
    
    def number(self, n):
        if type(n) is str:
            return self[n]
        elif type(n) is int:
            return n
        else:
            return None
        

log_level = Enum('DEBUG', 'INFO', 'WARNING', 'ERROR')
            

NameParsers = {} # Parser registry

def registered_parser(parser):
    """
    Decorator function to register a parser class.
    """
    NameParsers[parser.name] = parser
    return parser

@registered_parser
class Parser_ABX_Episode:
    """
    Default filename parsing algorithm.
    
    Assumes field-based filenames of the form:
    
    <series>E<episode>[-<seq>[-<block>[-Cam<camera>][-<shot>]]][-<title>]-<role>.<filetype>
    
    Where the <field> indicates fields with fieldnames, and there are three expected separators:
    
    - is the 'field_separator'
    E is the 'episode_separator'
    . is the 'filetype_separator'
    
    (These can be overridden in the initialization).
    The class is callable, taking a string as input and returning a dictionary of fields.
    """
    name = 'abx_episode'
    
    max_score = 10 # Maximum number of fields parsed
    
    # supported values for filetype
    filetypes = {
        'blend':    "Blender File",
        'kdenlive': "Kdenlive Video Editor File",
        'mlt':      "Kdenlive Video Mix Script",
        'svg':      "Scalable Vector Graphics (Inkscape)",
        'kra':      "Krita Graphic File",
        'xcf':      "Gimp Graphic File",
        'png':      "Portable Network Graphics (PNG) Image",
        'jpg':      "Joint Photographic Experts Group (JPEG) Image",
        'aup':      "Audacity Project",
        'ardour':   "Ardour Project",
        'flac':     "Free Lossless Audio Codec (FLAC)",
        'mp3':      "MPEG Audio Layer III (MP3) Audio File",
        'ogg':      "Ogg Vorbis Audio File",
        'avi':      "Audio Video Interleave (AVI) Video Container",
        'mkv':      "Matroska Video Container",
        'mp4':      "Moving Picture Experts Group (MPEG) 4 Format}",
        'txt':      "Plain Text File"
        }
    
    # Roles that make sense in an episode context
    roles = {
        'extras':   "Extras, crowds, auxillary animated movement",
        'mech':     "Mechanical animation",
        'anim':     "Character animation",
        'cam':      "Camera direction",
        'vfx':      "Visual special effects",
        'compos':   "Compositing",
        'bkg':      "Background  2D image",
        'bb':       "Billboard 2D image",
        'tex':      "Texture 2D image",
        'foley':    "Foley sound",
        'voice':    "Voice recording",
        'fx':       "Sound effects",
        'music':    "Music track",
        'cue':      "Musical cue",
        'amb':      "Ambient sound",
        'loop':     "Ambient sound loop",
        'edit':     "Video edit"
        }
    
    # A few filetypes imply their roles:
    roles_by_filetype = {
        'kdenlive': 'edit',
        'mlt': 'edit'
        }
    
    
    def __init__(self, field_separator='-', episode_separator='E', filetype_separator='.',
                 fields=None, filetypes=None, roles=None, **kwargs):
        if not fields:
            fields = {}
        if filetypes:
            self.filetypes = copy.deepcopy(self.filetypes)  # Copy class attribute to instance
            self.filetypes.update(filetypes)                # Update with new values
        if roles:
            self.roles = copy.deepcopy(self.roles)          # Copy class attribute to instance
            self.roles.update(roles)                        # Update with new values
        self.field_separator = field_separator
        self.episode_separator = episode_separator
        self.filetype_separator = filetype_separator
        
    def __call__(self, filename, namepath):
        score = 0.0
        fielddata  = {}
        
        # Check for filetype ending
        i_filetype = filename.rfind(self.filetype_separator)
        if i_filetype < 0:
            fielddata['filetype'] = None
        else:
            fielddata['filetype'] = filename[i_filetype+1:]
            filename = filename[:i_filetype]
            score = score + 1.0
            
        components = filename.split(self.field_separator)
        
        # Check for role marker in last component
        if components[-1] in self.roles:
            fielddata['role'] = components[-1]
            del components[-1]
            fielddata['hierarchy'] = 'episode'
            score = score + 2.0
        elif fielddata['filetype'] in self.roles_by_filetype:
            fielddata['role'] = self.roles_by_filetype[fielddata['filetype']]
            fielddata['hierarchy'] = 'episode'
        else:
            fielddata['role'] = None
            fielddata['hierarchy'] = None
            
        # Check for a descriptive title (must be 3+ characters in length)
        if components and len(components[-1])>2:
            # Normalize the title as words with spaces
            title = ' '.join(w for w in wordre.split(components[-1]) if wordre.fullmatch(w))
            del components[-1]
            score = score + 1.0
        else:
            title = None              
            
        # Check if first field contains series/episode number
        if components:
            prefix = components[0]
            try:
                fielddata['series'] = {}
                fielddata['episode'] = {}
                fielddata['series']['code'], episode_id = prefix.split(self.episode_separator)
                fielddata['episode']['code'] = int(episode_id)
                fielddata['rank'] = 'episode'
                del components[0]
                score = score + 2.0
            except:
                pass
        
        # Check for sequence/block/shot/camera designations
        if components:
            fielddata['seq'] = {}
            fielddata['seq']['code'] = components[0]
            fielddata['rank'] = 'seq'
            del components[0]
            score = score + 1.0
                       
        if components:
            try:
                fielddata['block'] = {}
                fielddata['block']['code'] = int(components[0])
                del components[0]
                fielddata['rank'] = 'block'
                score = score + 1.0
            except:
                pass
            
        if components and components[0].startswith('Cam'):
            fielddata['camera'] = {}
            fielddata['camera']['code'] = components[0][len('Cam'):]
            fielddata['rank'] = 'camera'
            del components[0]
            score = score + 1.0
        
        if components:
            # Any remaining structure is joined back to make the shot ID
            fielddata['shot'] = {}
            fielddata['shot']['code'] = ''.join(components)
            fielddata['rank'] = 'shot'
            components = None
            score = score + 1.0
        
        if title and fielddata['rank'] in fielddata:
            fielddata[fielddata['rank']]['title'] = title
            
        return score/self.max_score, fielddata
    
@registered_parser
class Parser_ABX_Schema(object):
    """
    Parser based on using the project_schema defined in the project root directory YAML.
    """
    name = 'abx_schema'
    
    def __init__(self, schemas=None, definitions=None,
                    filetype_separator = '.',
                    comment_separator = '--',
                    role_separator = '-',
                    title_separator = '-', 
                    **kwargs):
        
        self.filetype_separator = filetype_separator
        self.comment_separator = comment_separator
        self.role_separator = role_separator
        self.title_separator = title_separator
        
        self.schemas = schemas
        
        if 'roles' in definitions:
            self.roles = definitions['roles']
        else:
            self.roles = []
            
        if 'filetypes' in definitions:
            self.filetypes = definitions['filetypes']
        else:
            self.filetypes = []
            
        if 'roles_by_filetype' in definitions:
            self.roles_by_filetype = definitions['roles_by_filetype']
        else:
            self.roles_by_filetype = []
            
    def _parse_ending(self, filename, separator):
        try:
            remainder, suffix = filename.rsplit(separator, 1)
            score = 1.0
        except ValueError:
            remainder = filename
            suffix = None
            score = 0.0
        return (suffix, remainder, score)
    
    def _parse_beginning(self, filename, separator):
        try:
            prefix, remainder = filename.split(separator, 1)
            score = 1.0
        except ValueError:
            prefix = filename
            remainder = ''
            score = 0.0
        return (prefix, remainder, score) 
    
    def __call__ (self, filename, namepath, debug=False):
        fields = {}
        score = 0.0
        possible = 0.0
               
        # First get specially-handled extensions
        remainder = filename
        field, newremainder, s = self._parse_ending(remainder, self.filetype_separator)
        if field and field in self.filetypes:
            remainder = newremainder
            fields['filetype'] = field
            score += s*1.0
        else:
            fields['filetype'] = None
        
        field, remainder, s = self._parse_ending(remainder, self.comment_separator)
        fields['comment'] = field
        score += s*0.5
        
        field, newremainder, s = self._parse_ending(remainder, self.role_separator)
        if field and field in self.roles:
            remainder = newremainder
            fields['role'] = field
            score += s*0.5
        else:
            fields['role'] = None
            
        field, remainder, s = self._parse_ending(remainder, self.title_separator)
        fields['title'] = field
        score += s*0.5
            
        possible += 3.0
        
        # Implicit roles
        if (    not fields['role'] and 
                fields['filetype'] and 
                fields['role'] in self.roles_by_filetype):
            self.role = self.roles_by_filetype[fields['filetype']]
            score += 0.2
            
        #possible += 0.2
                    
        # Figure the rest out from the schema
        # Find the matching rank start position for the filename
        start = 0
        for start, (schema, name) in enumerate(zip(self.schemas, namepath)):
            field, r, s = self._parse_beginning(remainder, schema.delimiter)
            try:
                if field.lower() == schema.format.format(name).lower():
                    score += 1.0
                    break
            except ValueError:
                print(' (365) field, format', field, schema.format)
            
        possible += 1.0
            
        # Starting from that position, try to match fields
        # up to the end of the namepath (checking against it)
        irank = 0
        for irank, (schema, name) in enumerate(
                zip(self.schemas[start:], namepath[start:])):
            if not remainder: break
            field, remainder, s = self._parse_beginning(remainder, schema.delimiter)
            score += s
            try:
                if ( type(field) == str and
                     field.lower() == schema.format.format(name).lower()):
                    fields[schema.rank]={'code':field}
                    fields['rank'] = schema.rank
                    score += 1.0
            except ValueError:
                print(' (384) field, format', field, schema.format)
            possible += 2.0
        
        # Remaining fields are authoritative (doesn't affect score)
        for schema in self.schemas[irank:]:
            if not remainder: break
            field, remainder, s = self._parse_beginning(remainder, schema.delimiter)
            fields[schema.rank]={'code':field}
            fields['rank'] = schema.rank
                           
        if 'rank' in fields:
            fields[fields['rank']]['title'] = fields['title']
            
        if not fields['role'] and fields['filetype'] in self.roles_by_filetype:
            fields['role'] = self.roles_by_filetype[fields['filetype']]
        
        return score/possible, fields
    
@registered_parser
class Parser_ABX_Fallback(object):
    """
    Highly-tolerant parser to fall back to if the others fail
    or can't be used.
    """
    name = 'abx_fallback'
    
    filetypes   = DEFAULT_YAML['definitions']['filetypes']
    roles       = DEFAULT_YAML['definitions']['roles']
    roles_by_filetype = (
                  DEFAULT_YAML['definitions']['roles_by_filetype'])
    
    main_sep_re     = re.compile(r'\W+') # Any single non-word char
    comment_sep_re  = re.compile(r'[\W_][\W_]+|[~#$!=+&]+')
    
    
    def __init__(self, **kwargs):
        pass
            
    def _parse_ending(self, filename, separator):
        try:
            remainder, suffix = filename.rsplit(separator, 1)
            score = 1.0
        except ValueError:
            remainder = filename
            suffix = None
            score = 0.0
        return (suffix, remainder, score)
    
    def __call__(self, filename, namepath):
        fields = {}
        score = 1.0
        possible = 4.5
        
        split = filename.rsplit('.', 1)
        if len(split)<2 or split[1] not in self.filetypes:
            fields['filetype'] = None
            remainder = filename
            score += 1.0
        else:
            fields['filetype'] = split[1]
            remainder = split[0]
            
        comment_match = self.comment_sep_re.search(remainder)
        if comment_match:
            fields['comment'] = remainder[comment_match.end():]
            remainder = remainder[:comment_match.start()]
        else:
            fields['comment'] = None
        
        role = self.main_sep_re.split(remainder)[-1]      
        if role in self.roles:
            fields['role'] = role
            remainder = remainder[:-1-len(role)]
            score += 1.0
        else:
            fields['role'] = None
        
        # Implied role
        if fields['filetype'] in self.roles_by_filetype:
            fields['role'] = self.roles_by_filetype[fields['filetype']]
            score += 1.0        
        
        words = self.main_sep_re.split(remainder)
        fields['code']  = ''.join([w.capitalize() for w in words])
        fields['title'] = remainder
        
        return score/possible, fields
        
        
    
class RankNotFound(LookupError):
    pass
    
class NameSchema(object):
    """
    Represents a schema used for parsing and constructing designations, names, etc.
    """
    # Defaults
    _default_schema = {
        'delimiter':'-',
        
        'type': 'string',
        'format':'{:s}',        
        'minlength':1,          # Must be at least one character
        'maxlength':0,          # 0 means unlimited
        'words': False,         # If true, treat value as words and spaces
        'pad': '0',             # Left-padding character for fixed length
        'default': None,
        
        'rank': 'project',
        'irank': 0,
        'ranks': ('series', 'episode', 'sequence',
                  'block', 'camera', 'shot', 'element')
        }
    
    _codetypes = {
        'number':{}, 
        'string':{},
        'letter':{},
        'lowercase':{},
        }
    
    _letter = tuple((A,A,A) for A in string.ascii_uppercase)
    _lowercase = tuple((a,a,a) for a in string.ascii_lowercase)
        
    rank = 'project'
    irank = 0
    default = None
    
    ranks = ('project',)
    
    def __init__(self, parent=None, rank=None, schema=None, debug=False):
        # Three types of schema data:
        
        # Make sure schema is a copy -- no side effects!
        if not schema:
            schema = {}
        else:
            s = {}
            s.update(schema)
            schema = s
            
        if not rank and 'rank' in schema:
            rank = schema['rank']
        
        # Stepped down in rank from parent:
        self.parent = parent
        
        if parent and rank:
            # Check rank is defined in parent ranks and use that
            # We can skip optional ranks
            if rank in parent.ranks:
                j = parent.ranks.index(rank)
                self.ranks = parent.ranks[j+1:]
                self.rank = rank
            else:
                # It's an error to ask for a rank that isn't defined
                raise RankNotFound(
                    '"%s" not in defined ranks for "%s"' % (rank, parent))
                
        elif parent and not rank:
            # By default, get the first rank below parent
            self.rank = parent.ranks[0]
            self.ranks = parent.ranks[1:]
            
        elif rank and not parent:
            # With no parent, we're starting a new tree and renaming the root
            self.rank = rank
            self.ranks = self._default_schema['ranks']
            
        else: # not rank and not parent:
            # New tree with default rank
            self.rank = self._default_schema['rank']
            self.ranks = self._default_schema['ranks']
        
        # Directly inherited/acquired from parent
        # So far, only need a delimiter specified, but might be other stuff
        self.delimiter = self._default_schema['delimiter']
        if parent and parent.delimiter: self.delimiter = parent.delimiter
        
        # Explicit override by the new schema:
        if 'ranks'      in schema: self.ranks = schema['ranks']
        if 'delimiter'  in schema: self.delimiter = schema['delimiter'] 
        if 'default'    in schema:
            if schema['default'] == 'None':
                self.default = None
            else: 
                self.default = schema['default']
            
        # Default unless specified (i.e. not inherited from parent)
        newschema = {}
        newschema.update(self._default_schema)
        newschema.update(schema)
   
        self.format = str(newschema['format'])
        
        self.minlength = int(newschema['minlength'])
        self.maxlength = int(newschema['maxlength'])
        self.pad       = str(newschema['pad'])
        self.words     = bool(newschema['words'])
     
        if newschema['type'] == 'letter':
            self.codetype = self._letter
        
        elif newschema['type'] == 'lowercase':
            self.codetype = self._lowercase
                
        elif newschema['type'] == 'number':
            # Recognized Python types
            self.codetype = int
            if 'minlength' or 'maxlength' in schema:
                self.format = '{:0>%dd}' % self.minlength
                
        elif newschema['type'] == 'string':
            self.codetype = str
                
            if ('minlength' in schema) or ('maxlength' in schema):
                if self.maxlength == 0:
                    # Special case for unlimited length
                    self.format = '{:%1.1s>%ds}' % (self.pad, self.minlength)
                self.format = '{:%1.1s>%d.%ds}' % (
                                    self. pad, self.minlength, self.maxlength)
            
        elif newschema['type'] == 'bool':
                self.codetype = bool
                
        elif isinstance(newschema['type'], collections.Sequence):
            # Enumerated types
            # This is somewhat specific to Blender -- setting the 
            # enumeration values requires a sequence in a particular format
            self.codetype = []
            for option in newschema['type']:
                if type(option) is not str and isinstance(option, collections.Sequence):
                    option = tuple([str(e) for e in option][:3])
                else:
                    option = (str(option), str(option), str(option))
                self.codetype.append(option)
                
        elif isinstance(newschema['type'], collections.Mapping):
            self.codetype = []
            for key, val in newschema['type'].items():
                if type(val) is not str and isinstance(val, collections.Sequence):
                    if len(val) == 0:
                        option = (str(key), str(key), str(key))
                    elif len(val) == 1:
                        option = (str(key), str(val[0]), str(val[0]))
                    else:
                        option = (str(key), str(val[0]), str(val[1]))
                else:
                    option = (str(key), str(val), str(val))
                self.codetype.append(option)
        else:
            # If all else fails, just list the string
            self.codetype = None
            

        
    def __repr__(self):
        return('<(%s).NameSchema: %s (%s, %s, %s, (%s))>' % (
            repr(self.parent),
            #self.irank, 
            self.rank,
            self.delimiter,
            self.default,
            self.format,
            self.codetype
            ))
        

class NameContext(object):
    """
    Single naming context within the file (e.g. a Blender scene).
    """
    
    def __init__(self, container, fields=None, namepath_segment=(), ):
        self.clear()     
        if container or fields or namepath_segment:
            self.update(container, fields, namepath_segment)
        
    def clear(self):
        self.fields = {}
        self.schemas = ['project']
        self.rank = 0
        self.code = 'untitled'
        self.container = None
        self.namepath_segment = []
        
    def update(self, container=None, fields=None, namepath_segment=()):
        self.container = container
        
        if namepath_segment:
            self.namepath_segment = namepath_segment
        else:
            self.namepath_segment = []
        
        try:
            self.schemas  = self.container.schemas
        except AttributeError:
            self.schemas = []
            
        try:
            self.omit_ranks = self.container.omit_ranks
        except AttributeError:
            self.omit_ranks = {}
            self.omit_ranks.update({
                'edit': 0,
                'render': 1,
                'filename': 1,
                'scene': 3})
            
        if fields:
            if isinstance(fields, dict):
                self.fields.update(fields)
            elif isinstance(fields, str):
                self.fields.update(yaml.safe_load(fields))

    def update_fields(self, data):
        self.fields.update(data)
        
    def _load_schemas(self, schemas, start=0):
        """
        Load schemas from a list of schema dictionaries.
        
        @schemas: list of dictionaries containing schema field data (see NameSchema).
        The data will typically be extracted from YAML, and is
        expected to be a list of dictionaries, each of which defines
        fields understood by the NameSchema class, to instantiate
        NameSchema objects. The result is a linked chain of schemas from
        the top of the project tree down.
        
        @start: if a start value is given, the top of the existing schema
        chain is kept, and the provided schemas starts under the rank of
        the start level in the existing schema. This is what happens when
        the schema is locally overridden at some point in the hierarchy.
        """
        self.schemas = self.schemas[:start]
        if self.schemas:
            last = self.schemas[-1]
        else:
            last = None
        for schema in schemas:
            self.schemas.append(NameSchema(last, schema['rank'], schema=schema))
            #last = self.schemas[-1]
            
    def _parse_words(self, wordtext):
        words = []
        groups = re.split(r'[\W_]', wordtext)
        for group in groups:
            if len(group)>1:
                group = group[0].upper() + group[1:]
                words.extend(re.findall(r'[A-Z][a-z]*', group))
            elif len(group)==1:
                words.append(group[0].upper())
            else:
                continue
        return words
                
    def _cap_words(self, words):
        return ''.join(w.capitalize() for w in words)
    
    def _underlower_words(self, words):
        return '_'.join(w.lower() for w in words)
    
    def _undercap_words(self, words):
        return '_'.join(w.capitalize() for w in words)
    
    def _spacecap_words(self, words):
        return ' '.join(w.capitalize() for w in words)        
        
    def _compress_name(self, name):
        return self._cap_words(self._parse_words(name))
    
    @property
    def namepath(self):
        if self.container:
            return self.container.namepath + self.namepath_segment
        else:
            return self.namepath_segment
    
    @property
    def rank(self):
        if 'rank' in self.fields:
            return self.fields['rank']
        else:
            return None
        
    @rank.setter
    def rank(self, rank):
        self.fields['rank'] = rank
    
    @property
    def name(self):
        if 'name' in self.fields:
            return self.fields['name']
        elif 'title' in self.fields:
            return self._compress_name(self.fields['title'])
#         elif 'code' in self.fields:
#             return self.fields['code']
        else:
            return ''
        
    @name.setter
    def name(self, name):
        self.fields['name'] = name
        
    @property
    def code(self):
        if self.rank:
            return self.fields[self.rank]['code']
        else:
            return self.fields['code']
        
    @code.setter
    def code(self, code):
        if self.rank:
            self.fields[self.rank] = {'code': code}
        else:
            self.fields['code'] = code

    @property
    def description(self):
        if 'description' in self.fields:
            return self.fields['description']
        else:
            return ''
        
    @description.setter
    def description(self, description):
        self.fields['description'] = str(description)
        
    def _get_name_components(self):
        components = []
        for code, schema in zip(self.namepath, self.schemas):
            if code is None: continue
            components.append(schema.format.format(code))
            components.append(schema.delimiter)
        return components[:-1]
        
    @property
    def fullname(self):
        if self.name:
            return (self.designation + 
                    self.schemas[-1].delimiter + 
                    self._compress_name(self.name) )
        else:
            return self.designation
                    
    @property
    def designation(self):
        return ''.join(self._get_name_components())
                   
    @property
    def shortname(self):
        namebase = self.omit_ranks['filename']*2
        return  (''.join(self._get_name_components()[namebase:]) +
                        self.schemas[-1].delimiter +
                        self._compress_name(self.name))
    
    def get_scene_name(self, suffix=''):
        namebase = self.omit_ranks['scene']*2
        desig = ''.join(self._get_name_components()[namebase:])     
        
        if suffix:
            return desig + ' ' + suffix
        else:
            return desig
        
    def get_render_path(self, suffix='', framedigits=5, ext='png'):
        
        desig = ''.join(self._get_name_components()[self.omit_ranks['render']+1:])
        
        if ext in ('avi', 'mov', 'mp4', 'mkv'):
            if suffix:
                path = os.path.join(self.render_root, suffix,
                    desig + '-' + suffix + '.' + ext)
            else:
                path = os.path.join(self.render_root, ext.upper(),
                    desig + '.' + ext)
        else:
            if suffix:
                path = os.path.join(self.render_root, 
                    suffix, desig,
                    desig + '-' + suffix + '-f' + '#'*framedigits + '.' + ext)
            else:
                path = os.path.join(self.render_root,
                    ext.upper(), desig,
                    desig + '-f' + '#'*framedigits + '.' + ext)
        return path

        
            
class FileContext(NameContext):
    """
    Collected information about an object's location on disk: metadata
    about filename, directory names, and project, based on expected keywords.
    """
#     hierarchies = ()
#     hierarchy = None
    #schema = None
    
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
        self.name_contexts = []
                
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
        self.provided_data = RecursiveDict(DEFAULT_YAML)
        self.abx_fields = DEFAULT_YAML['abx']
                     
    def clear_notes(self):
        # We use this for logging, so it doesn't get cleared by the
        # normal clear process.
        self.notes = []
            
    def update(self, path):
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
        self.provided_data = RecursiveDict(DEFAULT_YAML)
        
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
            print("Errors finding Name Path (is there a 'project_schema' or 'project_unit' defined?")
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
        try:
            self.parsers = [NameParsers[self.provided_data['definitions']['parser']](**self.schema['filenames'])]
        except (TypeError, KeyError, IndexError):
            self.parsers = [
                #Parser_ABX_Episode(), 
                Parser_ABX_Schema(self.schemas, self.provided_data['definitions'])]
            
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
        if type(level) is str:
            level = log_level.index(level)
        self.notes.append((level, msg))
        
    def get_log_text(self, level=log_level.INFO):
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
        if 'filetype' in self.fields:
            return self.fields['filetype']
        else:
            return ''
        
    @filetype.setter
    def filetype(self, filetype):
        self.fields['filetype'] = filetype
        
    @property
    def role(self):
        if 'role' in self.fields:
            return self.fields['role']
        else:
            return ''
        
    @role.setter
    def role(self, role):
        self.fields['role'] = role
        
    @property
    def title(self):
        if 'title' in self.fields:
            return self.fields['title']
        else:
            return ''
    
    @title.setter
    def title(self, title):
        self.fields['title'] = title
        
    @property
    def comment(self):
        if 'comment' in self.fields:        
            return self.fields['comment']
        else:
            return ''
        
    @comment.setter
    def comment(self, comment):
        self.fields['comment'] = comment
        
    @classmethod    
    def deref_implications(cls, values, matchfields):
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
        Get a subunit from the current file.
        Any rank in the hierarchy may be specified, though element, shot,
        camera, and block are most likely.
        """
        fields = {}
        fields.update(self.fields)
        
        namepath_segment = []                      
        ranks = [s.rank for s in self.schemas]        
        i_rank = len(self.namepath)        
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
                    
        delta_rank = ranks.index(new_rank) - ranks.index(old_rank)
                
        # Truncate to the new rank:
        namepath_segment = namepath_segment[:delta_rank]
        
        fields['rank'] = new_rank
        fields['code'] = namepath_segment[-1]
                    
        self.name_contexts.append(NameContext(self, fields,
                namepath_segment=namepath_segment))
        return self.name_contexts[-1]
    






    