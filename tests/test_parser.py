import asyncio

from app.handlers.parser import Parser


def test_scrape_sends_referer_header(monkeypatch) -> None:
    request = {}

    class Response:
        status_code = 200
        text = "<html></html>"

    class Client:
        def __init__(self, **kwargs) -> None:
            pass

        def get(self, url: str, headers: dict[str, str]) -> Response:
            request["url"] = url
            request["headers"] = headers
            return Response()

    monkeypatch.setattr("app.handlers.parser.primp.Client", Client)

    result = asyncio.run(Parser.scrape(query="30499-the-youthful-you-who-was-so-beautiful", t="page"))

    assert request["headers"] == {"Referer": "https://mydramalist.com/"}
    assert request["url"] == "https://mydramalist.com/30499-the-youthful-you-who-was-so-beautiful"
    assert result.status_code == 200


def test_scrape_retries_server_error(monkeypatch) -> None:
    calls = 0
    delays = []

    class Response:
        text = "<html></html>"

        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    class Client:
        def __init__(self, **kwargs) -> None:
            pass

        def get(self, url: str, headers: dict[str, str]) -> Response:
            nonlocal calls
            calls += 1
            return Response(503 if calls == 1 else 200)

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.handlers.parser.primp.Client", Client)
    monkeypatch.setattr("app.handlers.parser.asyncio.sleep", record_sleep)

    result = asyncio.run(Parser.scrape(query="735043-life", t="page"))

    assert calls == 2
    assert delays == [1]
    assert result.status_code == 200


def test_scrape_retries_forbidden_response(monkeypatch) -> None:
    calls = 0
    delays = []

    class Response:
        text = "Forbidden"

        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    class Client:
        def __init__(self, **kwargs) -> None:
            pass

        def get(self, url: str, headers: dict[str, str]) -> Response:
            nonlocal calls
            calls += 1
            return Response(403 if calls < 3 else 200)

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.handlers.parser.primp.Client", Client)
    monkeypatch.setattr("app.handlers.parser.asyncio.sleep", record_sleep)

    result = asyncio.run(Parser.scrape(query="735043-life", t="page"))

    assert calls == 3
    assert delays == [1, 2]
    assert result.status_code == 200
    assert result.ok is True


def test_scrape_stops_after_three_forbidden_retries(monkeypatch) -> None:
    calls = 0
    delays = []

    class Response:
        status_code = 403
        text = "Forbidden"

    class Client:
        def __init__(self, **kwargs) -> None:
            pass

        def get(self, url: str, headers: dict[str, str]) -> Response:
            nonlocal calls
            calls += 1
            return Response()

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("app.handlers.parser.primp.Client", Client)
    monkeypatch.setattr("app.handlers.parser.asyncio.sleep", record_sleep)

    result = asyncio.run(Parser.scrape(query="735043-life", t="page"))

    assert calls == 4
    assert delays == [1, 2, 4]
    assert result.status_code == 403
    assert result.ok is False
