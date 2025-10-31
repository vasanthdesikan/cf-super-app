"""PostgreSQL Service Handler"""

import psycopg2
from psycopg2 import sql
from datetime import datetime
from .base_handler import DatabaseHandler

class PostgresHandler(DatabaseHandler):
    """Handler for PostgreSQL transactions"""
    
    def __init__(self):
        """Initialize PostgreSQL connection"""
        super().__init__(
            service_types=['p.postgresql', 'p-postgresql', 'postgresql', 'postgres'],
            default_port=5432,
            env_prefix='POSTGRES'
        )
        if not self.database:
            self.database = 'postgres'
        if not self.username:
            self.username = 'postgres'
        self.connection = None
    
    def _get_connection(self):
        """Get or create PostgreSQL connection"""
        if self.connection is None or self.connection.closed:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            self.connection.autocommit = False
        return self.connection
    
    def test_transaction(self, data=None):
        """Test PostgreSQL transaction (insert and select)"""
        if data is None:
            data = {}
        
        table_name = data.get('table_name', 'test_table')
        test_value = data.get('value', f'Test value at {datetime.now().isoformat()}')
        
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            create_table_sql = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL PRIMARY KEY,
                    test_value VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """).format(sql.Identifier(table_name))
            
            cursor.execute(create_table_sql)
            
            # Start transaction - INSERT
            insert_sql = sql.SQL("INSERT INTO {} (test_value) VALUES (%s) RETURNING id").format(
                sql.Identifier(table_name)
            )
            cursor.execute(insert_sql, (test_value,))
            insert_id = cursor.fetchone()[0]
            
            # SELECT to verify
            select_sql = sql.SQL("SELECT id, test_value, created_at FROM {} WHERE id = %s").format(
                sql.Identifier(table_name)
            )
            cursor.execute(select_sql, (insert_id,))
            result = cursor.fetchone()
            
            # Commit transaction
            self.connection.commit()
            
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
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise Exception(f"PostgreSQL transaction failed: {str(e)}")
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
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            # Get table information
            table_list = []
            for table in tables:
                table_name = table[0]
                # Get row count
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table_name)
                ))
                row_count = cursor.fetchone()[0]
                
                # Get table size - use format string to properly construct regclass
                # Escape the table name to prevent SQL injection
                escaped_table = table_name.replace("'", "''")
                cursor.execute(sql.SQL("SELECT pg_size_pretty(pg_total_relation_size({}::regclass))").format(
                    sql.Literal(f"public.{escaped_table}")
                ))
                size_result = cursor.fetchone()
                size = size_result[0] if size_result else '0 bytes'
                
                table_list.append({
                    'name': table_name,
                    'row_count': row_count if row_count else 0,
                    'size': size
                })
            
            return {
                'database': self.database,
                'tables': table_list,
                'count': len(table_list)
            }
        except Exception as e:
            raise Exception(f"Failed to list PostgreSQL tables: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def get_table_data(self, table_name, limit=100, offset=0):
        """Get data from a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get column names
            cursor.execute(sql.SQL("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = {}
                ORDER BY ordinal_position
            """).format(sql.Literal(table_name)))
            columns = [row[0] for row in cursor.fetchall()]
            
            # Get total row count
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(table_name)
            ))
            total_rows = cursor.fetchone()[0]
            
            # Get data with limit and offset
            cursor.execute(sql.SQL("SELECT * FROM {} LIMIT {} OFFSET {}").format(
                sql.Identifier(table_name),
                sql.Literal(limit),
                sql.Literal(offset)
            ))
            
            # Fetch all rows and convert to list of dicts
            rows = []
            column_names = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                row_dict = {}
                for i, value in enumerate(row):
                    # Convert datetime and other objects to strings
                    if hasattr(value, 'isoformat'):
                        row_dict[column_names[i]] = value.isoformat()
                    else:
                        row_dict[column_names[i]] = value
                rows.append(row_dict)
            
            return {
                'table': table_name,
                'columns': columns,
                'rows': rows,
                'total_rows': total_rows,
                'limit': limit,
                'offset': offset,
                'returned_rows': len(rows)
            }
        except Exception as e:
            raise Exception(f"Failed to get PostgreSQL table data: {str(e)}")
        finally:
            if cursor:
                cursor.close()
    
    def create_row(self, table_name, data):
        """Insert a new row into a table"""
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build INSERT statement using sql.Identifier for safety
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            values = list(data.values())
            
            insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join([sql.Identifier(col) for col in columns]),
                sql.SQL(placeholders)
            )
            
            # Execute with values
            cursor.execute(str(insert_sql), values)
            result = cursor.fetchone()
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description]
            inserted_row = {}
            for i, value in enumerate(result):
                if hasattr(value, 'isoformat'):
                    inserted_row[column_names[i]] = value.isoformat()
                else:
                    inserted_row[column_names[i]] = value
            
            conn.commit()
            
            return {
                'action': 'create',
                'table': table_name,
                'inserted_row': inserted_row,
                'data': data,
                'status': 'success'
            }
        except Exception as e:
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
            set_parts = []
            values = []
            for col, val in update_data.items():
                set_parts.append(sql.SQL("{} = %s").format(sql.Identifier(col)))
                values.append(val)
            
            values.extend(where_params)
            
            update_sql = sql.SQL("UPDATE {} SET {} WHERE {} RETURNING *").format(
                sql.Identifier(table_name),
                sql.SQL(', ').join(set_parts),
                sql.SQL(where_clause)
            )
            
            cursor.execute(str(update_sql), values)
            affected_rows = cursor.rowcount
            updated_rows = cursor.fetchall()
            
            conn.commit()
            
            return {
                'action': 'update',
                'table': table_name,
                'affected_rows': affected_rows,
                'update_data': update_data,
                'updated_rows': len(updated_rows),
                'status': 'success'
            }
        except Exception as e:
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
            
            delete_sql = sql.SQL("DELETE FROM {} WHERE {} RETURNING *").format(
                sql.Identifier(table_name),
                sql.SQL(where_clause)
            )
            
            cursor.execute(str(delete_sql), where_params)
            affected_rows = cursor.rowcount
            deleted_rows = cursor.fetchall()
            
            conn.commit()
            
            return {
                'action': 'delete',
                'table': table_name,
                'affected_rows': affected_rows,
                'deleted_rows': len(deleted_rows),
                'status': 'success'
            }
        except Exception as e:
            if conn:
                conn.rollback()
            raise Exception(f"Failed to delete row: {str(e)}")
        finally:
            if cursor:
                cursor.close()

