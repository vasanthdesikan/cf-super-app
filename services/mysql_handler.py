"""MySQL Service Handler"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime
from .base_handler import DatabaseHandler

class MySQLHandler(DatabaseHandler):
    """Handler for MySQL transactions"""
    
    def __init__(self):
        """Initialize MySQL connection"""
        super().__init__(
            service_types=['p.mysql', 'p-mysql', 'mysql'],
            default_port=3306,
            env_prefix='MYSQL'
        )
        if not self.database:
            self.database = 'testdb'
        if not self.username:
            self.username = 'root'
        self.connection = None
    
    def _get_connection(self):
        """Get or create MySQL connection"""
        if self.connection is None or not self.connection.is_connected():
            # Note: mysql.connector doesn't support URI directly, so we use parsed values
            # But we ensure URI is checked first during credential loading
            if not self.host:
                raise Exception("No connection information available. Please provide URI or hostname in service credentials.")
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                autocommit=False
            )
        return self.connection
    
    def test_transaction(self, data=None):
        """Test MySQL transaction (insert and select)"""
        if data is None:
            data = {}
        
        table_name = data.get('table_name', 'test_table')
        test_value = data.get('value', f'Test value at {datetime.now().isoformat()}')
        
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                test_value VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_sql)
            
            # Start transaction - INSERT
            insert_sql = f"INSERT INTO {table_name} (test_value) VALUES (%s)"
            cursor.execute(insert_sql, (test_value,))
            insert_id = cursor.lastrowid
            
            # SELECT to verify
            select_sql = f"SELECT id, test_value, created_at FROM {table_name} WHERE id = %s"
            cursor.execute(select_sql, (insert_id,))
            result = cursor.fetchone()
            
            # Commit transaction
            conn.commit()
            
            return {
                'action': 'insert_and_select',
                'table': table_name,
                'insert_id': insert_id,
                'inserted_value': test_value,
                'retrieved_row': {
                    'id': result[0],
                    'test_value': result[1],
                    'created_at': result[2].isoformat() if result[2] else None
                },
                'status': 'success'
            }
        except Error as e:
            if self.connection:
                self.connection.rollback()
            raise Exception(f"MySQL transaction failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def list_tables(self):
        """List all tables in the database"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            # Get table information
            table_list = []
            for table in tables:
                table_name = table[0]
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = cursor.fetchone()[0]
                
                # Get table size and info
                cursor.execute(f"""
                    SELECT 
                        table_rows,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                    FROM information_schema.TABLES 
                    WHERE table_schema = '{self.database}' 
                    AND table_name = '{table_name}'
                """)
                table_info = cursor.fetchone()
                
                table_list.append({
                    'name': table_name,
                    'row_count': row_count if row_count is not None else 0,
                    'estimated_rows': table_info[0] if table_info and table_info[0] else 0,
                    'size_mb': table_info[1] if table_info and table_info[1] else 0
                })
            
            return {
                'database': self.database,
                'tables': table_list,
                'count': len(table_list)
            }
        except Error as e:
            raise Exception(f"Failed to list MySQL tables: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def get_table_data(self, table_name, limit=100, offset=0):
        """Get data from a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)  # Return as dictionary
            
            # Get column names
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = [col['Field'] for col in cursor.fetchall()]
            
            # Get total row count
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            total_rows = cursor.fetchone()['count']
            
            # Get data with limit and offset
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s", (limit, offset))
            rows = cursor.fetchall()
            
            return {
                'table': table_name,
                'columns': columns,
                'rows': rows,
                'total_rows': total_rows,
                'limit': limit,
                'offset': offset,
                'returned_rows': len(rows)
            }
        except Error as e:
            raise Exception(f"Failed to get MySQL table data: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def create_row(self, table_name, data):
        """Insert a new row into a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Build INSERT statement
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            values = list(data.values())
            
            insert_sql = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in columns])}) VALUES ({placeholders})"
            cursor.execute(insert_sql, values)
            insert_id = cursor.lastrowid
            
            conn.commit()
            
            return {
                'action': 'create',
                'table': table_name,
                'insert_id': insert_id,
                'data': data,
                'status': 'success'
            }
        except Error as e:
            if conn:
                conn.rollback()
            raise Exception(f"Failed to create row: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def update_row(self, table_name, where_clause, where_params, update_data):
        """Update rows in a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build UPDATE statement
            set_clause = ', '.join([f"`{col}` = %s" for col in update_data.keys()])
            values = list(update_data.values()) + list(where_params)
            
            update_sql = f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause}"
            cursor.execute(update_sql, values)
            affected_rows = cursor.rowcount
            
            conn.commit()
            
            return {
                'action': 'update',
                'table': table_name,
                'affected_rows': affected_rows,
                'update_data': update_data,
                'status': 'success'
            }
        except Error as e:
            if conn:
                conn.rollback()
            raise Exception(f"Failed to update row: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def delete_row(self, table_name, where_clause, where_params):
        """Delete rows from a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            delete_sql = f"DELETE FROM `{table_name}` WHERE {where_clause}"
            cursor.execute(delete_sql, where_params)
            affected_rows = cursor.rowcount
            
            conn.commit()
            
            return {
                'action': 'delete',
                'table': table_name,
                'affected_rows': affected_rows,
                'status': 'success'
            }
        except Error as e:
            if conn:
                conn.rollback()
            raise Exception(f"Failed to delete row: {str(e)}")
        finally:
            if cursor:
                cursor.close()

