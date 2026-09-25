import pytest
import httpx


@pytest.fixture(autouse=True)
def no_paid_network_in_tests(monkeypatch):
    def denied(*args,**kwargs):
        raise AssertionError('Real external HTTP is forbidden in regression tests; supply a fixture transport')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',denied)
