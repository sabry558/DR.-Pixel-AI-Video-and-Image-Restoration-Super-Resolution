"""
Typed wrapper around the corruption classifier's raw output.

The classifier returns a list of dicts like:
    {"start_frame": 40, "end_frame": 45, "type": "low_light"}

Wrapping that in a small class (rather than passing raw dicts everywhere)
gives us:
    - one place to adapt if the classifier's dict keys ever change
    - validation (catches malformed entries early, with a clear error)
    - a clean `.indices()` helper instead of re-writing range() everywhere
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List


@dataclass(frozen=True)
class CorruptionRange:
    start_frame: int
    end_frame: int
    corruption_type: str

    def indices(self) -> range:
        """Inclusive range of frame indices covered by this corruption."""
        return range(self.start_frame, self.end_frame + 1)

    def __contains__(self, frame_idx: int) -> bool:
        return self.start_frame <= frame_idx <= self.end_frame

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CorruptionRange":
        """Build a CorruptionRange from the classifier's raw dict.

        If the classifier's key names ever change, this is the ONLY
        function that needs to be updated.
        """
        try:
            return cls(
                start_frame=int(d["start_frame"]),
                end_frame=int(d["end_frame"]),
                corruption_type=str(d.get("type", "unknown")),
            )
        except KeyError as e:
            raise ValueError(
                f"Malformed corruption range dict, missing key {e}: {d}"
            ) from e

    @staticmethod
    def from_dict_list(dicts: List[Dict[str, Any]]) -> List["CorruptionRange"]:
        return [CorruptionRange.from_dict(d) for d in dicts]


def flatten_to_index_set(ranges: List[CorruptionRange]) -> set:
    """All corrupted frame indices across every range, as a single set."""
    indices: set = set()
    for r in ranges:
        indices.update(r.indices())
    return indices


def iter_ranges_sorted(ranges: List[CorruptionRange]) -> Iterator[CorruptionRange]:
    return iter(sorted(ranges, key=lambda r: r.start_frame))
