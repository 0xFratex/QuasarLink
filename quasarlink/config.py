# QuasarLink/config.py
import json
import yaml # Requires PyYAML
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

logger = logging.getLogger("QuasarLink") # Main app logger

DEFAULT_SCHEMA: Dict[str, str] = {
    "title": "{title}",
    "url": "{url}",
    "content": "{content}",
    "sections": "{sections}"
}

def load_schema(schema_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
    if schema_path is None:
        logger.debug("No custom schema path provided, using default schema structure.")
        return DEFAULT_SCHEMA.copy()

    path = Path(schema_path)
    logger.info(f"Attempting to load custom schema from: {path}")
    if not path.exists():
        logger.error(f"Custom schema file not found: {path}")
        raise FileNotFoundError(f"Custom schema file not found: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() == ".json":
                logger.debug(f"Loading schema as JSON from {path}")
                schema = json.load(f)
            elif path.suffix.lower() in [".yaml", ".yml"]:
                logger.debug(f"Loading schema as YAML from {path}")
                schema = yaml.safe_load(f)
            else:
                logger.error(f"Unsupported schema file format: {path.suffix}. Use JSON or YAML.")
                raise ValueError(f"Unsupported schema file format: {path.suffix}")
        
        if not isinstance(schema, dict):
            logger.error(f"Custom schema from {path} must be a dictionary (object), but got {type(schema)}")
            raise ValueError(f"Custom schema from {path} must be a dictionary.")

        logger.info(f"Successfully loaded and validated custom schema from {path}")
        logger.debug(f"Custom schema content: {schema}")
        return schema
    except Exception as e:
        logger.error(f"Error loading custom schema from {path}: {e}", exc_info=True) # Log with traceback
        raise


def get_effective_schema(
    custom_schema_path: Optional[Union[str, Path]],
    keep_images: bool,
    keep_infobox: bool
) -> Dict[str, Any]:
    logger.debug(f"Determining effective schema. Custom path: '{custom_schema_path}', Keep images: {keep_images}, Keep infobox: {keep_infobox}")
    if custom_schema_path:
        schema = load_schema(custom_schema_path)
        # For custom schemas, we log if the flags are set but placeholders might be missing
        if keep_images and "{images}" not in str(schema.values()): # Crude check
             logger.warning("Using custom schema with --keep-images, but '{images}' placeholder might be missing in schema values.")
        if keep_infobox and "{infobox_data}" not in str(schema.values()): # Crude check
             logger.warning("Using custom schema with --keep-infobox, but '{infobox_data}' placeholder might be missing in schema values.")
        logger.info("Using user-provided custom schema.")
    else:
        schema = DEFAULT_SCHEMA.copy() # Start with default
        logger.info("Using default schema structure.")
        if keep_images:
            schema["images"] = "{images}"
            logger.info("Added 'images: {images}' to default schema due to --keep-images flag.")
        if keep_infobox:
            schema["infobox_data"] = "{infobox_data}"
            logger.info("Added 'infobox_data: {infobox_data}' to default schema due to --keep-infobox flag.")
            
    logger.debug(f"Effective schema determined: {schema}")
    return schema