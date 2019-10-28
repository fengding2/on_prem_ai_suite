from imports import *
from kafka import KafkaProducer
import requests
import abc


class AbstractUploader(abc.ABC):
    def __init__(self, **kwargs):
        pass

    """
    uploader transfer picture binary buffer
    to server end
    return (Success_status, Message)
    """
    @abc.abstractmethod
    def send_pic_buf(self, dir, file_name, stream):
        pass

class HttpUploader(AbstractUploader):
    def __init__(self, server, port):
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        if is_param_invalid(server) or is_param_invalid(port):
            self._logger.error("invalid HttpUploader initial parameter")
            raise AttributeError("invalid HttpUploader initial parameter")
        self._server = server
        self._port = port
    
    def send_pic_buf(self, dir, file_name, stream):
        try:
            http_url = self._get_url(dir)
            if not stream:
                self._logger.error(file_name + "is None")
                return (False, file_name + "is None")
            upload_file = {file_name: stream}
            resp = requests.post(http_url, files=upload_file)
            if resp.ok:
                return (True, 'Success')
            else:
                return (False, 'Http Upload Fails')
        except Exception as e:
            self._logger.error(repr(e))
            return (False, repr(e))

    def _get_url(self, dir):
        return 'http://' + self._server + ':' + self._port + '/' + dir

    def close(self):
        pass


class KafkaUploader(AbstractUploader):
    def __init__(self, brokers, topic):
        loggerfactory = LoggerFactory(__name__)
        loggerfactory.add_handler(handler='TIME_FILE', format=DEFAULT_LOG_FORMAT, 
        log_dir=LOG_PATH, log_name=LOG_FILE_NAME)
        self._logger = loggerfactory.get_logger()
        if is_empty_list(brokers) or is_param_invalid(topic):
            self._logger.error("invalid KafkaUploader initial parameter")
            raise AttributeError("invalid KafkaUploader initial parameter")
        self._producer = KafkaProducer(bootstrap_servers=brokers, api_version=(0,10))
        self._topic = topic
    
    def send_pic_buf(self, dir, file_name, stream):
        try:
            if not stream:
                self._logger.error(file_name + "is None")
                return (False, file_name + "is None")
            key = bytes(file_name, 'ascii')
            future = self._producer.send(self._topic, key=key, value=stream, partition=0)
            future.get(timeout=10)
            return (True, 'Success')
        except Exception as e:
            self._logger.error(repr(e))
            return (False, 'Kafka Upload Fails')

    def close(self):
        self._producer.close()