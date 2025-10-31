#!/usr/bin/env python3
"""
CLI interface for Cloud Foundry Service Tester
Provides command-line access to all UI functionality
"""

import os
import sys
import json
import argparse
import yaml
from datetime import datetime
from tabulate import tabulate

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import init_service_handlers, load_services_config, service_handlers

def format_json(data, indent=2):
    """Format data as JSON"""
    return json.dumps(data, indent=indent, default=str)

def print_table(headers, rows, title=None):
    """Print data in a formatted table"""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    if rows:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("No data found")
    print()

def list_tables(handler, service_name):
    """List tables for MySQL/PostgreSQL"""
    try:
        result = handler.list_tables()
        
        if result.get('tables'):
            rows = []
            for table in result['tables']:
                if service_name == 'mysql':
                    rows.append([
                        table['name'],
                        table['row_count'],
                        table.get('estimated_rows', 'N/A'),
                        f"{table.get('size_mb', 0):.2f} MB"
                    ])
                else:  # postgres
                    rows.append([
                        table['name'],
                        table['row_count'],
                        table.get('size', 'N/A')
                    ])
            
            headers = ['Table Name', 'Row Count', 'Estimated Rows' if service_name == 'mysql' else 'Size', 'Size (MB)'] if service_name == 'mysql' else ['Table Name', 'Row Count', 'Size']
            print_table(headers, rows, f"Tables in database: {result['database']}")
        else:
            print(f"No tables found in database: {result['database']}")
    except Exception as e:
        print(f"Error listing tables: {e}", file=sys.stderr)
        sys.exit(1)

def show_table_data(handler, table_name, limit=50, offset=0):
    """Show data from a table"""
    try:
        result = handler.get_table_data(table_name, limit=limit, offset=offset)
        
        if result.get('rows'):
            # Prepare table data
            headers = result['columns']
            rows = []
            for row in result['rows']:
                row_data = []
                for col in headers:
                    value = row.get(col, 'NULL')
                    if value is None:
                        row_data.append('NULL')
                    elif isinstance(value, (dict, list)):
                        row_data.append(json.dumps(value)[:50])
                    else:
                        str_val = str(value)
                        if len(str_val) > 50:
                            str_val = str_val[:47] + '...'
                        row_data.append(str_val)
                rows.append(row_data)
            
            print_table(
                headers, 
                rows, 
                f"Table: {result['table']} (Rows {result['offset'] + 1}-{result['offset'] + result['returned_rows']} of {result['total_rows']})"
            )
            
            # Show pagination info if needed
            if result['total_rows'] > result['limit']:
                current_page = (result['offset'] // result['limit']) + 1
                total_pages = (result['total_rows'] + result['limit'] - 1) // result['limit']
                print(f"Page {current_page} of {total_pages} (use --offset to navigate)")
        else:
            print(f"Table {table_name} is empty")
    except Exception as e:
        print(f"Error showing table data: {e}", file=sys.stderr)
        sys.exit(1)

def list_queues(handler):
    """List RabbitMQ queues"""
    try:
        result = handler.list_queues()
        
        if result.get('note'):
            print(result['note'])
            return
        
        if result.get('queues'):
            rows = []
            for queue in result['queues']:
                props = []
                if queue.get('durable'):
                    props.append('Durable')
                if queue.get('auto_delete'):
                    props.append('Auto-delete')
                
                rows.append([
                    queue['name'],
                    queue['messages'],
                    queue['consumers'],
                    ', '.join(props) if props else 'None'
                ])
            
            headers = ['Queue Name', 'Messages', 'Consumers', 'Properties']
            print_table(headers, rows, f"Queues in vhost: {result['vhost']}")
        else:
            print(f"No queues found in vhost: {result['vhost']}")
    except Exception as e:
        print(f"Error listing queues: {e}", file=sys.stderr)
        sys.exit(1)

def list_keys(handler, pattern='*', limit=100):
    """List Valkey cache keys"""
    try:
        result = handler.list_keys(pattern=pattern, limit=limit)
        
        if result.get('keys'):
            rows = []
            for key_info in result['keys']:
                ttl = f"{key_info['ttl']}s" if key_info.get('ttl') else "No expiration"
                value_preview = key_info.get('value_preview', 'N/A')
                if value_preview and len(value_preview) > 50:
                    value_preview = value_preview[:47] + '...'
                
                rows.append([
                    key_info['key'],
                    key_info['type'],
                    ttl,
                    value_preview
                ])
            
            headers = ['Key', 'Type', 'TTL', 'Value Preview']
            title = f"Keys matching pattern: {result['pattern']} (Showing {result['count']}"
            if result.get('total_found'):
                title += f" of {result['total_found']}"
            title += ")"
            print_table(headers, rows, title)
        else:
            print(f"No keys found matching pattern: {pattern}")
    except Exception as e:
        print(f"Error listing keys: {e}", file=sys.stderr)
        sys.exit(1)

def test_service(handler, service_name, data):
    """Test a service transaction"""
    try:
        result = handler.test_transaction(data)
        
        print(f"\n✓ {service_name.title()} Transaction Successful")
        print("=" * 50)
        print(format_json(result, indent=2))
        print()
    except Exception as e:
        print(f"\n✗ {service_name.title()} Transaction Failed", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Cloud Foundry Service Tester CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List MySQL tables
  %(prog)s mysql list-tables
  
  # Show MySQL table data
  %(prog)s mysql show-table --table test_table
  
  # Test MySQL transaction
  %(prog)s mysql test --table-name test_table --value "Test data"
  
  # List RabbitMQ queues
  %(prog)s rabbitmq list-queues
  
  # Test RabbitMQ transaction
  %(prog)s rabbitmq test --queue-name my_queue --message "Hello"
  
  # List Valkey keys
  %(prog)s valkey list-keys --pattern "test_*"
  
  # Test Valkey transaction
  %(prog)s valkey test --key my_key --value "my value"
  
  # CRUD Operations
  
  # Create a row (MySQL/PostgreSQL)
  %(prog)s mysql create --table users --data '{"name":"John","email":"john@example.com"}'
  
  # Update rows (MySQL/PostgreSQL)
  %(prog)s mysql update --table users --where "id = %s" --where-values '[1]' --data '{"name":"Jane"}'
  
  # Delete rows (MySQL/PostgreSQL)
  %(prog)s mysql delete --table users --where "id = %s" --where-values '[1]'
  
  # RabbitMQ CRUD Operations
  %(prog)s rabbitmq publish --queue my_queue --message "Hello"
  %(prog)s rabbitmq consume --queue my_queue
  %(prog)s rabbitmq purge --queue my_queue
  %(prog)s rabbitmq delete-queue --queue my_queue
  
  # Valkey CRUD Operations
  %(prog)s valkey set --key my_key --value "my value"
  %(prog)s valkey set --key my_key --value "my value" --ttl 3600
  %(prog)s valkey get --key my_key
  %(prog)s valkey exists --key my_key
  %(prog)s valkey delete --key my_key
        """
    )
    
    subparsers = parser.add_subparsers(dest='service', help='Service to interact with')
    
    # MySQL subcommands
    mysql_parser = subparsers.add_parser('mysql', help='MySQL operations')
    mysql_subparsers = mysql_parser.add_subparsers(dest='action', help='Action to perform')
    
    mysql_list = mysql_subparsers.add_parser('list-tables', help='List all tables')
    
    mysql_show = mysql_subparsers.add_parser('show-table', help='Show table data')
    mysql_show.add_argument('--table', required=True, help='Table name')
    mysql_show.add_argument('--limit', type=int, default=50, help='Number of rows to show (default: 50)')
    mysql_show.add_argument('--offset', type=int, default=0, help='Offset for pagination (default: 0)')
    
    mysql_test = mysql_subparsers.add_parser('test', help='Test transaction')
    mysql_test.add_argument('--table-name', default='test_table', help='Table name')
    mysql_test.add_argument('--value', default=None, help='Test value to insert')
    
    mysql_create = mysql_subparsers.add_parser('create', help='Create (insert) a row')
    mysql_create.add_argument('--table', required=True, help='Table name')
    mysql_create.add_argument('--data', required=True, help='JSON data for columns: {"col1":"val1","col2":"val2"}')
    
    mysql_update = mysql_subparsers.add_parser('update', help='Update rows')
    mysql_update.add_argument('--table', required=True, help='Table name')
    mysql_update.add_argument('--where', required=True, help='WHERE clause (e.g., "id = %s")')
    mysql_update.add_argument('--where-values', required=True, help='WHERE values as JSON array (e.g., "[1]")')
    mysql_update.add_argument('--data', required=True, help='JSON data to update: {"col1":"val1","col2":"val2"}')
    
    mysql_delete = mysql_subparsers.add_parser('delete', help='Delete rows')
    mysql_delete.add_argument('--table', required=True, help='Table name')
    mysql_delete.add_argument('--where', required=True, help='WHERE clause (e.g., "id = %s")')
    mysql_delete.add_argument('--where-values', required=True, help='WHERE values as JSON array (e.g., "[1]")')
    
    # PostgreSQL subcommands
    postgres_parser = subparsers.add_parser('postgres', help='PostgreSQL operations')
    postgres_subparsers = postgres_parser.add_subparsers(dest='action', help='Action to perform')
    
    postgres_list = postgres_subparsers.add_parser('list-tables', help='List all tables')
    
    postgres_show = postgres_subparsers.add_parser('show-table', help='Show table data')
    postgres_show.add_argument('--table', required=True, help='Table name')
    postgres_show.add_argument('--limit', type=int, default=50, help='Number of rows to show (default: 50)')
    postgres_show.add_argument('--offset', type=int, default=0, help='Offset for pagination (default: 0)')
    
    postgres_test = postgres_subparsers.add_parser('test', help='Test transaction')
    postgres_test.add_argument('--table-name', default='test_table', help='Table name')
    postgres_test.add_argument('--value', default=None, help='Test value to insert')
    
    postgres_create = postgres_subparsers.add_parser('create', help='Create (insert) a row')
    postgres_create.add_argument('--table', required=True, help='Table name')
    postgres_create.add_argument('--data', required=True, help='JSON data for columns: {"col1":"val1","col2":"val2"}')
    
    postgres_update = postgres_subparsers.add_parser('update', help='Update rows')
    postgres_update.add_argument('--table', required=True, help='Table name')
    postgres_update.add_argument('--where', required=True, help='WHERE clause (e.g., "id = %s")')
    postgres_update.add_argument('--where-values', required=True, help='WHERE values as JSON array (e.g., "[1]")')
    postgres_update.add_argument('--data', required=True, help='JSON data to update: {"col1":"val1","col2":"val2"}')
    
    postgres_delete = postgres_subparsers.add_parser('delete', help='Delete rows')
    postgres_delete.add_argument('--table', required=True, help='Table name')
    postgres_delete.add_argument('--where', required=True, help='WHERE clause (e.g., "id = %s")')
    postgres_delete.add_argument('--where-values', required=True, help='WHERE values as JSON array (e.g., "[1]")')
    
    # RabbitMQ subcommands
    rabbitmq_parser = subparsers.add_parser('rabbitmq', help='RabbitMQ operations')
    rabbitmq_subparsers = rabbitmq_parser.add_subparsers(dest='action', help='Action to perform')
    
    rabbitmq_list = rabbitmq_subparsers.add_parser('list-queues', help='List all queues')
    
    rabbitmq_test = rabbitmq_subparsers.add_parser('test', help='Test transaction')
    rabbitmq_test.add_argument('--queue-name', default='test_queue', help='Queue name')
    rabbitmq_test.add_argument('--message', default=None, help='Message to publish')
    
    rabbitmq_publish = rabbitmq_subparsers.add_parser('publish', help='Publish message to queue (CREATE)')
    rabbitmq_publish.add_argument('--queue', required=True, help='Queue name')
    rabbitmq_publish.add_argument('--message', required=True, help='Message to publish')
    rabbitmq_publish.add_argument('--durable', action='store_true', help='Make message persistent')
    
    rabbitmq_consume = rabbitmq_subparsers.add_parser('consume', help='Consume message from queue (READ)')
    rabbitmq_consume.add_argument('--queue', required=True, help='Queue name')
    rabbitmq_consume.add_argument('--no-ack', action='store_true', help='Do not auto-acknowledge message')
    
    rabbitmq_purge = rabbitmq_subparsers.add_parser('purge', help='Purge all messages from queue (DELETE)')
    rabbitmq_purge.add_argument('--queue', required=True, help='Queue name to purge')
    
    rabbitmq_delete_queue = rabbitmq_subparsers.add_parser('delete-queue', help='Delete a queue completely')
    rabbitmq_delete_queue.add_argument('--queue', required=True, help='Queue name to delete')
    rabbitmq_delete_queue.add_argument('--if-unused', action='store_true', help='Delete only if unused')
    rabbitmq_delete_queue.add_argument('--if-empty', action='store_true', help='Delete only if empty')
    
    # Valkey subcommands
    valkey_parser = subparsers.add_parser('valkey', help='Valkey operations')
    valkey_subparsers = valkey_parser.add_subparsers(dest='action', help='Action to perform')
    
    valkey_list = valkey_subparsers.add_parser('list-keys', help='List cache keys')
    valkey_list.add_argument('--pattern', default='*', help='Key pattern (default: *)')
    valkey_list.add_argument('--limit', type=int, default=100, help='Maximum number of keys (default: 100)')
    
    valkey_test = valkey_subparsers.add_parser('test', help='Test transaction')
    valkey_test.add_argument('--key', default='test_key', help='Key name')
    valkey_test.add_argument('--value', default=None, help='Value to set')
    
    valkey_set = valkey_subparsers.add_parser('set', help='Set a key value (CREATE/UPDATE)')
    valkey_set.add_argument('--key', required=True, help='Key name')
    valkey_set.add_argument('--value', required=True, help='Value to set')
    valkey_set.add_argument('--ttl', type=int, default=None, help='TTL in seconds (optional)')
    
    valkey_get = valkey_subparsers.add_parser('get', help='Get a key value (READ)')
    valkey_get.add_argument('--key', required=True, help='Key name')
    
    valkey_delete = valkey_subparsers.add_parser('delete', help='Delete a key (DELETE)')
    valkey_delete.add_argument('--key', required=True, help='Key name to delete')
    
    valkey_exists = valkey_subparsers.add_parser('exists', help='Check if a key exists')
    valkey_exists.add_argument('--key', required=True, help='Key name to check')
    
    args = parser.parse_args()
    
    if not args.service or not args.action:
        parser.print_help()
        sys.exit(1)
    
    # Initialize handlers (reuse from app)
    handlers = service_handlers
    
    if args.service not in handlers or handlers[args.service] is None:
        print(f"Error: {args.service} service is not enabled or initialized", file=sys.stderr)
        print("Check services-config.yml to ensure the service is enabled", file=sys.stderr)
        sys.exit(1)
    
    handler = handlers[args.service]
    
    # Execute action
    try:
        if args.service == 'mysql':
            if args.action == 'list-tables':
                list_tables(handler, 'mysql')
            elif args.action == 'show-table':
                show_table_data(handler, args.table, limit=args.limit, offset=args.offset)
            elif args.action == 'test':
                data = {
                    'table_name': args.table_name,
                    'value': args.value or f'Test value at {datetime.now().isoformat()}'
                }
                test_service(handler, 'mysql', data)
            elif args.action == 'create':
                try:
                    data = json.loads(args.data)
                    result = handler.create_row(args.table, data)
                    print(f"\n✓ Row created successfully in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --data argument", file=sys.stderr)
                    sys.exit(1)
            elif args.action == 'update':
                try:
                    where_values = json.loads(args.where_values)
                    update_data = json.loads(args.data)
                    result = handler.update_row(args.table, args.where, where_values, update_data)
                    print(f"\n✓ Update successful in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in arguments: {e}", file=sys.stderr)
                    sys.exit(1)
            elif args.action == 'delete':
                try:
                    where_values = json.loads(args.where_values)
                    result = handler.delete_row(args.table, args.where, where_values)
                    print(f"\n✓ Delete successful in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --where-values argument", file=sys.stderr)
                    sys.exit(1)
        
        elif args.service == 'postgres':
            if args.action == 'list-tables':
                list_tables(handler, 'postgres')
            elif args.action == 'show-table':
                show_table_data(handler, args.table, limit=args.limit, offset=args.offset)
            elif args.action == 'test':
                data = {
                    'table_name': args.table_name,
                    'value': args.value or f'Test value at {datetime.now().isoformat()}'
                }
                test_service(handler, 'postgres', data)
            elif args.action == 'create':
                try:
                    data = json.loads(args.data)
                    result = handler.create_row(args.table, data)
                    print(f"\n✓ Row created successfully in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --data argument", file=sys.stderr)
                    sys.exit(1)
            elif args.action == 'update':
                try:
                    where_values = json.loads(args.where_values)
                    update_data = json.loads(args.data)
                    result = handler.update_row(args.table, args.where, where_values, update_data)
                    print(f"\n✓ Update successful in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in arguments: {e}", file=sys.stderr)
                    sys.exit(1)
            elif args.action == 'delete':
                try:
                    where_values = json.loads(args.where_values)
                    result = handler.delete_row(args.table, args.where, where_values)
                    print(f"\n✓ Delete successful in table: {args.table}")
                    print("=" * 50)
                    print(format_json(result, indent=2))
                    print()
                except json.JSONDecodeError:
                    print(f"Error: Invalid JSON in --where-values argument", file=sys.stderr)
                    sys.exit(1)
        
        elif args.service == 'rabbitmq':
            if args.action == 'list-queues':
                list_queues(handler)
            elif args.action == 'test':
                data = {
                    'queue_name': args.queue_name,
                    'message': args.message or f'Test message at {datetime.now().isoformat()}'
                }
                test_service(handler, 'rabbitmq', data)
            elif args.action == 'publish':
                result = handler.publish_message(args.queue, args.message, durable=args.durable)
                print(f"\n✓ Message published to queue: {args.queue}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'consume':
                result = handler.consume_message(args.queue, auto_ack=not args.no_ack)
                if result['status'] == 'success':
                    print(f"\n✓ Message consumed from queue: {args.queue}")
                else:
                    print(f"\n⚠ {result.get('note', 'No message available')}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'purge':
                result = handler.purge_queue(args.queue)
                print(f"\n✓ Queue purged: {args.queue}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'delete-queue':
                result = handler.delete_queue(args.queue, if_unused=args.if_unused, if_empty=args.if_empty)
                print(f"\n✓ Queue deleted: {args.queue}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
        
        elif args.service == 'valkey':
            if args.action == 'list-keys':
                list_keys(handler, pattern=args.pattern, limit=args.limit)
            elif args.action == 'test':
                data = {
                    'key': args.key,
                    'value': args.value or f'Test value at {datetime.now().isoformat()}'
                }
                test_service(handler, 'valkey', data)
            elif args.action == 'set':
                result = handler.set_key(args.key, args.value, ttl=args.ttl)
                print(f"\n✓ Key set: {args.key}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'get':
                result = handler.get_key(args.key)
                if result['exists']:
                    print(f"\n✓ Retrieved key: {args.key}")
                else:
                    print(f"\n⚠ Key not found: {args.key}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'exists':
                result = handler.exists_key(args.key)
                status = "exists" if result['exists'] else "does not exist"
                print(f"\n✓ Key {args.key} {status}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
            elif args.action == 'delete':
                result = handler.delete_key(args.key)
                if result['deleted']:
                    print(f"\n✓ Key deleted: {args.key}")
                else:
                    print(f"\n⚠ Key not found: {args.key}")
                print("=" * 50)
                print(format_json(result, indent=2))
                print()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

