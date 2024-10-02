from PyQt5.QtCore import QObject, pyqtSignal

class Logger(QObject):
    logging_signal = pyqtSignal(object)

class MCLogger(QObject):
    logging_element = None
    logger = Logger()

    @classmethod
    def logControl(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='#4EC9B0'>[Mission Control] </font>{message}</html>")
    
    @classmethod
    def logOK(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='#2595A2'>[OK] </font>{message}</html>")
    
    @classmethod
    def logProblem(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='yellow'>[Problem] </font>{message}</html>")

    @classmethod
    def logError(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='red'>[Error] </font>{message}</html>")
    
    @classmethod
    def logRover(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='purple'>[Rover] </font>{message}</html>")
    
    @classmethod
    def logCritical(cls, message:str):
        MCLogger.logger.logging_signal.emit(f"<html><font color='red'>[CRITICAL] </font>{message}</html>")
    
    @classmethod
    def set_logging_element(cls, logging_element):
        MCLogger.logging_element = logging_element
        MCLogger.logger.logging_signal.connect(logging_element.log)


        
