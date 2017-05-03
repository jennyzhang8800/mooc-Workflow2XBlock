# coding: utf8
# luofuwen

import logging


class Util:
    @staticmethod
    def logger(config):
        '''
        获取logger
        '''
        fh = logging.FileHandler(config['logFile'], encoding="utf-8")
        fmt = logging.Formatter(config['logFmt'])
        fh.setFormatter(fmt)
        logger = logging.getLogger(config['logName'])
        logger.setLevel(config['logLevel'])
        logger.addHandler(fh)
        return logger
