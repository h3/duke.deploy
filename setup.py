from setuptools import setup
import os, sys

version = '0.0.1'

install_requires = [
  'setuptools',
  'zc.buildout',
]

try:
    import xml.etree
except ImportError:
    install_requires.append('elementtree')

try:
    import argparse
except ImportError:
    install_requires.append('argparse')

extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

setup(name='duke.deploy',
      version=version,
      description="A zc.buildout extension to ease the deployment of django projects.",
      long_description=open("README.rst").read(),#+ "\n\n" +
                      #open(os.path.join("docs", "HELP.txt")).read() +
                      #open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Buildout",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Maxime Haineault',
      author_email='max@motion-m.ca',
      url='https://github.com/h3/duke.deploy',
      license='BSD',
      packages=['duke', 'duke.deploy'],
      package_dir = {'': 'src'},
      namespace_packages=['duke'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
     #test_suite='dukedeploydjango.tests',
      entry_points="""
      [console_scripts]
      develop = duke.deploy.deploy:deploy
      [zc.buildout.extension]
      default = duke.deploy.extension:extension
      """,
      **extra
      )
