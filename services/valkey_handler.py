"""Valkey (Redis-compatible) Service Handler"""

import redis
from datetime import datetime
from .base_handler import CacheHandler

class ValkeyHandler(CacheHandler):
    """Handler for Valkey transactions"""
    
    def __init__(self):
        """Initialize Valkey connection"""
        super().__init__(
            service_types=['p.redis', 'p-redis', 'valkey', 'redis'],
            default_port=6379,
            env_prefix='VALKEY'
        )
        self.client = None
    
    def _get_client(self):
        """Get or create Valkey client"""
        # Check if credentials were loaded, if not, try to load them now
        if not self._credentials_loaded:
            try:
                self._load_credentials(self.service_types)
                self._credentials_loaded = True
                if hasattr(self, '_credential_error'):
                    delattr(self, '_credential_error')
            except Exception as e:
                error_msg = getattr(self, '_credential_error', str(e))
                raise Exception(f"Cannot connect to Valkey: {error_msg}")
        
        if self.client is None:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5
            )
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
    
    def list_keys(self, pattern='*', limit=100):
        """List keys in the cache"""
        try:
            client = self._get_client()
            
            # Get keys matching pattern
            keys = client.keys(pattern)
            
            # Limit results
            if limit and len(keys) > limit:
                keys = keys[:limit]
            
            # Get key info (value, TTL)
            key_list = []
            for key in keys:
                ttl = client.ttl(key)
                key_type = client.type(key)
                key_info = {
                    'key': key,
                    'type': key_type,
                    'ttl': ttl if ttl > 0 else None,
                    'exists': True
                }
                
                # Get value preview (first 100 chars)
                if key_type == 'string':
                    value = client.get(key)
                    if value:
                        key_info['value_preview'] = value[:100] + ('...' if len(value) > 100 else '')
                
                key_list.append(key_info)
            
            return {
                'pattern': pattern,
                'keys': key_list,
                'count': len(key_list),
                'total_found': len(client.keys(pattern)) if not limit else None
            }
        except Exception as e:
            raise Exception(f"Failed to list Valkey keys: {str(e)}")
    
    def delete_key(self, key):
        """Delete a key from the cache"""
        try:
            client = self._get_client()
            result = client.delete(key)
            return {
                'action': 'delete',
                'key': key,
                'deleted': result > 0,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to delete Valkey key: {str(e)}")
    
    def get_key(self, key):
        """Get a key's value from the cache (READ)"""
        try:
            client = self._get_client()
            value = client.get(key)
            key_type = client.type(key)
            ttl = client.ttl(key)
            
            return {
                'action': 'get',
                'key': key,
                'value': value,
                'type': key_type,
                'ttl': ttl if ttl > 0 else None,
                'exists': value is not None,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to get Valkey key: {str(e)}")
    
    def set_key(self, key, value, ttl=None):
        """Set a key's value in the cache (CREATE/UPDATE)"""
        try:
            client = self._get_client()
            
            if ttl:
                result = client.setex(key, ttl, value)
            else:
                result = client.set(key, value)
            
            return {
                'action': 'set',
                'key': key,
                'value': value,
                'ttl': ttl,
                'result': result,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to set Valkey key: {str(e)}")
    
    def exists_key(self, key):
        """Check if a key exists"""
        try:
            client = self._get_client()
            exists = client.exists(key)
            
            return {
                'action': 'exists',
                'key': key,
                'exists': exists > 0,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to check Valkey key existence: {str(e)}")

