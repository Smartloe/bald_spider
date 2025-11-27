from logging import Formatter, StreamHandler, INFO, getLogger, DEBUG, WARNING, ERROR, CRITICAL

LOG_FORMAT = f" %(asctime)s [%(name)s] %(levelname)s::%(message)s"


class LoggerManager:
    logger = {}

    @classmethod
    def get_logger(cls, name: str = "default", log_level=None, log_format=LOG_FORMAT):
        key = (name, log_level)

        def gen_logger():
            # 使用标准的 getLogger 方法创建 logger
            _logger = getLogger(name)
            _logger.handlers.clear()  # 清除可能存在的默认处理器
            
            # 创建格式化器和处理器
            logger_format = Formatter(log_format)
            handler = StreamHandler()
            handler.setFormatter(logger_format)
            
            # 设置日志级别
            level = log_level or INFO
            handler.setLevel(level)
            _logger.setLevel(level)
            
            # 添加处理器
            _logger.addHandler(handler)
            
            cls.logger[key] = _logger
            return _logger

        return cls.logger.get(key, None) or gen_logger()


get_logger = LoggerManager.get_logger
