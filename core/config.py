"""Configuration Management Pattern"""

import os
import yaml
from typing import Dict, Any
from functools import lru_cache


class ConfigManager:
    """Singleton pattern for configuration management"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    @property
    def services_config(self) -> Dict[str, Any]:
        """Get services configuration"""
        if self._config is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'services-config.yml'
            )
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        return self._config.get('services', {})
    
    def get_enabled_services(self) -> Dict[str, Any]:
        """Get all services for UI display (all tabs shown)"""
        # Always show all services in the UI, regardless of which app instance this is
        # Each app instance will only handle its own service, but the UI shows all tabs
        return {
            key: {
                'display_name': value.get('display_name', key.title()),
                'enabled': value.get('enabled', False)
            }
            for key, value in self.services_config.items()
            if value.get('enabled', False)
        }
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled"""
        # Check if service is enabled in config
        if not self.services_config.get(service_name, {}).get('enabled', False):
            return False
        
        # If we're in Cloud Foundry, check if this app handles this service
        # Each app instance only handles its own service type
        vcap_app = os.environ.get('VCAP_APPLICATION', '{}')
        if vcap_app and vcap_app != '{}':
            try:
                import json
                app_info = json.loads(vcap_app)
                app_name = app_info.get('application_name', '')
                
                # Map app names to service types
                app_service_map = {
                    'service-tester-postgres': 'postgres',
                    'service-tester-mysql': 'mysql',
                    'service-tester-rabbitmq': 'rabbitmq',
                    'service-tester-valkey': 'valkey'
                }
                
                # Get the service this app should handle
                app_service = app_service_map.get(app_name)
                
                # Only enable this service if it matches the app's service
                if app_service and app_service == service_name:
                    return True
                elif app_service:
                    # This app handles a different service, disable this one
                    return False
                # If app name not in map, allow all services (for local development)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Default: return config value (for local development)
        return self.services_config.get(service_name, {}).get('enabled', False)


# Singleton instance
config = ConfigManager()

