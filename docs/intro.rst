Introduction
============

One of the problems of the built-in `sqlite3` module is that doesn't work very well with multithreading.
S3M - is a wrapper of `sqlite3` that allows you to easily do multithreading:

* It locks parallel database operations so that only one can run at a time.
* It can also lock transactions (enabled by default) so that only one transaction can be active at a time.
* You won't get an `OperationalError` saying that the database is locked.
  All the database operations will just run in a queue.

Keep in mind that this library can only help you with **threads**, not **processes**.

What else is different from `sqlite3`?
######################################
* You can freely share connections between threads (not that you have to), given ``check_same_thread=False``.
* You can use the ``with`` statement with the connection object to acquire the locks.

Example
#############################################

.. code:: python

    import random
    import threading

    # Try replacing 's3m' with 'sqlite3' and see what happens
    import s3m

    # Open the database file,
    # isolation_level=None is needed to prevent sqlite3 from starting transactions on its own
    conn = s3m.connect("s3m_example.db", isolation_level=None)

    # Create table if it doesn't already exist
    conn.execute("CREATE TABLE IF NOT EXISTS numbers(number INTEGER)")

    def thread_func():
        conn = s3m.connect("s3m_example.db", isolation_level=None)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO numbers VALUES(?)", (random.randint(1, 100),))

        # Imagine there's some intense database work going on
        time.sleep(1)

        conn.commit()

    # Make 10 threads
    threads = [threading.Thread(target=thread_func) for i in range(10)]

    # Start them
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # Now let's look at what we got
    result = conn.execute("SELECT * FROM numbers").fetchall()
    print(result)

As you can see from this example, the usage is pretty much the same as with built-in `sqlite3`.
