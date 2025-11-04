"""Configuration Management"""

import os
import yaml
from typing import Dict, Any


class ConfigManager:
    """Singleton configuration manager"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def services_config(self) -> Dict[str, Any]:
        """Get services configuration (cached)"""
        if self._config is None:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services-config.yml')
            with open(path, 'r') as f:
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
        if not self.services_config.get(service_name, {}).get('enabled', False):
            return False
        
        # In CF: only enable service matching this app
        vcap = os.environ.get('VCAP_APPLICATION', '{}')
        if vcap and vcap != '{}':
            try:
                import json
                app_name = json.loads(vcap).get('application_name', '')
                app_service = {
                    'service-tester-postgres': 'postgres',
                    'service-tester-mysql': 'mysql',
                    'service-tester-rabbitmq': 'rabbitmq',
                    'service-tester-valkey': 'valkey'
                }.get(app_name)
                if app_service:
                    return app_service == service_name
            except (json.JSONDecodeError, KeyError):
                pass
        
        return self.services_config.get(service_name, {}).get('enabled', False)


# Singleton instance
config = ConfigManager()

