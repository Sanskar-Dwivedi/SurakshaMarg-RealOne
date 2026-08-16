"""
Append-only, hash-chained event ledger.

Any deterrent that acts on animals in public space will eventually be asked a
regulatory question: what did this device do, to which animal, at what level,
and on whose authority? A mutable CSV cannot answer that credibly, because
nothing stops an operator rewriting a bad night.

Each record embeds the SHA-256 of its predecessor, so altering or deleting any
historical entry invalidates every entry after it. `verify()` recomputes the
whole chain. This is not a blockchain and makes no distributed claim - it is a
single-writer tamper-EVIDENT log, which is the honest scope.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterator

GENESIS = "0" * 64


@dataclass
class Record:
    seq: int
    ts_unix: float
    ts_iso: str
    kind: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str = ""

    def digest(self) -> str:
        body = {
            "seq": self.seq,
            "ts_unix": round(self.ts_unix, 6),
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }
        blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict:
        return asdict(self)


class Ledger:
    """
    Single-writer append-only log backed by JSON Lines.

    Kinds in use:
        session_open / session_close
        detection      - an animal entered the monitored zone
        authorisation  - governor granted or denied, with every reason
        emission       - what was actually radiated, with the spectral report
        observation    - what the animal did afterwards
        escalation     - handoff to human dispatch
        stop           - a stop criterion fired
    """

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path) if path else None
        self.records: list[Record] = []
        if self.path and self.path.exists():
            self._load()

    # -- writing -----------------------------------------------------------

    def append(self, kind: str, payload: dict[str, Any]) -> Record:
        prev = self.records[-1].hash if self.records else GENESIS
        now = time.time()
        r = Record(
            seq=len(self.records),
            ts_unix=now,
            ts_iso=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + "Z",
            kind=kind,
            payload=payload,
            prev_hash=prev,
        )
        r.hash = r.digest()
        self.records.append(r)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(r.as_dict(), default=str) + "\n")
        return r

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.records.append(Record(**json.loads(line)))

    # -- reading -----------------------------------------------------------

    def verify(self) -> dict:
        """Recompute the chain. Reports the first break, if any."""
        prev = GENESIS
        for r in self.records:
            if r.prev_hash != prev:
                return {
                    "valid": False,
                    "records": len(self.records),
                    "broken_at_seq": r.seq,
                    "reason": "prev_hash does not match the preceding record",
                }
            if r.digest() != r.hash:
                return {
                    "valid": False,
                    "records": len(self.records),
                    "broken_at_seq": r.seq,
                    "reason": "record contents do not match their stored hash",
                }
            prev = r.hash
        return {
            "valid": True,
            "records": len(self.records),
            "head": prev,
            "scope": (
                "Single-writer tamper-evident log. Detects post-hoc edits and "
                "deletions; does not by itself prove the writer was honest at "
                "write time. Pair with an external timestamping authority for "
                "that claim."
            ),
        }

    def of_kind(self, kind: str) -> list[Record]:
        return [r for r in self.records if r.kind == kind]

    def __iter__(self) -> Iterator[Record]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)

    def summary(self) -> dict:
        kinds: dict[str, int] = {}
        for r in self.records:
            kinds[r.kind] = kinds.get(r.kind, 0) + 1
        return {
            "records": len(self.records),
            "by_kind": kinds,
            "head_hash": self.records[-1].hash if self.records else GENESIS,
            "chain": self.verify(),
        }

    def export(self) -> list[dict]:
        return [r.as_dict() for r in self.records]
