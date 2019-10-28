import logging
import logging.handlers
import json
import re
from datetime import date, datetime, time
import traceback
import importlib

from kafka import KafkaProducer
from logging import Formatter                                                          
from logging import StreamHandler 
from inspect import istraceback
from collections import OrderedDict

DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
RESERVED_ATTRS = (
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
    'funcName', 'levelname', 'levelno', 'lineno', 'module',
    'msecs', 'message', 'msg', 'name', 'pathname', 'process',
    'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName')

level_dict = {"INFO": logging.INFO, "DEBUG": logging.DEBUG, 
        "WARNING": logging.WARNING, "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL, "DEFAULT": logging.WARNING}

class Utils():
    @staticmethod
    def str_eq(ins, enum):
        return ins == enum

    @staticmethod
    def log_level(levelname):
        return level_dict.get(levelname, logging.WARNING)

class LoggerFactory():
    def __init__(self, name, level='WARNING'):
        self._name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(Utils.log_level(level))

    def add_handler(self, **kwargs):
        handler_ins = None
        handler = kwargs.pop('handler', None)
        if Utils.str_eq(handler, 'FILE'):
            log_dir = kwargs.pop('log_dir', '.')
            log_name = kwargs.pop('log_name', 'default.log')
            log_file_name = log_dir + '/' + log_name
            handler_ins = logging.FileHandler(log_file_name)
        elif Utils.str_eq(handler, 'TIME_FILE'):
            ## standard rotating interval unit is DAY
            log_dir = kwargs.pop('log_dir', '.')
            log_name = kwargs.pop('log_name', 'default.log')
            backup_count = kwargs.pop('backup_count', 7)
            log_file_name = log_dir + '/' + log_name
            handler_ins = logging.handlers.TimedRotatingFileHandler(
                log_file_name, when='D', backupCount=backup_count) 
            handler_ins.suffix = "%Y-%m-%d.log"
        elif Utils.str_eq(handler, 'SOCKET'):
            host = kwargs.pop('host', '127.0.0.1')
            port = kwargs.pop('port', '3333')
            handler_ins = logging.handlers.SocketHandler(host, port)
        elif Utils.str_eq(handler, 'KAFKA'):
            broker = kwargs.pop('broker', None)
            topic = kwargs.pop('topic', None)
            if broker is None or topic is None:
                raise ValueError('wrong parameters in kafka handler')
            handler_ins = KafkaHandler(broker, topic)
        elif Utils.str_eq(handler, 'CONSOLE'):
            handler_ins = logging.StreamHandler()
        else:
            raise ValueError('handler cannot be found')
        handler_ins.setLevel(Utils.log_level(kwargs.get('level', 'DEFAULT')))
        formatter = self._define_formatter(
                        kwargs.get('is_json', 'False'), 
                        kwargs.get('format', DEFAULT_FORMAT))
        handler_ins.setFormatter(formatter)
        self._logger.addHandler(handler_ins)
        return self

    def _define_formatter(self, is_json, format):
        if Utils.str_eq(is_json, 'True'):
            formatter = JsonFormatter(format)
            return formatter
        else:
            formatter = logging.Formatter(format)
            return formatter

    def get_logger(self):
        return self._logger


def merge_record_extra(record, target, reserved):
    """
    Merges extra attributes from LogRecord object into target dictionary

    :param record: logging.LogRecord
    :param target: dict to update
    :param reserved: dict or list with reserved keys to skip
    """
    for key, value in record.__dict__.items():
        # this allows to have numeric keys
        if (key not in reserved
            and not (hasattr(key, "startswith")
                     and key.startswith('_'))):
            target[key] = value
    return target

class JsonEncoder(json.JSONEncoder):
    """
    A custom encoder extending the default JSONEncoder
    """
    def default(self, obj):
        if isinstance(obj, (date, datetime, time)):
            return self.format_datetime_obj(obj)
        elif istraceback(obj):
            return ''.join(traceback.format_tb(obj)).strip()
        elif type(obj) == Exception \
                or isinstance(obj, Exception) \
                or type(obj) == type:
            return str(obj)
        try:
            return super(JsonEncoder, self).default(obj)
        except TypeError:
            try:
                return str(obj)
            except Exception:
                return None

    def format_datetime_obj(self, obj):
        return obj.isoformat()


class JsonFormatter(logging.Formatter):
    """
    A custom formatter to format logging records as json strings.
    Extra values will be formatted as str() if not supported by
    json default encoder
    """
    def __init__(self, *args, **kwargs):
        """
        :param json_default: a function for encoding non-standard objects
            as outlined in http://docs.python.org/2/library/json.html
        :param json_encoder: optional custom encoder
        :param json_serializer: a :meth:`json.dumps`-compatible callable
            that will be used to serialize the log record.
        :param json_indent: an optional :meth:`json.dumps`-compatible numeric value
            that will be used to customize the indent of the output json.
        :param prefix: an optional string prefix added at the beginning of
            the formatted string
        :param json_indent: indent parameter for json.dumps
        :param json_ensure_ascii: ensure_ascii parameter for json.dumps
        :param reserved_attrs: an optional list of fields that will be skipped when
            outputting json log record. Defaults to all log record attributes:
            http://docs.python.org/library/logging.html#logrecord-attributes
        :param timestamp: an optional string/boolean field to add a timestamp when
            outputting the json log record. If string is passed, timestamp will be added
            to log record using string as key. If True boolean is passed, timestamp key
            will be "timestamp". Defaults to False/off.
        """
        self.json_default = self._str_to_fn(kwargs.pop("json_default", None))
        self.json_encoder = self._str_to_fn(kwargs.pop("json_encoder", None))
        self.json_serializer = self._str_to_fn(kwargs.pop("json_serializer", json.dumps))
        self.json_indent = kwargs.pop("json_indent", None)
        self.json_ensure_ascii = kwargs.pop("json_ensure_ascii", True)
        self.prefix = kwargs.pop("prefix", "")
        reserved_attrs = kwargs.pop("reserved_attrs", RESERVED_ATTRS)
        self.reserved_attrs = dict(zip(reserved_attrs, reserved_attrs))
        self.timestamp = kwargs.pop("timestamp", False)

        # super(JsonFormatter, self).__init__(*args, **kwargs)
        logging.Formatter.__init__(self, *args, **kwargs)
        if not self.json_encoder and not self.json_default:
            self.json_encoder = JsonEncoder

        self._required_fields = self.parse()
        self._skip_fields = dict(zip(self._required_fields,
                                     self._required_fields))
        self._skip_fields.update(self.reserved_attrs)

    def _str_to_fn(self, fn_as_str):
        """
        If the argument is not a string, return whatever was passed in.
        Parses a string such as package.module.function, imports the module
        and returns the function.

        :param fn_as_str: The string to parse. If not a string, return it.
        """
        if not isinstance(fn_as_str, str):
            return fn_as_str

        path, _, function = fn_as_str.rpartition('.')
        module = importlib.import_module(path)
        return getattr(module, function)

    def parse(self):
        """
        Parses format string looking for substitutions

        This method is responsible for returning a list of fields (as strings)
        to include in all log messages.
        """
        standard_formatters = re.compile(r'\((.+?)\)', re.IGNORECASE)
        return standard_formatters.findall(self._fmt)

    def add_fields(self, log_record, record, message_dict):
        """
        Override this method to implement custom logic for adding fields.
        """
        for field in self._required_fields:
            log_record[field] = record.__dict__.get(field)
        log_record.update(message_dict)
        merge_record_extra(record, log_record, reserved=self._skip_fields)

        if self.timestamp:
            key = self.timestamp if type(self.timestamp) == str else 'timestamp'
            log_record[key] = datetime.utcnow()

    def process_log_record(self, log_record):
        """
        Override this method to implement custom logic
        on the possibly ordered dictionary.
        """
        return log_record

    def jsonify_log_record(self, log_record):
        """Returns a json string of the log record."""
        return self.json_serializer(log_record,
                                    default=self.json_default,
                                    cls=self.json_encoder,
                                    indent=self.json_indent,
                                    ensure_ascii=self.json_ensure_ascii)

    def format(self, record):
        """Formats a log record and serializes to json"""
        message_dict = {}
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = None
        else:
            record.message = record.getMessage()
        # only format time if needed
        if "asctime" in self._required_fields:
            record.asctime = self.formatTime(record, self.datefmt)

        # Display formatted exception, but allow overriding it in the
        # user-supplied dict.
        if record.exc_info and not message_dict.get('exc_info'):
            message_dict['exc_info'] = self.formatException(record.exc_info)
        if not message_dict.get('exc_info') and record.exc_text:
            message_dict['exc_info'] = record.exc_text
        # Display formatted record of stack frames
        # default format is a string returned from :func:`traceback.print_stack`
        try:
            if record.stack_info and not message_dict.get('stack_info'):
                message_dict['stack_info'] = self.formatStack(record.stack_info)
        except AttributeError:
            # Python2.7 doesn't have stack_info.
            pass

        try:
            log_record = OrderedDict()
        except NameError:
            log_record = {}

        self.add_fields(log_record, record, message_dict)
        log_record = self.process_log_record(log_record)

        return "%s%s" % (self.prefix, self.jsonify_log_record(log_record))


class KafkaHandler(StreamHandler):
    def __init__(self, broker, topic):
        super(KafkaHandler, self).__init__()
        self._broker = broker
        self._topic = topic
        self._kafka_producer = KafkaProducer(bootstrap_servers=broker)

    def emit(self, record):
        try:
            msg = self.format(record)
            self._kafka_producer.send(self._topic, value=bytes(msg, 'utf-8'))
        except Exception:
            self.handleError(record)