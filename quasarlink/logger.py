# QuasarLink/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
import queue # For the QueueListener
from rich.logging import RichHandler
from rich.console import Console

LOG_FILE = "QuasarLink.log"
MAX_LOG_SIZE_MB = 5
BACKUP_COUNT = 3

rich_console_for_logging = Console(stderr=True)
log_queue = queue.Queue(-1) # Infinite size queue

# Global listener variable, to be started by the main process
_queue_listener = None

def setup_logger(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    global _queue_listener
    logger = logging.getLogger("QuasarLink")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File Handler Setup (using QueueListener for multiprocessing safety) ---
    try:
        # This is the actual handler that writes to the file
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - P%(process)d T%(threadName)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

        # If the listener isn't running, set it up and start it
        # This should ideally only happen once in the main process
        if _queue_listener is None:
            _queue_listener = QueueListener(log_queue, file_handler, respect_handler_level=True)
            _queue_listener.start()
            # Add a handler that puts records onto the queue
            queue_log_handler = QueueHandler(log_queue)
            logger.addHandler(queue_log_handler)
            logger.info("QueueListener for file logging started. File logs will be processed via queue.")
        else:
            # If listener is already running, just add the QueueHandler
            # This path might be taken if setup_logger is called multiple times in the same process,
            # or if child processes also call setup_logger (though they should inherit the root logger config).
            queue_log_handler = QueueHandler(log_queue)
            if not any(isinstance(h, QueueHandler) for h in logger.handlers): # Avoid duplicate queue handlers
                 logger.addHandler(queue_log_handler)


    except Exception as e:
        sys.stderr.write(f"CRITICAL: Failed to initialize file logging system: {e}\n")


    # --- Console Handler (using RichHandler if not quiet) ---
    if not quiet:
        # Check if a RichHandler is already present to avoid duplication
        if not any(isinstance(h, RichHandler) for h in logger.handlers):
            rich_handler = RichHandler(
                level=logging.DEBUG if verbose else logging.INFO,
                console=rich_console_for_logging,
                show_time=True,
                show_level=True,
                show_path=False, # Keeps console logs cleaner
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=verbose,
                log_time_format="[%X]" # e.g., [14:30:59]
            )
            # RichHandler's formatter is mostly controlled by its own parameters
            # Forcing a formatter can sometimes conflict with its rich output.
            # If specific formatting is needed, it's often better to subclass RichHandler.
            logger.addHandler(rich_handler)
            logger.info("Rich console logging initialized.")
    
    # Minimal stderr for critical errors if quiet
    if quiet:
        if not any(h.name == "critical_stderr_handler" for h in logger.handlers):
            error_ch = logging.StreamHandler(sys.stderr)
            error_ch.name = "critical_stderr_handler"
            error_formatter = logging.Formatter('CRITICAL ERROR: %(message)s')
            error_ch.setFormatter(error_formatter)
            error_ch.setLevel(logging.CRITICAL)
            logger.addHandler(error_ch)

    if verbose and not quiet:
        logger.debug("Verbose (DEBUG level) logging enabled for console and file.")
    
    logger.info("Logger setup complete. File: %s, Verbose: %s, Quiet: %s", LOG_FILE, verbose, quiet)
    return logger

def stop_logger_queue_listener():
    """Stops the queue listener, ensuring all logs are flushed."""
    global _queue_listener
    if _queue_listener:
        logger = logging.getLogger("QuasarLink")
        logger.info("Stopping logger queue listener...")
        _queue_listener.stop()
        _queue_listener = None
        print("Logger queue listener stopped.", file=sys.stderr) # Direct print as logger might be down