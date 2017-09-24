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
The usage is similar to `sqlite3` with a few exceptions.

There is no cursor()
--------------------
You never have to use cursors. `s3m.Connection` object is completely self-sufficent, it has the methods of both a connection and a cursor.

Connections can be freely shared between threads (given `check_same_thread=False`)
----------------------------------------------------------------------------------
Multiple threads can use the same connection at the same time without any problems, that is, assuming that the connection was created with `check_same_thread=False`.
