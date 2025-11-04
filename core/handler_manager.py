"""Service Handler Manager with Dependency Injection"""

from typing import Dict, Optional
import logging

from services.factory import ServiceHandlerFactory
from core.config import config
from core.exceptions import ServiceNotFoundError, ServiceConnectionError


logger = logging.getLogger(__name__)


class HandlerManager:
    """Manages service handler lifecycle and provides dependency injection"""
    
    def __init__(self):
        self._handlers: Dict[str, Optional[object]] = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialize all enabled service handlers"""
        for service_name in ServiceHandlerFactory.get_registered_services():
            if config.is_service_enabled(service_name):
                try:
                    handler = ServiceHandlerFactory.create(service_name)
                    self._handlers[service_name] = handler
                    if handler is None:
                        logger.warning(f"Failed to create handler for {service_name}")
                    else:
                        logger.info(f"Successfully initialized handler for {service_name}")
                except Exception as e:
                    # Log the error but still allow handler creation - fail at connection time instead
                    logger.warning(f"Handler initialization warning for {service_name}: {e}")
                    # Try to create handler anyway - errors will surface at connection time
                    try:
                        handler = ServiceHandlerFactory.create(service_name)
                        self._handlers[service_name] = handler
                    except Exception as e2:
                        logger.error(f"Failed to initialize {service_name}: {e2}")
                        self._handlers[service_name] = None
            else:
                self._handlers[service_name] = None
    
    def get_handler(self, service_name: str):
        """
        Get service handler (dependency injection)
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service handler instance
            
        Raises:
            ServiceNotFoundError: If service is not enabled or not found
        """
        if service_name not in self._handlers:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        handler = self._handlers[service_name]
        if handler is None:
            raise ServiceNotFoundError(f"Service {service_name} is not enabled or initialized")
        
        return handler
    
    @property
    def handlers(self) -> Dict[str, Optional[object]]:
        """Get all handlers (for backward compatibility)"""
        return self._handlers

