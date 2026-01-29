import unittest
import sqlite3
from QueryManager import QueriesSQLite  # Import the QueriesSQLite class

class TestQueriesSQLite(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database for testing
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        # Create some test tables
        self.cursor.execute("CREATE TABLE test_table1 (id INTEGER PRIMARY KEY, name TEXT)")
        self.cursor.execute("CREATE TABLE test_table2 (id INTEGER PRIMARY KEY, name TEXT)")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_count_procedures_in_schema(self):
        queries = QueriesSQLite()
        schema = 'test'
        query = queries.count_procedures_in_schema(schema)
        self.cursor.execute(query)
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 2)  # Assuming we have 2 tables with names starting with 'test'

if __name__ == '__main__':
    unittest.main()
