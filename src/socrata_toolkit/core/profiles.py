from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


def _slug(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "default"
    # Keep it filesystem-friendly (windows + cross-platform).
    v = re.sub(r"[^A-Za-z0-9._-]+", "_", v)
    v = v.strip("._-")
    return v or "default"

@dataclass(frozen=True)
class ProfilePaths:
    name: str
    dir: Path
    analyst_profile: Path
    publish_profile: Path
    publish_presets_dir: Path
    state_dir: Path

def profiles_root(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / "config" / "profiles"

def active_profile_name(default: str = "default") -> str:
    # Environment wins so Dash/EXE/scheduled task can share it.
    return _slug(os.getenv("TOOLKIT_PROFILE", "") or os.getenv("PROFILE_NAME", "") or default)

def profile_paths(name: str | None = None, *, root: Path | None = None, state_root: Path | None = None) -> ProfilePaths:
    root_path = root or Path.cwd()
    prof = _slug(name or active_profile_name())
    pdir = profiles_root(root_path) / prof
    env_state_root = os.getenv("TOOLKIT_STATE_ROOT", "").strip()
    resolved_state_root = state_root or (Path(env_state_root) if env_state_root else None)
    state_dir = (resolved_state_root or (root_path / "outputs" / ".state" / "profiles")) / prof
    return ProfilePaths(
        name=prof,
        dir=pdir,
        analyst_profile=pdir / "analyst_profile.yaml",
        publish_profile=pdir / "publish_profile.yaml",
        publish_presets_dir=pdir / "publish_presets",
        state_dir=state_dir,
    )

def ensure_profile_exists(name: str | None = None, *, root: Path | None = None) -> ProfilePaths:
    """Create profile folder structure if missing (does not overwrite YAMLs)."""
    paths = profile_paths(name, root=root)
    paths.dir.mkdir(parents=True, exist_ok=True)
    paths.publish_presets_dir.mkdir(parents=True, exist_ok=True)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    return paths

def list_profiles(*, root: Path | None = None) -> list[str]:
    pr = profiles_root(root)
    if not pr.exists():
        return []
    return sorted([p.name for p in pr.iterdir() if p.is_dir()])

