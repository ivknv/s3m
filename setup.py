#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os
from setuptools import setup

module_dir = os.path.dirname(__file__)

with codecs.open(os.path.join(module_dir, "README.rst"), encoding="utf8") as f:
    long_description = f.read()

setup(name="s3m",
      version="1.1.0",
      py_modules=["s3m"],
      description="sqlite3 wrapper for multithreaded applications",
      long_description=long_description,
      author="Ivan Konovalov",
      author_email="ivknv0@gmail.com",
      url="https://github.com/ivknv/s3m",
      project_urls={"Source code": "https://github.com/ivknv/s3m",
                    "Documentation": "https://s3m.readthedocs.io"},
      license="LGPLv3",
      python_requires=">=3",
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Topic :: Database",
          "Topic :: Software Development :: Libraries",
          "Topic :: Software Development :: Libraries :: Python Modules"],
      keywords="sqlite3 sqlite multithreading thread")
