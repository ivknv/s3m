# S3M
S3M - is a sqlite3 wrapper for multithreaded python applications.

# Table of contents
1. [multithreading](#multithreading-support)
2. [Installation](#installation)
3. [Usage](#usage)

## Multithreading support
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
The usage is similar to `sqlite3` with a few exceptions.

### There is no cursor()
You never have to use cursors. `s3m.Connection` object is completely self-sufficent, it has the methods of both a connection and a cursor.

### Connections can be freely shared between threads (given `check_same_thread=False`)
Multiple threads can use the same connection at the same time without any problems, that is, assuming that the connection was created with `check_same_thread=False`.
