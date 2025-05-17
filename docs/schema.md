# RabbitLink JSON Schema Guide

RabbitLink allows you to customize the structure of the JSON output using a schema file. This guide explains how to create and use custom schemas.

## Default Schema

If no custom schema is provided, RabbitLink uses a default schema. The exact fields depend on flags like `--keep-images` and `--keep-infobox`. A typical default output for an article might look like this (if all flags are enabled):

```json
{
  "title": "Page Title",
  "url": "https://en.wikipedia.org/wiki/Page_Title",
  "content": "Cleaned article text…",
  "sections": ["Introduction", "History", "..."],
  "images": [
    {
      "src": "https://example.com/image.jpg",
      "alt": "Image alt text",
      "caption": "Image caption"
    }
  ],
  "infobox_data": {
    "Born": "1 January 1900",
    "Occupation": "Scientist"
    // ... other infobox fields
  }
}

Markdown
The final output is a JSON array of these objects.
Custom Schema Files
You can provide your own schema using the --schema <path_to_schema_file> option. The schema file can be in JSON or YAML format.
The schema file defines a template for each individual article object in the output JSON array.
Placeholders
Within your schema, you can use placeholders that RabbitLink will replace with extracted data. The available placeholders are:
{title}: The title of the Wikipedia page.
{url}: The URL of the Wikipedia page.
{content}: The cleaned main textual content of the article.
{sections}: A list of main section titles (typically H2 headings).
{images}: A list of image objects (dictionaries with src, alt, caption). Only populated if --keep-images is used and data is available. Otherwise, null.
{infobox_data}: A dictionary of key-value pairs from the article's infobox. Only populated if --keep-infobox is used and data is available. Otherwise, null.
Example Custom Schema (YAML)
Let's say you want a very specific output format:
my_schema.yaml:
article_id: "{title}"       # Use page title as an ID
source: "{url}"
text_content: "{content}"
# We are omitting sections in this custom schema
media: "{images}"           # Requires --keep-images
details: "{infobox_data}"   # Requires --keep-infobox
metadata:
  retrieval_date: "2023-10-27" # Static value
  tool_version: "RabbitLink v0.1" # Static value

Yaml
When you run RabbitLink with this schema:
rabbitlink --num-pages 1 --schema my_schema.yaml --keep-images --output my_data.json

Bash
The output for one article in my_data.json might look like:
[
  {
    "article_id": "Example Page",
    "source": "https://en.wikipedia.org/wiki/Example_Page",
    "text_content": "This is the cleaned content of the example page...",
    "media": [
      {
        "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Example.svg/100px-Example.svg.png",
        "alt": "Example SVG",
        "caption": "An example image."
      }
    ],
    "details": null, // Assuming no infobox or --keep-infobox was not used for this item
    "metadata": {
      "retrieval_date": "2023-10-27",
      "tool_version": "RabbitLink v0.1"
    }
  }
]

Json
Schema Structure (JSON example)
The equivalent JSON schema for the YAML example above would be:
my_schema.json:
{
  "article_id": "{title}",
  "source": "{url}",
  "text_content": "{content}",
  "media": "{images}",
  "details": "{infobox_data}",
  "metadata": {
    "retrieval_date": "2023-10-27",
    "tool_version": "RabbitLink v0.1"
  }
}

Json
Notes on Placeholders and Data Availability
If a placeholder like {images} or {infobox_data} is used in the schema, but the corresponding data is not available for an article (e.g., no images on the page, or the --keep-images flag was not used), the value for that key in the output JSON will be null.
If your schema includes a placeholder for which RabbitLink does not have corresponding data (e.g., you use {custom_field} but custom_field is not an internal data key), its value will also be null.
The schema applies to each article object. The final output file will always be a JSON array of these schema-formatted objects.
This placeholder-based system gives you significant flexibility in tailoring the JSON output to your specific needs for downstream processing.