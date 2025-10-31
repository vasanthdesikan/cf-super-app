#!/usr/bin/env python3
"""
Cloud Foundry App for Testing Backend Services
Supports: RabbitMQ, Valkey, MySQL, PostgreSQL
"""

import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime

from core.config import config
from core.handler_manager import HandlerManager
from core.exceptions import ServiceNotFoundError, ServiceOperationError

app = Flask(__name__)

# Initialize handler manager (singleton pattern)
handler_manager = HandlerManager()

@app.route('/')
def index():
    """Main page with tabbed UI"""
    return render_template('index.html', services=config.get_enabled_services())

@app.route('/api/services')
def get_services():
    """API endpoint to get enabled services"""
    return jsonify(config.get_enabled_services())

@app.route('/api/test/<service_name>', methods=['POST'])
def test_service(service_name):
    """Test a specific service transaction"""
    try:
        handler = handler_manager.get_handler(service_name)
        result = handler.test_transaction(request.get_json() or {})
        return jsonify({
            'success': True,
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'data': result
        })
    except ServiceNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ServiceOperationError as e:
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
    try:
        handler = handler_manager.get_handler(service_name)
        
        # Strategy pattern: Route to appropriate method based on service type
        if service_name in ['mysql', 'postgres']:
            table_name = request.args.get('table')
            if table_name:
                result = handler.get_table_data(
                    table_name,
                    limit=int(request.args.get('limit', 100)),
                    offset=int(request.args.get('offset', 0))
                )
            else:
                result = handler.list_tables()
        elif service_name == 'rabbitmq':
            result = handler.list_queues()
        elif service_name == 'valkey':
            result = handler.list_keys(
                pattern=request.args.get('pattern', '*'),
                limit=int(request.args.get('limit', 100))
            )
        else:
            return jsonify({'success': False, 'error': 'Unsupported service'}), 400
        
        return jsonify({
            'success': True,
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'data': result
        })
    except ServiceNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ServiceOperationError as e:
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

