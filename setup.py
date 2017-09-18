#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name="s3m",
      version="1.0.2",
      py_modules=["s3m"],
      description="sqlite3 wrapper for multi-threaded applications",
      author="Ivan Konovalov",
      author_email="rvan.mega@gmail.com",
      url="https://github.com/SPython/s3m",
      license="GPLv3",
      python_requires=">=3",
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Topic :: Database",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules"],
      keywords="sqlite3 sqlite multithreading thread")
