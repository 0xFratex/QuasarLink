# QuasarLink/serializer.py
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("QuasarLink") # Main app logger

class ArticleSerializer:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        logger.debug(f"ArticleSerializer initialized with schema: {self.schema}")

    def _apply_schema_to_article(self, article_data: Dict[str, Any], article_title: str) -> Dict[str, Any]:
        output_article: Dict[str, Any] = {}
        # logger.debug(f"Applying schema to article '{article_title}'. Input keys: {list(article_data.keys())}")
        
        expected_keys = ["title", "url", "content", "sections", "images", "infobox_data"]
        for expected_key in expected_keys:
            article_data.setdefault(expected_key, None) # Ensure keys exist for placeholder replacement

        for key, value_template in self.schema.items():
            if isinstance(value_template, str) and value_template.startswith("{") and value_template.endswith("}"):
                placeholder = value_template[1:-1]
                if placeholder in article_data:
                    output_article[key] = article_data[placeholder]
                    # logger.debug(f"Mapped schema key '{key}' to article data['{placeholder}'] for '{article_title}'")
                else:
                    output_article[key] = None 
                    logger.warning(f"Placeholder '{{{placeholder}}}' for schema key '{key}' not found in article data for '{article_title}'. Setting to None.")
            else: 
                output_article[key] = value_template
                # logger.debug(f"Set schema key '{key}' to static value '{value_template}' for '{article_title}'")
        # logger.debug(f"Finished applying schema for '{article_title}'. Output keys: {list(output_article.keys())}")
        return output_article

    def serialize_articles(self, articles_data: List[Dict[str, Any]], output_path: Path) -> None:
        if not articles_data:
            logger.warning("No articles data provided to serialize. Writing empty list to output file.")
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                logger.info(f"Wrote empty list to {output_path} as no articles were processed or provided.")
            except IOError as e:
                logger.error(f"Failed to write empty output JSON to {output_path}: {e}", exc_info=True)
            return

        logger.info(f"Serializing {len(articles_data)} articles to {output_path} using the configured schema.")
        
        output_list: List[Dict[str, Any]] = []
        for idx, article_data_item in enumerate(articles_data):
            if article_data_item and isinstance(article_data_item, dict): 
                article_title = article_data_item.get("title", f"Unknown Article {idx+1}")
                logger.debug(f"Processing article {idx+1}/{len(articles_data)} ('{article_title}') for serialization.")
                processed_article = self._apply_schema_to_article(article_data_item, article_title)
                output_list.append(processed_article)
            else:
                logger.warning(f"Skipping invalid or empty article data item at index {idx} during serialization.")


        logger.debug(f"Attempting to write {len(output_list)} processed articles to {output_path}.")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_list, f, indent=2, ensure_ascii=False) # ensure_ascii=False for better unicode handling
            logger.info(f"Successfully wrote {len(output_list)} processed articles to {output_path}")
        except IOError as e:
            logger.error(f"Failed to write output JSON to {output_path}: {e}", exc_info=True)
            raise
        except Exception as e: # Catch any other unexpected errors during json.dump
            logger.error(f"An unexpected error occurred during JSON serialization to {output_path}: {e}", exc_info=True)
            raise