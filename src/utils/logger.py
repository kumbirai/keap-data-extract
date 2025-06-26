import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.
    
    Args:
        name: The name for the logger, typically __name__
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
