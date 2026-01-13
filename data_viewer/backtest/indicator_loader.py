"""
Indicator Loader
Discovers and loads indicators from the indicators/ folder
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Path to indicators folder (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDICATORS_DIR = PROJECT_ROOT / "indicators"

# Reference project paths (for loading strategies from development project)
try:
    from data_viewer.config import REFERENCE_PROJECT_PATH, REFERENCE_STRATEGY_DIR, REFERENCE_INDICATORS_DIR
except ImportError:
    REFERENCE_PROJECT_PATH = Path("D:/DEV__PHASE---2 MC-META-TRADER-----")
    REFERENCE_STRATEGY_DIR = REFERENCE_PROJECT_PATH / "src" / "strategy"
    REFERENCE_INDICATORS_DIR = REFERENCE_PROJECT_PATH / "indicators"

# Add project root and reference project to path for imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(REFERENCE_PROJECT_PATH) not in sys.path:
    sys.path.insert(0, str(REFERENCE_PROJECT_PATH))
if str(REFERENCE_PROJECT_PATH / "src") not in sys.path:
    sys.path.insert(0, str(REFERENCE_PROJECT_PATH / "src"))


class IndicatorLoader:
    """Loads and discovers indicators from the indicators/ folder"""
    
    def __init__(self, indicators_dir: Path = None):
        """
        Initialize indicator loader
        
        Args:
            indicators_dir: Path to indicators directory (default: PROJECT_ROOT/indicators)
        """
        self.indicators_dir = indicators_dir or INDICATORS_DIR
        self._indicators_cache: Dict[str, Any] = {}
    
    def discover_indicators(self) -> List[Dict[str, Any]]:
        """
        Discover all available indicators from reference project directories
        
        Returns:
            List of indicator metadata dictionaries with:
            - name: Indicator name (file name without extension)
            - class_name: Strategy class name
            - file_path: Path to indicator file
            - description: Docstring from strategy class
            - source: "reference_strategy" or "reference_indicators"
        """
        indicators = []
        seen_names = set()  # Avoid duplicates
        
        # First, search in reference project src/strategy directory
        if REFERENCE_STRATEGY_DIR.exists():
            for file_path in REFERENCE_STRATEGY_DIR.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                try:
                    indicator_name = file_path.stem
                    if indicator_name in seen_names:
                        continue
                    
                    strategy_class = self._load_indicator_class(file_path, is_reference=True, source_type="strategy")
                    
                    if strategy_class:
                        # Get class docstring
                        description = strategy_class.__doc__ or ""
                        if description:
                            description = description.strip().split('\n')[0]
                        
                        indicators.append({
                            "name": indicator_name,
                            "class_name": strategy_class.__name__,
                            "file_path": str(file_path),
                            "description": description,
                            "source": "reference_strategy"
                        })
                        seen_names.add(indicator_name)
                except Exception as e:
                    logger.error(f"Failed to load indicator from {file_path}: {e}")
                    continue
        
        # Then, search in reference project indicators directory
        if REFERENCE_INDICATORS_DIR.exists():
            for file_path in REFERENCE_INDICATORS_DIR.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                try:
                    indicator_name = file_path.stem
                    if indicator_name in seen_names:
                        continue
                    
                    strategy_class = self._load_indicator_class(file_path, is_reference=True, source_type="indicators")
                    
                    if strategy_class:
                        # Get class docstring
                        description = strategy_class.__doc__ or ""
                        if description:
                            description = description.strip().split('\n')[0]
                        
                        indicators.append({
                            "name": indicator_name,
                            "class_name": strategy_class.__name__,
                            "file_path": str(file_path),
                            "description": description,
                            "source": "reference_indicators"
                        })
                        seen_names.add(indicator_name)
                except Exception as e:
                    logger.error(f"Failed to load indicator from {file_path}: {e}")
                    continue
        
        # Finally, search in current project indicators directory (fallback)
        if self.indicators_dir.exists():
            for file_path in self.indicators_dir.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                try:
                    indicator_name = file_path.stem
                    if indicator_name in seen_names:
                        continue
                    
                    strategy_class = self._load_indicator_class(file_path, is_reference=False)
                    
                    if strategy_class:
                        # Get class docstring
                        description = strategy_class.__doc__ or ""
                        if description:
                            description = description.strip().split('\n')[0]
                        
                        indicators.append({
                            "name": indicator_name,
                            "class_name": strategy_class.__name__,
                            "file_path": str(file_path),
                            "description": description,
                            "source": "local"
                        })
                        seen_names.add(indicator_name)
                except Exception as e:
                    logger.error(f"Failed to load indicator from {file_path}: {e}")
                    continue
        
        return indicators
    
    def _load_indicator_class(self, file_path: Path, is_reference: bool = False, source_type: str = "indicators") -> Optional[Any]:
        """
        Load strategy class from indicator file
        
        Args:
            file_path: Path to indicator Python file
            is_reference: Whether this is from the reference project
            source_type: "strategy" or "indicators" (for reference project)
            
        Returns:
            Strategy class or None if not found
        """
        try:
            # Import BaseStrategy from reference project
            try:
                from src.strategy.base_strategy import BaseStrategy
                base_strategy_source = "src.strategy.base_strategy"
            except ImportError:
                try:
                    from strategy.base_strategy import BaseStrategy
                    base_strategy_source = "strategy.base_strategy"
                except ImportError:
                    logger.error("Could not import BaseStrategy")
                    return None
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Determine module name and package based on source
            if is_reference:
                if source_type == "strategy":
                    # For src/strategy files, use src.strategy package
                    module_name = f"src.strategy.{file_path.stem}"
                    package_name = "src.strategy"
                else:
                    # For indicators files, use indicators package
                    module_name = f"indicators.{file_path.stem}"
                    package_name = "indicators"
            else:
                # Local indicators
                module_name = f"indicators.{file_path.stem}"
                package_name = "indicators"
            
            # Modify imports to work with our module structure
            modified_content = file_content
            
            # Handle relative imports for reference project strategies
            if is_reference and source_type == "strategy":
                # Replace: from .base_strategy import BaseStrategy
                modified_content = modified_content.replace(
                    'from .base_strategy import BaseStrategy',
                    f'from {base_strategy_source} import BaseStrategy'
                )
                # Replace: from ..indicators. import ...
                modified_content = modified_content.replace(
                    'from ..indicators.',
                    'from src.indicators.'
                )
            else:
                # For indicators or local files, create a base_strategy module alias
                import types
                if 'indicators' not in sys.modules:
                    indicators_module = types.ModuleType('indicators')
                    sys.modules['indicators'] = indicators_module
                
                # Create base_strategy module within indicators package
                base_strategy_module = types.ModuleType('indicators.base_strategy')
                base_strategy_module.BaseStrategy = BaseStrategy
                sys.modules['indicators.base_strategy'] = base_strategy_module
                
                # Replace relative imports
                modified_content = modified_content.replace(
                    'from .base_strategy import BaseStrategy',
                    'from indicators.base_strategy import BaseStrategy'
                )
                modified_content = modified_content.replace(
                    'from ..indicators.',
                    'from src.indicators.'
                )
            
            # Create module spec
            spec = importlib.util.spec_from_file_location(
                module_name, file_path
            )
            if spec is None or spec.loader is None:
                return None
            
            # Create module and register it BEFORE execution (needed for dataclasses)
            module = importlib.util.module_from_spec(spec)
            module.__package__ = package_name
            module.__file__ = str(file_path)
            module.__name__ = module_name
            
            # Register module BEFORE executing code (important for dataclasses)
            sys.modules[module_name] = module
            
            # Execute the modified code
            code = compile(modified_content, str(file_path), 'exec')
            exec(code, module.__dict__)
            
            # Find strategy class
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (name.endswith("Strategy") and 
                    hasattr(obj, 'generate_signal') and
                    name != "BaseStrategy"):
                    return obj
            
            return None
        except Exception as e:
            logger.error(f"Error loading indicator class from {file_path}: {e}", exc_info=True)
            return None
    
    def get_indicator_settings_schema(self, indicator_name: str) -> Dict[str, Any]:
        """
        Get settings schema for an indicator
        
        Args:
            indicator_name: Name of the indicator (file name without extension)
            
        Returns:
            Dictionary with settings schema:
            - parameters: List of parameter definitions
            - defaults: Dictionary of default values
        """
        # Search in reference project first, then local
        indicator_file = None
        is_reference = False
        source_type = "indicators"
        
        # Check reference strategy directory
        if REFERENCE_STRATEGY_DIR.exists():
            potential_file = REFERENCE_STRATEGY_DIR / f"{indicator_name}.py"
            if potential_file.exists():
                indicator_file = potential_file
                is_reference = True
                source_type = "strategy"
        
        # Check reference indicators directory
        if not indicator_file and REFERENCE_INDICATORS_DIR.exists():
            potential_file = REFERENCE_INDICATORS_DIR / f"{indicator_name}.py"
            if potential_file.exists():
                indicator_file = potential_file
                is_reference = True
                source_type = "indicators"
        
        # Check local indicators directory
        if not indicator_file:
            indicator_file = self.indicators_dir / f"{indicator_name}.py"
        
        if not indicator_file or not indicator_file.exists():
            return {"parameters": [], "defaults": {}}
        
        try:
            strategy_class = self._load_indicator_class(indicator_file, is_reference=is_reference, source_type=source_type)
            if not strategy_class:
                return {"parameters": [], "defaults": {}}
            
            # Get __init__ signature
            init_sig = inspect.signature(strategy_class.__init__)
            parameters = []
            defaults = {}
            
            for param_name, param in init_sig.parameters.items():
                if param_name == 'self':
                    continue
                
                param_info = {
                    "name": param_name,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "required": param.default == inspect.Parameter.empty
                }
                
                # Try to infer parameter type from default value
                if param.default != inspect.Parameter.empty:
                    defaults[param_name] = param.default
                    if isinstance(param.default, (int, float)):
                        param_info["type"] = "number"
                    elif isinstance(param.default, str):
                        param_info["type"] = "string"
                    elif isinstance(param.default, bool):
                        param_info["type"] = "boolean"
                    elif isinstance(param.default, dict):
                        param_info["type"] = "object"
                    elif isinstance(param.default, list):
                        param_info["type"] = "array"
                else:
                    # Infer from annotation
                    if "str" in param_info["type"].lower():
                        param_info["type"] = "string"
                    elif "int" in param_info["type"].lower() or "float" in param_info["type"].lower():
                        param_info["type"] = "number"
                    elif "bool" in param_info["type"].lower():
                        param_info["type"] = "boolean"
                    elif "dict" in param_info["type"].lower():
                        param_info["type"] = "object"
                    elif "list" in param_info["type"].lower():
                        param_info["type"] = "array"
                
                parameters.append(param_info)
            
            return {
                "parameters": parameters,
                "defaults": defaults
            }
        except Exception as e:
            logger.error(f"Error getting settings schema for {indicator_name}: {e}")
            return {"parameters": [], "defaults": {}}
    
    def create_indicator_instance(
        self, 
        indicator_name: str, 
        symbol: str,
        settings: Dict[str, Any] = None
    ) -> Optional[Any]:
        """
        Create an instance of an indicator strategy
        
        Args:
            indicator_name: Name of the indicator
            symbol: Trading symbol
            settings: Dictionary of indicator settings
            
        Returns:
            Strategy instance or None if creation fails
        """
        # Search in reference project first, then local
        indicator_file = None
        is_reference = False
        source_type = "indicators"
        
        # Check reference strategy directory
        if REFERENCE_STRATEGY_DIR.exists():
            potential_file = REFERENCE_STRATEGY_DIR / f"{indicator_name}.py"
            if potential_file.exists():
                indicator_file = potential_file
                is_reference = True
                source_type = "strategy"
        
        # Check reference indicators directory
        if not indicator_file and REFERENCE_INDICATORS_DIR.exists():
            potential_file = REFERENCE_INDICATORS_DIR / f"{indicator_name}.py"
            if potential_file.exists():
                indicator_file = potential_file
                is_reference = True
                source_type = "indicators"
        
        # Check local indicators directory
        if not indicator_file:
            indicator_file = self.indicators_dir / f"{indicator_name}.py"
        
        if not indicator_file or not indicator_file.exists():
            logger.error(f"Indicator file not found: {indicator_name}")
            return None
        
        try:
            strategy_class = self._load_indicator_class(indicator_file, is_reference=is_reference, source_type=source_type)
            if not strategy_class:
                logger.error(f"Could not load strategy class from {indicator_file}")
                return None
            
            # Get default settings
            schema = self.get_indicator_settings_schema(indicator_name)
            defaults = schema.get("defaults", {})
            
            # Merge defaults with provided settings
            if settings:
                defaults.update(settings)
            
            # Create instance - name and symbol are required
            instance_settings = {
                "name": f"{indicator_name}_backtest",
                "symbol": symbol,
                **defaults
            }
            
            # Extract conditions if present (for OHLCPriceStrategy and similar)
            buy_conditions_data = None
            sell_conditions_data = None
            if settings:
                buy_conditions_data = settings.pop('buy_conditions', None)
                sell_conditions_data = settings.pop('sell_conditions', None)
            
            # Instantiate strategy
            instance = strategy_class(**instance_settings)
            
            # Apply SL/TP and risk management settings from indicator_settings
            # These are BaseStrategy attributes that should be set after instantiation
            sl_tp_settings = [
                'sl_type', 'sl_value', 'sl_enabled', 'tp_value', 'tp_enabled', 'use_ratio',
                'enable_trailing_sl', 'trailing_sl_gap',
                'enable_profit_lock', 'profit_lock_trigger', 'profit_lock_value',
                'profit_trail_step', 'profit_trail_amount'
            ]
            
            for setting in sl_tp_settings:
                if settings and setting in settings:
                    setattr(instance, setting, settings[setting])
            
            # Add conditions if this is an OHLCPriceStrategy or similar
            if buy_conditions_data or sell_conditions_data:
                if hasattr(instance, 'add_buy_condition') and hasattr(instance, 'add_sell_condition'):
                    # Try to get OHLCPriceCondition from the loaded module
                    OHLCPriceCondition = None
                    try:
                        # First try to get it from the module we just loaded
                        module_name = f"indicators.{indicator_name}"
                        module = sys.modules.get(module_name)
                        if module and hasattr(module, 'OHLCPriceCondition'):
                            OHLCPriceCondition = module.OHLCPriceCondition
                        else:
                            # Try importing from indicators.ohlc_price_strategy
                            from indicators.ohlc_price_strategy import OHLCPriceCondition
                    except (ImportError, AttributeError) as e:
                        logger.warning(f"Could not import OHLCPriceCondition: {e}. Conditions will not be added.")
                        return instance
                    
                    if not OHLCPriceCondition:
                        logger.warning(f"OHLCPriceCondition not found. Conditions will not be added.")
                        return instance
                    
                    # Add buy conditions
                    if buy_conditions_data:
                        for cond_data in buy_conditions_data:
                            try:
                                condition = OHLCPriceCondition.from_dict(cond_data)
                                instance.add_buy_condition(condition)
                            except Exception as e:
                                logger.error(f"Error adding buy condition: {e}", exc_info=True)
                    
                    # Add sell conditions
                    if sell_conditions_data:
                        for cond_data in sell_conditions_data:
                            try:
                                condition = OHLCPriceCondition.from_dict(cond_data)
                                instance.add_sell_condition(condition)
                            except Exception as e:
                                logger.error(f"Error adding sell condition: {e}", exc_info=True)
            
            return instance
        except Exception as e:
            logger.error(f"Error creating indicator instance {indicator_name}: {e}", exc_info=True)
            return None

