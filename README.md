# QuasarLink 🔗✨

**QuasarLink** is a powerful command-line tool designed to efficiently harvest, clean, and export Wikipedia articles into a structured JSON format, optimized for use with Large Language Models (LLMs) and other data analysis tasks. It provides robust content extraction, customizable output schemas, and concurrent processing capabilities.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add other badges as appropriate, e.g., build status, code coverage -->

## Features

*   **Targeted Content Extraction:** Intelligently extracts the main textual content of Wikipedia articles, removing navigation elements, sidebars, footers, references, and other boilerplate.
*   **Structured Output:** Exports data as JSON, with a default schema including title, URL, content, and section headings.
*   **Customizable Schema:** Define your own output JSON structure using a simple template file.
*   **Infobox Extraction:** Optionally extract structured data from Wikipedia infoboxes.
*   **Image Data:** Optionally include URLs, alt text, and captions for images found in articles.
*   **Concurrent Processing:** Utilizes multithreading or multiprocessing to fetch and process multiple articles simultaneously, significantly speeding up large-scale scraping tasks.
*   **Flexible Input:**
    *   Scrape a specified number of random Wikipedia articles.
    *   Process a list of specific article titles from a text file.
*   **Robust Error Handling:** Gracefully handles network issues and problematic page structures.
*   **Rate Limiting:** Respectful to Wikipedia's servers with configurable request delays.
*   **Detailed Logging:** Comprehensive logging for monitoring and debugging, with verbose and quiet modes.
*   **Rich CLI Output:** User-friendly command-line interface with progress bars and clear status messages, powered by Rich and Typer.
*   **Optimized Parsing:** Uses `lxml` for faster HTML parsing if available, falling back to Python's built-in `html.parser`.

## Requirements

*   Python 3.8+
*   Pip (Python package installer)

## Installation

1.  **Clone the repository (or download the source files):**
    ```bash
    git clone https://github.com/your-username/QuasarLink.git
    cd QuasarLink
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(You will need to create a `requirements.txt` file based on the imports in your project. Key dependencies include: `requests`, `beautifulsoup4`, `typer`, `rich`, `PyYAML`. Optionally `lxml` for faster parsing.)*

    A basic `requirements.txt` might look like:
    ```
    requests>=2.25.0
    beautifulsoup4>=4.9.0
    typer[all]>=0.9.0 # Includes 'rich'
    PyYAML>=5.0
    lxml>=4.6.0 # Optional, but recommended for speed
    ```

## Usage

QuasarLink is run from the command line.

```bash
python -m QuasarLink.cli [OPTIONS]
```

Or, if you set up an entry point in setup.py (see "Development" section below), you might be able to run it as:

```bash
quasarlink [OPTIONS]
```

## Command-Line Options
```text
Usage: python -m QuasarLink.cli [OPTIONS]

 QuasarLink ✨: Harvests, cleans, and exports Wikipedia articles to JSON. 🐇🔗

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --num-pages             -n      INTEGER    Number of Wikipedia pages to scrape (if --titles not used).   │
│                                            [min: 1]                                                      │
│ --titles                -t      PATH       Path to a text file with newline-separated page titles.       │
│                                            [exists]                                                      │
│ --output                -o      PATH       Path to the destination JSON file.                            │
│ --schema                -s      PATH       Path to a custom JSON or YAML schema template file. [exists]  │
│ --keep-images                      BOOLEAN  Include image URLs, alt text, and captions in the output.     │
│ --keep-infobox                   BOOLEAN  Include structured data extracted from the page's infobox.    │
│ --max-workers           -w      INTEGER    Max concurrent workers. For 'thread' (I/O-bound), can be >    │
│                                            CPU cores (e.g., 10-20). For 'process' (CPU-bound), best near │
│                                            os.cpu_count(). Default uses os.cpu_count(). [default: (num  │
│                                            CPUs)] [min: 1]                                               │
│ --executor-type         -e      [thread|  Concurrency model: 'thread' for I/O-bound tasks (like         │
│                                 process]   fetching) or 'process' for CPU-bound tasks (like intensive  │
│                                            cleaning). [default: thread]                                  │
│ --verbose               -v                 Enable verbose logging (DEBUG level to console and file).     │
│ --quiet                 -q                 Suppress most console output (INFO/DEBUG logs). Progress bar  │
│                                            also disabled. Errors still shown.                            │
│ --version                                  Show version and exit.                                        │
│ --help                          -h         Show this message and exit.                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Examples
Scrape 10 random Wikipedia articles and save to output.json:

```bash
python -m QuasarLink.cli --num-pages 10 --output random_articles.json
```

Process titles from my_titles.txt and include infobox data:

```bash
python -m QuasarLink.cli --titles my_titles.txt --keep-infobox --output processed_articles.json
```

my_titles.txt:
```text
Albert Einstein
Python (programming language)
Photosynthesis
```

Use a custom output schema and 8 worker threads:
Create my_schema.json:
```json
{
  "page_title": "{title}",
  "source_url": "{url}",
  "main_text": "{content}",
  "retrieved_images": "{images}"
}
```

Run the command:

```bash
python -m QuasarLink.cli --num-pages 5 --schema my_schema.json --keep-images --max-workers 8 --output custom_output.json
```

Run in verbose mode for detailed logging:

```bash
python -m QuasarLink.cli --num-pages 2 --verbose
```

Logs will be printed to the console and saved to QuasarLink.log.

## Output Data Structure

By default, each article in the output JSON array will have the following structure:

```json
[
  {
    "title": "Article Title",
    "url": "https://en.wikipedia.org/wiki/Article_Title",
    "content": "Cleaned textual content of the article...\n\n## Section 1\nText of section 1...\n\n## Section 2\nText of section 2...",
    "sections": [
      "Introduction", // If applicable
      "Section 1",
      "Section 2"
    ]
    // "images": [...] (if --keep-images is used)
    // "infobox_data": {...} (if --keep-infobox is used)
  },
  // ... more articles
]
```

content: The main textual content, with section headings formatted as Markdown (e.g., ## Section Title).
sections: A list of section titles found in the article. An "Introduction" section is often added if content exists before the first main heading.
images (optional): If --keep-images is enabled, this will be a list of dictionaries, each with src, alt, and caption for an image.
infobox_data (optional): If --keep-infobox is enabled, this will be a dictionary of key-value pairs extracted from the article's infobox.

## Custom Schema

You can define a custom structure for the output JSON objects. Create a JSON or YAML file where keys are your desired output keys, and values are either:
Placeholders: Strings like {title}, {url}, {content}, {sections}, {images}, {infobox_data}. These will be replaced by the corresponding extracted data.
Static values: Any other JSON/YAML value will be included as-is.

Example custom_schema.yaml:

```yaml
document_id: "{title}" # Map 'title' to 'document_id'
wiki_url: "{url}"
article_body: "{content}"
metadata:
  source: "Wikipedia"
  scraped_with: "QuasarLink"
  has_infobox: "{infobox_data}" # This will be the infobox dict or null
```

If a placeholder is used in the schema but the corresponding data isn't available (e.g., {images} when --keep-images is off or no images are found), its value will be null in the output.

## Logging

Console: Provides real-time feedback. Use --verbose for DEBUG level messages, or --quiet to suppress INFO/DEBUG logs.
File (QuasarLink.log): A rotating log file is created in the current directory, capturing detailed information. This file logs at INFO level by default, or DEBUG level if --verbose is used.

## Development & Contribution

Contributions are welcome! If you'd like to contribute:
Fork the repository.
Create a new branch for your feature or bug fix.
Make your changes.
Ensure your code is well-formatted (e.g., using Black) and includes tests if applicable.
Submit a pull request.

## Project Structure

```text
QuasarLink/
├── QuasarLink/                 # Main application package
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface logic (Typer)
│   ├── cleaner.py              # HTML cleaning and content extraction (BeautifulSoup)
│   ├── fetcher.py              # Wikipedia page fetching (Requests)
│   ├── serializer.py           # Data serialization to JSON
│   ├── config.py               # Schema loading and configuration
│   ├── logger.py               # Logging setup
│   ├── utils.py                # Utility functions
│   └── __main__.py             # Allows running with `python -m QuasarLink` (if created)
├── tests/                      # Unit and integration tests (recommended)
├── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

To make the tool runnable directly (e.g., quasarlink), you would typically add a setup.py or pyproject.toml file and define an entry point. For example, in pyproject.toml (using Poetry or Hatch, etc.):

```toml
[project.scripts]
quasarlink = "QuasarLink.cli:app"
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
(You'll need to create a LICENSE file containing the MIT License text.)

## Disclaimer

QuasarLink is a tool for accessing publicly available data from Wikipedia. Please be mindful of Wikipedia's Terms of Use and API usage guidelines. Use this tool responsibly and avoid making an excessive number of requests in a short period. The default request delay helps with this, but be considerate.