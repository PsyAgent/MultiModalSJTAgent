import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

class DatasetConfig:
    """Configuration management for dataset paths and metadata."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent
        self._data_paths = self._build_data_paths()
    
    def _build_data_paths(self) -> dict[str, dict[str, Path]]:
        """Build dataset paths configuration."""
        return {
            "IPIP120": {
                "en": self.base_dir / "scales" / "IPIP" / "ipip120_en.json",
                "zh": self.base_dir / "scales" / "IPIP" / "ipip120_zh.json",
            },
            "NEO-PI-R": {
                "en": self.base_dir / "scales" / "NEO-PI-R" / "neo-pi-r_en.json",
                "zh": self.base_dir / "scales" / "NEO-PI-R" / "neo-pi-r_zh.json",
            },
            "PSJT-Mussel": {
                "en": self.base_dir / "scales" / "SJTs" / "mussel_en.json",
                "zh": self.base_dir / "scales" / "SJTs" / "mussel_zh.json",
            },
            "traits_definition": {
                "en": self.base_dir / "TRAIT_DEF" / "BF_detailed_en.json",
            },
            "aig_prompts_Li": {
                "en": self.base_dir / "aig_prompts" / "Li_en.py",
                "zh": self.base_dir / "aig_prompts" / "Li_zh.py",
            },
            "aig_prompts_Krumm": {
                "en": self.base_dir / "aig_prompts" / "Krumm_en.py",
                "zh": self.base_dir / "aig_prompts" / "Krumm_zh.py",
            }
        }
    
    @property
    def data_paths(self) -> dict[str, dict[str, Path]]:
        """Get dataset paths."""
        return self._data_paths
    
    def get_dataset_path(self, dataset_name: str, language: str) -> Path:
        """Get path for specific dataset and language."""
        if dataset_name not in self._data_paths:
            raise ValueError(f"Dataset '{dataset_name}' not found. Available: {list(self._data_paths.keys())}")
        
        dataset_paths = self._data_paths[dataset_name]
        if language not in dataset_paths:
            raise ValueError(f"Language '{language}' not available for dataset '{dataset_name}'. Available: {list(dataset_paths.keys())}")
        
        return dataset_paths[language]
    
    def get_meta_path(self, dataset_name: str) -> Path:
        """Get metadata path for dataset."""
        if dataset_name not in self._data_paths:
            raise ValueError(f"Dataset '{dataset_name}' not found. Available: {list(self._data_paths.keys())}")
        
        # Get first available path to determine directory
        first_path = next(iter(self._data_paths[dataset_name].values()))
        return first_path.parent / "meta.json"

class DatasetError(Exception):
    """Base exception for dataset-related errors."""
    pass

class DatasetNotFoundError(DatasetError):
    """Raised when dataset is not found."""
    pass

class LanguageNotSupportedError(DatasetError):
    """Raised when language is not supported for a dataset."""
    pass

class DataLoader:
    """Robust data loader for psychological assessment datasets."""
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        """Initialize DataLoader with optional custom configuration.
        
        Args:
            config: Custom dataset configuration. If None, uses default config.
        """
        self.config = config or DatasetConfig()
        self._cache = {}
    
    @property
    def available_datasets(self) -> dict[str, dict[str, Path]]:
        """Get available datasets and their language variants."""
        return self.config.data_paths
    
    def _repr_html_(self) -> str:
        """Generate HTML representation for Jupyter notebooks."""
        rows = []
        for dataset_name, lang_paths in self.available_datasets.items():
            available_langs = list(lang_paths.keys())
            meta_exists = self._meta_exists(dataset_name)
            
            rows.append({
                "Dataset": dataset_name,
                "Languages": ", ".join(available_langs),
                "Meta Exists": str(meta_exists)
            })
        
        df = pd.DataFrame(rows)
        html_table = df.to_html(index=False)
        usage = (
            "<p>Use <code>load(dataset_name, language='en')</code> to load data,<br>"
            "and <code>load_meta(dataset_name)</code> to load metadata.</p>"
        )
        return f"<h3>Available datasets:</h3>{html_table}{usage}"
    
    def _meta_exists(self, dataset_name: str) -> bool:
        """Check if metadata file exists for dataset."""
        try:
            meta_path = self.config.get_meta_path(dataset_name)
            return meta_path.exists()
        except (ValueError, FileNotFoundError):
            return False
    
    def _load_json_file(self, file_path: Path) -> dict[str, Any]:
        """Load JSON file with proper error handling."""
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Successfully loaded data from {file_path}")
            return data
        except json.JSONDecodeError as e:
            raise DatasetError(f"Invalid JSON format in {file_path}: {e}")
        except UnicodeDecodeError as e:
            raise DatasetError(f"Encoding error reading {file_path}: {e}")
        except Exception as e:
            raise DatasetError(f"Unexpected error loading {file_path}: {e}")
    
    def load(
        self, 
        dataset_name: str,
        language: str = "en",
        use_cache: bool = True
    ) -> dict[str, Any]:
        """Load dataset with specified language.
        
        Args:
            dataset_name: Name of the dataset to load
            language: Language variant ("en" or "zh")
            use_cache: Whether to use cached data if available
            
        Returns:
            Loaded dataset as dictionary
            
        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            LanguageNotSupportedError: If language not supported
            DatasetError: If loading fails
        """
        # Validate inputs
        if not isinstance(dataset_name, str) or not dataset_name.strip():
            raise ValueError("dataset_name must be a non-empty string")
        
        if language not in ["en", "zh"]:
            raise LanguageNotSupportedError(f"Language '{language}' not supported. Use 'en' or 'zh'")
        
        cache_key = f"{dataset_name}_{language}"
        
        # Return cached data if available and requested
        if use_cache and cache_key in self._cache:
            logger.debug(f"Returning cached data for {cache_key}")
            return self._cache[cache_key]
        
        try:
            file_path = self.config.get_dataset_path(dataset_name, language)
            if file_path.suffix == ".py":
                return str(file_path)
            
            data = self._load_json_file(file_path)
            
            # Cache the loaded data
            if use_cache:
                self._cache[cache_key] = data
                logger.debug(f"Cached data for {cache_key}")
            
            return data
            
        except ValueError as e:
            if "Dataset" in str(e) and "not found" in str(e):
                raise DatasetNotFoundError(str(e))
            elif "Language" in str(e) and "not available" in str(e):
                raise LanguageNotSupportedError(str(e))
            else:
                raise
    
    def load_meta(self, dataset_name: str, use_cache: bool = True) -> dict[str, Any]:
        """Load metadata for specified dataset.
        
        Args:
            dataset_name: Name of the dataset
            use_cache: Whether to use cached metadata if available
            
        Returns:
            Dataset metadata as dictionary
            
        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            DatasetError: If loading fails
        """
        if not isinstance(dataset_name, str) or not dataset_name.strip():
            raise ValueError("dataset_name must be a non-empty string")
        
        cache_key = f"{dataset_name}_meta"
        
        # Return cached metadata if available and requested
        if use_cache and cache_key in self._cache:
            logger.debug(f"Returning cached metadata for {dataset_name}")
            return self._cache[cache_key]
        
        try:
            meta_path = self.config.get_meta_path(dataset_name)
            metadata = self._load_json_file(meta_path)
            
            # Cache the loaded metadata
            if use_cache:
                self._cache[cache_key] = metadata
                logger.debug(f"Cached metadata for {dataset_name}")
            
            return metadata
            
        except ValueError as e:
            raise DatasetNotFoundError(str(e))
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_dataset_info(self, dataset_name: str) -> dict[str, Any]:
        """Get comprehensive information about a dataset.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Dictionary with dataset information
        """
        if dataset_name not in self.available_datasets:
            raise DatasetNotFoundError(f"Dataset '{dataset_name}' not found")
        
        info = {
            "name": dataset_name,
            "available_languages": list(self.available_datasets[dataset_name].keys()),
            "has_metadata": self._meta_exists(dataset_name),
            "file_paths": {
                lang: str(path) for lang, path in self.available_datasets[dataset_name].items()
            }
        }
        
        # Add file existence check
        info["files_exist"] = {
            lang: path.exists() for lang, path in self.available_datasets[dataset_name].items()
        }
        
        return info
