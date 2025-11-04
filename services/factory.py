"""Factory Pattern for Service Handler Creation"""

from typing import Optional, Type, Dict
import importlib

from .base_handler import ServiceHandler


class ServiceHandlerFactory:
    """Factory for creating service handlers"""
    
    _handler_registry: Dict[str, Dict[str, any]] = {
        'rabbitmq': {
            'module': 'services.rabbitmq_handler',
            'class': 'RabbitMQHandler',
            'service_types': ['p.rabbitmq', 'p-rabbitmq', 'rabbitmq']
        },
        'valkey': {
            'module': 'services.valkey_handler',
            'class': 'ValkeyHandler',
            'service_types': ['p.redis', 'p-redis', 'valkey', 'redis']
        },
        'mysql': {
            'module': 'services.mysql_handler',
            'class': 'MySQLHandler',
            'service_types': ['p.mysql', 'p-mysql', 'mysql']
        },
        'postgres': {
            'module': 'services.postgres_handler',
            'class': 'PostgresHandler',
            'service_types': ['p.postgresql', 'p-postgresql', 'postgresql', 'postgres']
        }
    }
    
    @classmethod
    def create(cls, service_name: str) -> Optional[ServiceHandler]:
        """
        Create a service handler instance
        
        Args:
            service_name: Name of the service (rabbitmq, valkey, mysql, postgres)
            
        Returns:
            ServiceHandler instance or None if creation fails
        """
        if service_name not in cls._handler_registry:
            return None
        
        config = cls._handler_registry[service_name]
        
        try:
            module = importlib.import_module(config['module'])
            handler_class = getattr(module, config['class'])
            return handler_class()
        except (ImportError, AttributeError):
            return None
        except Exception:
            # Retry once for credential loading errors
            try:
                module = importlib.import_module(config['module'])
                handler_class = getattr(module, config['class'])
                return handler_class()
            except Exception:
                return None
    
    @classmethod
    def get_registered_services(cls) -> list:
        """Get list of all registered service names"""
        return list(cls._handler_registry.keys())

