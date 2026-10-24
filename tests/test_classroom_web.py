import threading
import time

from scaffolding.classroom import listen_host, main, outside_lock
from scaffolding.model_generator import deepseek_complete, model_limit
from tests.classroom_helpers import room
from tests.test_classroom_launch import _block


def test_a_cloud_url_is_what_students_open(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    monkeypatch.setenv("CLASSROOM_URL", "  https://class.example/room  ")
    seen = _block(monkeypatch)

    assert main([]) == 0
    assert seen["port"] == 8000
    assert capsys.readouterr().out == "https://class.example/room\n"
    assert listen_host() == "0.0.0.0"


def test_a_url_without_https_stays_on_this_computer(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    monkeypatch.setenv("CLASSROOM_URL", "http://class.example")
    seen = _block(monkeypatch)

    assert main([]) == 0
    assert seen["port"] == 8000
    assert capsys.readouterr().out == "http://127.0.0.1:8000\n"
    assert listen_host() == "127.0.0.1"


def test_model_limit_is_16_unless_a_whole_number_is_set(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_CONCURRENCY", raising=False)
    assert model_limit() == 16
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "  ")
    assert model_limit() == 16
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "0")
    assert model_limit() == 16
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "no")
    assert model_limit() == 16
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "8")
    assert model_limit() == 8


def test_a_model_call_lets_other_students_save(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "1")
    lock = threading.RLock()
    lock.acquire()
    saved = []

    def save_answer():
        acquired = lock.acquire(timeout=0.5)
        saved.append(acquired)
        if acquired:
            lock.release()

    def call_model():
        thread = threading.Thread(target=save_answer)
        thread.start()
        thread.join()

    outside_lock(lock, call_model)
    lock.release()
    assert saved == [True]


def test_one_model_slot_does_not_overlap(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_CONCURRENCY", "1")
    state = {"inside": 0, "max": 0}
    guard = threading.Lock()

    def post(url, headers, payload):
        with guard:
            state["inside"] += 1
            state["max"] = max(state["max"], state["inside"])
        time.sleep(0.05)
        with guard:
            state["inside"] -= 1
        return 200, {"choices": [{"message": {"content": "ok"}}]}

    threads = [
        threading.Thread(
            target=deepseek_complete,
            args=([{"role": "user", "content": "题"}],),
            kwargs={"post": post, "api_key": "k"},
        )
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert state["max"] == 1


def test_the_web_app_serves_the_classroom_home():
    from fastapi.testclient import TestClient

    from scaffolding.web import create_app

    client = TestClient(create_app(room()))
    response = client.get("/")
    assert response.status_code == 200
    assert "<h1>登录</h1>" in response.text
    assert 'name="role"' in response.text
