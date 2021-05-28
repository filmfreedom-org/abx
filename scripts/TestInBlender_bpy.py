#
# This testrunner is based on a Stack Overflow answer:
# https://stackoverflow.com/questions/1732438/how-do-i-run-all-python-unit-tests-in-a-directory
#
ABX_PATH = '/project/terry/Dev/Git/abx'

import os, unittest

loader = unittest.TestLoader()
start_dir = os.path.join(ABX_PATH, 'tests')
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)

