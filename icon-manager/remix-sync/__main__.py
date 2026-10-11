import argparse
import json
from pathlib import Path
import tarfile

from jsonschema import ValidationError

from validators.ui_ir import ROOT, load_json
from .manager import CUSTOM, STORE, atomic_write, build_snapshot, current, fetch, json_bytes, logical, metadata, publish


def main():
    parser = argparse.ArgumentParser(description="Official Remix Icon version check, synchronization and semantic lookup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    sync = commands.add_parser("sync")
    sync.add_argument("--version", required=True)
    sync.add_argument("--migration", action="store_true")
    commands.add_parser("verify")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--style", choices=("line", "fill", "neutral"), default="line")
    args = parser.parse_args()
    output = ROOT / "artifacts/task-008"
    qa_path = output / "icon_qa_report.json"
    if args.command == "sync":
        atomic_write(qa_path, json_bytes({"scope": "official_icon_source_sync", "status": "RUNNING"}))
    try:
        previous = current()
        if args.command == "check":
            latest, _ = metadata()
            report = {"scope": "icon_version_check", "status": "PASS", "latestVersion": latest["version"],
                      "latestGitCommit": latest["gitHead"], "currentSourceVersion": previous["sourceVersion"] if previous else None,
                      "updateAvailable": previous is None or previous["sourceVersion"] != f"remixicon@{latest['version']}+{latest['gitHead']}",
                      "automaticUpgrade": False}
            atomic_write(output / "version_check_report.json", json_bytes(report))
        elif args.command == "sync":
            if args.version == "latest":
                raise ValueError("sync requires an explicit pinned version, never latest")
            source = fetch(args.version)
            custom = load_json(CUSTOM)
            data, index, diff = build_snapshot(source, custom, previous, migration=args.migration)
            for name, key in (("remixicon.tgz", "archiveBytes"), ("official-tags.json", "tagsBytes"), ("npm-metadata.json", "metadataBytes")):
                atomic_write(output / "source" / name, source[key])
            snapshot_hash = publish(source, custom, data, index)
            current()  # Offline re-validation of published bytes and all historical assets.
            atomic_write(output / "incremental_diff.json", json_bytes(diff))
            report = {"scope": "official_icon_source_sync", "status": "PASS", "sourceVersion": data["sourceVersion"],
                      "snapshotSha256": snapshot_hash, "registrySha256": logical.digest(data),
                      "iconCount": len(data["icons"]), "operations": {key: len(values) for key, values in diff["operations"].items()},
                      "nativePlatformApplication": "NOT_RUN", "issues": []}
            atomic_write(qa_path, json_bytes(report))
        elif previous is None:
            raise ValueError("missing_icon_registry: run pinned official synchronization first")
        elif args.command == "verify":
            report = {"scope": "icon_registry_evidence", "status": "PASS", "registrySha256": logical.digest(previous),
                      "iconCount": len(previous["icons"]), "nativePlatformApplication": "NOT_RUN", "issues": []}
            atomic_write(output / "icon_registry_qa_report.json", json_bytes(report))
        else:
            report = logical.IconRegistry(previous).search(args.query, style=args.style)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, ValidationError) as exc:
        report = {"scope": "official_icon_source_sync", "status": "FAIL", "issues": [{"code": "invalid_icon_source", "detail": str(exc)}]}
        if args.command in ("sync", "verify"):
            atomic_write(qa_path if args.command == "sync" else output / "icon_registry_qa_report.json", json_bytes(report))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
