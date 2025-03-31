import asyncio

try:
    from asyncinotify import Inotify, Mask

    _INOTIFY = True
except TypeError:
    _INOTIFY = False


async def async_fswatcher(*, path, callback, logger=None, pollfreq=None):
    if _INOTIFY:
        if pollfreq is not None and logger:
            logger.info("Ignoring polling frequency and using inotify…")

        with Inotify() as inotify:
            inotify.add_watch(path, Mask.MODIFY | Mask.ATTRIB)
            if logger:
                logger.debug(f"Added watcher on {path}")
            await callback(path)
            async for event in inotify:
                if logger:
                    logger.debug(f"Event in {path}: {event}")
                await callback(path)

    else:
        if logger:
            logger.info(f"No inotify support, resorting to polling ({pollfreq}s)…")
        mtime_last = 0
        while True:
            if logger:
                logger.debug(f"Polling {path}…")
            if (mtime := path.stat().st_mtime) > mtime_last:
                if logger:
                    logger.debug(f"{path} has been modified.")
                mtime_last = mtime
                await callback(path)
            await asyncio.sleep(pollfreq)


def make_watcher_ctx(*, path, callback, pollfreq, name=None, logger=None):

    async def watcher_ctx(app):
        try:
            async with asyncio.TaskGroup() as tg:
                task = tg.create_task(
                    async_fswatcher(
                        path=path,
                        callback=callback,
                        logger=logger,
                        pollfreq=pollfreq
                    ),
                    name=name or f"Watcher[{path}]",
                )
                logger.debug(f"Created watcher task: {task}")

                yield

                app.logger.debug(f"Tearing down watcher task: {task}")
                task.cancel()

        except* FileNotFoundError:
            # override the silly Windows error message
            raise FileNotFoundError(f"Path does not exist: {path}")

        except* Exception:
            raise task.exception()

    return watcher_ctx
