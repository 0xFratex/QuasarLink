# RabbitLink Usage Guide

This guide provides a quickstart and examples for using RabbitLink.

## Installation

(Refer to README.md for detailed installation instructions)

```bash
git clone https://github.com/your-org/rabbitlink.git
cd rabbitlink
# Create venv and activate
pip install -r requirements.txt 
# or poetry install

Markdown
Basic Commands
The main entry point is the rabbitlink command.
Interactive Mode
If you run rabbitlink without any arguments, it will enter interactive mode:
$ rabbitlink
RabbitLink: How many pages to scrape? ▸ 10
Confirm: scrape 10 pages? (Y/N) ▸ y
Enter output file [./output.json]: ▸ 
INFO: RabbitLink v0.1.0 starting...
INFO: Using 10 (random) pages from user input.
# ... progress ...
INFO: Successfully exported 10 articles to output.json
INFO: RabbitLink finished successfully!


Bash
Specifying Number of Pages
Use --num-pages or -n to specify how many random pages to scrape:
rabbitlink --num-pages 5

Bash
This will scrape 5 random Wikipedia pages and save them to output.json by default.
Specifying Output File
Use --output or -o to set the destination file:
rabbitlink --num-pages 3 --output data/my_articles.json

Bash
Scraping Specific Titles
Create a text file (e.g., titles.txt) with one Wikipedia page title per line:
titles.txt:
Albert Einstein
Theory of relativity
Python (programming language)

Then run:

rabbitlink --titles titles.txt --output articles_from_list.json

Bash
The --num-pages option will be ignored if --titles is used.
Content Options
Keeping Images
To include URLs and captions of images found on the page:
rabbitlink --num-pages 2 --keep-images --output articles_with_images.json
Use code with caution.
Bash
The output JSON for each article will include an "images" key (or as defined by your schema) containing a list of image objects.
Keeping Infobox Data
To include structured data from the page's infobox:
rabbitlink --num-pages 2 --keep-infobox --output articles_with_infobox.json
Use code with caution.
Bash
The output JSON will include an "infobox_data" key (or as defined by your schema) containing key-value pairs from the infobox.
Customizing JSON Output Schema
You can define the structure of the output JSON using a schema file (JSON or YAML).
Placeholders like {title}, {url}, {content}, {sections}, {images}, and {infobox_data} will be replaced.
my_custom_schema.yaml:
page_heading: "{title}"
web_url: "{url}"
article_body: "{content}"
# You can omit fields you don't need, e.g., sections
# static_field: "This value is always included"

Yaml
Run RabbitLink with your schema:
rabbitlink --num-pages 1 --schema my_custom_schema.yaml --output custom_output.json

Bash
The custom_output.json will contain objects structured according to my_custom_schema.yaml.
See docs/schema.md for more details on schema customization.
Logging
Logs are saved to rabbitlink.log in the directory where you run the command.
Use --verbose / -v for more detailed console and file logging (DEBUG level).
Use --quiet / -q to suppress most console output (errors will still be shown).
Examples
Scrape 5 random pages, include images and infobox data, save to detailed_articles.json, with verbose logging:
rabbitlink -n 5 --keep-images --keep-infobox -o detailed_articles.json -v

Bash
Scrape titles from mytitles.txt using a custom schema schema.json and save to final_data.json quietly:
rabbitlink -t mytitles.txt -s schema.json -o final_data.json -q