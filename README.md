# S3M
S3M - is a sqlite3 wrapper for multi-threaded python applications.

# Table of contents
1. [Multi-threading](#multi-threading-support)
2. [Installation](#installation)
3. [Usage](#usage)
5. [Documentation](#documentation)
4. [Examples](#examples)

## Multi-threading support
S3M prevents multiple database operations (or transactions, can be disabled) from running at once.
That's basically the whole point of this library.

## Installation
```bash
pip install s3m
```

or

```bash
python setup.py install
```
There are no requirements.

## Usage
The usage is similar to `sqlite3` but with a few exceptions.

### There is no cursor()
You never have to use cursors. `s3m.Connection` object is completely self-sufficent, it has the methods of both a connection and a cursor.

### Connections can be freely shared between threads (given `check_same_thread=False`)
Multiple threads can use the same connection at the same time without any problems, that is, assuming that the connection was created with `check_same_thread=False`.

## Documentation
See `docs/index.html`

## Examples
```python
# Opens database and selects from some_table

import s3m

conn = s3m.connect("path/to/database.db")
conn.execute("SELECT * FROM some_table")
result = conn.fetchall()
print(result)
```

```python
# Inserts 10 random numbers in transaction in parallel

import random
import threading

import s3m

conn = s3m.connect("database.db", isolation_level=None, check_same_thread=False)
conn.execute("BEGIN TRANSACTION")

def thread_func():
    conn.execute("INSERT INTO numbers VALUES(?)", (random.randint(1, 100),))

threads = [threading.Thread(target=thread_func) for i in range(10)]

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

conn.commit()
```

```python
# Each thread connects to the same database, starts it's own transaction and inserts some numbers.
# All threads run in parallel

import threading

import s3m

conn = s3m.connect("test.db", isolation_level=None)
conn.execute("CREATE TABLE test(id INTEGER)")

def thread_func():
    conn = s3m.connect("test.db", isolation_level=None)
    conn.execute("BEGIN TRANSACTION")
    conn.execute("INSERT INTO test VALUES(1)")
    conn.execute("INSERT INTO test VALUES(2)")
    conn.execute("INSERT INTO test VALUES(3)")
    conn.commit()

threads = [threading.Thread(target=thread_func) for i in range(10)]

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
```


```python
# Each thread connects to the same database, then inserts some numbers while blocking other threads.
# All threads run in parallel

import threading

import s3m

conn = s3m.connect("test.db", isolation_level=None)
conn.execute("CREATE TABLE test(id INTEGER)")

def thread_func():
    conn = s3m.connect("test.db", isolation_level=None)
    
    with conn: # This blocks other threads
        conn.execute("INSERT INTO test VALUES(1)")
        conn.execute("INSERT INTO test VALUES(2)")
        conn.execute("INSERT INTO test VALUES(3)")

threads = [threading.Thread(target=thread_func) for i in range(10)]

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
```
