# parsers (sub-package)
"""
Filename Parsers & Registry for FileContext.
"""     

import re, copy, os

import yaml

NameParsers = {} # Parser registry

def registered_parser(parser):
    """
    Decorator function to register a parser class.
    """
    NameParsers[parser.name] = parser
    return parser

wordre = re.compile(r'([A-Z][a-z]+|[a-z]+|[0-9]+|[A-Z][A-Z]+)')

@registered_parser
class Parser_ABX_Episode:
    """
    Original "Lunatics!" filename parsing algorithm.  (DEPRECATED)
    
    This parser was written before the Schema parser. It hard-codes the schema used
    in the "Lunatics!" Project, and can probably be safely replaced by using the Schema
    parser with appropriate YAML settings in the <project>.yaml file, which also allows
    much more flexibility in naming schemes.
    
    YAML parameter settings available for this parser:
    
    ---
    definitions:
        parser: abx_episode                    # Force use of this parser
        
        parser_options:                        # Available settings (w/ defaults)     
            field_separator:      '-'
            episode_separator:    'E'
            filetype_separator:   '.'    
    
    Filetypes and roles are hard-code, and can't be changed from the YAML.
    
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




DEFAULT_YAML = {}
with open(os.path.join(os.path.dirname(__file__), 'abx.yaml')) as def_yaml_file:
    DEFAULT_YAML.update(yaml.safe_load(def_yaml_file)) 


    
@registered_parser
class Parser_ABX_Fallback(object):
    """
    Highly-tolerant parser to fall back on if others fail.

    The fallback parser makes only a very minimal and robust set of assumptions.
    
    Any legal filename will successfully return a simple parse, though much
    interpretation may be lost. It still allows for common field-based practices,
    but falls back on using the unaltered filename if necessary.
    
    YAML options available:
    
    ---
    definitions:
        parser: abx_fallback                # Force use of this parser.
        
    There are no other options. Field separators are defined very broadly,
    and include most non-word characters (~#$!=+&_-). This was mostly designed
    to work without a project schema available.    
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
        
    
@registered_parser
class Parser_ABX_Schema(object):
    """
    Parser based on using the list of schemas.    
    The schemas are normally defined in the project root directory YAML.
    
    Expands on the 'abx_episode' parser by allowing all the schema to
    be defined by outside configuration data (generally provided in a
    project YAML file, but this module does not depend on the data
    source used).
    
    The project YAML can additionally control parsing with this parser:
    
    ---
    definitions:
        parser: abx_schema                 # Force use of this parser
        
        parser_options:                    # Set parameters
            filetype_separator:    '.'
            comment_separator:     '--'
            role_separator:        '-'
            title_separator:       '-'
    
        filetypes:                         # Recognized filetypes.
            blend:    Blender File         # <filetype>: documentation
            ...
            
        roles:                             # Recognized role fields.
            anim:    Character Animation   # <role>: documentation
            ...
            
        roles_by_filetype:                 # Roles implied by filetype.
            kdenlive: edit                 # <filetype>:<role>
            ...
            
        (For the full default lists see abx/abx.yaml). 
    
    schemas (list):    The current schema-list defining how filenames should be parsed.
                       This "Schema" parser uses this to determine both parsing and
                       mapping of text fields in the filename.
                       
    definitions(dict): The project definitions currently visible to the parser.    
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

