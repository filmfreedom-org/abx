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
    """
    List of options defined in a two-way dictionary.
    """
    def __init__(self, *options):
        """
        Args:
            *options (list): a list of strings to be used as enumerated values.
        """       
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
        Gives the options in a Blender-friendly format.
        
        Returns:
            A list of triples containing the three required fields for 
            Blender's bpy.props.EnumProperty.
        
        If the Enum was initialized with strings, the options will
        contain the same string three times. If initialized with
        tuples of strings, they will be used unaltered.
        """
        options = []
        number_keys = sorted([k for k in self.keys() if type(k) is int])
        return [self[i] for i in number_keys]
    
    def name(self, n):
        """
        Return the name (str) value of enum, regardless of which is provided.
        
        Args:
            n (str, int): An enum value (either number or string).
            
        Returns:
            Returns a string if n is recognized. Returns None if not.
        """
        if type(n) is int:
            return self[n][0]
        elif type(n) is str:
            return n
        else:
            return None
    
    def number(self, n):
        """
        Return the number (int) value of enum, regardless of which is provided.
        
        Args:
            n (str, int): An enum value (either number or string).
            
        Returns:
            Returns a number if n is recognized. Returns None if not.
        """
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
    Parser based on using the list of schemas.
    
    The schemas are normally defined in the project root directory YAML.
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
    Highly-tolerant parser to fall back to if others fail.
    
    Makes very minimal assumptions about filename structure.
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
    """
    Error returned if an unexpected 'rank' is encountered.
    """
    pass
    
class NameSchema(object):
    """
    Represents a schema used for parsing and constructing names.
    
    We need naming information in various formats, based on knowledge about
    the role of the Blender file and scene in the project. This object tracks
    this information and returns correct names based on it via properties.
    
    Note that NameSchema is NOT an individual project unit name, but a defined
    pattern for how names are treat at that level in the project. It is a class
    of names, not a name itself. Thus "shot" has a schema, but is distinct from
    "shot A" which is a particular "project unit". The job of the schema is
    to tell us things like "shots in this project will be represented by
    single capital letters".
    
    See NameContext for the characteristics of a particular unit.
    
    Attributes:
        codetype (type):    Type of code name used for this rank.
                            Usually it will be int, str, or Enum.
                            Pre-defined enumerations are available
                            for uppercase letters (_letters) and
                            lowercase letters (_lowercase) (Roman --
                            in principle, other alphabets could be added).
        
        rank (int):         Rank of hierarchy under project (which is 0). The
                            rank value increases as you go "down" the tree.
                            Sorry about that confusion.
        
        ranks (list(Enum)): List of named ranks known to schema (may include
                            both higher and lower ranks).
                            
        parent (NameSchema|None):
                            Earlier rank to which this schema is attached.
        
        format (str):       Code for formatting with Python str.format() method.
                            Optional: format can also be specified with the
                            following settings, or left to default formatting.
        
        pad (str):          Padding character.
        minlength (int):    Minimum character length (0 means it may be empty).
        maxlength (int):    Maximum character length (0 means no limit).
        
        words (bool):       Treat name/title fields like a collection of words,
                            which can then be represented using "TitleCaps" or
                            "underscore_spacing", etc for identifier use.
                            
        delimiter (str):    Field delimiter marking the end of this ranks'
                            code in designations. Note this is the delimiter
                            after this rank - the higher (lower value) rank
                            controls the delimiter used before it.
                            
        default:            The default value for this rank. May be None, 
                            in which case, the rank will be treated as unset
                            until a setting is made. The UI must provide a
                            means to restore the unset value. Having no values
                            set below a certain rank is how a NameContext's
                            rank is determined.
                            
        Note that the rank may go back to a lower value than the schema's
        parent object in order to overwrite earlier schemas (for overriding a
        particular branch in the project) or (compare this to the use of '..'
        in operating system paths). Or it may skip a rank, indicating an
        implied intermediate value, which will be treated as having a fixed
        value.  (I'm not certain I want that, but it would allow us to keep
        rank numbers synchronized better in parallel hierarchies in a project).
        
        Note that schemas can be overridden at any level in a project by 
        'project_schema' directives in unit YAML files, so it is possible to
        change the schema behavior locally. By design, only lower levels in
        the hierarchy (higher values of rank) can be affected by overrides.
        
        This kind of use isn't fully developed yet, but the plan is to include
        things like managing 'Library' assets with a very different structure
        from shot files. This way, the project can split into 'Library' and
        'Episode' forks with completely different schemas for each.
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
    
    # Really this is more like a set than a dictionary right now, but I
    # thought I might refactor to move the definitions into the dictionary:
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
        """
        Create a NameSchema from schema data source.
        
        NameSchema is typically initialized based on data from YAML files
        within the project. This allows us to avoid encoding project structure
        into ABX, leaving how units are named up to the production designer.
        
        If you want our suggestions, you can look at the "Lunatics!" project's
        'lunatics.yaml' file, or the 'myproject.yaml' file in the ABX source
        distribution.
        
        Arguments:
            parent (NameSchema):    
                           The level in the schema hierarchy above this one.
                           Should be None if this is the top.
                            
            rank (int):    The rank of this schema to be created.
            
            schema (dict): Data defining the schema, typically loaded from a
                           YAML file in the project.
                           
            debug (bool):  Used only for testing. Turns on some verbose output
                           about internal implementation.
        
        Note that the 'rank' is specified because it may NOT be sequential from
        the parent schema. 
        """
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
            # If all else fails
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
    
    NameContext defines the characteristics of any particular project
    unit (taxon) within the project. So, for example, it may represent
    the context of an "Episode" or a "Sequence" or a "Shot".
    
    Used in Blender, it will typically be used in two ways: one to represent
    the entire file (as the base class for FileContext) and one to represent
    a particular Blender scene within the file, which may represent a single
    shot, multiple shots with the same camera, or perhaps just an element
    of a compositing shot created from multiple Blender scenes.
    
    Examples of all three uses occur in "Lunatics!" episode 1: the
    "Press Conference" uses multicam workflow, with scenes for each camera
    with multiple shots selected from the timeline, using the VSE; most scenes
    are done 'single camera' on a shot-per-scene basis; but some shots use a
    'Freestyle camera clipping' technique which puts the line render in a
    separate (but linked) scene, while the final shot in the episode combines
    three different Blender scenes in a 2D composite, to effect a smooth
    transition to the titles.
    
    Attributes:
        container (NameContext):
                        The project unit that contains this one. One step
                        up the tree, but not necessarily the next step up
                        in rank (because there can be skipped ranks).
                        
        schemas (list(NameSchema)):
                        The schema list as seen by this unit, taking into
                        account any schema overrides.
                        
        namepath_segment (list):
                        List of namepath codes defined in this object, not
                        including the container's namepath. (Implementation)
                        
        omit_ranks dict(str:int):
                        How many ranks to omit from the beginning in shortened
                        names for specific uses. (Implementation).
                        Probably a mistake this isn't in the NameSchema instead.
                        
        fields (dict):  The field values used to initialize the NameContext,
                        May include some details not defined in this attribution
                        API, and it includes the raw state of the 'name', 'code',
                        and 'title' fields, determining which are
                        authoritative -- i.e. fields which aren't specified are
                        left to 'float', being generated by the related ones.
                        Thus, name implies title, or title implies name. You
                        can have one or the other or both, but the other will be
                        generated from the provided one if it isn't specified.
                        (Implementation).
                        
        code (str|int|Enum):
                        Identification code for the unit (I replaced 'id' in earlier
                        versions, because 'id' is a reserved word in Python for Python
                        memory reference / pointer identity.
                        (R/W Property).
        
        namepath (list):
                        List of codes for project units above this one.
                        (R/O Property, generated from namepath_segment and
                        container).
        
        rank (int):     Rank of this unit (same as in Schema).
                        (R/W Property, may affect other attributes).
                        
        name (str):     Short name for the unit.
                        (R/W Property, may affect title).
                        
        title (str):    Full title for the unit.
                        (R/W Property, may affect name).
                        
        designation (str):
                        Full designation for the unit, including all
                        the namepath elements, but no title.
                        
        fullname (str): The full designation, plus the current unit name.
        
        shortname (str):Abbreviated designation, according to omit_ranks,
                        with name.
                        

                        
    
        
    
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
        """
        Create a name for the current scene, based on namepath.
        
        Arguments:
            suffix (str):   Optional suffix code used to improve
                            identifications of scenes.
        """
        namebase = self.omit_ranks['scene']*2
        desig = ''.join(self._get_name_components()[namebase:])     
        
        if suffix:
            return desig + ' ' + suffix
        else:
            return desig
        
    def get_render_path(self, suffix='', framedigits=5, ext='png'):
        """
        Create a render filepath, based on namepath and parameters.
        
        Arguments:
            suffix (str):
                Optional unique code (usually for render profile).
            
            framedigits (int):
                How many digits to reserve for frame number.
                
            ext (str):
                Filetype extension for the render.
                
        This is meant to be called by render_profile to combine namepath
        based name with parameters for the specific render, to uniquely
        idenfify movie or image-stream output.
        """        
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
    Collected information about a file's storage location on disk.
    
    Collects name and path information from a filepath, used to identify
    the file's role in a project. In order to do this correctly, the
    FileContext object needs a schema defined for the project, which
    explains how to read and parse project file names, to determine what
    unit, name, or role they might have in the project.
    
    For this, you will need to have a <project>.yaml file which defines
    the 'project_schema' (a list of dictionaries used to initialize a list
    of NameSchema objects). Examples of <project>.yaml are provided in the
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
        self.provided_data = RecursiveDict(DEFAULT_YAML)
        self.abx_fields = DEFAULT_YAML['abx']
                     
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
    






    