from setuptools import setup, find_packages

# The version is updated automatically with bumpversion
# Do not update manually
__version = '0.2.1-alpha'

long_description = """The Opus socket-server offers network bridge to
manipulate the OPUS Spectroscopy Software (BRUKER).
This server must be run in the same machine that the OPUS Spectroscopy
Software, the communication with the software is done via a named PIPE.
The Opus socket-server can execute  several Opus cmd in the PIPE in order to
reduce the communication between clients (macro mode)"""


classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Scientific/Engineering',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'Programming Language :: Python :: 2.7',
]


setup(
    name='opusserver',
    version=__version,
    packages=find_packages(),
    entry_points={
        'console_scripts':
            ['opusserver = opusserver.opusserver:run_opus_server']
    }, # METADATA
    author='Carlos Falcon',
    author_email='cfalcon@cells.es',
    maintainer='ctgensoft',
    maintainer_email='ctgensoft@cells.es',
    url='https://github.com/ALBA-Synchrotron/opusDS.git',
    keywords='APP',
    license='LGPL',
    description='Socket Server for OpusDS',
    long_description=long_description,
    classifiers=classifiers
)