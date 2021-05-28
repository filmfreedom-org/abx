#!/usr/bin/env python3
"""
Test the file_context module.

This was written well after I wrote the module, and starts out as a conversion
from the doctests I had in the module already.
"""


import unittest, os, textwrap
import yaml

import sys
print("__file__ = ", __file__)
sys.path.append(os.path.normpath(os.path.join(__file__, '..', '..')))

from abx import file_context

class FileContext_Utilities_Tests(unittest.TestCase):
    """
    Test utility functions and classes that FileContext features depend on.
    """
    
    def test_enum_class_basics(self):
        my_enum = file_context.Enum('ZERO', 'ONE', 'TWO', 'THREE')
                
        self.assertEqual(my_enum.number(my_enum.ZERO), 0)
        self.assertEqual(my_enum.number(0), 0)
        self.assertEqual(my_enum.number('ZERO'), 0)
        
        self.assertEqual(my_enum.name(my_enum.ZERO), 'ZERO')
        self.assertEqual(my_enum.name(0), 'ZERO')
        self.assertEqual(my_enum.name('ZERO'), 'ZERO')
        
        self.assertEqual(my_enum.ONE, 1)
        self.assertEqual(my_enum.name(my_enum.TWO), 'TWO')        
        self.assertEqual(my_enum.name(2), 'TWO')        
        self.assertEqual(my_enum.number('THREE'), 3)
        
    def test_enum_class_blender_enum_options(self):
        my_options = file_context.Enum(
            ('ZP', 'ZeroPoint', 'Zero Point'),
            ('FP', 'FirstPoint', 'First Point'),
            ('LP', 'LastPoint', 'Last Point'))
        
        #print("dir(my_options) = ", dir(my_options))
        
        self.assertEqual(my_options.number(my_options.ZP), 0)
        self.assertEqual(my_options.number(my_options.FP), 1)
        
        self.assertEqual(my_options.name(my_options.ZP), 'ZP')
        self.assertEqual(my_options.name(1), 'FP')
        self.assertEqual(my_options.name('LP'), 'LP')
        
        self.assertEqual(my_options[my_options.number('FP')], 
            ('FP', 'FirstPoint', 'First Point'))              
        
        self.assertListEqual(my_options.options,
            [('ZP', 'ZeroPoint', 'Zero Point'),
            ('FP', 'FirstPoint', 'First Point'),
            ('LP', 'LastPoint', 'Last Point')])


class FileContext_NameSchema_Interface_Tests(unittest.TestCase):
    """
    Test the interfaces presented by NameSchema.
    
    NameSchema is not really intended to be used from outside the
    file_context module, but it is critical to the behavior of the
    module, so I want to make sure it's working as expected.
    """    
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPROJECTYAML = os.path.join(TESTDATA, 'myproject', 'myproject.yaml')
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')

    
    # Normally from 'project_schema' in YAML
    TESTSCHEMA_LIST =[
                     {'rank': 'project', 'delimiter':'-', 'format':'{:s}', 'words':True},
                     {'rank': 'series',  'delimiter':'E', 'format':'{:2s}'},
                     {'rank': 'episode', 'delimiter':'-', 'format':'{!s:>02s}'},
                     {'rank': 'sequence','delimiter':'-', 'format':'{:2s}'},
                     {'rank': 'block',   'delimiter':'-', 'format':'{!s:1s}'},
                     {'rank': 'shot',    'delimiter':'-', 'format':'{!s:s}'},
                     {'rank': 'element', 'delimiter':'-', 'format':'{!s:s}'}]
    
    def test_NameSchema_create_single(self):
        ns = file_context.NameSchema(schema = self.TESTSCHEMA_LIST[0])
       
        # Test for ALL the expected properties:
        
        # Set by the test schema
        self.assertEqual(ns.rank, 'project')
        self.assertEqual(ns.delimiter, '-')
        self.assertEqual(ns.format, '{:s}')
        self.assertEqual(ns.words, True)
        self.assertEqual(ns.codetype, str)
        
        # Default values
        self.assertEqual(ns.pad, '0')
        self.assertEqual(ns.minlength, 1)
        self.assertEqual(ns.maxlength, 0)
        self.assertEqual(ns.default, None)
        
        # Candidates for removal:
        self.assertEqual(ns.irank, 0)   # Is this used at all?
        self.assertEqual(ns.parent, None)
        self.assertListEqual(list(ns.ranks),
            ['series', 'episode', 'sequence', 
             'block', 'camera', 'shot', 'element'])
        
    def test_NameSchema_load_chain_from_project_yaml(self):
        with open(self.TESTPROJECTYAML, 'rt') as yaml_file:
            data = yaml.safe_load(yaml_file)
        schema_dicts = data['project_schema']
        
        schema_chain = []
        last = None
        for schema_dict in schema_dicts:
            rank = schema_dict['rank']
            parent = last
            schema_chain.append(file_context.NameSchema(
                parent = parent,
                rank = rank,
                schema = schema_dict))
            last = schema_chain[-1]
            
        #print( schema_chain )
        
        self.assertEqual(len(schema_chain), 8)
        
        self.assertEqual(
            schema_chain[-1].parent.parent.parent.parent.parent.parent.parent.rank,
            'project')
        
        self.assertEqual(schema_chain[5].rank, 'camera')
        self.assertEqual(schema_chain[5].codetype[1], ('c2', 'c2', 'c2')) 
                
         
    

class FileContext_Parser_UnitTests(unittest.TestCase):
    TESTFILENAMES = ('S1E01-SF-4-SoyuzDMInt-cam.blend', 'S1E02-MM-MediaMontage-compos.blend',
                     'S1E01-PC-PressConference-edit.kdenlive',
                     'S1E01-LA-Launch.kdenlive')
    
    # Collected by analyzing YAML control files ('project_unit').
    TESTNAMEPATHS = (('Lunatics', 'S1', '1', 'SF', '4'),
                     ('Lunatics', 'S1', '2', 'MM'),
                     ('Lunatics', 'S1', '1', 'PC'),
                     ('Lunatics', 'S1', '1', 'LA'))
    
    # Normally from 'project_schema' in YAML
    TESTSCHEMA_LIST =[
                     {'rank': 'project', 'delimiter':'-', 'format':'{:s}', 'words':True},
                     {'rank': 'series',  'delimiter':'E', 'format':'{:2s}'},
                     {'rank': 'episode', 'delimiter':'-', 'format':'{!s:>02s}'},
                     {'rank': 'sequence','delimiter':'-', 'format':'{:2s}'},
                     {'rank': 'block',   'delimiter':'-', 'format':'{!s:1s}'},
                     {'rank': 'shot',    'delimiter':'-', 'format':'{!s:s}'},
                     {'rank': 'element', 'delimiter':'-', 'format':'{!s:s}'}]
    
    # Normally from 'definitions' in YAML
    TESTDEFS = {
        'filetypes':{
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
            },
        'roles':{
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
            },
        'roles_by_filetype': {
            'kdenlive': 'edit',
            'mlt': 'edit'
            }
        }
    
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')
    
    def setUp(self):
        self.TESTSCHEMAS = [file_context.NameSchema(    #rank=s['rank'], 
                                schema=s)
                                for s in self.TESTSCHEMA_LIST]
      
    def test_parsing_filenames_w_episode_parser(self):
        abx_episode_parser = file_context.NameParsers['abx_episode']()
        
        data = abx_episode_parser('S1E01-SF-4-SoyuzDMInt-cam.blend', [])   
        self.assertDictEqual(data[1],
            {'filetype': 'blend', 
             'role': 'cam', 
             'hierarchy': 'episode', 
             'series': {'code': 'S1'}, 
             'episode': {'code': 1}, 
             'rank': 'block', 
             'seq': {'code': 'SF'}, 
             'block': {'code': 4, 'title': 'Soyuz DMI nt'}})
        
        data = abx_episode_parser('S1E02-MM-MediaMontage-compos.blend', [])
        self.assertDictEqual(data[1],
            {'filetype': 'blend', 
             'role': 'compos', 
             'hierarchy': 'episode',
             'series': {'code': 'S1'},
             'episode': {'code': 2},
             'rank': 'seq',
             'seq': {'code': 'MM', 'title': 'Media Montage'}})
            
        data = abx_episode_parser('S1E01-PC-PressConference-edit.kdenlive', [])
        self.assertDictEqual(data[1],
            {'filetype': 'kdenlive',
             'role': 'edit',
             'hierarchy': 'episode',
             'series': {'code': 'S1'},
             'episode': {'code': 1},
             'rank': 'seq',
             'seq': {'code': 'PC', 'title': 'Press Conference'}})
            
        data = abx_episode_parser('S1E01-LA-Launch.kdenlive', [])
        self.assertDictEqual(data[1],
            {'filetype': 'kdenlive',
             'role': 'edit',
             'hierarchy': 'episode',
             'series': {'code': 'S1'},
             'episode': {'code': 1},
             'rank': 'seq',
             'seq': {'code': 'LA', 'title': 'Launch'}})


    def test_parsing_filenames_w_schema_parser(self):        
        abx_schema_parser = file_context.NameParsers['abx_schema'](
            schemas=self.TESTSCHEMAS, definitions=self.TESTDEFS)
        
        data = abx_schema_parser('S1E01-SF-4-SoyuzDMInt-cam.blend',
                namepath=self.TESTNAMEPATHS[0])
        self.assertDictEqual(data[1],
            {'filetype': 'blend',
             'comment': None,
             'role': 'cam',
             'title': 'SoyuzDMInt',
             'series': {'code': 'S1'},
             'episode': {'code': '01'},
             'sequence': {'code': 'SF'},
             'block': {'code': '4', 'title':'SoyuzDMInt'},
             'rank': 'block'}
             )
        
        data = abx_schema_parser('S1E02-MM-MediaMontage-compos.blend',
                namepath=self.TESTNAMEPATHS[1])
        self.assertDictEqual(data[1],
            {'filetype': 'blend',
             'comment': None,
             'role': 'compos',
             'title': 'MediaMontage',
             'series': {'code': 'S1'},
             'episode': {'code': '02'},
             'sequence': {'code': 'MM', 'title':'MediaMontage'},
             'rank': 'sequence'}
             )
        
        data = abx_schema_parser('S1E01-PC-PressConference-edit.kdenlive',
                namepath=self.TESTNAMEPATHS[2])
        self.assertDictEqual(data[1],
            {'filetype': 'kdenlive',
             'comment': None,
             'role': 'edit',
             'title': 'PressConference',
             'series': {'code': 'S1'},
             'episode': {'code': '01'},
             'sequence': {'code': 'PC', 'title':'PressConference'},
             'rank': 'sequence'}
             )     
        
        data = abx_schema_parser('S1E01-LA-Launch.kdenlive',
                namepath=self.TESTNAMEPATHS[3])
        self.assertDictEqual(data[1],
            {'filetype': 'kdenlive',
             'comment': None,
             'role': 'edit',
             'title': 'Launch',
             'series': {'code': 'S1'},
             'episode': {'code': '01'},
             'sequence': {'code': 'LA', 'title':'Launch'},
             'rank': 'sequence'}
             ) 
        
    def test_parsing_filenames_w_fallback_parser(self):        
        abx_fallback_parser = file_context.NameParsers['abx_fallback']()
        
        data = abx_fallback_parser('S1E01-SF-4-SoyuzDMInt-cam.blend', None)
        self.assertDictEqual(data[1],
            {'filetype': 'blend',
             'role': 'cam',
             'comment': None,
             'title': 'S1E01-SF-4-SoyuzDMInt',
             'code': 'S1e01Sf4Soyuzdmint'
            })
        
        data = abx_fallback_parser('S1E01-SF-4-SoyuzDMInt-cam~~2021-01.blend', None)
        self.assertDictEqual(data[1],
            {'filetype': 'blend',
             'role': 'cam',
             'comment': '2021-01',
             'title': 'S1E01-SF-4-SoyuzDMInt',
             'code': 'S1e01Sf4Soyuzdmint'
            })        
        
        
        data = abx_fallback_parser('S1E02-MM-MediaMontage-compos.blend', None)
        self.assertDictEqual(data[1],
            {'filetype':'blend',
             'role':'compos',
             'comment': None,
             'title': 'S1E02-MM-MediaMontage',
             'code': 'S1e02MmMediamontage'
            })
        
        data = abx_fallback_parser('S1E01-PC-PressConference', None)
        self.assertDictEqual(data[1],
            {'filetype': None,
             'role': None,
             'comment': None,
             'title': 'S1E01-PC-PressConference',
             'code': 'S1e01PcPressconference'
            })
        
        
class FileContext_Implementation_UnitTests(unittest.TestCase):
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')
    
    def test_filecontext_finds_and_loads_file(self):
        fc = file_context.FileContext(self.TESTPATH)
        
#         print('\ntest_filecontext_finds_and_loads_file')
#         print(fc.get_log_text('INFO'))
#         print(dir(self))
        
        self.assertEqual(fc.filename, 'A.001-LP-1-BeginningOfEnd-anim.txt')
        self.assertEqual(fc.root, os.path.join(self.TESTDATA, 'myproject'))
        self.assertListEqual(fc.folders,
            ['myproject', 'Episodes', 'A.001-Pilot', 'Seq', 'LP-LastPoint'])
        
    def test_filecontext_gets_correct_yaml_for_file(self):
        fc = file_context.FileContext(self.TESTPATH)
        # Look for data from three expected YAML files:    
        # From the project YAML file:
        self.assertEqual(fc.provided_data['definitions']['omit_ranks']['scene'], 3)        
        # From the sequence directory YAML file:
        self.assertEqual(fc.provided_data['project_unit'][-2]['name'], 'Last Point')        
        # From the sidecar YAML file:
        self.assertEqual(fc.provided_data['project_unit'][-1]['code'], 1)
        
    def test_filecontext_gets_correct_filename_info(self):
        fc = file_context.FileContext(self.TESTPATH)
        self.assertEqual(fc.filetype, 'txt')
        self.assertEqual(fc.role, 'anim')
        self.assertEqual(fc.title, 'BeginningOfEnd')
        self.assertEqual(fc.comment, None)
        
    def test_filecontext_abx_fields_include_default(self):
        fc0 = file_context.FileContext()
        fc1 = file_context.FileContext('')
        fc2 = file_context.FileContext(self.TESTPATH)
        
        for fc in (fc0, fc1, fc2):
            self.assertIn('render_profiles', fc.abx_fields)
            
                
            
class FileContext_API_UnitTests(unittest.TestCase):
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')    
    
    def setUp(self):
        self.fc = file_context.FileContext(self.TESTPATH)

    def test_filecontext_API_namepath(self):
        self.assertListEqual( self.fc.namepath, ['myproject', 'A', 1, 'LP', 1])
        
    def test_filecontext_API_rank(self):
        self.assertEqual(self.fc.rank, 'block')
        
    def test_filecontext_API_code(self):
        self.assertEqual(self.fc.code, 1)
        
    def test_filecontext_API_name(self):
        self.assertEqual(self.fc.name, 'BeginningOfEnd')
        
    def test_filecontext_API_designation(self):
        self.assertEqual(self.fc.designation,
            'myproject-A.001-LP-1')
        
    def test_filecontext_API_fullname(self):
        self.assertEqual(self.fc.fullname, 'myproject-A.001-LP-1-BeginningOfEnd')
                    
    def test_filecontext_API_shortname(self):
        self.assertEqual(self.fc.shortname, 'A.001-LP-1-BeginningOfEnd')
        
    def test_filecontext_API_scene_name(self):
        self.assertEqual(self.fc.get_scene_name('Test'), 'LP-1 Test')
        
    def test_filecontext_API_render_root(self):
        self.assertEqual(os.path.abspath(self.fc.render_root),
                         os.path.abspath(os.path.join(self.TESTDATA,
                        'myproject/Episodes/A.001-Pilot/Renders')))
        
    def test_filecontext_API_get_render_path(self):
        self.assertEqual(os.path.abspath(self.fc.get_render_path(suffix='T')),
                         os.path.abspath(os.path.join(self.TESTDATA,
                            'myproject', 'Episodes', 'A.001-Pilot', 'Renders',
                            'T', 'A.001-LP-1', 'A.001-LP-1-T-f#####.png')))
        
    def test_filecontext_API_new_name_context_explicit(self):
        nc = self.fc.new_name_context(shot='A')
        self.assertEqual(nc.get_scene_name('Exp'), 'LP-1-A Exp')
        
    def test_filecontext_API_new_name_context_implicit(self):
        nc = self.fc.new_name_context(rank='shot')
        self.assertEqual(nc.get_scene_name('Imp'), 'LP-1-A Imp')
        
        
class NameContext_API_Tests(unittest.TestCase):
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TESTPATH = os.path.join(TESTDATA, 'myproject/Episodes/' +
                'A.001-Pilot/Seq/LP-LastPoint/' +
                'A.001-LP-1-BeginningOfEnd-anim.txt')    
    
    def setUp(self):
        fc = file_context.FileContext(self.TESTPATH)
        self.nc = fc.new_name_context(rank='shot', shot='A')
        
    def test_namecontext_reports_correct_rank(self):
        self.assertEqual(self.nc.rank, 'shot')
        
    def test_namecontext_reports_correct_code(self):
        self.assertEqual(self.nc.code, 'A')
        
    def test_namecontext_reports_correct_namepath(self):
        self.assertEqual(self.nc.namepath, ['myproject', 'A', 1, 'LP', 1, None, 'A'])
    

class FileContext_FailOver_Tests(unittest.TestCase):
    """
    Tests of how well FileContext copes with imperfect data.
    
    It's very likely that ABX will encounter projects that aren't
    set up perfectly (or at all), and we don't want it to crash
    in that situation, but rather fail gracefully or even work
    around the problem.
    """
    TESTDATA = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'testdata'))
    
    TEST_EMPTY_PROJECT = os.path.join(TESTDATA, 'empty')
    
    TEST_NONEXISTENT_PATH = os.path.join(TESTDATA,
        'empty', 'Non', 'Existing', 'F', 'F-1-NonExisting-anim.blend')
    
    TEST_NO_YAML = os.path.join(TESTDATA,
        'yamlless', 'Episodes', 'Ae1-Void', 'Seq', 'VN-VagueName',
        'Ae1-VN-1-VoidOfData-anim.txt')
    
    TEST_MINIMAL_YAML = os.path.join(TESTDATA,
        'yaminimal', 'Episodes', 'Ae1-Void', 'Seq', 'VN-VagueName',
        'Ae1-VN-1-VoidOfData-anim.txt')
    
    def test_filecontext_finds_default_yaml(self):
        self.assertIn('abx_default', file_context.DEFAULT_YAML)
    
    def test_filecontext_no_project_path(self):
        fc = file_context.FileContext()
        self.assertFalse(fc.file_exists)
        self.assertFalse(fc.folder_exists)
        self.assertIn('abx_default', fc.provided_data)
        # What to test?
        # The main thing is that it doesn't crash.
    
    def test_filecontext_failover_empty_project(self):
        fc = file_context.FileContext(self.TEST_EMPTY_PROJECT)
        self.assertFalse(fc.file_exists)
        self.assertTrue(fc.folder_exists)
        self.assertIn('abx_default', fc.provided_data)
        
    def test_filecontext_failover_nonexisting_file(self):
        fc = file_context.FileContext(self.TEST_NONEXISTENT_PATH)
        self.assertFalse(fc.file_exists)
        self.assertFalse(fc.folder_exists)
        self.assertIn('abx_default', fc.provided_data)
        
    def test_filecontext_failover_no_yaml(self):
        fc = file_context.FileContext(self.TEST_NO_YAML)
        self.assertIn('abx_default', fc.provided_data)
        # It finds the backstop root YAML in the testdata:
        self.assertEqual(fc.root, self.TESTDATA)
        
    def test_filecontext_failover_minimal_yaml(self):
        fc = file_context.FileContext(self.TEST_MINIMAL_YAML)
        self.assertIn('abx_default', fc.provided_data)
        
