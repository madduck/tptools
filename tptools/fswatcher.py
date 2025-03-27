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
            await callback()
            async for event in inotify:
                if logger:
                    logger.debug(f"Event in {path}: {event}")
                await callback()

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
                await callback()
            await asyncio.sleep(pollfreq)
