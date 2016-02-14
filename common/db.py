import os
from sqlite3 import dbapi2 as sqlite3

class GarageDb:
    def __init__(self, instance_path, resource_path):
        self.db_file = os.path.join(instance_path, 'history.db')
        self.init_file = os.path.join(resource_path, 'schema.sql')

        # Now connect to database
        rv = sqlite3.connect(self.db_file)
        rv.row_factory = sqlite3.Row
        self.__conn = rv

        # Run init script
        with open(self.init_file, mode='r') as f:
            self.__conn.cursor().executescript(f.read())
        self.__conn.commit()

    def __del__(self):
        self.close()

    def close(self):
        if self.__conn is not None:
            self.__conn.close()
            self.__conn = None

    def record_event(self, user_agent: str, login: str, event: str, description: str):
        self.__conn.execute('insert into entries (UserAgent, Login, Event, Description) values (?, ?, ?, ?)',
                            [user_agent, login, event, description])
        self.__conn.commit()

    def read_history(self):
        cur = self.__conn.execute('select datetime(timestamp, \'localtime\') as timestamp, event, description from entries order by timestamp desc')
        return cur.fetchall()
