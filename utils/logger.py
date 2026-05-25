import logging
import os

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('AriaDownloader')
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    fh = logging.FileHandler('logs/app.log')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

log = setup_logger()