import asyncio
import logging
import pathlib
import threading
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from types import MappingProxyType, TracebackType
from typing import Any, Protocol, Self

from watchdog.events import FileModifiedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger(__name__)

type StateType = MappingProxyType


class CallbackType(Protocol):
    async def __call__(self) -> StateType: ...


class AsyncWaitableEvent(threading.Event):
    async def async_wait(self, *, period: float = 0.1) -> None:
        while not super().wait(0):
            await asyncio.sleep(period)


class ThreadingEventOnModifiedHandler(FileSystemEventHandler):
    def __init__(
        self,
        event: AsyncWaitableEvent,
        path: pathlib.Path,
        *,
        grace_period: float = 0.5,
    ) -> None:
        super().__init__()
        self._event = event
        self._last_event_time: float = 0.0
        self._grace_period = grace_period
        self._path = path.absolute()

    @property
    def event(self) -> AsyncWaitableEvent:
        return self._event

    def on_modified(
        self, event: FileSystemEvent, *, at_time: float | None = None
    ) -> None:
        if at_time is None:
            at_time = time.time()

        path = pathlib.Path(
            srcpath if isinstance(srcpath := event.src_path, str) else srcpath.decode()
        )

        if path != self._path:
            # See the WARNING in the FileWatcher.__init__ constructor for
            # why we might be called file changes that we don't care about
            logger.debug(f"Ignored: {event}")
            return

        if at_time - self._last_event_time > self._grace_period:
            self._last_event_time = at_time
            logger.debug(f"File modified: {path}")
            self._event.set()
        else:
            logger.debug(
                f"File modified (again) within {self._grace_period}s "
                f"of last modification: {path}, ignoring…"
            )


class FileWatcher(AbstractAsyncContextManager[StateType]):
    def __init__(
        self,
        path: pathlib.Path,
        event: AsyncWaitableEvent | None = None,
        fire_once_asap: bool = False,
        *,
        observer: BaseObserver | None = None,
        event_handler_cls: Callable[
            [AsyncWaitableEvent, pathlib.Path], ThreadingEventOnModifiedHandler
        ] = ThreadingEventOnModifiedHandler,
    ) -> None:
        self._path = path
        self._event = event or AsyncWaitableEvent()
        self._fire_once_asap = fire_once_asap
        self._callbacks: list[CallbackType] = []
        self._state: dict[str, Any] = {}
        self._observer = observer or Observer()
        self._observer.schedule(
            event_handler_cls(self._event, self._path),
            str(self._path.parent.absolute()),
            # WARNING: Most likely due to a bug/limitation in `watchdog`
            # (https://github.com/gorakhargosh/watchdog/issues/1034),
            # it is not possible to listen to the file/path directly. Hence,
            # we must observe the file's parent (directory), filter the
            # generated events for FileModifiedEvent (to weed out
            # DirModifiedEvent) and then also compare the path of an
            # event to react only when the actual file is modified.
            event_filter=[FileModifiedEvent],
        )
        logger.info(f"Initialised FileWatcher on {self._path}")

    def register_callback(self, callback: CallbackType) -> None:
        self._callbacks.append(callback)

    @property
    def callbacks(self) -> frozenset[CallbackType]:
        return frozenset(self._callbacks)

    @property
    def state(self) -> StateType:
        return MappingProxyType(self._state)

    def __call__(self) -> Self:
        logger.debug(f"Configured FileWatcher on {self._path}")
        if self._fire_once_asap:
            logger.debug("Firing event handler per fire_once_asap")
            self._event.set()
        return self

    async def __aenter__(self) -> StateType:
        self._observer.start()
        logger.debug(f"Started FileWatcher {self._observer}")
        return MappingProxyType(self._state)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        _ = exc_type, exc_value, traceback

        self._observer.stop()
        logger.debug(f"Stopped FileWatcher {self._observer}")
        self._observer.join()

    async def _invoke_callbacks(self) -> None:
        for callback in self._callbacks:
            if (state_update := await callback()) is not None:
                self._state.update(state_update)

    def fire(self) -> None:
        self._event.set()

    async def reactor_task(self) -> None:
        while True:
            try:
                logger.debug("Waiting for watched file to change…")
                await self._event.async_wait()
                logger.info("Watched file changed, invoking callbacks…")
                await self._invoke_callbacks()

            except asyncio.CancelledError:
                logger.debug("Cancelling FileWatcher reactor task…")
                raise

            finally:
                self._event.clear()
