"""Valkey (Redis-compatible) Service Handler"""

import os
import json
import redis
from datetime import datetime
from urllib.parse import urlparse
from .credential_helper import find_service_credentials, get_connection_params_from_creds

class ValkeyHandler:
    """Handler for Valkey transactions"""
    
    def __init__(self):
        """Initialize Valkey connection"""
        # Service types to search for (Tanzu Data Services and standard)
        service_types = [
            'p.redis',          # Tanzu Data Services
            'p-redis',          # Standard Cloud Foundry
            'p.redis-for-kubernetes',
            'redis',
            'valkey',
            'p.valkey'
        ]
        
        # Try to find credentials from VCAP_SERVICES (supports Tanzu and UPS)
        creds = find_service_credentials(service_types)
        
        if creds:
            # Check if URI is available (common in Tanzu services)
            uri = creds.get('uri') or creds.get('url') or creds.get('redis_uri')
            if uri:
                parsed = urlparse(uri)
                self.host = parsed.hostname or 'localhost'
                self.port = parsed.port or 6379
                # Password might be in URI or separate
                self.password = parsed.password or creds.get('password')
            else:
                # Extract from credential dictionary
                params = get_connection_params_from_creds(creds, 'localhost', 6379)
                self.host = params['host']
                self.port = params['port'] or 6379
                self.password = params['password']
        else:
            # Fallback to environment variables
            self.host = os.environ.get('VALKEY_HOST', 'localhost')
            self.port = int(os.environ.get('VALKEY_PORT', 6379))
            self.password = os.environ.get('VALKEY_PASSWORD', None)
        
        self.client = None
    
    def _get_client(self):
        """Get or create Valkey client"""
        if self.client is None:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
        return self.client
    
    def test_transaction(self, data=None):
        """Test Valkey transaction (set and get)"""
        if data is None:
            data = {}
        
        key = data.get('key', 'test_key')
        value = data.get('value', f'Test value at {datetime.now().isoformat()}')
        
        try:
            client = self._get_client()
            
            # Set value
            client.set(key, value)
            
            # Get value
            retrieved_value = client.get(key)
            
            # Additional operations
            client.expire(key, 60)  # Set expiration
            ttl = client.ttl(key)
            
            return {
                'action': 'set_and_get',
                'key': key,
                'set_value': value,
                'retrieved_value': retrieved_value,
                'ttl': ttl,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Valkey transaction failed: {str(e)}")

