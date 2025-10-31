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

# Import service handlers
from services.rabbitmq_handler import RabbitMQHandler
from services.valkey_handler import ValkeyHandler
from services.mysql_handler import MySQLHandler
from services.postgres_handler import PostgresHandler

app = Flask(__name__)

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
            handlers['rabbitmq'] = RabbitMQHandler()
        except Exception as e:
            app.logger.warning(f"Failed to initialize RabbitMQ: {e}")
            handlers['rabbitmq'] = None
    
    # Valkey
    if config.get('valkey', {}).get('enabled', False):
        try:
            handlers['valkey'] = ValkeyHandler()
        except Exception as e:
            app.logger.warning(f"Failed to initialize Valkey: {e}")
            handlers['valkey'] = None
    
    # MySQL
    if config.get('mysql', {}).get('enabled', False):
        try:
            handlers['mysql'] = MySQLHandler()
        except Exception as e:
            app.logger.warning(f"Failed to initialize MySQL: {e}")
            handlers['mysql'] = None
    
    # PostgreSQL
    if config.get('postgres', {}).get('enabled', False):
        try:
            handlers['postgres'] = PostgresHandler()
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

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

