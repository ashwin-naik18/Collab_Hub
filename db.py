import mysql.connector
from mysql.connector import Error, pooling
from config import Config
from contextlib import contextmanager

connection_pool = None


def init_db_pool():
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="collabhub_pool",
            pool_size=5,
            pool_reset_session=True,    
            **Config.DB_CONFIG
        )
        print("Database connection pool created successfully")
        return True
    except Error as e:
        print(f"Error creating connection pool: {e}")
        return False


@contextmanager
def get_db_connection():
    global connection_pool
    connection = None
    try:
        if connection_pool is None:
            init_db_pool()
        connection = connection_pool.get_connection()
        yield connection
    except Error as e:
        print(f"Database error: {e}")
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()


def get_db_cursor(dictionary=True):

    global connection_pool
    try:
        if connection_pool is None:
            init_db_pool()
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=dictionary)
        return connection, cursor
    except Error as e:
        print(f"Error getting database cursor: {e}")
        raise


def execute_query(query, params=None, fetch=False, fetch_one=False):

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())

            if fetch_one:
                result = cursor.fetchone()
                cursor.close()
                return result
            elif fetch:
                results = cursor.fetchall()
                cursor.close()
                return results
            else:
                conn.commit()
                if query.strip().upper().startswith('INSERT'):
                    inserted_id = cursor.lastrowid
                    cursor.close()
                    return inserted_id
                else:
                    affected = cursor.rowcount
                    cursor.close()
                    return affected
        except Error as e:
            print(f"Query execution error: {e}")
            cursor.close()
            raise


def test_connection():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            print(" Database connection successful")
            return True
    except Error as e:
        print(f"Database connection failed: {e}")
        return False

