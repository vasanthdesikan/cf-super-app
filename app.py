#!/usr/bin/env python3
"""Cloud Foundry App for Testing Backend Services"""

import os
import json
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# App configuration
APP_TYPE = os.environ.get('APP_TYPE', 'backend')
IS_UI_APP = APP_TYPE == 'ui'

# Backend app name mapping
BACKEND_APPS = {
    'postgres': 'service-tester-postgres',
    'mysql': 'service-tester-mysql',
    'rabbitmq': 'service-tester-rabbitmq',
    'valkey': 'service-tester-valkey'
}

# Cache for domain and space info
_DOMAIN_CACHE = None
_SPACE_NAME_CACHE = None

def _get_domain_and_space():
    """Extract domain and space name from VCAP_APPLICATION"""
    global _DOMAIN_CACHE, _SPACE_NAME_CACHE
    if _DOMAIN_CACHE is not None and _SPACE_NAME_CACHE is not None:
        return _DOMAIN_CACHE, _SPACE_NAME_CACHE
    
    vcap = os.environ.get('VCAP_APPLICATION', '{}')
    if vcap and vcap != '{}':
        try:
            app_info = json.loads(vcap)
            uris = app_info.get('uris', [])
            space_name = app_info.get('space_name', '')
            
            if uris and '.' in uris[0]:
                # Extract domain from URI
                # Format: app-name.random-route.domain.com -> domain.com
                domain = '.'.join(uris[0].split('.')[1:])
                _DOMAIN_CACHE = domain
                _SPACE_NAME_CACHE = space_name
                return domain, space_name
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
    
    _DOMAIN_CACHE = ''
    _SPACE_NAME_CACHE = ''
    return '', ''

def get_backend_url(service_name):
    """Generate backend app URL using domain-based approach with space name"""
    backend_app = BACKEND_APPS.get(service_name)
    if not backend_app:
        return None
    
    # Check for explicit backend URL in environment (set in manifest)
    env_var = f'BACKEND_{service_name.upper()}_URL'
    backend_url = os.environ.get(env_var)
    if backend_url:
        return backend_url
    
    # Get domain and space name from VCAP_APPLICATION
    domain, space_name = _get_domain_and_space()
    
    if domain:
        # Construct URL: http://{app-name}-{space-name}.{domain}
        # Note: Routes must be created with this format for this to work
        # Cloud Foundry will create routes as {app-name}.{domain} by default
        # To use {app-name}-{space-name}.{domain}, routes must be created post-deployment
        if space_name:
            url = f'http://{backend_app}-{space_name}.{domain}'
        else:
            # Fallback: use app name with domain (matches default CF route)
            url = f'http://{backend_app}.{domain}'
        return url
    
    # Last resort: try direct app name (may work within same space)
    return f'http://{backend_app}'


# Lazy load handlers only for backend apps
if not IS_UI_APP:
    from core.handler_manager import HandlerManager
    from core.exceptions import ServiceNotFoundError, ServiceOperationError
    handler_manager = HandlerManager()
else:
    handler_manager = None
    import requests

@app.route('/')
def index():
    """Main page with tabbed UI"""
    if IS_UI_APP:
        from core.config import config
        return render_template('index.html', services=config.get_enabled_services())
    return jsonify({'error': 'This is a backend service. Access via UI app.'}), 403

@app.route('/api/services')
def get_services():
    """API endpoint to get enabled services"""
    from core.config import config
    return jsonify(config.get_enabled_services())

def _proxy_request(method, service_name, url_suffix='', **kwargs):
    """Proxy request to backend app"""
    backend_url = get_backend_url(service_name)
    if not backend_url:
        return jsonify({'success': False, 'error': f'Unknown service: {service_name}'}), 404
    
    try:
        url = f'{backend_url}/api/{url_suffix}{service_name}'
        if method == 'POST':
            response = requests.post(url, json=kwargs.get('json', {}), 
                                    headers={'Content-Type': 'application/json'}, timeout=30)
        else:
            response = requests.get(url, params=kwargs.get('params', {}), timeout=30)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error proxying to {service_name}: {e}")
        return jsonify({
            'success': False,
            'service': service_name,
            'error': f'Backend service unavailable: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 503

def _handle_backend_request(service_name, action='test', **kwargs):
    """Handle request in backend app"""
    try:
        handler = handler_manager.get_handler(service_name)
        if action == 'test':
            result = handler.test_transaction(kwargs.get('data', {}))
        elif action == 'list':
            if service_name in ['mysql', 'postgres']:
                table = kwargs.pop('table', None)
                if table:
                    # Extract table-specific kwargs (limit, offset) and remove table
                    result = handler.get_table_data(
                        table,
                        limit=kwargs.pop('limit', 100),
                        offset=kwargs.pop('offset', 0)
                    )
                else:
                    result = handler.list_tables()
            elif service_name == 'rabbitmq':
                result = handler.list_queues()
            elif service_name == 'valkey':
                result = handler.list_keys(**kwargs)
            else:
                return jsonify({'success': False, 'error': 'Unsupported service'}), 400
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        return jsonify({
            'success': True,
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'data': result
        })
    except ServiceNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ServiceOperationError as e:
        app.logger.error(f"Error in {service_name}: {e}")
        return jsonify({
            'success': False,
            'service': service_name,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in {service_name}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'service': service_name,
            'error': f'Internal error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/test/<service_name>', methods=['POST'])
def test_service(service_name):
    """Test a specific service transaction"""
    if IS_UI_APP:
        return _proxy_request('POST', service_name, 'test/', json=request.get_json() or {})
    return _handle_backend_request(service_name, 'test', data=request.get_json() or {})

@app.route('/api/list/<service_name>', methods=['GET'])
def list_service_resources(service_name):
    """List resources for a specific service"""
    if IS_UI_APP:
        return _proxy_request('GET', service_name, 'list/', params=request.args)
    
    # Build kwargs based on service type
    kwargs = {}
    if service_name in ['mysql', 'postgres']:
        table = request.args.get('table')
        if table:
            kwargs = {
                'table': table,
                'limit': int(request.args.get('limit', 100)),
                'offset': int(request.args.get('offset', 0))
            }
    elif service_name == 'valkey':
        kwargs = {
            'pattern': request.args.get('pattern', '*'),
            'limit': int(request.args.get('limit', 100))
        }
    elif service_name == 'rabbitmq':
        # RabbitMQ doesn't need any kwargs
        kwargs = {}
    
    return _handle_backend_request(service_name, 'list', **kwargs)

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

