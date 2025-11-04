"""Base Service Handler with common functionality"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import os

from .credential_helper import find_service_credentials, get_connection_params_from_creds


class ServiceHandler(ABC):
    """Abstract base class for all service handlers"""
    
    def __init__(self, service_types: list, default_port: int, env_prefix: str):
        """
        Initialize service handler with credential discovery
        
        Args:
            service_types: List of service type identifiers to search for
            default_port: Default port for the service
            env_prefix: Environment variable prefix (e.g., 'RABBITMQ' for RABBITMQ_HOST)
        """
        self.default_port = default_port
        self.env_prefix = env_prefix
        self.service_types = service_types
        self._credentials_loaded = False
        self._credential_error = None
        
        # Try to load credentials, but don't fail if not available
        # This allows handlers to be created even if credentials aren't available yet
        try:
            self._load_credentials(service_types)
            self._credentials_loaded = True
        except Exception as e:
            # Store error to show later when connection is attempted
            self._credential_error = str(e)
            self._credentials_loaded = False
    
    def _load_credentials(self, service_types: list):
        """Load credentials from VCAP_SERVICES or environment variables"""
        creds = find_service_credentials(service_types)
        
        if creds:
            # First check if URI is available (prioritize URI for user-provided services)
            uri = self._extract_uri(creds)
            if uri:
                self._parse_uri(uri)
                return
            
            # Also check if URI is in params (from get_connection_params_from_creds)
            params = get_connection_params_from_creds(creds, None, self.default_port)
            if params.get('uri'):
                self._parse_uri(params['uri'])
                return
            
            # If no URI, use individual fields but don't default host to localhost
            try:
                self._parse_credentials(creds)
            except ValueError as e:
                # If parsing fails, raise a more helpful error
                raise ValueError(
                    f"Unable to find connection information in service credentials. "
                    f"Expected URI (uri/url/connection_string) or hostname. "
                    f"Available credential keys: {list(creds.keys())}. "
                    f"Error: {str(e)}"
                )
        else:
            # No credentials found - try environment variables as fallback
            env_host = os.environ.get(f'{self.env_prefix}_HOST')
            if env_host:
                self._load_from_env()
            else:
                # Don't raise error here - allow handler to be created
                # Error will be shown when connection is attempted
                raise ValueError(
                    f"Service not found in VCAP_SERVICES and no {self.env_prefix}_HOST environment variable. "
                    f"Please bind a service or set environment variables. "
                    f"Looking for service types: {service_types}"
                )
    
    def _extract_uri(self, creds: Dict[str, Any]) -> Optional[str]:
        """Extract URI from credentials (override in subclasses)"""
        return (
            creds.get('uri') or 
            creds.get('url') or 
            creds.get('connection_string') or
            creds.get('connectionString') or
            creds.get('connection_uri') or
            creds.get('connectionUri')
        )
    
    def _parse_uri(self, uri: str):
        """Parse URI (override in subclasses for specific parsing)"""
        parsed = urlparse(uri)
        if not parsed.hostname:
            raise ValueError(f"URI does not contain a hostname: {uri}")
        self.host = parsed.hostname
        self.port = parsed.port or self.default_port
    
    def _parse_credentials(self, creds: Dict[str, Any]):
        """Parse credentials dictionary (override in subclasses)"""
        params = get_connection_params_from_creds(creds, None, self.default_port)
        self.host = params.get('host')
        self.port = params.get('port') or self.default_port
        
        # If no host found, raise error
        if not self.host:
            raise ValueError(f"No hostname found in credentials. Available keys: {list(creds.keys())}")
    
    def _load_from_env(self):
        """Load from environment variables"""
        env_host = os.environ.get(f'{self.env_prefix}_HOST')
        if not env_host:
            raise ValueError(
                f"Environment variable {self.env_prefix}_HOST is not set. "
                f"Cannot connect to service without host information."
            )
        self.host = env_host
        port_str = os.environ.get(f'{self.env_prefix}_PORT', str(self.default_port))
        self.port = int(port_str)
    
    @abstractmethod
    def test_transaction(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test a transaction with the service"""
        pass


class DatabaseHandler(ServiceHandler):
    """Base class for database handlers (MySQL, PostgreSQL)"""
    
    def _extract_uri(self, creds: Dict[str, Any]) -> Optional[str]:
        """Extract database URI"""
        return (
            creds.get('uri') or 
            creds.get('url') or 
            creds.get('connection_string') or
            creds.get('connectionString') or
            creds.get('connection_uri') or
            creds.get('connectionUri') or
            creds.get('jdbcUrl') or 
            creds.get('jdbc_url') or
            creds.get('jdbc_uri') or
            creds.get('jdbcUri')
        )
    
    def _parse_uri(self, uri: str):
        """Parse database URI"""
        from urllib.parse import unquote
        # Store original URI for direct connection
        self._connection_uri = uri
        # Also parse for individual fields as fallback
        parsed = urlparse(uri.replace('mysql2://', 'mysql://').replace('postgres://', 'postgresql://'))
        if not parsed.hostname:
            raise ValueError(f"Database URI does not contain a hostname: {uri}")
        self.host = parsed.hostname
        self.port = parsed.port or self.default_port
        self.username = unquote(parsed.username) if parsed.username else None
        self.password = unquote(parsed.password) if parsed.password else ''
        self.database = parsed.path.lstrip('/') if parsed.path else None
    
    def _parse_credentials(self, creds: Dict[str, Any]):
        """Parse database credentials"""
        # Don't default host to localhost - only use if explicitly provided
        params = get_connection_params_from_creds(creds, None, self.default_port)
        self.host = params.get('host') if params.get('host') else None
        self.port = params.get('port') or self.default_port
        self.username = params.get('username')
        self.password = params.get('password') or ''
        self.database = params.get('database')
        
        # If no host found, raise error to prevent localhost fallback
        if not self.host:
            raise ValueError(f"No connection information found in credentials. Expected URI or hostname. Found keys: {list(creds.keys())}")
    
    def _load_from_env(self):
        """Load database config from environment"""
        super()._load_from_env()
        self.username = os.environ.get(f'{self.env_prefix}_USER')
        self.password = os.environ.get(f'{self.env_prefix}_PASSWORD', '')
        self.database = os.environ.get(f'{self.env_prefix}_DATABASE')


class CacheHandler(ServiceHandler):
    """Base class for cache handlers (Valkey)"""
    
    def _extract_uri(self, creds: Dict[str, Any]) -> Optional[str]:
        """Extract cache URI"""
        return creds.get('uri') or creds.get('url') or creds.get('redis_uri')
    
    def _parse_uri(self, uri: str):
        """Parse cache URI"""
        parsed = urlparse(uri)
        self.host = parsed.hostname or 'localhost'
        self.port = parsed.port or self.default_port
        self.password = parsed.password or None
    
    def _parse_credentials(self, creds: Dict[str, Any]):
        """Parse cache credentials"""
        params = get_connection_params_from_creds(creds, 'localhost', self.default_port)
        self.host = params['host']
        self.port = params.get('port') or self.default_port
        self.password = params.get('password')
    
    def _load_from_env(self):
        """Load cache config from environment"""
        super()._load_from_env()
        self.password = os.environ.get(f'{self.env_prefix}_PASSWORD')


class MessageQueueHandler(ServiceHandler):
    """Base class for message queue handlers (RabbitMQ)"""
    
    def _extract_uri(self, creds: Dict[str, Any]) -> Optional[str]:
        """Extract RabbitMQ URI"""
        return creds.get('uri') or creds.get('url') or creds.get('amqp_uri')
    
    def _parse_uri(self, uri: str):
        """Parse RabbitMQ URI"""
        parsed = urlparse(uri)
        self.host = parsed.hostname or 'localhost'
        self.port = parsed.port or self.default_port
        self.username = parsed.username or 'guest'
        self.password = parsed.password or 'guest'
        self.vhost = parsed.path.lstrip('/') if parsed.path else '/'
    
    def _parse_credentials(self, creds: Dict[str, Any]):
        """Parse RabbitMQ credentials"""
        params = get_connection_params_from_creds(creds, 'localhost', self.default_port)
        self.host = params['host']
        self.port = params.get('port') or self.default_port
        self.username = params.get('username') or 'guest'
        self.password = params.get('password') or 'guest'
        self.vhost = params.get('vhost') or '/'
    
    def _load_from_env(self):
        """Load RabbitMQ config from environment"""
        super()._load_from_env()
        self.username = os.environ.get(f'{self.env_prefix}_USER', 'guest')
        self.password = os.environ.get(f'{self.env_prefix}_PASS', 'guest')
        self.vhost = os.environ.get(f'{self.env_prefix}_VHOST', '/')

