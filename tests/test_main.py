from selenia import LocalRanker, Selenia


class RecordingClient:
    def __init__(self):
        self.calls = []

    def locate(self, driver, description):
        self.calls.append(("locate", driver, description))
        return "one"

    def locate_all(self, driver, description):
        self.calls.append(("locate_all", driver, description))
        return ["one", "two"]


def test_find_asks_the_client_for_one_element():
    client, driver = RecordingClient(), object()
    assert Selenia(driver, client).find("the login button") == "one"
    assert client.calls == [("locate", driver, "the login button")]


def test_find_all_asks_the_client_for_every_match():
    client, driver = RecordingClient(), object()
    assert Selenia(driver, client).find_all("add to cart") == ["one", "two"]
    assert client.calls == [("locate_all", driver, "add to cart")]


def test_default_client_is_the_local_ranker(monkeypatch):
    from selenia import local_ranker
    monkeypatch.setattr(local_ranker, "Scorer", lambda model_dir: "scorer")
    monkeypatch.setenv("SELENIA_MODEL_DIR", "somewhere")
    selenia = Selenia(object())
    assert isinstance(selenia.model_client, LocalRanker)
    assert selenia.model_client.scorer == "scorer"


def test_package_exports():
    import selenia
    assert set(selenia.__all__) == {"Selenia", "LocalRanker"}
