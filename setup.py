#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OMERO database management plugin
"""

import setuptools


setuptools.setup(
    name='omero-server-setup',
    author='Simon Li',
    author_email='spli@dundee.ac.uk',
    description='OMERO database management plugin',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license='GPLv2',
    url='https://github.com/manics/omero-server-setup',
    packages=[
        'omero_database',
        'omero.plugins',
    ],
    setup_requires=[
        'setuptools_scm',
    ],
    install_requires=[
        'omero-py>=5.6.0',
    ],
    use_scm_version={
        'write_to': 'omero_database/_version.py',
    },
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2'
        ' (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    tests_require=[
        'pytest',
        'mox3',
    ],
)
