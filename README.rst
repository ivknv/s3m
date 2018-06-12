S3M
===
S3M - is a sqlite3 wrapper for multithreaded python applications.

Table of contents
#################

1. Multithreading_
2. Documentation_
3. Installation_
4. Usage_

.. _Multithreading:

Multithreading support
######################

S3M prevents multiple database operations (or transactions, can be disabled) from running at once.
That's basically the whole point of this library.

.. _Documentation:

Documentation
#############
.. _Read the Docs: http://s3m.readthedocs.io

Documentation is available at `Read the Docs`_

.. _Installation:

Installation
############

.. code:: sh

    pip install s3m


or

.. code:: sh

    python setup.py install

There are no requirements.

.. _Usage:

Usage
#####

The usage is pretty much the same as with built-in `sqlite3`.
