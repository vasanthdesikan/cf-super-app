"""Helper module for discovering service credentials from VCAP_SERVICES"""

import os
import json

def _unwrap_nested_credentials(creds, max_depth=5):
    """
    Unwrap nested credentials structure recursively.
    Handles formats like {'credentials': {...}} or deeply nested structures.
    """
    if not creds or not isinstance(creds, dict) or max_depth <= 0:
        return creds
    
    # Connection-related keys that indicate we've found actual credentials
    connection_keys = ['hostname', 'host', 'uri', 'url', 'connection_string', 'connectionString',
                       'username', 'user', 'userName', 'password', 'pass', 'Password',
                       'database', 'db', 'name', 'databaseName', 'db_name',
                       'port', 'Port', 'vhost', 'vHost', 'VHost',
                       'jdbcUrl', 'jdbc_url', 'jdbc_uri', 'connectionUri', 'connection_uri',
                       'amqp_uri', 'redis_uri', 'ssl', 'ssl_ca', 'service_gateway']
    
    # Check if current level has connection keys (we've found actual credentials)
    if any(key in creds for key in connection_keys):
        return creds
    
    # If 'credentials' key exists, unwrap it
    if 'credentials' in creds:
        nested = creds.get('credentials')
        if isinstance(nested, dict):
            unwrapped = _unwrap_nested_credentials(nested, max_depth - 1)
            if unwrapped and isinstance(unwrapped, dict):
                if any(key in unwrapped for key in connection_keys):
                    return unwrapped
                if 'credentials' in unwrapped and len(unwrapped) == 1:
                    return _unwrap_nested_credentials(unwrapped.get('credentials'), max_depth - 1)
                return unwrapped if unwrapped else creds
    
    # If only has 'credentials' key and nothing else, unwrap it
    if len(creds) == 1 and 'credentials' in creds:
        nested = creds.get('credentials')
        if isinstance(nested, dict):
            return _unwrap_nested_credentials(nested, max_depth - 1)
    
    return creds

def find_service_credentials(service_types, service_name=None):
    """
    Find service credentials from VCAP_SERVICES.
    
    Simple approach: Each app is bound to ONE service with a matching name.
    - service-tester-postgres app → service-tester-postgres service
    - service-tester-mysql app → service-tester-mysql service
    - service-tester-rabbitmq app → service-tester-rabbitmq service
    - service-tester-valkey app → service-tester-valkey service
    
    Args:
        service_types: List of service type identifiers (used to determine expected service name)
        service_name: Optional exact service instance name to match
    
    Returns:
        dict: Service credentials or None if not found
    """
    vcap_services = os.environ.get('VCAP_SERVICES', '{}')
    
    if not vcap_services or vcap_services == '{}':
        return None
    
    try:
        vcap = json.loads(vcap_services)
    except json.JSONDecodeError:
        return None
    
    # Map service types to expected service instance names
    service_name_map = {
        'postgres': 'service-tester-postgres',
        'postgresql': 'service-tester-postgres',
        'mysql': 'service-tester-mysql',
        'rabbitmq': 'service-tester-rabbitmq',
        'redis': 'service-tester-valkey',
        'valkey': 'service-tester-valkey'
    }
    
    # Determine expected service name
    expected_service_name = service_name
    if not expected_service_name:
        # Find the expected service name from service types
        for st in service_types:
            clean_type = st.replace('p.', '').replace('p-', '').replace('.', '-').lower()
            if clean_type in service_name_map:
                expected_service_name = service_name_map[clean_type]
                break
    
    if not expected_service_name:
        return None
    
    # Search all services in VCAP_SERVICES for the expected service name
    for service_type, services in vcap.items():
        for service in services:
            if service.get('name') == expected_service_name:
                creds = service.get('credentials', {})
                if creds:
                    creds = _unwrap_nested_credentials(creds)
                    if creds:
                        return creds
    
    # Not found
    return None

def get_connection_params_from_creds(creds, default_host=None, default_port=None):
    """
    Extract connection parameters from credentials dictionary.
    Handles various credential formats including URIs, connection strings, and structured credentials.
    
    Args:
        creds: Credentials dictionary
        default_host: Default hostname if not found in credentials
        default_port: Default port if not found in credentials
    
    Returns:
        dict: Connection parameters with keys: host, port, username, password, database, uri, etc.
    """
    if not creds:
        return {}
    
    # Unwrap nested credentials first
    creds = _unwrap_nested_credentials(creds)
    
    if not creds:
        return {}
    
    params = {}
    
    # Priority 1: URI extraction (highest priority - use URI directly)
    # For PostgreSQL: prefer service_gateway.uri
    # For MySQL: prefer top-level uri
    # If only URI is present, use that
    
    # Check for service_gateway URI first (for PostgreSQL)
    service_gateway = creds.get('service_gateway', {})
    if isinstance(service_gateway, dict) and service_gateway:
        if service_gateway.get('uri'):
            params['uri'] = service_gateway.get('uri')
        elif service_gateway.get('jdbcUrl'):
            params['uri'] = service_gateway.get('jdbcUrl')
    
    # If no service_gateway URI, check top-level URI (for MySQL or fallback)
    if not params.get('uri'):
        uri = (
            creds.get('uri') or 
            creds.get('url') or 
            creds.get('connection_string') or
            creds.get('connectionString') or
            creds.get('jdbcUrl') or 
            creds.get('jdbc_url') or
            creds.get('connection_uri') or
            creds.get('connectionUri')
        )
        if uri:
            params['uri'] = uri
    
    # Host/hostname variations (extract for fallback, but URI takes precedence)
    if not params.get('host'):
        # Handle hosts array (CUPS format)
        hosts = creds.get('hosts')
        if isinstance(hosts, list) and len(hosts) > 0:
            params['host'] = hosts[0]
        else:
            # Try service_gateway host first (for PostgreSQL)
            if isinstance(service_gateway, dict) and service_gateway.get('host'):
                params['host'] = service_gateway.get('host')
            else:
                params['host'] = (
                    creds.get('hostname') or 
                    creds.get('host') or 
                    creds.get('primary_host') or
                    creds.get('hostname_or_ip') or
                    creds.get('hostName') or
                    creds.get('HostName') or
                    default_host
                )
                if not params['host'] and default_host == 'localhost':
                    params['host'] = 'localhost'
    
    # Port variations (extract for fallback, but URI takes precedence)
    if not params.get('port'):
        if isinstance(service_gateway, dict) and service_gateway.get('port'):
            try:
                params['port'] = int(service_gateway.get('port'))
            except (ValueError, TypeError):
                pass
        
        if not params.get('port'):
            port_value = (
                creds.get('port') or 
                creds.get('ssl_port') or
                creds.get('Port') or
                default_port
            )
            if port_value:
                try:
                    params['port'] = int(port_value)
                except (ValueError, TypeError):
                    params['port'] = default_port or None
    
    # Username/user variations
    params['username'] = (
        creds.get('username') or 
        creds.get('user') or 
        creds.get('user_id') or
        creds.get('userName') or
        creds.get('UserName') or
        None
    )
    
    # Password variations
    params['password'] = (
        creds.get('password') or 
        creds.get('pass') or
        creds.get('Password') or
        None
    )
    
    # Database/name variations
    params['database'] = (
        creds.get('database') or 
        creds.get('db') or 
        creds.get('name') or
        creds.get('db_name') or
        creds.get('databaseName') or
        creds.get('Database') or
        None
    )
    
    # Additional common fields
    params['vhost'] = creds.get('vhost') or creds.get('vHost') or creds.get('VHost') or '/'
    params['ssl'] = creds.get('ssl') or creds.get('SSL') or False
    params['ssl_ca'] = creds.get('ssl_ca') or creds.get('sslCa') or creds.get('SSL_CA')
    
    # Handle TLS cert from nested structure (CUPS format)
    tls = creds.get('tls', {})
    if isinstance(tls, dict):
        cert = tls.get('cert', {})
        if isinstance(cert, dict) and cert.get('ca'):
            params['ssl_ca'] = cert.get('ca')
    
    return params
