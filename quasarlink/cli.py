# --- START OF MODIFIED cli.py ---

import logging
import typer # type: ignore
import click # For click.Choice
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    SpinnerColumn,
    MofNCompleteColumn,
)
from rich.table import Table

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed 
import threading 
import os 
import time # For timing

from . import __version__
from .logger import setup_logger
from .fetcher import WikipediaFetcher
from .cleaner import WikipediaCleaner
from .serializer import ArticleSerializer
from .config import get_effective_schema

console = Console(highlight=False) 
QuasarLink_BRAND_COLOR = "orange3" 
QuasarLink_TITLE = f"[bold {QuasarLink_BRAND_COLOR}]QuasarLink[/bold {QuasarLink_BRAND_COLOR}]"

app = typer.Typer(
    add_completion=False,
    help=Panel(Text(f"{QuasarLink_TITLE}: Harvest, clean, and export Wikipedia articles. 🔗", justify="center"), 
               title=QuasarLink_TITLE, 
               subtitle="[dim]Your Wikipedia Data Harvester[/dim]",
               border_style=QuasarLink_BRAND_COLOR),
    rich_markup_mode="markdown"
)

log_cli: Optional[logging.Logger] = None # Renamed to avoid conflict if 'log' is used elsewhere


def process_single_page_wrapper(args_tuple: Tuple[str, bool, bool, Dict[str, Any], bool]) -> Dict[str, Any]:
    page_title_arg, keep_images_cfg, keep_infobox_cfg, fetcher_init_cfg, verbose_cfg = args_tuple
    
    # Get a logger instance for this worker. It should inherit parent's setup.
    worker_log = logging.getLogger("QuasarLink.Worker") # Child logger
    
    process_id = os.getpid()
    thread_id = threading.get_ident()
    worker_id_str = f"PID:{process_id}/TID:{thread_id}"

    worker_log.info(f"[{worker_id_str}] Starting task for page: '{page_title_arg}'")
    task_start_time = time.monotonic()

    try:
        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] Initializing WikipediaFetcher with config: {fetcher_init_cfg}")
        init_fetcher_start = time.monotonic()
        local_fetcher = WikipediaFetcher(**fetcher_init_cfg)
        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] WikipediaFetcher initialized in {time.monotonic() - init_fetcher_start:.4f}s.")

        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] Initializing WikipediaCleaner (images: {keep_images_cfg}, infobox: {keep_infobox_cfg})")
        init_cleaner_start = time.monotonic()
        local_cleaner = WikipediaCleaner(keep_images=keep_images_cfg, keep_infobox=keep_infobox_cfg)
        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] WikipediaCleaner initialized in {time.monotonic() - init_cleaner_start:.4f}s.")

    except Exception as e:
        worker_log.error(f"[{worker_id_str} | {page_title_arg}] Component initialization failed: {e}", exc_info=verbose_cfg)
        return {"title": page_title_arg, "error": f"Component initialization failed: {str(e)}"}

    # Fetching
    worker_log.debug(f"[{worker_id_str} | {page_title_arg}] Starting HTML fetch.")
    fetch_start_time = time.monotonic()
    html_content = local_fetcher.fetch_page_html(page_title_arg)
    fetch_duration = time.monotonic() - fetch_start_time
    worker_log.debug(f"[{worker_id_str} | {page_title_arg}] HTML fetch completed in {fetch_duration:.4f}s.")

    if not html_content:
        msg = f"Could not fetch HTML for page: {page_title_arg}. Skipping."
        worker_log.warning(f"[{worker_id_str} | {page_title_arg}] {msg}")
        task_duration = time.monotonic() - task_start_time
        worker_log.info(f"[{worker_id_str}] Task for page '{page_title_arg}' ended with fetch failure in {task_duration:.4f}s.")
        return {"title": page_title_arg, "error": "Failed to fetch HTML"}

    # Cleaning
    worker_log.debug(f"[{worker_id_str} | {page_title_arg}] Starting HTML cleaning.")
    clean_start_time = time.monotonic()
    try:
        cleaned_data = local_cleaner.clean_html_content(html_content, page_title=page_title_arg)
        clean_duration = time.monotonic() - clean_start_time
        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] HTML cleaning completed in {clean_duration:.4f}s.")
        
        cleaned_title_for_url = cleaned_data.get("title", page_title_arg) # Use title from cleaning if different
        cleaned_data["url"] = local_fetcher.get_page_url_from_title(cleaned_title_for_url)
        worker_log.debug(f"[{worker_id_str} | {page_title_arg}] Added URL to cleaned data: {cleaned_data['url']}")
        
        task_duration = time.monotonic() - task_start_time
        worker_log.info(f"[{worker_id_str}] Task for page '{page_title_arg}' (final title: '{cleaned_title_for_url}') completed successfully in {task_duration:.4f}s.")
        return {"title": page_title_arg, "data": cleaned_data}
    except Exception as e:
        clean_duration = time.monotonic() - clean_start_time
        worker_log.error(f"[{worker_id_str} | {page_title_arg}] Error cleaning page after {clean_duration:.4f}s: {e}", exc_info=verbose_cfg)
        task_duration = time.monotonic() - task_start_time
        worker_log.info(f"[{worker_id_str}] Task for page '{page_title_arg}' ended with cleaning error in {task_duration:.4f}s.")
        return {"title": page_title_arg, "error": f"Cleaning error: {str(e)}"}


def version_callback(value: bool):
    if value:
        console.print(f"{QuasarLink_TITLE} Version: [cyan]{__version__}[/cyan]")
        raise typer.Exit()

@app.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True
)
def main(
    num_pages_option: Optional[int] = typer.Option(None, "--num-pages", "-n", help="Number of Wikipedia pages to scrape (if --titles not used).", show_default=False, min=1),
    titles_file: Optional[Path] = typer.Option(None, "--titles", "-t", help="Path to a text file with newline-separated page titles.", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True, show_default=False),
    output_file_option: Optional[Path] = typer.Option(None, "--output", "-o", help="Path to the destination JSON file.", file_okay=True, dir_okay=False, writable=True, resolve_path=True, show_default=False),
    schema_file: Optional[Path] = typer.Option(None, "--schema", "-s", help="Path to a custom JSON or YAML schema template file.", exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True, show_default=False),
    keep_images: bool = typer.Option(False, "--keep-images", help="Include image URLs, alt text, and captions in the output."),
    keep_infobox: bool = typer.Option(False, "--keep-infobox", help="Include structured data extracted from the page's infobox."),
    max_workers: int = typer.Option(lambda: os.cpu_count() or 1, "--max-workers", "-w", help="Max concurrent workers. For 'thread' (I/O-bound), can be > CPU cores (e.g., 10-20). For 'process' (CPU-bound), best near os.cpu_count(). Default uses os.cpu_count().", min=1, max=64), # Updated help
    executor_type: str = typer.Option("thread", "--executor-type", "-e", help="Concurrency model: 'thread' for I/O-bound tasks (like fetching) or 'process' for CPU-bound tasks (like intensive cleaning).", case_sensitive=False, click_type=click.Choice(["thread", "process"], case_sensitive=False)),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging (DEBUG level to console and file)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress most console output (INFO/DEBUG logs). Progress bar also disabled. Errors still shown."),
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show version and exit."),
):
    """
    {QuasarLink_TITLE}: Harvests, cleans, and exports Wikipedia articles to JSON. 🐇🔗
    """ 
    global log_cli # Use the renamed global logger variable
    log_cli = setup_logger(verbose=verbose, quiet=quiet) # log_cli is now the main logger for CLI
    
    if not quiet:
        console.print(Panel(f"{QuasarLink_TITLE} v{__version__} starting...", title=f"[bold {QuasarLink_BRAND_COLOR}]Status[/bold {QuasarLink_BRAND_COLOR}]", expand=False, border_style=QuasarLink_BRAND_COLOR))
    log_cli.info(f"QuasarLink v{__version__} starting with args: num_pages_option={num_pages_option}, titles_file={titles_file}, output_file_option={output_file_option}, schema_file={schema_file}, keep_images={keep_images}, keep_infobox={keep_infobox}, max_workers={max_workers}, executor_type='{executor_type}', verbose={verbose}, quiet={quiet}")


    num_pages: int
    page_titles_to_fetch: List[str] = []

    if titles_file:
        log_cli.info(f"Loading titles from file: {titles_file}")
        try:
            with open(titles_file, 'r', encoding='utf-8') as f:
                page_titles_to_fetch = [line.strip() for line in f if line.strip()]
            if not page_titles_to_fetch:
                msg = f"Titles file [cyan]{titles_file}[/cyan] is empty or contains no valid titles."
                log_cli.error(msg)
                if not quiet: console.print(f"[bold red]Error:[/bold red] {msg}")
                raise typer.Exit(code=1)
            log_cli.info(f"Loaded {len(page_titles_to_fetch)} titles from {titles_file}.")
            if not quiet: console.print(f"🗂️ Loaded [bold yellow]{len(page_titles_to_fetch)}[/bold yellow] titles from [cyan]{titles_file}[/cyan].")
        except Exception as e:
            log_cli.error(f"Error reading titles file {titles_file}: {e}", exc_info=verbose)
            if not quiet: console.print(f"[bold red]Error:[/bold red] Could not read [cyan]{titles_file}[/cyan]: {e}")
            raise typer.Exit(code=1)
        num_pages = len(page_titles_to_fetch)
        if num_pages_option is not None and num_pages_option != num_pages:
            log_cli.warning(f"--num-pages ({num_pages_option}) ignored as --titles file provides {num_pages} titles.")
            if not quiet: console.print(f"[yellow]⚠️ Warning:[/yellow] --num-pages option ignored; using {num_pages} titles from file.")
    elif num_pages_option is not None:
        num_pages = num_pages_option
        log_cli.info(f"Number of pages to scrape set to {num_pages} from CLI option.")
    else:
        if quiet:
            log_cli.error("Number of pages not specified and quiet mode enabled. Please use --num-pages or run interactively.")
            raise typer.Exit(code=1)
        log_cli.debug("Prompting user for number of pages.")
        num_pages = typer.prompt(Text("➡️ How many pages to scrape?", style="bold magenta"), type=int, default=10)
        log_cli.info(f"User entered {num_pages} pages to scrape.")


    output_path: Path
    if output_file_option is not None:
        output_path = output_file_option
        log_cli.info(f"Output file path set to {output_path} from CLI option.")
    else:
        if quiet:
            output_path = Path("./output.json").resolve()
            log_cli.info(f"Quiet mode: Output file path defaulting to {output_path}")
        else:
            default_output_str = "./output.json"
            log_cli.debug(f"Prompting user for output file path (default: {default_output_str}).")
            output_path_str = typer.prompt(Text("➡️ Enter output file path", style="bold magenta"), default=default_output_str)
            output_path = Path(output_path_str).resolve()
            log_cli.info(f"User entered output file path: {output_path}")

    if not quiet:
        confirm_text = Text("", style="bold magenta")
        if not page_titles_to_fetch:
            confirm_text.append("❓ Confirm: scrape ").append(str(num_pages), style="bold yellow").append(" random pages")
        else:
            confirm_text.append("❓ Confirm: process ").append(str(num_pages), style="bold yellow").append(" titles from file")
        confirm_text.append(" using ").append(str(max_workers), style="bold cyan").append(f" {executor_type}(s)")
        confirm_text.append(" and save to ").append(str(output_path.name), style="cyan")
        confirm_text.append(f" (in {output_path.parent})?", style="bold magenta")
        
        log_cli.debug(f"Prompting user for confirmation: {confirm_text.plain}")
        if not typer.confirm(confirm_text, default=True):
            log_cli.info("User cancelled operation at confirmation prompt.")
            console.print("[yellow]⛔ Operation cancelled by user.[/yellow]")
            raise typer.Exit()
        log_cli.info("User confirmed operation.")
    
    if output_path.is_dir():
        msg = f"Output path [cyan]{output_path}[/cyan] is a directory. Please specify a file path."
        log_cli.error(msg); 
        if not quiet: console.print(f"[bold red]Error:[/bold red] {msg}")
        raise typer.Exit(code=1)
    try:
        log_cli.debug(f"Ensuring output directory {output_path.parent} exists.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log_cli.error(f"Could not create output directory {output_path.parent}: {e}", exc_info=verbose)
        if not quiet: console.print(f"[bold red]Error:[/bold red] Could not create output directory [cyan]{output_path.parent}[/cyan]: {e}")
        raise typer.Exit(code=1)

    try:
        log_cli.debug(f"Loading effective schema (custom: {schema_file}, images: {keep_images}, infobox: {keep_infobox}).")
        effective_schema = get_effective_schema(schema_file, keep_images, keep_infobox)
        log_cli.debug(f"Initializing ArticleSerializer with schema: {effective_schema}")
        serializer = ArticleSerializer(schema=effective_schema)
    except Exception as e:
        log_cli.error(f"Initialization error (schema/serializer): {e}", exc_info=verbose)
        if not quiet: console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not page_titles_to_fetch: # Only fetch random if no titles file was provided or it was empty
        log_cli.info(f"Fetching {num_pages} random page titles as no specific titles were provided.")
        if not quiet: console.print(f"⏳ Fetching [bold yellow]{num_pages}[/bold yellow] random page titles...")
        
        # User agent for initial random title fetching (can be simpler)
        initial_fetcher_config = {
            "user_agent": f"QuasarLink/{__version__}/RandomTitleFetcher (your-contact@example.com)", 
            "request_delay": 0.2, "retries": 2 # Lighter delay for API calls if they are batched
        }
        log_cli.debug(f"Initializing fetcher for random titles with config: {initial_fetcher_config}")
        initial_fetcher = WikipediaFetcher(**initial_fetcher_config)
        
        random_fetch_start = time.monotonic()
        page_titles_to_fetch = initial_fetcher.get_random_page_titles(num_pages)
        random_fetch_duration = time.monotonic() - random_fetch_start
        
        if not page_titles_to_fetch:
             log_cli.error(f"Failed to fetch any random page titles after {random_fetch_duration:.4f}s. Exiting.")
             if not quiet: console.print("[bold red]Error:[/bold red] Failed to fetch random page titles.")
             raise typer.Exit(code=1)
        log_cli.info(f"Fetched {len(page_titles_to_fetch)} random titles in {random_fetch_duration:.4f}s.")
        if not quiet: console.print(f"✅ Fetched {len(page_titles_to_fetch)} titles. Now processing content...")
    
    if not page_titles_to_fetch:
        if not quiet: console.print("[yellow]No pages to process. Exiting.[/yellow]")
        log_cli.info("No page titles available to process after attempting to load/fetch. Exiting.")
        raise typer.Exit()

    all_articles_data: List[Dict[str, Any]] = []
    failed_articles_summary: List[Dict[str, str]] = []
    
    # User agent for main content fetching
    fetcher_worker_config = {
        "user_agent": f"QuasarLink/{__version__} (https://your-project-url-or-contact.com; your-contact@example.com)", # **UPDATE THIS USER AGENT**
        "retries": 3, "backoff_factor": 0.5, "request_delay": 1.0 # Standard delay for page scraping
    }
    log_cli.debug(f"Worker fetcher configuration set: {fetcher_worker_config}")

    tasks_args_list: List[Tuple[str, bool, bool, Dict[str, Any], bool]] = [
        (title, keep_images, keep_infobox, fetcher_worker_config, verbose) for title in page_titles_to_fetch
    ]

    log_cli.info(f"Starting to process {len(tasks_args_list)} Wikipedia pages using up to {max_workers} {executor_type}(s)...")
    if not quiet: console.print(f"⚙️ Submitting {len(tasks_args_list)} tasks to [bold cyan]{max_workers} {executor_type}(s)[/bold cyan]...")

    simplified_progress_columns = [
        SpinnerColumn(spinner_name="dots", style=QuasarLink_BRAND_COLOR),
        TextColumn("[progress.description]{task.description}", style="green"),
        BarColumn(bar_width=None, style=QuasarLink_BRAND_COLOR, complete_style="green"),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%", style="magenta"),
        TimeElapsedColumn(),
        TextColumn("ETA:", style=f"dim {QuasarLink_BRAND_COLOR}"),
        TimeRemainingColumn(elapsed_when_finished=True),
    ]
    
    SelectedExecutor = ThreadPoolExecutor if executor_type == "thread" else ProcessPoolExecutor
    log_cli.debug(f"Selected executor: {SelectedExecutor.__name__}")

    overall_processing_start_time = time.monotonic()
    with Progress(*simplified_progress_columns, console=console, disable=quiet, transient=False) as progress_bar:
        overall_task_id = progress_bar.add_task(
            f"Processing {len(tasks_args_list)} Wikipedia pages...",
            total=len(tasks_args_list)
        )
        
        with SelectedExecutor(max_workers=max_workers) as executor:
            log_cli.debug(f"Executor '{executor_type}' started with {max_workers} workers.")
            future_to_original_title = {}
            for idx, arg_tuple in enumerate(tasks_args_list):
                original_title = arg_tuple[0]
                log_cli.debug(f"Submitting task {idx+1}/{len(tasks_args_list)} for page '{original_title}' to executor.")
                future = executor.submit(process_single_page_wrapper, arg_tuple)
                future_to_original_title[future] = original_title
            
            log_cli.info(f"All {len(tasks_args_list)} tasks submitted to executor. Waiting for completion...")

            for future_idx, future in enumerate(as_completed(future_to_original_title)):
                original_title = future_to_original_title[future]
                progress_bar.update(overall_task_id, advance=1)
                log_cli.debug(f"Future {future_idx+1}/{len(tasks_args_list)} for page '{original_title}' completed.")

                try:
                    result_dict = future.result() # This call blocks until the future is done.
                    if "data" in result_dict and result_dict["data"] is not None:
                        all_articles_data.append(result_dict["data"])
                        log_cli.debug(f"Successfully processed and received data for page '{original_title}'.")
                    elif "error" in result_dict:
                        failed_articles_summary.append({"title": result_dict["title"], "error_message": result_dict["error"]})
                        log_cli.warning(f"Page '{result_dict['title']}' processing resulted in error: {result_dict['error']}")
                except Exception as exc: # This catches errors from future.result() itself (e.g. if task raised unhandled exception)
                    log_cli.error(f"Task for '{original_title}' generated an unhandled exception during future.result(): {exc}", exc_info=verbose)
                    if not quiet: console.print(f"[bold red]Critical Error for '{original_title}': {exc}[/bold red]")
                    failed_articles_summary.append({"title": original_title, "error_message": f"Unhandled worker exception: {exc}"})
        
        log_cli.info(f"All {len(tasks_args_list)} submitted tasks have been processed by the executor.")
        progress_bar.update(overall_task_id, description=f"[bold green]All pages processed using {executor_type}(s)!")
    
    overall_processing_duration = time.monotonic() - overall_processing_start_time
    log_cli.info(f"Total processing time for {len(tasks_args_list)} pages: {overall_processing_duration:.4f} seconds.")

    success_count = len(all_articles_data)
    failure_count = len(failed_articles_summary)
    total_attempted = len(page_titles_to_fetch)

    if not quiet:
        summary_panel_title = f"[bold {QuasarLink_BRAND_COLOR}]Processing Summary[/bold {QuasarLink_BRAND_COLOR}]"
        summary_text = Text()
        summary_text.append(f"Total processing time: {overall_processing_duration:.2f} seconds\n", style="dim")
        summary_text.append(f"Attempted: {total_attempted} pages\n", style="dim")
        summary_text.append(f"Successfully processed: {success_count} pages\n", style="green")
        summary_text.append(f"Failed to process: {failure_count} pages", style="red" if failure_count > 0 else "dim")
        console.print(Panel(summary_text, title=summary_panel_title, border_style=QuasarLink_BRAND_COLOR, expand=False))

    if failure_count > 0 and not quiet:
        log_cli.warning(f"Encountered {failure_count} errors during processing. See summary and QuasarLink.log.")
        console.print(Panel(f"[bold yellow]⚠️ Encountered {failure_count} errors during processing.[/bold yellow]", title="[orange_red1]Error Details[/orange_red1]", border_style="orange_red1"))
        error_table = Table(title=f"Failed Pages (showing up to 10 of {failure_count})", show_lines=True, border_style="dim red", expand=True, caption_style="dim")
        error_table.add_column("Page Title", style="cyan", overflow="fold", min_width=20, no_wrap=False)
        error_table.add_column("Error Message", style="red", overflow="fold", min_width=40, no_wrap=False)
        for item in failed_articles_summary[:10]:
            error_table.add_row(item["title"], item["error_message"])
        if failure_count > 10:
            error_table.caption = f"...and {failure_count - 10} more. Check `QuasarLink.log` for all errors."
        console.print(error_table)

    if all_articles_data:
        try:
            log_cli.info(f"Serializing {success_count} successfully processed articles to {output_path}.")
            serialization_start_time = time.monotonic()
            serializer.serialize_articles(all_articles_data, output_path)
            serialization_duration = time.monotonic() - serialization_start_time
            log_cli.info(f"Successfully exported {success_count} articles to {output_path} in {serialization_duration:.4f}s.")
            if not quiet: console.print(Panel(f"✅ Successfully exported [bold yellow]{success_count}[/bold yellow] articles to [cyan]{output_path}[/cyan] (took {serialization_duration:.2f}s)", title=f"[bold {QuasarLink_BRAND_COLOR}]Output Saved[/bold {QuasarLink_BRAND_COLOR}]", expand=False, border_style=QuasarLink_BRAND_COLOR))
        except Exception as e:
            log_cli.error(f"Failed to serialize articles to {output_path}: {e}", exc_info=verbose)
            if not quiet: console.print(f"[bold red]Error:[/bold red] Failed to serialize articles to [cyan]{output_path}[/cyan]: {e}")
    elif total_attempted > 0:
        log_cli.warning("No data was successfully processed to serialize.")
        if not quiet: console.print("[yellow]No data was successfully processed to serialize.[/yellow]")
    else:
        log_cli.info("No articles were attempted, so nothing to serialize.")


    log_cli.info("QuasarLink finished operation.")
    final_message_style = f"bold {QuasarLink_BRAND_COLOR}" 
    final_message = f"🎉 {QuasarLink_TITLE} finished successfully!"
    if failure_count > 0:
        final_message_style = "bold orange_red1"
        final_message = f"🏁 {QuasarLink_TITLE} finished with {failure_count} errors. Please check logs and error summary."
    elif success_count == 0 and total_attempted > 0:
        final_message_style = "bold yellow"
        final_message = f"🏁 {QuasarLink_TITLE} finished, but no articles were successfully processed."
    elif total_attempted == 0:
        final_message_style = "dim"
        final_message = f"🏁 {QuasarLink_TITLE} finished. No pages were specified for processing."

    if not quiet or failure_count > 0 or (success_count == 0 and total_attempted > 0) :
        console.print(final_message, style=final_message_style)

if __name__ == "__main__":
    app()
# --- END OF MODIFIED cli.py