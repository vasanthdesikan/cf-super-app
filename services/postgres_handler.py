"""PostgreSQL Service Handler"""

import os
import json
import psycopg2
from psycopg2 import sql
from datetime import datetime
from urllib.parse import urlparse, unquote
from .credential_helper import find_service_credentials, get_connection_params_from_creds

class PostgresHandler:
    """Handler for PostgreSQL transactions"""
    
    def __init__(self):
        """Initialize PostgreSQL connection"""
        # Service types to search for (Tanzu Data Services and standard)
        service_types = [
            'p.postgresql',     # Tanzu Data Services
            'p-postgresql',     # Standard Cloud Foundry
            'p.postgresql-for-kubernetes',
            'postgresql',
            'postgres',
            'p.postgres'
        ]
        
        # Try to find credentials from VCAP_SERVICES (supports Tanzu and UPS)
        creds = find_service_credentials(service_types)
        
        if creds:
            # Check if URI is available (common in Tanzu services)
            uri = creds.get('uri') or creds.get('url') or creds.get('jdbcUrl') or creds.get('jdbc_url')
            if uri:
                # Handle PostgreSQL URI format: postgresql://user:pass@host:port/db
                parsed = urlparse(uri.replace('postgres://', 'postgresql://'))
                self.host = parsed.hostname or 'localhost'
                self.port = parsed.port or 5432
                self.username = unquote(parsed.username) if parsed.username else 'postgres'
                self.password = unquote(parsed.password) if parsed.password else ''
                self.database = parsed.path.lstrip('/') if parsed.path else 'postgres'
            else:
                # Extract from credential dictionary
                params = get_connection_params_from_creds(creds, 'localhost', 5432)
                self.host = params['host']
                self.port = params['port'] or 5432
                self.database = params['database'] or 'postgres'
                self.username = params['username'] or 'postgres'
                self.password = params['password'] or ''
        else:
            # Fallback to environment variables
            self.host = os.environ.get('POSTGRES_HOST', 'localhost')
            self.port = int(os.environ.get('POSTGRES_PORT', 5432))
            self.database = os.environ.get('POSTGRES_DATABASE', 'postgres')
            self.username = os.environ.get('POSTGRES_USER', 'postgres')
            self.password = os.environ.get('POSTGRES_PASSWORD', '')
        
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

