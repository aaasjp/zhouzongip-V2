import logging

def setup_logging():
    logging.basicConfig(filename='logs/vector_db_server.log', encoding='utf-8', level=logging.INFO,
                        format='%(asctime)s - %(filename)s - %(funcName)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
