"""考勤系统日志配置。"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir):
    """同时输出到终端和轮转日志文件。"""
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'attendance.log')
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(getattr(h, '_attendance_handler', False) for h in root_logger.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console._attendance_handler = True

        file_handler = RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler._attendance_handler = True
        root_logger.addHandler(console)
        root_logger.addHandler(file_handler)

    logger = logging.getLogger('attendance')

    def log_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical('程序发生未处理异常',
                        exc_info=(exc_type, exc_value, exc_traceback))

    def log_thread_exception(args):
        logger.critical('后台线程 %s 发生未处理异常',
                        args.thread.name if args.thread else '未知',
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = log_uncaught_exception
    threading.excepthook = log_thread_exception
    logger.info('日志已启用: %s', log_path)
    return logger
