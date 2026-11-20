# ABOUTME: Tests for the bind logic of the /bpe:review server in bpe/scripts/review-server.py.
# ABOUTME: Loads the script by path because its hyphenated filename cannot be imported by name.
"""Tests for the review server's bind_server function."""

import importlib.util
import socket
from pathlib import Path
from types import ModuleType

import pytest

REVIEW_SERVER_PATH = Path(__file__).resolve().parent.parent / "bpe" / "scripts" / "review-server.py"


@pytest.fixture(scope="module")
def review_server() -> ModuleType:
    """Load review-server.py as a module.

    Returns:
        The executed module object.

    Raises:
        ImportError: When the script cannot be located for loading.
    """
    spec = importlib.util.spec_from_file_location("review_server", REVIEW_SERVER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {REVIEW_SERVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBindServer:
    """bind_server picks a port and reports why it could not."""

    def test_unresolvable_address_fails_on_the_first_attempt(
        self,
        review_server: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An address that does not resolve is reported as such, not as a full port range."""
        attempted_ports: list[int] = []

        def refuse_to_resolve(server_address: tuple[str, int], handler_class: type) -> None:
            attempted_ports.append(server_address[1])
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

        monkeypatch.setattr(review_server, "HTTPServer", refuse_to_resolve)

        with pytest.raises(SystemExit) as exit_info:
            review_server.bind_server("no-such-host.invalid")

        captured = capsys.readouterr()
        assert exit_info.value.code == 1
        assert attempted_ports == [9000]
        assert "Cannot resolve the bind address 'no-such-host.invalid'" in captured.err
        assert "No free port" not in captured.err

    def test_port_in_use_counts_down_to_the_next_port(
        self,
        review_server: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A port that is taken moves the bind one port down."""

        def refuse_port_9000(server_address: tuple[str, int], handler_class: type) -> tuple[str, int]:
            if server_address[1] == 9000:
                raise OSError("Address already in use")
            return server_address

        monkeypatch.setattr(review_server, "HTTPServer", refuse_port_9000)

        assert review_server.bind_server("127.0.0.1") == ("127.0.0.1", 8999)
