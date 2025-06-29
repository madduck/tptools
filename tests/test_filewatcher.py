import asyncio
import pathlib
from types import MappingProxyType

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer

from tptools.filewatcher import (
    AsyncWaitableEvent,
    CallbackType,
    FileWatcher,
    StateType,
    ThreadingEventOnModifiedHandler,
)


@pytest.mark.asyncio
async def test_asyncwaitableevent(mocker: MockerFixture) -> None:
    wait = mocker.patch("threading.Event.wait")
    wait.side_effect = [False, True]
    sleep = mocker.patch("asyncio.sleep")

    event = AsyncWaitableEvent()

    await event.async_wait(period=0.1)

    sleep.assert_called_once_with(0.1)
    for call in wait.call_args_list:
        assert call.args[0] == 0


_ = CallbackType


@pytest.fixture
def path() -> pathlib.Path:
    return pathlib.Path("/does/not/exist")


@pytest.fixture
def handler(path: pathlib.Path) -> ThreadingEventOnModifiedHandler:
    return ThreadingEventOnModifiedHandler(AsyncWaitableEvent(), path)


def test_handler_constructor(handler: ThreadingEventOnModifiedHandler) -> None:
    _ = handler


@pytest.fixture
def fakeevent(path: pathlib.Path) -> FileSystemEvent:
    return FileSystemEvent(src_path=str(path), is_synthetic=True)


def test_handler_sets_event_on_modified(
    handler: ThreadingEventOnModifiedHandler,
    fakeevent: FileSystemEvent,
) -> None:
    assert not handler.event.is_set()
    handler.on_modified(fakeevent)
    assert handler.event.is_set()


def test_handler_on_modified_skip_too_fast(
    handler: ThreadingEventOnModifiedHandler,
    fakeevent: FileSystemEvent,
) -> None:
    timestamp: float = 1
    handler.on_modified(fakeevent, at_time=timestamp)
    handler.event.clear()
    handler.on_modified(fakeevent, at_time=timestamp + 0.001)
    assert not handler.event.is_set()


def test_handler_on_modified_ignore_other_path(
    handler: ThreadingEventOnModifiedHandler,
    path: pathlib.Path,
) -> None:
    otherevent = FileSystemEvent(src_path=str(path.parent / "other"), is_synthetic=True)
    handler.on_modified(otherevent)
    assert not handler.event.is_set()


def test_constructor(path: pathlib.Path) -> None:
    _ = FileWatcher(path)


def test_constructor_with_observer(
    path: pathlib.Path, mocker: MockerFixture, monkeypatch: MonkeyPatch
) -> None:
    observer = Observer()
    schedule = mocker.patch.object(observer, "schedule", autospec=True)
    _ = FileWatcher(path, observer=observer)
    schedule.assert_called_once()
    assert isinstance(schedule.call_args.args[0], ThreadingEventOnModifiedHandler)
    assert schedule.call_args.args[1] == str(path.parent)


@pytest.fixture
def watcher_with_mocked_handler(
    path: pathlib.Path, mocker: MockerFixture
) -> FileWatcher:
    fw = FileWatcher(path, event_handler_cls=lambda *_: mocker.stub("event_handler"))
    return fw


def test_registering_callback(
    watcher_with_mocked_handler: FileWatcher, mocker: MockerFixture
) -> None:
    cb = mocker.stub("callback")
    watcher_with_mocked_handler.register_callback(cb)
    assert cb in watcher_with_mocked_handler.callbacks


@pytest.mark.parametrize("fire", [True, False])
def test_call(
    watcher_with_mocked_handler: FileWatcher,
    fire: bool,
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    event_set = mocker.patch("threading.Event.set")
    monkeypatch.setattr(watcher_with_mocked_handler._event, "set", event_set)
    monkeypatch.setattr(watcher_with_mocked_handler, "_fire_once_asap", fire)
    watcher_with_mocked_handler()
    assert event_set.called == fire


@pytest.mark.asyncio
async def test_context_manager_without_call(
    watcher_with_mocked_handler: FileWatcher,
    mocker: MockerFixture,
) -> None:
    observer = mocker.patch.object(
        watcher_with_mocked_handler, "_observer", autospec=True
    )

    async with watcher_with_mocked_handler:
        observer.start.assert_called_once_with()

    observer.stop.assert_called_once_with()
    observer.join.assert_called_once_with()


@pytest.mark.asyncio
async def test_context_manager_with_call(
    watcher_with_mocked_handler: FileWatcher,
    mocker: MockerFixture,
) -> None:
    observer = mocker.patch.object(
        watcher_with_mocked_handler, "_observer", autospec=True
    )

    async with watcher_with_mocked_handler():
        observer.start.assert_called_once_with()

    observer.stop.assert_called_once_with()
    observer.join.assert_called_once_with()


@pytest.mark.asyncio
async def test_on_modified_no_state_update(
    watcher_with_mocked_handler: FileWatcher,
    mocker: MockerFixture,
) -> None:
    callback = mocker.async_stub("callback")
    callback.return_value = None
    state = watcher_with_mocked_handler.state
    watcher_with_mocked_handler.register_callback(callback)
    await watcher_with_mocked_handler._invoke_callbacks()
    assert watcher_with_mocked_handler.state == state


@pytest.mark.asyncio
async def test_on_modified_state_update(
    watcher_with_mocked_handler: FileWatcher,
    mocker: MockerFixture,
) -> None:
    callback = mocker.async_stub("callback")
    callback.return_value = {"foo": "bar"}
    watcher_with_mocked_handler.register_callback(callback)
    await watcher_with_mocked_handler._invoke_callbacks()
    assert watcher_with_mocked_handler.state.get("foo") == "bar"


@pytest.mark.asyncio
async def test_reactor_task(watcher_with_mocked_handler: FileWatcher) -> None:
    task = asyncio.create_task(watcher_with_mocked_handler.reactor_task())

    sync = asyncio.Event()

    async def callback() -> StateType:
        task.cancel("pytest")
        sync.set()
        return MappingProxyType({})

    watcher_with_mocked_handler.register_callback(callback)
    watcher_with_mocked_handler._event.set()

    await sync.wait()
    assert task.cancelling()
