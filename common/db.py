import os
from sqlite3 import dbapi2 as sqlite3

class GarageDb:
    def __init__(self, instance_path, resource_path):
        self.db_file = os.path.join(instance_path, 'history.db')
        self.init_file = os.path.join(resource_path, 'schema.sql')

        # Run init script to ensure database structure
        conn = self.get_connection()
        with open(self.init_file, mode='r') as f:
            conn.cursor().executescript(f.read())
        conn.commit()
        conn.close()

    def get_connection(self):
        rv = sqlite3.connect(self.db_file)
        rv.row_factory = sqlite3.Row
        return rv

    def record_event(self, user_agent: str, login: str, event: str, description: str):
        conn = self.get_connection()
        conn.execute('insert into entries (UserAgent, Login, Event, Description) values (?, ?, ?, ?)',
                     [user_agent, login, event, description])
        conn.commit()
        conn.close()

    def read_history(self):
        conn = self.get_connection()
        cur = conn.execute('select datetime(timestamp, \'localtime\') as timestamp, event, description from entries order by timestamp desc')
        records = cur.fetchall()
        conn.close()
        return records
