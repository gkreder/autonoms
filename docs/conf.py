import os
import sys
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../src'))
sys.path.insert(0, os.path.abspath('../src/mochams'))



project = 'AutonoMS'
copyright = '2023, Gabriel Reder'
author = 'Gabriel Reder'
release = '0.0.1'


extensions = ['sphinx.ext.autodoc', 'sphinx_copybutton']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


html_theme = 'alabaster'
html_static_path = ['_static']
