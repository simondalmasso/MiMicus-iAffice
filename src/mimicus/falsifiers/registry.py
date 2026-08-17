from __future__ import annotations

from mimicus.falsifiers.spec import FalsifierSpec


class FalsifierRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, FalsifierSpec] = {}

    def add(self, spec: FalsifierSpec) -> str:
        digest = spec.hash
        if digest in self._specs and self._specs[digest] != spec:
            raise ValueError("immutable falsifier hash collision")
        self._specs[digest] = spec
        return digest

    def get(self, digest: str) -> FalsifierSpec:
        spec = self._specs[digest]
        if spec.hash != digest:
            raise ValueError("stored falsifier spec hash mismatch")
        return spec

    def values(self) -> list[FalsifierSpec]:
        return list(self._specs.values())
