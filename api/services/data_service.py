import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sys
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from api.core.logging import get_logger
from api.utils.exceptions import DataLoaderException, raise_data_error
from api.models.requests import SearchConfigRequest
from api.models.responses import SearchTemplate, ConfigData

class TemplateManager:
    """Manages search templates and configurations"""
    
    def __init__(self):
        self.logger = get_logger("api.template_manager")
        self.templates_dir = settings.project_root / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default search templates"""
        try:
            default_templates = self._get_default_template_configs()
            
            for template_name, template_config in default_templates.items():
                template_file = self.templates_dir / f"{template_name}.json"
                
                # Only create if doesn't exist
                if not template_file.exists():
                    self._save_template_to_file(template_name, template_config)
                    self.logger.info(f"Created default template: {template_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default templates: {str(e)}")
    
    def _get_default_template_configs(self) -> Dict[str, Dict]:
        """Get default template configurations"""
        return {
            "momentum_pump_12h": {
                "name": "Momentum Pump Detection (12h)",
                "description": "Detect momentum pumps in 12-hour timeframe",
                "timeframe": "12h",
                "start_date": "2022-01-01",
                "end_date": "2022-12-31",
                "lookback_periods": 100,
                "forward_periods": 6,
                "sample_limit": 500,
                "min_volume": 1000000,
                "exclude_new_listing_days": 7,
                "initial_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "price_change",
                        "operator": ">=",
                        "value": 0.10,
                        "description": "Price pump >= 10%"
                    },
                    {
                        "condition_type": "volume",
                        "parameter": "volume",
                        "operator": ">=",
                        "value": 1000000,
                        "description": "Volume >= 1M USDT"
                    }
                ],
                "advanced_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "future_max_drawdown",
                        "operator": ">=",
                        "value": -0.05,
                        "description": "Max drawdown <= 5%"
                    }
                ],
                "negative_sampling": True,
                "positive_negative_ratio": 2.0,
                "is_default": True
            },
            "momentum_pump_4h": {
                "name": "Momentum Pump Detection (4h)",
                "description": "Detect momentum pumps in 4-hour timeframe",
                "timeframe": "4h",
                "start_date": "2022-01-01",
                "end_date": "2022-12-31",
                "lookback_periods": 100,
                "forward_periods": 12,
                "sample_limit": 500,
                "min_volume": 500000,
                "exclude_new_listing_days": 7,
                "initial_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "price_change",
                        "operator": ">=",
                        "value": 0.08,
                        "description": "Price pump >= 8%"
                    }
                ],
                "advanced_conditions": [],
                "negative_sampling": True,
                "positive_negative_ratio": 1.5,
                "is_default": True
            },
            "low_volatility_consolidation": {
                "name": "Low Volatility Consolidation",
                "description": "Detect low volatility consolidation periods",
                "timeframe": "4h",
                "start_date": "2022-01-01",
                "end_date": "2022-12-31",
                "lookback_periods": 100,
                "forward_periods": 6,
                "sample_limit": 300,
                "min_volume": 100000,
                "exclude_new_listing_days": 7,
                "initial_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "price_change",
                        "operator": "between",
                        "value": [-0.02, 0.02],
                        "description": "Price change between -2% and 2%"
                    }
                ],
                "advanced_conditions": [
                    {
                        "condition_type": "price",
                        "parameter": "future2_close_return",
                        "operator": "between",
                        "value": [-0.03, 0.03],
                        "description": "Future return between -3% and 3%"
                    }
                ],
                "negative_sampling": False,
                "positive_negative_ratio": 1.0,
                "is_default": True
            }
        }
    
    def _save_template_to_file(self, template_name: str, template_config: Dict):
        """Save template configuration to file"""
        template_file = self.templates_dir / f"{template_name}.json"
        
        # Add metadata
        template_data = {
            "metadata": {
                "name": template_name,
                "created_at": datetime.now().isoformat(),
                "version": "1.0"
            },
            "config": template_config
        }
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    def get_all_templates(self) -> List[SearchTemplate]:
        """Get all available search templates"""
        templates = []
        
        try:
            for template_file in self.templates_dir.glob("*.json"):
                template_data = self._load_template_from_file(template_file)
                if template_data:
                    templates.append(template_data)
            
            return sorted(templates, key=lambda t: t.name)
            
        except Exception as e:
            self.logger.error(f"Failed to load templates: {str(e)}")
            return []
    
    def _load_template_from_file(self, template_file: Path) -> Optional[SearchTemplate]:
        """Load template from file"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            config = template_data.get("config", {})
            metadata = template_data.get("metadata", {})
            
            return SearchTemplate(
                name=config.get("name", template_file.stem),
                description=config.get("description", ""),
                config=config,
                is_default=config.get("is_default", False),
                created_at=datetime.fromisoformat(
                    metadata.get("created_at", datetime.now().isoformat())
                )
            )
            
        except Exception as e:
            self.logger.error(f"Failed to load template {template_file}: {str(e)}")
            return None
    
    def get_template(self, template_name: str) -> Optional[SearchTemplate]:
        """Get specific template by name"""
        template_file = self.templates_dir / f"{template_name}.json"
        
        if template_file.exists():
            return self._load_template_from_file(template_file)
        return None
    
    def save_template(self, template_name: str, config: SearchConfigRequest) -> bool:
        """Save new template"""
        try:
            template_config = config.dict()
            template_config["name"] = template_name
            template_config["is_default"] = False
            
            self._save_template_to_file(template_name, template_config)
            self.logger.info(f"Saved template: {template_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save template {template_name}: {str(e)}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """Delete template (only non-default templates)"""
        try:
            template = self.get_template(template_name)
            if template and not template.is_default:
                template_file = self.templates_dir / f"{template_name}.json"
                template_file.unlink()
                self.logger.info(f"Deleted template: {template_name}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete template {template_name}: {str(e)}")
            return False

class ConfigManager:
    """Manages system configuration"""
    
    def __init__(self):
        self.logger = get_logger("api.config_manager")
    
    def get_current_config(self) -> ConfigData:
        """Get current system configuration"""
        return ConfigData(
            max_concurrent_searches=settings.max_concurrent_searches,
            search_timeout_seconds=settings.search_timeout_seconds,
            enable_cache=settings.enable_cache,
            cache_ttl_seconds=settings.cache_ttl_seconds,
            supported_timeframes=["1h", "4h", "12h", "1d"],
            max_lookback_periods=500,
            max_sample_limit=5000
        )
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update system configuration (runtime only)"""
        try:
            # Update settings in memory (note: these won't persist across restarts)
            for key, value in updates.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
                    self.logger.info(f"Updated config {key} = {value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {str(e)}")
            return False

class DataService:
    """Main data service for managing templates and configuration"""
    
    def __init__(self):
        self.logger = get_logger("api.data_service")
        self.template_manager = TemplateManager()
        self.config_manager = ConfigManager()
    
    def get_templates(self) -> List[SearchTemplate]:
        """Get all search templates"""
        return self.template_manager.get_all_templates()
    
    def get_template(self, template_name: str) -> Optional[SearchTemplate]:
        """Get specific template"""
        return self.template_manager.get_template(template_name)
    
    def save_template(self, template_name: str, config: SearchConfigRequest) -> bool:
        """Save new template"""
        return self.template_manager.save_template(template_name, config)
    
    def delete_template(self, template_name: str) -> bool:
        """Delete template"""
        return self.template_manager.delete_template(template_name)
    
    def get_config(self) -> ConfigData:
        """Get system configuration"""
        return self.config_manager.get_current_config()
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update system configuration"""
        return self.config_manager.update_config(updates)
    
    def validate_symbol_list(self, symbols: List[str]) -> List[str]:
        """Validate and filter symbol list"""
        # Basic validation - ensure USDT pairs
        valid_symbols = []
        
        for symbol in symbols:
            symbol = symbol.upper().strip()
            if symbol.endswith('USDT') and len(symbol) > 4:
                valid_symbols.append(symbol)
            else:
                self.logger.warning(f"Invalid symbol format: {symbol}")
        
        return valid_symbols
    
    def get_market_phase(self, timestamp: datetime) -> str:
        """Get market phase for given timestamp"""
        try:
            # Import here to avoid circular imports
            from momentum.DataExtraction.Market_Screener_Configuration import MarketConfig
            return MarketConfig.get_market_phase(timestamp)
        except Exception as e:
            self.logger.error(f"Failed to get market phase: {str(e)}")
            return "UNKNOWN"

# Global service instance
data_service = DataService()

# Export
__all__ = ["DataService", "data_service", "TemplateManager", "ConfigManager"]