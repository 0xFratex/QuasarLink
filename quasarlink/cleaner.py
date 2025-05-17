# QuasarLink/cleaner.py
# -*- coding: utf-8 -*-
import re
import logging
import time 
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from typing import List, Dict, Any, Optional

from .utils import normalize_whitespace

logger = logging.getLogger("QuasarLink")

DEFAULT_PARSER = 'html.parser'
try:
    import lxml # type: ignore
    DEFAULT_PARSER = 'lxml'
    logger.info("Using 'lxml' as the HTML parser for BeautifulSoup (faster).")
except ImportError:
    logger.info("Using 'html.parser' as the HTML parser for BeautifulSoup. Consider installing 'lxml' for better performance.")


class WikipediaCleaner:
    def __init__(self, keep_images: bool = False, keep_infobox: bool = False):
        self.keep_images = keep_images
        self.keep_infobox = keep_infobox
        logger.debug(f"Cleaner instance created: keep_images={self.keep_images}, keep_infobox={self.keep_infobox}, parser_preference='{DEFAULT_PARSER}'")

    def _remove_by_selectors(self, soup: BeautifulSoup, selectors: List[str]):
        for selector in selectors:
            try:
                elements_found = soup.select(selector)
                if elements_found:
                    # logger.debug(f"Removing {len(elements_found)} element(s) matching selector '{selector}'") # Too verbose
                    for element in elements_found:
                        element.decompose()
            except Exception as e:
                logger.warning(f"Problem with CSS selector '{selector}': {e}. Skipping this selector for this page.")

    def _preprocess_html(self, soup: BeautifulSoup):
        start_time = time.monotonic()
        # logger.debug("Starting HTML preprocessing (comments, scripts, styles, etc.).") # Covered by step timing
        
        comments_found = soup.find_all(string=lambda text_node: isinstance(text_node, Comment))
        if comments_found:
            # logger.debug(f"Removing {len(comments_found)} HTML comments.") # Too verbose
            for comment_tag in comments_found:
                comment_tag.extract()
        
        selectors_to_remove = [
            "script", "style", "noscript", "link[rel='stylesheet']",
            ".mw-empty-elt",
            "span.Z3988",
            ".sr-only", ".visually-hidden", ".screen-reader-text",
            "span#coordinates", "div#coordinates", ".geo-default", ".geo-multi-punct", ".geo",
            "div.vector-body-before-content", 
            "div#siteNotice", "div#centralNotice", "div.mw-indicators"
        ]
        self._remove_by_selectors(soup, selectors_to_remove)
        duration = time.monotonic() - start_time
        logger.debug(f"HTML preprocessing finished in {duration:.4f} seconds.")


    def _extract_infobox_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        if not self.keep_infobox:
            # logger.debug("Infobox extraction skipped as per configuration (keep_infobox=False).")
            for ib_table in soup.select("table.infobox"): ib_table.decompose()
            for ib_div in soup.select("div.infobox"): ib_div.decompose()
            return None

        start_time = time.monotonic()
        # logger.debug("Attempting to extract infobox data.") # Covered by step timing
        infobox_tag = soup.find("table", class_="infobox")
        if not infobox_tag:
            infobox_tag = soup.find("div", class_="infobox") 
        
        if not infobox_tag:
            # logger.debug("No infobox found on the page.") # Covered by return None and duration log
            return None

        # logger.debug(f"Found infobox tag: <{infobox_tag.name} class='{infobox_tag.get('class', '')}'>") # Can be verbose
        data: Dict[str, Any] = {}
        caption_tag = infobox_tag.find("caption")
        if caption_tag:
            data["_caption_"] = normalize_whitespace(caption_tag.get_text(separator=" ", strip=True))
            # logger.debug(f"Extracted infobox caption: {data['_caption_']}") # Too verbose if many infoboxes
        
        # rows_processed = 0 # Not logged, so not needed here
        for row in infobox_tag.find_all("tr", recursive=False):
            # rows_processed +=1
            header_tag = row.find("th", recursive=False)
            value_cell_tag = row.find("td", recursive=False)
            
            if header_tag and value_cell_tag:
                key = normalize_whitespace(header_tag.get_text(separator=" ", strip=True))
                if not key: continue

                for sup_tag in value_cell_tag.find_all("sup", class_="reference"): sup_tag.decompose()
                for br_tag in value_cell_tag.find_all("br"): br_tag.replace_with("\n")

                list_items = value_cell_tag.find_all("li")
                if list_items:
                    value_parts = [normalize_whitespace(li.get_text(separator=" ", strip=True)) for li in list_items]
                    data[key] = [part for part in value_parts if part]
                else:
                    value_text = value_cell_tag.get_text(separator=" ", strip=True)
                    data[key] = normalize_whitespace(value_text.replace("\n", " ").strip())
                # logger.debug(f"Infobox: Extracted '{key}': '{str(data[key])[:50]}...'") # Too verbose
            elif value_cell_tag and not header_tag and len(row.find_all(['th','td'], recursive=False)) == 1:
                text_content = normalize_whitespace(value_cell_tag.get_text(separator=" ", strip=True))
                img_in_cell = value_cell_tag.find("img")
                if text_content and not img_in_cell :
                     data.setdefault("_infobox_notes_", []).append(text_content)
                     # logger.debug(f"Infobox: Added note: '{text_content[:50]}...'") # Too verbose
        
        # logger.debug(f"Processed {rows_processed} rows in infobox. Found {len(data)} data items.")
        infobox_tag.decompose()
        duration = time.monotonic() - start_time
        logger.debug(f"Infobox data extraction finished in {duration:.4f} seconds. Extracted {len(data)} items.")
        return data if data else None


    def _remove_unwanted_wikipedia_elements(self, soup: BeautifulSoup):
        start_time = time.monotonic()
        # logger.debug("Starting removal of unwanted Wikipedia elements (navboxes, banners, metadata, etc.).") # Covered by step timing
        selectors_to_remove = [
            "div.navbox", "table.navbox", "div.vertical-navbox", "table.vertical-navbox",
            "table.ambox", "table.tmbox", "table.fmbox", "div.ombox", "table.commons-caption",
            "div.metadata", "table.metadata",
            "div#siteSub", "div#jump-to-nav", "div.printfooter", "div.catlinks",
            "div#p-search", "div#p-lang-btn", "div#p-namespaces", "div#p-personal",
            "div#p-views", "div#p-navigation", "div#p-interaction", "div#p-tb",
            "div#p-coll-print_export", "div#footer", "span.mw-editsection",
            "sup.reference", "sup.noprint", ".noprint", ".mw-cite- είχε", ".citation-needed-content",
            "figure", "gallery", "ul.gallery", "table.gallery", 
            "table.wikitable.sidebar", "div.thumbcaption[style*='display:none']",
            "div.hatnote", "div.rellink", "div.Dablink", 
            "table.fmbox-system", "div.authority-control", "div.shortdescription",
            "div#toc", "table#toc", ".toc", 
            "div.reflist", "ol.references", "ul.plainlinks",
            ".portalbox", ".sisterproject",
            "div.mw-references-wrap", 
            "span.mwe-math-fallback-image-inline", 
        ]
        if not self.keep_infobox: 
            # logger.debug("Adding general infobox selectors to removal list as keep_infobox is False.")
            selectors_to_remove.extend(["table.infobox", "div.infobox"])
        
        try:
            jump_links = soup.select('div[class*="mw-jump"]')
            if jump_links:
                # logger.debug(f"Removing {len(jump_links)} mw-jump link elements.") # Too verbose
                for el in jump_links: el.decompose()
        except Exception as e:
            logger.warning(f"Error processing mw-jump selector: {e}")

        self._remove_by_selectors(soup, selectors_to_remove)
        
        trailing_section_keywords = [
            "references", "external links", "see also", "notes",
            "bibliography", "further reading", "sources", "citations", "gallery"
        ]
        all_headings = soup.find_all(['h2', 'h3', 'h4'], recursive=True)
        removed_trailing_sections_count = 0
        if all_headings:
            for h_tag in reversed(all_headings): 
                headline_span = h_tag.find("span", class_="mw-headline")
                title_text_container = headline_span if headline_span else h_tag
                title_text = normalize_whitespace(title_text_container.get_text(separator=" ", strip=True)).lower()

                if any(keyword in title_text for keyword in trailing_section_keywords):
                    # logger.debug(f"Removing trailing section starting with: '{title_text[:30]}...'") # Too verbose
                    elements_to_remove_for_section = [h_tag]
                    for sibling in h_tag.find_next_siblings():
                        if sibling.name and sibling.name.startswith('h') and sibling.name <= h_tag.name:
                            break 
                        elements_to_remove_for_section.append(sibling)
                    
                    for el_to_remove in elements_to_remove_for_section:
                        if el_to_remove.name:
                            el_to_remove.decompose()
                    removed_trailing_sections_count += 1
        
        duration = time.monotonic() - start_time
        logger.debug(f"Removal of unwanted Wikipedia elements finished in {duration:.4f} seconds. {removed_trailing_sections_count} trailing sections removed.")


    def _extract_images_from_content(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        if not self.keep_images:
            # logger.debug("Image extraction skipped as per configuration (keep_images=False).")
            self._remove_by_selectors(soup, ["img", "div.thumb", "figure.image", "a.image", "div.PopUpMediaTransform", "div.thumbinner", "div.thumbimage", "div.floatnone", "div.floatright", "div.floatleft", "div.gallerybox", 'td[style*="padding"] > a.image', "figcaption", "div.thumbcaption", "div.gallerytext", "div.mw-caption-text"])
            return []

        start_time = time.monotonic()
        # logger.debug("Attempting to extract images.") # Covered by step timing
        images_found: List[Dict[str, str]] = []
        
        image_container_selectors = ['figure.image', '.thumb', 'div.thumbimage', 'div.image', 'div.floatnone', 'div.floatright', 'div.floatleft', '.gallerybox', 'td[style*="padding"] > a.image']

        for selector in image_container_selectors:
            containers = soup.select(selector)
            if not containers: continue
            # logger.debug(f"Processing {len(containers)} image containers for selector '{selector}'.") # Too verbose
            for container in containers:
                img_tag = container.find("img")
                if img_tag and 'src' in img_tag.attrs:
                    src = img_tag['src']
                    if src.startswith("//"): src = "https:" + src
                    alt = normalize_whitespace(img_tag.get('alt', ''))
                    caption_text = ""
                    
                    caption_tag = container.find(["figcaption", "div"], class_=["thumbcaption", "gallerytext", "mw-caption-text"])
                    if not caption_tag: 
                        caption_tag = container.find(class_=lambda x: x and "caption" in x)

                    if caption_tag:
                        for edit_span in caption_tag.select("span.mw-editsection"): edit_span.decompose()
                        caption_text = normalize_whitespace(caption_tag.get_text(separator=" ", strip=True))
                    
                    images_found.append({"src": src, "alt": alt, "caption": caption_text})
                    # logger.debug(f"Extracted image: src='{src}', alt='{alt[:30]}...', caption='{caption_text[:30]}...'") # Too verbose
                
                if container.name:
                    container.decompose() 
            # logger.debug(f"Decomposed processed image containers for selector '{selector}'.") # Too verbose

        loose_imgs = soup.find_all("img")
        if loose_imgs:
            # logger.debug(f"Processing {len(loose_imgs)} remaining loose <img> tags.") # Too verbose
            for img_tag in loose_imgs: 
                if 'src' in img_tag.attrs:
                     src = img_tag['src']
                     if src.startswith("//"): src = "https:" + src
                     alt = normalize_whitespace(img_tag.get('alt', ''))
                     images_found.append({"src": src, "alt": alt, "caption": ""}) 
                     # logger.debug(f"Extracted loose image: src='{src}', alt='{alt[:30]}...'") # Too verbose
                img_tag.decompose()
        
        duration = time.monotonic() - start_time
        log_level = logger.info if (images_found and self.keep_images) else logger.debug # Log as INFO only if we actually kept images and found some
        log_level(f"Image extraction finished in {duration:.4f} seconds. Found {len(images_found)} images (kept: {self.keep_images}).")
        return images_found


    def _element_to_text_parts(self, element: Tag) -> List[str]:
        text_parts: List[str] = []
        # CRITICAL PERFORMANCE: logger.debug(f"Processing element for text: <{element.name} ...>") # DO NOT UNCOMMENT IN PRODUCTION
        
        if element.name in [f"h{i}" for i in range(1, 7)]:
            level = int(element.name[1])
            headline_span = element.find("span", class_="mw-headline")
            title = normalize_whitespace(headline_span.get_text(strip=True) if headline_span else element.get_text(strip=True))
            if title and title.lower() not in ["references", "external links", "see also", "notes", "contents", "bibliography", "further reading", "gallery"]:
                text_parts.append(f"\n\n{'#' * level} {title}\n")
            return text_parts

        elif element.name == 'p':
            for hidden_span in element.find_all("span", style=lambda s: s and "display:none" in s.lower()): hidden_span.decompose()
            paragraph_text = normalize_whitespace(element.get_text(separator=" ", strip=True))
            if paragraph_text:
                text_parts.append(paragraph_text + "\n")
            return text_parts

        elif element.name == 'ul':
            list_items_texts = []
            for li in element.find_all("li", recursive=False):
                item_content = "".join(self._process_children_for_text(li)).strip()
                if item_content: list_items_texts.append(f"* {item_content}\n")
            if list_items_texts: text_parts.extend(["\n"] + list_items_texts + ["\n"])
            return text_parts

        elif element.name == 'ol':
            list_items_texts = []
            for i, li in enumerate(element.find_all("li", recursive=False)):
                item_content = "".join(self._process_children_for_text(li)).strip()
                if item_content: list_items_texts.append(f"{i+1}. {item_content}\n")
            if list_items_texts: text_parts.extend(["\n"] + list_items_texts + ["\n"])
            return text_parts
        
        elif element.name == 'dl':
            for child_node in element.find_all(['dt', 'dd'], recursive=False):
                item_text = normalize_whitespace(child_node.get_text(separator=" ", strip=True))
                if item_text:
                    prefix = "**" if child_node.name == 'dt' else "  "
                    suffix = "**:" if child_node.name == 'dt' else ""
                    text_parts.append(f"{prefix}{item_text}{suffix}\n")
            if text_parts: text_parts.insert(0, "\n"); text_parts.append("\n")
            return text_parts

        elif element.name == 'br':
            return ["\n"]
        
        text_parts.extend(self._process_children_for_text(element))
        return text_parts

    def _process_children_for_text(self, parent_element: Tag) -> List[str]:
        child_text_parts: List[str] = []
        for child in parent_element.contents:
            if isinstance(child, NavigableString):
                text = str(child) 
                if text.strip(): 
                    child_text_parts.append(text)
            elif isinstance(child, Tag):
                if child.name in ['table', 'figure', 'img', 'sup', 'style', 'script'] or \
                   child.get('class') and any(c in child.get('class', []) for c in ['reference', 'noprint', 'mw-editsection']):
                    continue
                child_text_parts.extend(self._element_to_text_parts(child)) 
        return child_text_parts


    def clean_html_content(self, html_content: str, page_title: str) -> Dict[str, Any]:
        logger.info(f"Starting cleaning process for page: '{page_title}'")
        overall_start_time = time.monotonic()

        if not html_content:
            logger.warning(f"Received empty HTML content for cleaning page: {page_title}")
            return {"title": page_title, "url": "", "content": "", "sections": [], "images": None, "infobox_data": None}

        parse_start_time = time.monotonic()
        soup = BeautifulSoup(html_content, DEFAULT_PARSER)
        parse_duration = time.monotonic() - parse_start_time
        logger.debug(f"HTML parsing for '{page_title}' took {parse_duration:.4f} seconds.")

        html_title_tag = soup.find("h1", id="firstHeading")
        title_text = page_title
        if html_title_tag:
            extracted_title = normalize_whitespace(html_title_tag.get_text(separator=" ", strip=True))
            if extracted_title: title_text = extracted_title
            html_title_tag.decompose()

        self._preprocess_html(soup) 
        infobox_data_extracted = self._extract_infobox_data(soup) 
        self._remove_unwanted_wikipedia_elements(soup) 
        images_data_extracted = self._extract_images_from_content(soup) 

        content_area_find_start = time.monotonic()
        content_area = soup.find("div", class_="mw-parser-output")
        if not content_area:
            mw_content_text_div = soup.find("div", id="mw-content-text")
            if mw_content_text_div:
                content_area = mw_content_text_div.find("div", class_="mw-parser-output")
                if not content_area: content_area = mw_content_text_div
            else: content_area = None
        
        content_area_find_duration = time.monotonic() - content_area_find_start

        if not content_area:
            logger.error(f"Failed to find main content area for '{title_text}' after {content_area_find_duration:.4f}s. Content will be empty.")
            return {
                "title": title_text, "url": "", "content": "", "sections": [], 
                "images": images_data_extracted, "infobox_data": infobox_data_extracted
            }
        
        sections_list: List[str] = []
        if content_area:
            h2_tags_in_content = content_area.find_all("h2", recursive=False) 
            for h2_tag in h2_tags_in_content: 
                headline_span = h2_tag.find("span", class_="mw-headline")
                section_title_text = normalize_whitespace(headline_span.get_text(strip=True) if headline_span else h2_tag.get_text(strip=True))
                if section_title_text and section_title_text.lower() not in ["references", "external links", "see also", "notes", "contents", "bibliography", "further reading", "gallery"]:
                    sections_list.append(section_title_text)
        
        text_extraction_start_time = time.monotonic()
        text_build_parts: List[str] = []
        if content_area:
            direct_children = content_area.find_all(True, recursive=False)
            for element in direct_children: 
                text_parts_from_element = self._element_to_text_parts(element)
                text_build_parts.extend(text_parts_from_element)
        
        full_content_text = "".join(text_build_parts)
        text_extraction_duration = time.monotonic() - text_extraction_start_time
        logger.debug(f"Raw text extraction for '{title_text}' finished in {text_extraction_duration:.4f} seconds. Raw length: {len(full_content_text)} chars.")
        
        normalize_start_time = time.monotonic()
        full_content_text = normalize_whitespace(full_content_text) 
        full_content_text = re.sub(r'\s+\n', '\n', full_content_text) 
        full_content_text = re.sub(r'(\n\s*){3,}', '\n\n', full_content_text) 
        full_content_text = full_content_text.strip()
        normalize_duration = time.monotonic() - normalize_start_time
        logger.debug(f"Final text normalization for '{title_text}' finished in {normalize_duration:.4f} seconds. Final length: {len(full_content_text)} chars.")

        if sections_list and full_content_text:
            first_section_title_md = f"## {sections_list[0]}"
            if not full_content_text.lower().strip().startswith(first_section_title_md.lower().strip()):
                first_heading_match = re.search(r"^\s*(##+\s*.+?)\n", full_content_text, re.MULTILINE) 
                if first_heading_match:
                    intro_text_candidate = full_content_text[:first_heading_match.start()].strip()
                    if intro_text_candidate: 
                        sections_list.insert(0, "Introduction")
                elif full_content_text: 
                     sections_list.insert(0, "Introduction")
        elif not sections_list and full_content_text:
            sections_list.append("Content") 

        overall_duration = time.monotonic() - overall_start_time
        logger.info(f"Cleaning process for page '{title_text}' finished in {overall_duration:.4f} seconds.")
        
        return {
            "title": title_text,
            "url": "", 
            "content": full_content_text,
            "sections": sections_list,
            "images": images_data_extracted if self.keep_images else None,
            "infobox_data": infobox_data_extracted if self.keep_infobox else None,
        }