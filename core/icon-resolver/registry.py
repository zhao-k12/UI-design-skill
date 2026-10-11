"""Source-backed logical icons and deterministic semantic lookup; no platform models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def terms(value):
    return [part for part in re.split(r"[\s,;/]+", value.strip().casefold()) if part]


def build_index(data):
    index = {}
    for icon_id, entry in sorted(data["icons"].items()):
        if entry["status"] == "deprecated":
            continue
        sources = {"official": entry["officialTags"], "custom": entry["customTags"],
                   "name": (entry["name"].rsplit("-", 1)[0] if entry["style"] != "neutral" else entry["name"]).split("-")}
        for origin, tags in sources.items():
            for term in sorted({word for tag in tags for word in terms(tag)}):
                index.setdefault(term, []).append({"iconId": icon_id, "origin": origin})
    return {"indexVersion": "0.1.0", "registrySha256": digest(data), "terms": dict(sorted(index.items()))}


class IconError(ValueError):
    def __init__(self, code, icon_id, message):
        self.code, self.icon_id = code, icon_id
        super().__init__(message)


class IconRegistry:
    def __init__(self, data, *, allow_test_fixtures=False):
        schema = json.loads((Path(__file__).resolve().parents[2] / "schemas/icon-registry.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(data)
        if data["scope"] == "test-fixture" and not allow_test_fixtures:
            raise IconError("test_fixture_forbidden", "", "Test icon sources are not production resources")
        for icon_id, entry in data["icons"].items():
            if icon_id != "remix." + entry["name"]:
                raise IconError("invalid_icon_identity", icon_id, "Logical ID must match official name")
            suffix = entry["name"].rsplit("-", 1)[-1]
            if entry["style"] != (suffix if suffix in ("line", "fill") else "neutral"):
                raise IconError("invalid_icon_style", icon_id, "Style must match official suffix")
        self._data = deepcopy(data)
        self._index = build_index(data)

    @property
    def snapshot(self):
        return deepcopy(self._data)

    @property
    def fingerprint(self):
        return digest(self._data)

    @property
    def semantic_index(self):
        return deepcopy(self._index)

    def resolve(self, icon_id, *, historical=False):
        entry = self._data["icons"].get(icon_id)
        if entry is None:
            raise IconError("missing_icon", icon_id, "No registered official icon")
        if entry["status"] == "deprecated" and not historical:
            raise IconError("deprecated_icon", icon_id, "Deleted upstream; retained for historical references")
        return {"iconId": icon_id, "descriptor": deepcopy(entry), "registrySha256": self.fingerprint}

    def search(self, query, *, style="line"):
        if style not in ("line", "fill", "neutral"):
            raise ValueError("Style must be line, fill or neutral")
        words = terms(query)
        scores = {}
        matched = {}
        weights = {"custom": 1.0, "official": 0.85, "name": 0.75}
        for word in set(words):
            for hit in self._index["terms"].get(word, []):
                icon_id = hit["iconId"]
                if self._data["icons"][icon_id]["style"] != style:
                    continue
                scores.setdefault(icon_id, {})[word] = max(scores.get(icon_id, {}).get(word, 0), weights[hit["origin"]])
                matched.setdefault(icon_id, set()).add(hit["origin"])
        candidates = [{"iconId": icon_id, "confidence": round(sum(values.values()) / len(set(words)), 6),
                       "origins": sorted(matched[icon_id])} for icon_id, values in scores.items()]
        candidates.sort(key=lambda item: (-item["confidence"], item["iconId"]))
        reason = "missing_semantic_match" if not candidates else "low_confidence" if candidates[0]["confidence"] < 0.8 else None
        if reason is None and len(candidates) > 1 and candidates[0]["confidence"] == candidates[1]["confidence"]:
            reason = "ambiguous_semantic_match"
        return {"query": query, "status": "no_icon" if reason else "MATCH", "reason": reason,
                "iconId": None if reason else candidates[0]["iconId"],
                "confidence": candidates[0]["confidence"] if candidates else 0,
                "candidates": candidates[:10], "registrySha256": self.fingerprint}
