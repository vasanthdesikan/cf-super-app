"""Helper module for discovering service credentials from VCAP_SERVICES"""

import os
import json

def find_service_credentials(service_types, service_name=None):
    """
    Find service credentials from VCAP_SERVICES.
    
    Supports:
    1. Tanzu Data Services (p.rabbitmq, p.mysql, etc.)
    2. User Provisioned Services (UPS/CUPS) - identified by name or tags
    3. Standard Cloud Foundry services
    4. Service-key format credentials
    
    Args:
        service_types: List of service type identifiers to search for
        service_name: Optional service name to match
    
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
    
    # Strategy 1: Look for Tanzu Data Services and standard service types
    for service_type in service_types:
        if service_type in vcap:
            services = vcap[service_type]
            if services and len(services) > 0:
                # If service_name specified, try to match
                if service_name:
                    for svc in services:
                        if svc.get('name') == service_name:
                            creds = svc.get('credentials', {})
                            if creds:
                                # Handle nested credentials (service-key format)
                                if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                                    creds = creds.get('credentials', {})
                                return creds
                # Otherwise return first service
                creds = services[0].get('credentials', {})
                if creds:
                    # Handle nested credentials (service-key format)
                    if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                        creds = creds.get('credentials', {})
                    return creds
    
    # Strategy 2: Look for User Provisioned Services (UPS/CUPS)
    if 'user-provided' in vcap:
        ups_services = vcap['user-provided']
        
        # First, try to match by service name (if provided)
        if service_name:
            for service in ups_services:
                if service.get('name') == service_name:
                    creds = service.get('credentials', {})
                    if creds:
                        # Handle nested credentials (service-key format)
                        if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                            creds = creds.get('credentials', {})
                        return creds
        
        # Then try to match by tags
        for service in ups_services:
            tags = service.get('tags', [])
            tag_list = [tag.lower() for tag in tags]
            
            for service_type in service_types:
                # Clean service type for comparison
                clean_type = service_type.replace('p.', '').replace('p-', '').replace('.', '-').lower()
                
                # Match various tag formats
                if (clean_type in tag_list or 
                    service_type.lower() in tag_list or
                    clean_type.replace('postgresql', 'postgres') in tag_list or
                    clean_type.replace('postgres', 'postgresql') in tag_list or
                    'database' in tag_list and clean_type in ['mysql', 'postgres', 'postgresql'] or
                    'cache' in tag_list and clean_type in ['redis', 'valkey'] or
                    'queue' in tag_list and clean_type in ['rabbitmq']):
                    creds = service.get('credentials', {})
                    if creds:
                        # Handle nested credentials (service-key format)
                        if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                            creds = creds.get('credentials', {})
                        return creds
        
        # Strategy 2b: Match by service name patterns (if no tags)
        # Check if service name contains the service type
        for service in ups_services:
            service_name_check = service.get('name', '').lower()
            for service_type in service_types:
                clean_type = service_type.replace('p.', '').replace('p-', '').replace('.', '-').lower()
                # Check if service name contains the service type
                if clean_type in service_name_check or service_type.lower() in service_name_check:
                    creds = service.get('credentials', {})
                    if creds:
                        # Handle nested credentials (service-key format)
                        if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                            creds = creds.get('credentials', {})
                        return creds
    
    # Strategy 3: Search all services by name (if provided)
    if service_name:
        for service_type, services in vcap.items():
            for service in services:
                if service.get('name') == service_name:
                    creds = service.get('credentials', {})
                    if creds:
                        # Handle nested credentials (service-key format)
                        if isinstance(creds, dict) and 'credentials' in creds and len(creds) == 1:
                            creds = creds.get('credentials', {})
                        return creds
    
    # Strategy 4: Match by credential patterns (most aggressive - works even without tags)
    # This handles cases where service might be bound but not tagged properly
    if 'user-provided' in vcap:
        ups_services = vcap['user-provided']
        for service in ups_services:
            creds = service.get('credentials', {})
            if not creds:
                continue
            # Handle nested credentials (service-key format)
            if isinstance(creds, dict) and 'credentials' in creds:
                # If credentials only has 'credentials' key, it's likely nested
                if len(creds) == 1 or all(k == 'credentials' for k in creds.keys() if k != 'credentials'):
                    creds = creds.get('credentials', {})
            
            # Check if credentials have fields that match service type
            for service_type in service_types:
                clean_type = service_type.replace('p.', '').replace('p-', '').replace('.', '-').lower()
                
                # Check for common credential patterns
                if clean_type in ['mysql', 'postgres', 'postgresql']:
                    # Database services should have hostname/host and database/name
                    # OR have a URI
                    has_host = creds.get('hostname') or creds.get('host')
                    has_db = creds.get('database') or creds.get('name') or creds.get('db')
                    has_uri = creds.get('uri') or creds.get('url') or creds.get('connection_string') or creds.get('connectionString')
                    
                    if has_uri or (has_host and has_db):
                        return creds
                elif clean_type in ['rabbitmq']:
                    # RabbitMQ should have hostname/host and vhost OR URI
                    has_host = creds.get('hostname') or creds.get('host')
                    has_vhost = creds.get('vhost')
                    has_uri = creds.get('uri') or creds.get('url') or creds.get('amqp_uri')
                    
                    if has_uri or (has_host and has_vhost):
                        return creds
                elif clean_type in ['redis', 'valkey']:
                    # Redis/Valkey should have hostname/host OR URI
                    if (creds.get('hostname') or creds.get('host') or 
                        creds.get('uri') or creds.get('url') or 
                        creds.get('redis_uri')):
                        return creds
    
    return None

def get_connection_params_from_creds(creds, default_host=None, default_port=None):
    """
    Extract connection parameters from credentials dictionary.
    Handles various credential formats including service-key formats.
    """
    if not creds:
        return {}
    
    # Handle nested credentials (service-key format: {'credentials': {...}})
    if isinstance(creds, dict):
        # If credentials only has 'credentials' key, unwrap it
        if 'credentials' in creds and (len(creds) == 1 or all(k == 'credentials' for k in creds.keys())):
            creds = creds.get('credentials', {})
        # Also check if it's a nested structure with other metadata
        elif 'credentials' in creds and isinstance(creds.get('credentials'), dict):
            # Prefer nested credentials if they exist
            nested_creds = creds.get('credentials', {})
            if nested_creds and len(nested_creds) > 0:
                creds = nested_creds
    
    if not creds:
        return {}
    
    params = {}
    
    # URI variations (prioritize these for user-provided services)
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
    
    # Host/hostname variations (only if URI not found)
    if not params.get('uri'):
        params['host'] = (
            creds.get('hostname') or 
            creds.get('host') or 
            creds.get('hostname_or_ip') or
            creds.get('hostName') or
            creds.get('HostName') or
            default_host
        )
        # Only default to localhost if explicitly provided
        if not params['host'] and default_host == 'localhost':
            params['host'] = 'localhost'
    
    # Port variations
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
    
    return params
