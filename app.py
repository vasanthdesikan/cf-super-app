#!/usr/bin/env python3
"""
Cloud Foundry App for Testing Backend Services
Supports: RabbitMQ, Valkey, MySQL, PostgreSQL
"""

import os
import json
import yaml
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# Lazy import service handlers (only when needed)
def import_handler(handler_name):
    """Import service handler dynamically"""
    try:
        if handler_name == 'rabbitmq':
            from services.rabbitmq_handler import RabbitMQHandler
            return RabbitMQHandler
        elif handler_name == 'valkey':
            from services.valkey_handler import ValkeyHandler
            return ValkeyHandler
        elif handler_name == 'mysql':
            from services.mysql_handler import MySQLHandler
            return MySQLHandler
        elif handler_name == 'postgres':
            from services.postgres_handler import PostgresHandler
            return PostgresHandler
    except ImportError as e:
        app.logger.warning(f"Failed to import {handler_name} handler: {e}")
        return None
    return None

# Load services configuration
def load_services_config():
    """Load services configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(__file__), 'services-config.yml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('services', {})

# Initialize service handlers based on configuration
def init_service_handlers():
    """Initialize only enabled service handlers"""
    config = load_services_config()
    handlers = {}
    
    # RabbitMQ
    if config.get('rabbitmq', {}).get('enabled', False):
        try:
            HandlerClass = import_handler('rabbitmq')
            if HandlerClass:
                handlers['rabbitmq'] = HandlerClass()
            else:
                handlers['rabbitmq'] = None
        except Exception as e:
            app.logger.warning(f"Failed to initialize RabbitMQ: {e}")
            handlers['rabbitmq'] = None
    
    # Valkey
    if config.get('valkey', {}).get('enabled', False):
        try:
            HandlerClass = import_handler('valkey')
            if HandlerClass:
                handlers['valkey'] = HandlerClass()
            else:
                handlers['valkey'] = None
        except Exception as e:
            app.logger.warning(f"Failed to initialize Valkey: {e}")
            handlers['valkey'] = None
    
    # MySQL
    if config.get('mysql', {}).get('enabled', False):
        try:
            HandlerClass = import_handler('mysql')
            if HandlerClass:
                handlers['mysql'] = HandlerClass()
            else:
                handlers['mysql'] = None
        except Exception as e:
            app.logger.warning(f"Failed to initialize MySQL: {e}")
            handlers['mysql'] = None
    
    # PostgreSQL
    if config.get('postgres', {}).get('enabled', False):
        try:
            HandlerClass = import_handler('postgres')
            if HandlerClass:
                handlers['postgres'] = HandlerClass()
            else:
                handlers['postgres'] = None
        except Exception as e:
            app.logger.warning(f"Failed to initialize PostgreSQL: {e}")
            handlers['postgres'] = None
    
    return handlers

# Initialize handlers
service_handlers = init_service_handlers()

@app.route('/')
def index():
    """Main page with tabbed UI"""
    config = load_services_config()
    
    # Filter enabled services for UI
    enabled_services = {
        key: {
            'display_name': value.get('display_name', key.title()),
            'enabled': value.get('enabled', False)
        }
        for key, value in config.items()
        if value.get('enabled', False)
    }
    
    return render_template('index.html', services=enabled_services)

@app.route('/api/services')
def get_services():
    """API endpoint to get enabled services"""
    config = load_services_config()
    enabled_services = {
        key: {
            'display_name': value.get('display_name', key.title()),
            'enabled': value.get('enabled', False)
        }
        for key, value in config.items()
        if value.get('enabled', False)
    }
    return jsonify(enabled_services)

@app.route('/api/test/<service_name>', methods=['POST'])
def test_service(service_name):
    """Test a specific service transaction"""
    if service_name not in service_handlers or service_handlers[service_name] is None:
        return jsonify({
            'success': False,
            'error': f'Service {service_name} is not enabled or initialized'
        }), 404
    
    handler = service_handlers[service_name]
    data = request.get_json() or {}
    
    try:
        result = handler.test_transaction(data)
        return jsonify({
            'success': True,
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'data': result
        })
    except Exception as e:
        app.logger.error(f"Error testing {service_name}: {e}")
        return jsonify({
            'success': False,
            'service': service_name,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/list/<service_name>', methods=['GET'])
def list_service_resources(service_name):
    """List resources for a specific service (tables, queues, keys)"""
    if service_name not in service_handlers or service_handlers[service_name] is None:
        return jsonify({
            'success': False,
            'error': f'Service {service_name} is not enabled or initialized'
        }), 404
    
    handler = service_handlers[service_name]
    
    try:
        if service_name in ['mysql', 'postgres']:
            # Check if table parameter is provided to get table data
            table_name = request.args.get('table')
            if table_name:
                limit = int(request.args.get('limit', 100))
                offset = int(request.args.get('offset', 0))
                result = handler.get_table_data(table_name, limit=limit, offset=offset)
            else:
                result = handler.list_tables()
        elif service_name == 'rabbitmq':
            result = handler.list_queues()
        elif service_name == 'valkey':
            pattern = request.args.get('pattern', '*')
            limit = int(request.args.get('limit', 100))
            result = handler.list_keys(pattern=pattern, limit=limit)
        else:
            return jsonify({
                'success': False,
                'error': f'Listing not supported for service {service_name}'
            }), 400
        
        return jsonify({
            'success': True,
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'data': result
        })
    except Exception as e:
        app.logger.error(f"Error listing {service_name} resources: {e}")
        return jsonify({
            'success': False,
            'service': service_name,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

