"""Parse explicit host, model, and CAD runtime profiles.

Profiles are configuration for the application host. They intentionally live in
``local_app/profiles`` rather than in the CAD workflow implementation.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_PROFILES_DIR = Path(__file__).resolve().parents[1] / "local_app" / "profiles"

_PROFILE_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REQUIRED_FIELDS = frozenset(
    {
        "profile",
        "agent",
        "model_provider",
        "model_endpoint",
        "model",
        "inference_backend",
        "cad_backend",
        "cad_endpoint",
        "tool_profile",
        "export_directory",
    }
)
_MODEL_PROVIDERS = frozenset({"claude", "lemonade"})
_INFERENCE_BACKENDS = frozenset({"cloud", "cuda", "vulkan", "rocm"})
_CAD_BACKENDS = frozenset({"fusion", "freecad", "mock"})
_TOOL_PROFILES = frozenset({"full", "guided"})


class RuntimeProfileError(ValueError):
    """Raised when a runtime profile cannot be found, decoded, or validated."""


@dataclass(frozen=True)
class RuntimeProfile:
    """Validated configuration for one ParamAItric runtime stack."""

    profile: str
    agent: str
    model_provider: str
    model_endpoint: str | None
    model: str | None
    inference_backend: str
    cad_backend: str
    cad_endpoint: str
    tool_profile: str
    export_directory: Path

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of the profile."""

        result = asdict(self)
        result["export_directory"] = str(self.export_directory)
        return result


def list_runtime_profiles(profiles_dir: str | Path | None = None) -> tuple[str, ...]:
    """Return the available profile names in deterministic order."""

    directory = _profiles_directory(profiles_dir)
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.stem for path in directory.glob("*.json") if path.is_file()))


def load_runtime_profile(
    name: str,
    profiles_dir: str | Path | None = None,
) -> RuntimeProfile:
    """Load and validate a named JSON runtime profile.

    ``name`` is deliberately restricted to a profile identifier, not a path. A
    caller may inject ``profiles_dir`` when loading profiles from another root.
    """

    if not isinstance(name, str) or not _PROFILE_NAME_PATTERN.fullmatch(name):
        raise RuntimeProfileError(
            "profile name must use lowercase letters, numbers, and single hyphens."
        )

    directory = _profiles_directory(profiles_dir)
    path = directory / f"{name}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        available = list_runtime_profiles(directory)
        suffix = f" Available profiles: {', '.join(available)}." if available else ""
        raise RuntimeProfileError(f"runtime profile '{name}' was not found.{suffix}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeProfileError(
            f"runtime profile '{name}' contains invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}."
        ) from exc
    except OSError as exc:
        raise RuntimeProfileError(f"runtime profile '{name}' could not be read: {exc}.") from exc

    return _parse_runtime_profile(raw, expected_name=name)


def _profiles_directory(profiles_dir: str | Path | None) -> Path:
    if profiles_dir is None:
        return DEFAULT_PROFILES_DIR
    return Path(profiles_dir).expanduser()


def _parse_runtime_profile(raw: object, *, expected_name: str) -> RuntimeProfile:
    if not isinstance(raw, dict):
        raise RuntimeProfileError(f"runtime profile '{expected_name}' must be a JSON object.")

    keys = set(raw)
    missing = sorted(_REQUIRED_FIELDS - keys)
    unknown = sorted(keys - _REQUIRED_FIELDS)
    if missing:
        raise RuntimeProfileError(
            f"runtime profile '{expected_name}' is missing required fields: {', '.join(missing)}."
        )
    if unknown:
        raise RuntimeProfileError(
            f"runtime profile '{expected_name}' has unknown fields: {', '.join(unknown)}."
        )

    profile = _required_string(raw, "profile", expected_name)
    if profile != expected_name:
        raise RuntimeProfileError(
            f"runtime profile name '{profile}' must match filename '{expected_name}.json'."
        )

    model_provider = _choice(raw, "model_provider", _MODEL_PROVIDERS, expected_name)
    model_endpoint = _optional_string(raw, "model_endpoint", expected_name)
    model = _optional_string(raw, "model", expected_name)
    inference_backend = _choice(
        raw, "inference_backend", _INFERENCE_BACKENDS, expected_name
    )

    if model_provider == "lemonade":
        if model_endpoint is None:
            raise RuntimeProfileError(
                f"runtime profile '{expected_name}' requires model_endpoint for Lemonade."
            )
        if model is None:
            raise RuntimeProfileError(
                f"runtime profile '{expected_name}' requires model for Lemonade."
            )
        if inference_backend == "cloud":
            raise RuntimeProfileError(
                f"runtime profile '{expected_name}' cannot use cloud inference with Lemonade."
            )
    elif inference_backend != "cloud":
        raise RuntimeProfileError(
            f"runtime profile '{expected_name}' must use cloud inference with Claude."
        )

    if model_endpoint is not None:
        _validate_http_endpoint(model_endpoint, "model_endpoint", expected_name)
    cad_endpoint = _required_string(raw, "cad_endpoint", expected_name)
    _validate_http_endpoint(cad_endpoint, "cad_endpoint", expected_name)

    export_directory = Path(
        _required_string(raw, "export_directory", expected_name)
    ).expanduser()

    return RuntimeProfile(
        profile=profile,
        agent=_required_string(raw, "agent", expected_name),
        model_provider=model_provider,
        model_endpoint=model_endpoint,
        model=model,
        inference_backend=inference_backend,
        cad_backend=_choice(raw, "cad_backend", _CAD_BACKENDS, expected_name),
        cad_endpoint=cad_endpoint,
        tool_profile=_choice(raw, "tool_profile", _TOOL_PROFILES, expected_name),
        export_directory=export_directory,
    )


def _required_string(raw: dict[str, object], field: str, profile: str) -> str:
    value = raw[field]
    if not isinstance(value, str) or not value.strip():
        raise RuntimeProfileError(
            f"runtime profile '{profile}' field '{field}' must be a non-empty string."
        )
    return value.strip()


def _optional_string(raw: dict[str, object], field: str, profile: str) -> str | None:
    value = raw[field]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RuntimeProfileError(
            f"runtime profile '{profile}' field '{field}' must be null or a non-empty string."
        )
    return value.strip()


def _choice(
    raw: dict[str, object],
    field: str,
    choices: frozenset[str],
    profile: str,
) -> str:
    value = _required_string(raw, field, profile)
    if value not in choices:
        raise RuntimeProfileError(
            f"runtime profile '{profile}' field '{field}' must be one of: "
            f"{', '.join(sorted(choices))}."
        )
    return value


def _validate_http_endpoint(value: str, field: str, profile: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeProfileError(
            f"runtime profile '{profile}' field '{field}' must be an HTTP or HTTPS URL."
        )
