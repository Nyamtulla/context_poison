"""Load and validate config.yaml (SRS NFR-3 — config-driven, nothing hardcoded)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    raw: dict[str, Any]
    repo_root: Path = REPO_ROOT

    @property
    def start_year(self) -> int:
        return self.raw["search"]["start_year"]

    @property
    def end_year(self) -> int | None:
        return self.raw["search"].get("end_year")

    @property
    def hop_depth(self) -> int:
        return self.raw["hop_depth"]

    @property
    def tracks(self) -> dict[str, Any]:
        return self.raw["tracks"]

    @property
    def venue_soft_list(self) -> list[str]:
        return self.raw["venues"]["soft_list"]

    @property
    def screening(self) -> dict[str, Any]:
        return self.raw["screening"]

    @property
    def track_signatures(self) -> dict[str, list[str]]:
        return self.raw["track_signatures"]

    @property
    def apis(self) -> dict[str, Any]:
        return self.raw["apis"]

    def path(self, key: str) -> Path:
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else self.repo_root / p

    def s2_api_key(self) -> str | None:
        env_var = self.apis["semantic_scholar"]["api_key_env"]
        return os.environ.get(env_var) or None

    def openalex_contact_email(self) -> str | None:
        env_var = self.apis["openalex"]["contact_email_env"]
        return os.environ.get(env_var) or None

    def flat_clusters(self, track: str) -> list[dict[str, Any]]:
        """Each cluster -> {'variants': [...], 'query_label': str}."""
        clusters = self.tracks[track]["keyword_clusters"]
        out = []
        for cluster in clusters:
            variants = cluster if isinstance(cluster, list) else [cluster]
            out.append({"variants": variants, "query_label": " | ".join(variants)})
        return out


def load_config(config_path: str | Path | None = None) -> Config:
    load_dotenv(REPO_ROOT / ".env")
    path = Path(config_path) if config_path else REPO_ROOT / "config.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Config(raw=raw)
