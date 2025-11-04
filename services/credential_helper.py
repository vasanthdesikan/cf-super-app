"""Helper module for discovering service credentials from VCAP_SERVICES"""

import os
import json

def find_service_credentials(service_types, service_name=None):
    """
    Find service credentials from VCAP_SERVICES.
    
    Supports:
    1. Tanzu Data Services (p.rabbitmq, p.mysql, etc.)
    2. User Provisioned Services (UPS) - identified by name or tags
    3. Standard Cloud Foundry services
    4. Environment variables as fallback
    
    Args:
        service_types: List of service type identifiers to search for
        service_name: Optional service name to match (for UPS)
    
    Returns:
        dict: Service credentials or None if not found
    """
    vcap_services = os.environ.get('VCAP_SERVICES', '{}')
    
    if not vcap_services:
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
                            return svc.get('credentials', {})
                # Otherwise return first service
                return services[0].get('credentials', {})
    
    # Strategy 2: Look for User Provisioned Services (UPS/CUPS)
    if 'user-provided' in vcap:
        ups_services = vcap['user-provided']
        for service in ups_services:
            # Match by service name (if provided)
            if service_name and service.get('name') == service_name:
                return service.get('credentials', {})
            # Match by tags (common convention: service type in tags)
            if not service_name:  # Only match by tags if no specific name requested
                tags = service.get('tags', [])
                for service_type in service_types:
                    # Clean service type for comparison (remove dots, hyphens, prefixes)
                    clean_type = service_type.replace('p.', '').replace('p-', '').replace('.', '-').lower()
                    tag_list = [tag.lower() for tag in tags]
                    # Match various tag formats
                    if (clean_type in tag_list or 
                        service_type.lower() in tag_list or
                        clean_type.replace('postgresql', 'postgres') in tag_list or
                        clean_type.replace('postgres', 'postgresql') in tag_list):
                        return service.get('credentials', {})
    
    # Strategy 3: Search all services by name (if provided)
    if service_name:
        for service_type, services in vcap.items():
            for service in services:
                if service.get('name') == service_name:
                    return service.get('credentials', {})
    
    return None

def get_connection_params_from_creds(creds, default_host=None, default_port=None):
    """
    Extract connection parameters from credentials dictionary.
    Handles various credential formats.
    """
    params = {}
    
    # Host/hostname variations - only use default if explicitly provided
    params['host'] = (
        creds.get('hostname') or 
        creds.get('host') or 
        creds.get('hostname_or_ip') or
        default_host
    )
    # Only default to localhost if default_host was explicitly 'localhost'
    if not params['host'] and default_host == 'localhost':
        params['host'] = 'localhost'
    
    # Port variations
    port_value = (
        creds.get('port') or 
        creds.get('ssl_port') or
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
        None
    )
    
    # Password variations
    params['password'] = (
        creds.get('password') or 
        creds.get('pass') or
        None
    )
    
    # Database/name variations
    params['database'] = (
        creds.get('database') or 
        creds.get('db') or 
        creds.get('name') or
        creds.get('db_name') or
        None
    )
    
    # URI variations (parse if available) - prioritize these for user-provided services
    uri = (
        creds.get('uri') or 
        creds.get('url') or 
        creds.get('connection_string') or
        creds.get('connectionString') or
        creds.get('jdbcUrl') or
        creds.get('jdbc_url')
    )
    if uri:
        params['uri'] = uri
    
    # Additional common fields
    params['vhost'] = creds.get('vhost', '/')
    params['ssl'] = creds.get('ssl', False)
    params['ssl_ca'] = creds.get('ssl_ca')
    
    return params

