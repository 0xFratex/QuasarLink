#!/bin/bash

# Activate your virtual environment if not using poetry run
# source venv/bin/activate

PYTHON_EXEC="poetry run python -m" # Or just "poetry run" if quasarlink script is preferred
# PYTHON_EXEC="python -m" # If not using poetry and venv is active
# CMD="quasarlink" # If installed globally or editable and in PATH
CMD="$PYTHON_EXEC quasarlink.cli"

echo "INFO: Make sure to update the User-Agent in quasarlink/cli.py (fetcher_worker_config)!"
echo "INFO: For Windows console, try 'chcp 65001' or set \$env:PYTHONUTF8='1' for better Unicode."
echo ""

echo "--- Running quasarlink with interactive prompts (defaults: 10 pages, thread, output.json) ---"
$CMD
# Example responses: 2, output1.json, Y

echo ""
echo "--- Running quasarlink for 3 random pages (threads), verbose output to custom_output.json ---"
$CMD --num-pages 3 --output examples/custom_output_threads.json --verbose --executor-type thread

echo ""
echo "--- Running quasarlink for 2 random pages (processes), keeping images ---"
$CMD -n 2 --output examples/custom_output_processes.json --keep-images -e process -w 2

echo ""
echo "--- Running quasarlink with a titles list and keeping infobox (max 1 worker) ---"
echo -e "Python (programming language)\nWeb scraping\nNatural language processing" > examples/sample_titles.txt
$CMD --titles examples/sample_titles.txt --output examples/titles_output.json --keep-infobox -w 1

echo ""
echo "--- Running quasarlink with a custom schema (2 pages, process executor) ---"
$CMD -n 2 --schema examples/custom_schema.yaml --output examples/schema_output.json --keep-images --keep-infobox -e process

echo ""
echo "Check quasarlink.log for detailed logs."
echo "Output files will be in ./ or examples/ directory."