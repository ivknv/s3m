#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
S3M - sqlite3 wrapper for multithreaded applications
"""

# S3M - sqlite3 wrapper for multi-threaded applications
# Copyright (C) 2018 Ivan Konovalov
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library. If not, see <http://www.gnu.org/licenses/>.

import os
import sqlite3
import threading
import weakref

__all__ = ["connect", "Connection", "Cursor", "S3MError", "LockTimeoutError"]

__version__ = "1.1.0"

# Global lock storage
DB_STATES = {}

# Locks access to DB_STATES
DICT_LOCK = threading.Lock()

class S3MError(Exception):
    """The base class of all the other exceptions in this module"""
    pass

class LockTimeoutError(S3MError):
    """Thrown when Lock.acquire() took too long"""

    def __init__(self, conn, msg=None):
        if msg is None:
            if conn is None or not isinstance(conn.lock_timeout, (int, float)):
                msg = "Lock timeout exceeded"
            else:
                msg = "Lock timeout exceeded (> %s)" % (conn.lock_timeout)

        S3MError.__init__(self, msg)

        self.connection = conn

def normalize_path(path):
    """
    >>> normalize_path("/a/b/c/")
    '/a/b/c'
    >>> normalize_path("/a/b/c")
    '/a/b/c'
    >>> normalize_path("/a/b/c////////")
    '/a/b/c'
    >>> normalize_path("///a/b/c")
    '/a/b/c'
    >>> normalize_path("/a/././b/../b/c/")
    '/a/b/c'
    >>> normalize_path(":memory:")
    ':memory:'
    """
    if path == ":memory:":
        return path

    return os.path.normcase(os.path.normpath(os.path.realpath(path)))

class FakeLock(object):
    """Only pretends to be a lock, doesn't do anything"""

    def acquire(self, *args, **kwargs):
        return True

    def release(self, *args, **kwargs):
        return True

class DBState(object):
    """Stores database locks and the currently active connection"""

    def __init__(self, connection=None):
        # Blocks parallel database operations
        self.lock = threading.RLock()

        # Blocks parallel transactions
        self.transaction_lock = threading.Lock()
        self.active_connection = connection

class FakeDBState(object):
    """Like DBState but uses FakeLock"""

    def __init__(self, connection=None):
        self.lock = FakeLock()
        self.transaction_lock = FakeLock()
        self.active_connection = None

def chain(f):
    def wrapper(self, *args, **kwargs):
        f(self, *args, **kwargs)
        return self

    wrapper.__doc__ = f.__doc__

    return wrapper

class Cursor(object):
    """The cursor class, analogous to :any:`sqlite3.Cursor`."""

    def __init__(self, connection):
        self.closed = False
        self._cursor = None
        self._connection = weakref.ref(connection)

        self._cursor = connection.connection.cursor()

    def __enter__(self):
        self.connection.acquire()

    def __exit__(self, *args, **kwargs):
        self.connection.release()

    def __del__(self):
        self.close()

    def close(self):
        """Close the cursor"""

        if self.closed or self.connection.closed:
            return

        self._cursor.close()
        self.closed = True

    @chain
    def execute(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.execute`

           :returns: self
        """

        with self:
            self._cursor.execute(*args, **kwargs)

    @chain
    def executemany(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.executemany`

           :returns: self
        """

        with self:
            self._cursor.executemany(*args, **kwargs)

    @chain
    def executescript(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.executescript`

           :returns: self
        """

        with self:
            self._cursor.executescript(*args, **kwargs)

    def fetchone(self):
        """Analogous to :any:`sqlite3.Cursor.fetchone`"""

        with self:
            return self._cursor.fetchone()

    def fetchmany(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.fetchmany`"""

        with self:
            return self._cursor.fetchmany(*args, **kwargs)

    def fetchall(self):
        """Analogous to :any:`sqlite3.Cursor.fetchall`"""

        with self:
            return self._cursor.fetchall()

    @property
    def rowcount(self):
        """Analogous to :any:`sqlite3.Cursor.rowcount`"""

        return self._cursor.rowcount

    @property
    def lastrowid(self):
        """Analogous to :any:`sqlite3.Cursor.lastrowid`"""

        return self._cursor.lastrowid

    @property
    def arraysize(self):
        """Analogous to :any:`sqlite3.Cursor.arraysize`"""

        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def description(self):
        """Analogous to :any:`sqlite3.Cursor.description`"""

        return self._cursor.description

    @property
    def connection(self):
        """Connection used by the cursor"""

        return self._connection()

class Connection(object):
    """The connection class. It won't let multiple database operations execute in parallel.
       It can also block parallel transactions (with lock_transactions=True).

       `with` statement is also supported, it acquires the locks, thus blocking all the competing threads.
       This can be useful to ensure that database queries will complete in the specified order.

       :param path: Path to the database
       :param lock_transactions: If True, parallel transactions will be blocked
       :param lock_timeout: Maximum amount of time the connection is allowed to wait for a lock.
                            If the timeout is exceeded, LockTimeoutError will be thrown.
                            -1 disables the timeout.
       :param single_cursor_mode: Use only one cursor (default: True)
    """

    def __init__(self, path, lock_transactions=True, lock_timeout=-1, single_cursor_mode=False, *args, **kwargs):
        self.path = normalize_path(path)
        self.connection = None
        self._cursor = None
        self.closed = False
        self.db_state = None
        self.single_cursor_mode = single_cursor_mode

        # Maximum amount of time the connection is allowed to wait when acquiring the lock.
        self.lock_timeout = lock_timeout

        # Used in with block
        self.was_in_transaction = False

        # Should parallel transactions be allowed?
        self.lock_transactions = lock_transactions

        # This lock is used to control sharing of the connection between threads
        self.personal_lock = threading.RLock()

        # Number of active with blocks
        self.with_count = 0

        if self.path == ":memory:":
            # No two :memory: connections point to the same database => locks are not needed
            self.db_state = FakeDBState()
        else:
            with DICT_LOCK:
                self.db_state = DB_STATES.get(self.path)

                # If the object doesn't already exist, make a new one
                if self.db_state is None:
                    self.db_state = DBState()

                    def func(path):
                        with DICT_LOCK:
                            DB_STATES.pop(path)

                    # Automatically cleanup DB_STATES
                    DB_STATES[self.path] = weakref.finalize(self.db_state, func, self.path)
                else:
                    self.db_state = self.db_state.peek()[0]

        self.connection = sqlite3.connect(self.path, *args, **kwargs)

        if self.single_cursor_mode:
            self._cursor = Cursor(self)

    def cursor(self):
        """Analogous to :any:`sqlite3.Connection.cursor`"""

        if self.single_cursor_mode:
            if self._cursor is None:
                raise sqlite3.ProgrammingError("Cannot operate on a closed database.")

            return self._cursor

        return Cursor(self)

    @property
    def in_transaction(self):
        """Analogous to :any:`sqlite3.Connection.in_transaction`"""

        if self.connection is not None:
            return self.connection.in_transaction

        raise sqlite3.ProgrammingError("Cannot operate on a closed database.")

    @property
    def isolation_level(self):
        """Analogous to :any:`sqlite3.Connection.isolation_level`"""

        return self.connection.isolation_level

    @isolation_level.setter
    def isolation_level(self, value):
        self.connection.isolation_level = value

    @property
    def row_factory(self):
        """Analogous to :any:`sqlite3.Connection.row_factory`"""

        return self.connection.row_factory

    @row_factory.setter
    def row_factory(self, value):
        self.connection.row_factory = value

    @property
    def text_factory(self):
        """Analogous to :any:`sqlite3.Connection.text_factory`"""

        return self.connection.text_factory

    @property
    def total_changes(self):
        return self.connection.total_changes

    def __enter__(self):
        self.acquire()

    def __exit__(self, *args, **kwargs):
        self.release()

    def acquire(self, lock_transactions=None):
        """
            Acquire the connection locks.

            :param lock_transactions: `bool`, acquire the transaction lock
                                      (`self.lock_transactions` is the default value)
        """

        if not self.personal_lock.acquire(timeout=self.lock_timeout):
            raise LockTimeoutError(self)

        self.with_count += 1

        if lock_transactions is None:
            lock_transactions = self.lock_transactions

        if lock_transactions and self.db_state.active_connection is not self:
            if not self.db_state.transaction_lock.acquire(timeout=self.lock_timeout):
                self.personal_lock.release()
                raise LockTimeoutError(self)

            self.db_state.active_connection = self

        if not self.db_state.lock.acquire(timeout=self.lock_timeout):
            self.personal_lock.release()

            if lock_transactions:
                self.db_state.active_connection = None
                self.transaction_lock.release()

            raise LockTimeoutError(self)

        try:
            # If the connection is closed, an exception is thrown
            in_transaction = self.in_transaction
        except sqlite3.ProgrammingError:
            in_transaction = False

        self.was_in_transaction = in_transaction

    def release(self, lock_transactions=None):
        """
            Release the connection locks.

            :param lock_transactions: `bool`, release the transaction lock
                                      (`self.lock_transactions` is the default value)
        """

        self.personal_lock.release()

        self.with_count -= 1

        if lock_transactions is None:
            lock_transactions = self.lock_transactions

        if not lock_transactions:
            self.db_state.lock.release()
            return

        try:
            # If the connection is closed, an exception is thrown
            in_transaction = self.in_transaction
        except sqlite3.ProgrammingError:
            in_transaction = False

        # The transaction lock should be released only if:
        # 1) the connection was previously in a transaction and now it isn't
        # 2) the connection wasn't previously in a transaction and still isn't
        if (self.was_in_transaction and not in_transaction) or not in_transaction:
            if self.with_count == 0: # This is for nested with statements
                self.db_state.active_connection = None
                self.db_state.transaction_lock.release()

        self.db_state.lock.release()

    def __del__(self):
        self.close()

    def close(self):
        """Close the connection"""

        if self.closed:
            return

        # Make sure no one minds the connection to be closed
        # This will help avoid MemoryError in other threads,
        # they will get sqlite3.ProgrammingError instead
        if not self.personal_lock.acquire(timeout=self.lock_timeout):
            raise LockTimeoutError(self)

        try:
            try:
                if self.in_transaction:
                    self.db_state.active_connection = None
                    self.db_state.transaction_lock.release()
            except sqlite3.ProgrammingError:
                pass

            if self._cursor is not None and not self._cursor.closed:
                self._cursor._cursor.close()
                self._cursor.closed = True

            if self.connection is not None:
                self.connection.close()

            self.closed = True
        finally:
            self.personal_lock.release()

    def execute(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.execute`"""

        return self.cursor().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.executemany`"""

        return self.cursor().executemany(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Cursor.executescript`"""

        return self.cursor().executescript(*args, **kwargs)

    def commit(self):
        """Analogous to :any:`sqlite3.Connection.commit`"""

        with self:
            self.connection.commit()

    def rollback(self):
        """Analogous to :any:`sqlite3.Connection.rollback`"""

        with self:
            self.connection.rollback()

    def fetchone(self):
        """
            Analogous to :any:`sqlite3.Cursor.fetchone`.
            
            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.fetchone() while not in single cursor mode")

        return self._cursor.fetchone()

    def fetchmany(self, *args, **kwargs):
        """
            Analogous to :any:`sqlite3.Cursor.fetchmany`.

            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.fetchmany() while not in single cursor mode")

        return self._cursor.fetchmany(*args, **kwargs)

    def fetchall(self):
        """
            Analogous to :any:`sqlite3.Cursor.fetchall`.
        
            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.fetchall() while not in single cursor mode")

        return self._cursor.fetchall()

    @property
    def rowcount(self):
        """
            Analogous to :any:`sqlite3.Cursor.rowcount`.
            
            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.rowcount() while not in single cursor mode")

        return self._cursor.rowcount

    @property
    def lastrowid(self):
        """
            Analogous to :any:`sqlite3.Cursor.lastrowid`.

            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.lastrowid() while not in single cursor mode")

        return self._cursor.lastrowid

    @property
    def arraysize(self):
        """
            Analogous to :any:`sqlite3.Cursor.arraysize`

            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.arraysize() while not in single cursor mode")

        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def description(self):
        """
            Analogous to :any:`sqlite3.Cursor.description`

            Works only in single cursor mode.
        """

        if not self.single_cursor_mode:
            raise S3MError("Calling Connection.description() while not in single cursor mode")

        return self._cursor.description

    def interrupt(self):
        """Analogous to :any:`sqlite3.Connection.interrupt`"""

        return self.connection.interrupt()

    def create_function(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.create_function`"""

        self.connection.create_function(*args, **kwargs)

    def create_aggregate(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.create_aggregate`"""

        self.connection.create_aggregate(*args, **kwargs)

    def create_collation(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.create_collation`"""

        self.connection.create_collation(*args, **kwargs)

    def set_authorizer(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.set_authorizer`"""

        self.connection.set_authorizer(*args, **kwargs)

    def set_progress_handler(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.set_progress_handler`"""
        self.connection.set_progress_handler(*args, **kwargs)

    def set_trace_callback(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.set_trace_callback`"""

        self.connection.set_trace_callback(*args, **kwargs)

    def enable_load_extension(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.enable_load_extension`"""

        self.connection.enable_load_extension(*args, **kwargs)

    def load_extension(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.load_extension`"""

        self.connection.load_extension(*args, **kwargs)

    def iterdump(self, *args, **kwargs):
        """Analogous to :any:`sqlite3.Connection.iterdump`"""

        return self.connection.iterdump()

def connect(path, lock_transactions=True, lock_timeout=-1, single_cursor_mode=False,
            factory=Connection, *args, **kwargs):
    """Analogous to sqlite3.connect()

       :param path: Path to the database
       :param lock_transactions: If `True`, parallel transactions will be blocked
       :param lock_timeout: Maximum amount of time the connection is allowed to wait for a lock.
                            If the timeout i exceeded, :any:`LockTimeoutError` will be thrown.
                            -1 disables the timeout.
       :param single_cursor_mode: Use only one cursor (default: `True`)
       :param factory: Connection class (default: :any:`Connection`)
    """

    return factory(path,
                   lock_transactions=lock_transactions,
                   lock_timeout=lock_timeout,
                   single_cursor_mode=single_cursor_mode,
                   *args, **kwargs)
