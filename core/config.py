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
        """Get only enabled services"""
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
        return self.services_config.get(service_name, {}).get('enabled', False)


# Singleton instance
config = ConfigManager()

