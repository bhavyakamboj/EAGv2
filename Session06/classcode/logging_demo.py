import logging, time
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(levelno)s - %(pathname)s - %(relativeCreated)d - %(thread)d - %(message)s')

logger = logging.getLogger(__name__)    

time.sleep(0.5)
logger.debug("This is a debug message")
time.sleep(1)
logger.info("This is an info message")
time.sleep(2)
logger.warning("This is a warning message")
time.sleep(0.5)
logger.error("This is an error message")
time.sleep(5)
logger.critical("This is a critical message")       

