"""Lossless web-font packaging, preserving every original SFNT table."""
import hashlib
from pathlib import Path
from fontTools.ttLib import TTFont


def table_snapshot(path):
    with TTFont(path, lazy=True, recalcTimestamp=False) as font:
        result = {}
        for tag in font.reader.keys():
            data = font.reader[tag]
            # The SFNT container checksum changes when its directory changes.
            # No metric, glyph, name, timestamp or hinting field is excluded.
            if tag == "head":
                data = data[:8] + bytes(4) + data[12:]
            result[tag] = hashlib.sha256(data).hexdigest()
        return result


def prepare_woff(source, destination, expected_sha256):
    source, destination = Path(source), Path(destination)
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError("source_font_hash_mismatch")
    if destination.exists():
        raise ValueError("font_artifact_exists")
    with TTFont(source, lazy=True, recalcTimestamp=False) as font:
        if font.flavor is not None:
            raise ValueError("expected_original_sfnt_font")
        font.flavor = "woff"
        font.save(destination, reorderTables=False)
    original, packed = table_snapshot(source), table_snapshot(destination)
    if original != packed:
        raise ValueError("font_table_content_changed")
    return {"status": "PASS", "evidenceKind": "lossless-font-container-comparison",
            "sourceSha256": actual, "woffSha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "sourcePath": str(source), "woffPath": str(destination), "tableSha256": original,
            "tableCount": len(original), "normalizedFields": ["head.checkSumAdjustment"],
            "metricsGlyphsNamesAndHintingUnchanged": True, "nativeRenderingVerified": False,
            "admissionEligible": False}
