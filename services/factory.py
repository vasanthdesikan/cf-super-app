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
            # Create handler - it should handle credential loading errors gracefully
            handler = handler_class()
            return handler
        except ImportError as e:
            # Import errors are real problems
            return None
        except AttributeError as e:
            # Attribute errors are real problems
            return None
        except Exception as e:
            # For other exceptions (like credential errors), still create the handler
            # The handler's __init__ should catch these and store them
            # But if it doesn't, log and try to create anyway
            try:
                module = importlib.import_module(config['module'])
                handler_class = getattr(module, config['class'])
                # Force creation - handler should handle errors internally
                handler = handler_class()
                return handler
            except Exception as e2:
                # If we still can't create, it's a real problem
                return None
    
    @classmethod
    def get_registered_services(cls) -> list:
        """Get list of all registered service names"""
        return list(cls._handler_registry.keys())

