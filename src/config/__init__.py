"""
Configuration package
Exports Config class from parent config.py module
"""

# Import Config from the parent directory's config.py file
# Since we're in src/config/__init__.py, we need to import from src/config.py
# We use importlib to avoid circular import issues
import importlib.util
from pathlib import Path

# Get path to parent directory's config.py
_parent_dir = Path(__file__).parent.parent
_config_file = _parent_dir / "config.py"

if _config_file.exists():
    # Load config.py as a module
    spec = importlib.util.spec_from_file_location("_config_module", _config_file)
    _config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_config_module)
    # Export Config class
    Config = _config_module.Config
else:
    # Fallback if config.py doesn't exist
    raise ImportError("config.py not found in src directory")

