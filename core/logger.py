import logging
import sys
from collections import deque
from threading import Lock

LOG_BUFFER_SIZE = 500
log_buffer: deque = deque(maxlen=LOG_BUFFER_SIZE)
log_buffer_lock = Lock()


class _BufferHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._next_id = 0

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with log_buffer_lock:
            self._next_id += 1
            log_buffer.append({
                "id": self._next_id,
                "level": record.levelname,
                "thread": record.threadName,
                "message": record.getMessage(),
                "formatted": msg,
            })


_FMT = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    "%H:%M:%S",
)

logger = logging.getLogger("autoscript")
logger.setLevel(logging.INFO)

_console = logging.StreamHandler(sys.stdout)
_console.setFormatter(_FMT)
logger.addHandler(_console)

_buffer = _BufferHandler()
_buffer.setFormatter(_FMT)
logger.addHandler(_buffer)

logger.propagate = False
