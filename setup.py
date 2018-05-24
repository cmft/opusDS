#!/usr/bin/env python

from setuptools import setup, find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '0.2.0-alpha'

long_description = """This is a DS to remotely manipulate the OPUS
Spectroscopy Software (BRUKER) from Linux to Windows.

The device server send OPUS commands to a socket sever (opusserver) included in
the project)  that must be run in the same machine that the OPUS Spectroscopy
Software, the server set the communication with the software via a named PIPE."""


classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Scientific/Engineering',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'Programming Language :: Python :: 2.7',
]

setup(
    name='opusDS',
    version=__version,
    packages=find_packages(),
    entry_points={
        'console_scripts': ['opusDS = opusds.opusds:runDS']
    }, # METADATA
    author='Carlos Falcon',
    author_email='cfalcon@cells.es',
    include_package_data=True,
    license='LGPL',
    description='Opus Device Server',
    long_description=long_description,
    requires=['setuptools (>=1.1)'],
    install_requires=['PyTango'],
    classifiers=classifiers
)
