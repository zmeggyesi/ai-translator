"""
Configuration manager for the Translation GUI.
Handles saving and loading application settings.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


class ConfigurationManager:
    """Manages application configuration and persistence."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / ".translation-gui"
        self.config_file = self.config_dir / "config.json"
        self.default_config = {
            "window": {
                "width": 900,
                "height": 700,
                "maximized": False
            },
            "last_tab": 0,
            "recent_files": [],
            "default_languages": {
                "source": "en",
                "target": "es"
            },
            "resource_paths": {
                "glossary": "",
                "style_guide": "",
                "tmx": ""
            }
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default if not exists."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with default config to ensure all keys exist
                merged_config = self.default_config.copy()
                self._deep_update(merged_config, config)
                return merged_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_window_geometry(self) -> Dict[str, Any]:
        """Get window geometry settings."""
        return self.config["window"]
    
    def set_window_geometry(self, width: int, height: int, maximized: bool = False) -> None:
        """Set window geometry settings."""
        self.config["window"]["width"] = width
        self.config["window"]["height"] = height
        self.config["window"]["maximized"] = maximized
        self.save_config()
    
    def get_last_tab(self) -> int:
        """Get index of last selected tab."""
        return self.config["last_tab"]
    
    def set_last_tab(self, tab_index: int) -> None:
        """Set index of last selected tab."""
        self.config["last_tab"] = tab_index
        self.save_config()
    
    def get_recent_files(self) -> List[str]:
        """Get list of recently used files."""
        return self.config["recent_files"]
    
    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list."""
        if file_path in self.config["recent_files"]:
            self.config["recent_files"].remove(file_path)
        
        self.config["recent_files"].insert(0, file_path)
        
        # Keep only the 10 most recent files
        self.config["recent_files"] = self.config["recent_files"][:10]
        self.save_config()
    
    def get_default_languages(self) -> Dict[str, str]:
        """Get default source and target languages."""
        return self.config["default_languages"]
    
    def set_default_languages(self, source: str, target: str) -> None:
        """Set default source and target languages."""
        self.config["default_languages"]["source"] = source
        self.config["default_languages"]["target"] = target
        self.save_config()
    
    def get_resource_path(self, resource_type: str) -> str:
        """Get path for a specific resource type."""
        return self.config["resource_paths"].get(resource_type, "")
    
    def set_resource_path(self, resource_type: str, path: str) -> None:
        """Set path for a specific resource type."""
        self.config["resource_paths"][resource_type] = path
        self.save_config()
    
    def _deep_update(self, d: Dict, u: Dict) -> None:
        """Recursively update a dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v