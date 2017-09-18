#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import sys
import threading
import unittest

import s3m

class S3MTestCase(unittest.TestCase):
    def setUp(self):
        self.n_connections = 25
        self.db_path = "s3m_test.db"

        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass

    def insert_func(self, *args, **kwargs):
        conn = self.connect_db(*args, **kwargs)
        if conn.path == ":memory:":
            self.assertFalse(conn.path in s3m.CONNECTION_LOCKS)
        else:
            self.assertIs(conn.lock, s3m.CONNECTION_LOCKS[s3m.normalize_path(conn.path)])

        queries = ["CREATE TABLE IF NOT EXISTS a(id INTEGER)",
                   "BEGIN TRANSACTION",
                   "INSERT INTO a VALUES(1)",
                   "INSERT INTO a VALUES(2)",
                   "INSERT INTO a VALUES(3)",
                   "COMMIT"]

        if os.environ.get("S3M_TEST_DEBUG"):
            for query in queries:
                print("%s: %s" % (threading.get_ident(), query))
                conn.execute(query)
        else:
            for query in queries:
                conn.execute(query)

        conn.close()

    def connect_db(self, path=None, *args, **kwargs):
        path = self.db_path if path is None else path
        kwargs.setdefault("isolation_level", None)
        return s3m.connect(path, *args, **kwargs)

    def setup_db(self, *args, **kwargs):
        threads = [threading.Thread(target=self.insert_func, args=args, kwargs=kwargs)
                   for i in range(self.n_connections)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def test_s3m(self):
        self.setup_db(self.db_path)
        conn = self.connect_db(self.db_path)
        conn.execute("SELECT id FROM a")
        result = conn.fetchall()
        self.assertEqual(result, [(1,), (2,), (3,)] * self.n_connections)

    def test_s3m_lock_transactions(self):
        conn1 = self.connect_db(self.db_path, lock_transactions=False, lock_timeout=0.5)
        conn2 = self.connect_db(self.db_path, lock_transactions=False, lock_timeout=0.5,
                                check_same_thread=False)

        def thread_func():
            conn2.execute("BEGIN TRANSACTION")
            conn2.execute("CREATE TABLE b(id INTEGER);")

        conn1.execute("BEGIN TRANSACTION")

        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        conn1.rollback()
        conn2.rollback()

    def test_s3m_lock_timeout(self):
        conn1 = self.connect_db(self.db_path, lock_timeout=0.01)
        conn2 = self.connect_db(self.db_path, lock_timeout=0.01)

        def thread_func():
            if self.assertRaises(s3m.LockTimeoutError, conn2.execute, "BEGIN TRANSACTION"):
                return
            conn2.execute("CREATE TABLE b(id INTEGER);")

        conn1.execute("BEGIN TRANSACTION")

        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        conn1.rollback()
        conn2.rollback()

    def test_in_memory1(self):
        self.setup_db(":memory:")

    def test_in_memory2(self):
        conn1 = self.connect_db(":memory:")
        conn2 = self.connect_db(":memory:")

        conn1.execute("BEGIN TRANSACTION")
        conn2.execute("BEGIN TRANSACTION")
        conn1.execute("CREATE TABLE a(id INTEGER)")
        conn2.execute("CREATE TABLE a(id INTEGER)")
        conn1.commit()
        conn2.commit()

    def test_sharing(self):
        conn = self.connect_db(":memory:", check_same_thread=False)

        conn.execute("CREATE TABLE a(id INTEGER)")
        conn.execute("BEGIN TRANSACTION")

        def func():
            for i in range(25):
                conn.execute("INSERT INTO a VALUES(?)", (i,))

        thread = threading.Thread(target=func)

        thread.start()
        func()
        thread.join()

        conn.commit()

        conn.execute("SELECT id FROM a")

        self.assertEqual(len(conn.fetchall()), 50)

    def test_close(self):
        # This doesn't work properly on windows
        if sys.platform.startswith("win"):
            return

        conn = self.connect_db(":memory:", check_same_thread=False)

        success = True
        message = None

        def func():
            nonlocal success, message

            try:
                for i in range(50):
                    conn.execute("SELECT 1")
            except BaseException as e:
                if not isinstance(e, sqlite3.ProgrammingError):
                    # sqlite3.ProgrammingError is ok
                    success = False
                    message = "%s: %s" % (type(e).__name__, e)

        threads = [threading.Thread(target=func) for i in range(25)]

        for thread in threads:
            thread.start()

        conn.close()

        for thread in threads:
            thread.join()

        self.assertTrue(success, message)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except FileNotFoundError:
            pass
