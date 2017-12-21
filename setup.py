#!/usr/bin/env python3
""" installs npl """

from setuptools import setup

from npl import __version__


def readme():
    """ return readme for long description """
    with open("README.rst") as readmefile:
        return readmefile.read()

setup(name="npl",
      version=__version__,
      description="a shit program to display XPS data",
      long_description=readme(),
      author="Simon Fischer",
      author_email="sfischer@ifp.uni-bremen.de",
      license="GPLv3",
      url="https://github.com/schachmett/npl",
      packages=["npl"],
      zip_safe=False,
      requires=[
          "configparser",
          "cairocffi",
          "json",
          "gi",
          "matplotlib",
          "sqlite3",
          "pickle",
          "numpy"],
      classifiers=[
          "Development Status ::2 - Pre-Alpha",
          "Programming Language :: Python :: 3",
          "Environment :: X11 Applications :: GTK",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Topic :: Scientific/Engineering :: Physics"],
      include_package_data=True)
