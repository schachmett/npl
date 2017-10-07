#!/usr/bin/env python3

from setuptools import setup
from npl import __version__


setup(name="npl",
      version=__version__,
      description="a shit program to display XPS data"
      author="Simon Fischer"
      author_email="sfischer@ifp.uni-bremen.de"
      license="GPLv3",
      packages=["npl"],
      zip_safe=False
      requires=[
        "configparser",
        "json",
        "gi",
        "matplotlib",
        "sqlite3",
        "pickle",
        "numpy"
        ],
      classifiers=[
        "Development Status ::2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Environment :: X11 Applications :: GTK",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Scientific/Engineering :: Physics"
        ])
