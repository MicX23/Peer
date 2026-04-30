import logging, os

#   Python 3.13.7
#
# level:int -> 
# 1 — отладка               logging.DEBUG
# 2 — информация            logging.INFO
# 3 — предупреждение        logging.WARNING
# 4 — ошибка                logging.ERROR
# 5 — критическая ошибка    logging.CRITICAL
#

def get_logger(name:str, console:bool = True, level:int = 1) -> logging.Logger:
    if not level > 0 and not level < 6: return None 

    logger = logging.getLogger(name)
    match level:
        case 1: logger.setLevel(logging.DEBUG)
        case 2: logger.setLevel(logging.INFO)
        case 3: logger.setLevel(logging.WARNING)
        case 4: logger.setLevel(logging.ERROR)
        case 5: logger.setLevel(logging.CRITICAL)
    
    formartter = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s in %(filename)s:%(lineno)d: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'  
    )
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(f"./{log_dir}/{name}.log", encoding='utf-8')
    file_handler.setFormatter(formartter)    
    logger.addHandler(file_handler )  



    if console:
        console_handler = logging.StreamHandler()
        console_handler.stream.reconfigure(encoding='utf-8')
        console_handler.setFormatter(formartter) 
        logger.addHandler(console_handler)

    return logger   



if __name__ == '__main__':
    d = get_logger('test')
    d.debug("its ok")