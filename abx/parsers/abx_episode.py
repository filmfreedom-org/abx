# abx_episode.py
"""
Custom parser written for "Lunatics!" Project Episode files.

Superseded by 'abx_schema' parser (probably).
"""

import re, copy

from . import registered_parser

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
