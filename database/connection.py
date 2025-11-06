import pymysql

def get_db_connection():
    """Create and return a new database connection."""
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",   # leave empty if no password
        database="studybuddy_db",
        cursorclass=pymysql.cursors.DictCursor
    )
