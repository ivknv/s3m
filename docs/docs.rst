Documentation
=============

.. automodule:: s3m
   :members:

Using ``with`` statement
########################

The `Connection` (as well as `Cursor`) object supports the ``with`` statement.
It acquires the locks which will result either in the current thread waiting for other threads
or making other threads wait until the current thread exits the ``with`` block.

.. code:: python

    conn = s3m.connect("database.db", ...)
    ...

    with conn: # This blocks other threads
        conn.execute(<something>)
        conn.execute(<something else>)

    # The other threads are no longer blocked
