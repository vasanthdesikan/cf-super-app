#!/usr/bin/env python3
"""
Cloud Foundry App for Testing Backend Services
Supports: RabbitMQ, Valkey, MySQL, PostgreSQL
"""

import os
import requests
from flask import Flask, render_template, jsonify, request
from datetime import datetime

from core.config import config
from core.handler_manager import HandlerManager
from core.exceptions import ServiceNotFoundError, ServiceOperationError

app = Flask(__name__)

# Check if this is UI app or backend app
APP_TYPE = os.environ.get('APP_TYPE', 'backend')
IS_UI_APP = APP_TYPE == 'ui'

# Initialize handler manager (singleton pattern) - only for backend apps
handler_manager = HandlerManager() if not IS_UI_APP else None

# Map service names to backend app names
BACKEND_APP_MAP = {
    'postgres': 'service-tester-postgres',
    'mysql': 'service-tester-mysql',
    'rabbitmq': 'service-tester-rabbitmq',
    'valkey': 'service-tester-valkey'
}

def get_backend_url(service_name):
    """Get internal URL for backend app"""
    backend_app = BACKEND_APP_MAP.get(service_name)
    if not backend_app:
        return None
    # Use internal Cloud Foundry route
    return f'http://{backend_app}.internal'

@app.route('/')
def index():
    """Main page with tabbed UI"""
    if IS_UI_APP:
        # UI app: show UI with all enabled services
        return render_template('index.html', services=config.get_enabled_services())
    else:
        # Backend app: redirect or show error
        return jsonify({'error': 'This is a backend service. Access via UI app.'}), 403

@app.route('/api/services')
def get_services():
    """API endpoint to get enabled services"""
    return jsonify(config.get_enabled_services())

@app.route('/api/test/<service_name>', methods=['POST'])
def test_service(service_name):
    """Test a specific service transaction"""
    if IS_UI_APP:
        # UI app: proxy to backend app
        backend_url = get_backend_url(service_name)
        if not backend_url:
            return jsonify({'success': False, 'error': f'Unknown service: {service_name}'}), 404
        
        try:
            response = requests.post(
                f'{backend_url}/api/test/{service_name}',
                json=request.get_json() or {},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error proxying to backend {service_name}: {e}")
            return jsonify({
                'success': False,
                'service': service_name,
                'error': f'Backend service unavailable: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 503
    else:
        # Backend app: handle the request
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
        except Exception as e:
            app.logger.error(f"Unexpected error testing {service_name}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'service': service_name,
                'error': f'Internal error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 500

@app.route('/api/list/<service_name>', methods=['GET'])
def list_service_resources(service_name):
    """List resources for a specific service (tables, queues, keys)"""
    if IS_UI_APP:
        # UI app: proxy to backend app
        backend_url = get_backend_url(service_name)
        if not backend_url:
            return jsonify({'success': False, 'error': f'Unknown service: {service_name}'}), 404
        
        try:
            response = requests.get(
                f'{backend_url}/api/list/{service_name}',
                params=request.args,
                timeout=30
            )
            return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error proxying to backend {service_name}: {e}")
            return jsonify({
                'success': False,
                'service': service_name,
                'error': f'Backend service unavailable: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 503
    else:
        # Backend app: handle the request
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
        except Exception as e:
            app.logger.error(f"Unexpected error listing {service_name} resources: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'service': service_name,
                'error': f'Internal error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

