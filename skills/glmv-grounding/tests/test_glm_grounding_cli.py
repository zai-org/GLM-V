import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock


def _load_cli(monkeypatch):
    scripts_dir = Path(__file__).parents[1] / "scripts"
    for name, attributes in {
        "utils_boxes": ("parse_coordinates_from_response", "visualize_boxes"),
        "utils_detection": ("parse_detection_from_response",),
        "utils_video": ("parse_mot_from_response", "visualize_mot"),
    }.items():
        module = ModuleType(name)
        for attribute in attributes:
            setattr(module, attribute, Mock())
        monkeypatch.setitem(sys.modules, name, module)

    monkeypatch.setattr(sys, "platform", "linux")
    spec = importlib.util.spec_from_file_location(
        "glm_grounding_cli", scripts_dir / "glm_grounding_cli.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_media_bytes_rejects_requests_parser_bypass(monkeypatch):
    cli = _load_cli(monkeypatch)
    get = Mock()
    monkeypatch.setattr(cli.requests, "get", get)

    content, error = cli.load_media_bytes(r"http://127.0.0.1:6666\@1.1.1.1")

    assert content is None
    assert error.startswith("Rejected URL for security reasons:")
    get.assert_not_called()


def test_load_media_bytes_validates_and_fetches_the_same_prepared_url(monkeypatch):
    cli = _load_cli(monkeypatch)
    response = Mock(content=b"image-bytes")
    get = Mock(return_value=response)
    monkeypatch.setattr(cli.requests, "get", get)
    monkeypatch.setattr(
        cli.socket,
        "getaddrinfo",
        Mock(
            return_value=[
                (
                    cli.socket.AF_INET,
                    cli.socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", 0),
                )
            ]
        ),
    )

    content, error = cli.load_media_bytes("https://example.com/image name.png")

    assert content == b"image-bytes"
    assert error == ""
    get.assert_called_once_with("https://example.com/image%20name.png", timeout=10)
    response.raise_for_status.assert_called_once_with()
