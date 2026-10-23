import threading

import scaffolding.classroom as classroom
from scaffolding.classroom import response_for
from tests.classroom_helpers import room


class _ContendedLock:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._guard = threading.Lock()
        self._owner = None
        self._depth = 0
        self.contended = threading.Event()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        ident = threading.get_ident()
        with self._guard:
            if self._depth > 0 and self._owner != ident:
                self.contended.set()
        if not self._lock.acquire(blocking, timeout):
            return False
        with self._guard:
            if self._owner == ident:
                self._depth += 1
            else:
                self._owner = ident
                self._depth = 1
        return True

    def release(self) -> None:
        with self._guard:
            self._depth -= 1
            if self._depth == 0:
                self._owner = None
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def test_two_response_for_calls_on_one_room_are_exclusive(monkeypatch):
    page = room()
    page._lock = _ContendedLock()
    entered = threading.Event()
    release = threading.Event()
    active = {"count": 0, "max": 0}
    gate = threading.Lock()
    original = classroom._dispatch_response

    def dispatch(current, method, path, body, now, headers="", uploads=None, filenames=None):
        with gate:
            active["count"] += 1
            active["max"] = max(active["max"], active["count"])
            pause = not entered.is_set()
        if pause:
            entered.set()
            assert release.wait(10)
        try:
            return original(current, method, path, body, now, headers, uploads, filenames)
        finally:
            with gate:
                active["count"] -= 1

    monkeypatch.setattr(classroom, "_dispatch_response", dispatch)

    def call() -> None:
        response_for(page, "GET", "/", "", 0)

    first = threading.Thread(target=call, daemon=True)
    second = threading.Thread(target=call, daemon=True)
    first.start()
    try:
        assert entered.wait(5)
        second.start()
        assert page._lock.contended.wait(5)
        assert second.is_alive()
        assert active["max"] == 1
    finally:
        release.set()
    first.join(5)
    second.join(5)
    assert not first.is_alive()
    assert not second.is_alive()
    assert active["max"] == 1
