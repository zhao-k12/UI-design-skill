"""Fetch official Remix Icon, preserve byte-exact SVGs, publish immutable snapshots."""
import base64
from copy import deepcopy
import hashlib
from importlib import import_module
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from validators.ui_ir import ROOT, load_json

logical = import_module("core.icon-resolver.registry")
STORE = ROOT / "registries/icons"
CUSTOM = ROOT / "icon-manager/semantic-index/custom-tags.json"
REPOSITORY = "https://github.com/Remix-Design/RemixIcon"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_url(url, *, limit=32 * 1024 * 1024):
    request = urllib.request.Request(url, headers={"User-Agent": "ui-design-skill/0.1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        expected = urllib.parse.urlsplit(url)
        actual = urllib.parse.urlsplit(response.geturl())
        if actual.scheme != "https" or actual.netloc != expected.netloc:
            raise ValueError("Unexpected source redirect")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Source response exceeds size limit")
    return content


def metadata(version="latest"):
    if version != "latest" and not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Expected an explicit stable version")
    raw = read_url(f"https://registry.npmjs.org/remixicon/{version}", limit=2 * 1024 * 1024)
    data = json.loads(raw)
    if data.get("name") != "remixicon" or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", data.get("version", "")):
        raise ValueError("Unexpected official package identity")
    if version != "latest" and data["version"] != version:
        raise ValueError("Requested version does not match publication")
    repository = data.get("repository", {}).get("url", "").lower()
    if repository not in ("git+https://github.com/remix-design/remixicon.git", "https://github.com/remix-design/remixicon.git"):
        raise ValueError("Package repository is not official Remix Icon")
    if not re.fullmatch(r"[0-9a-f]{40}", data.get("gitHead", "")):
        raise ValueError("Official package must identify an exact source commit")
    return data, raw


def validate_svg(raw):
    if len(raw) > 1024 * 1024 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsupported SVG entities or excessive size")
    try:
        tree = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Invalid SVG XML") from exc
    if tree.tag != "{http://www.w3.org/2000/svg}svg" or tree.get("viewBox") != "0 0 24 24":
        raise ValueError("Expected official SVG namespace and 24x24 viewBox")
    allowed = {"svg", "path", "g", "rect", "circle", "ellipse", "line", "polyline", "polygon", "defs", "clipPath"}
    for node in tree.iter():
        if node.tag.split("}")[-1] not in allowed:
            raise ValueError("Unsupported SVG element")
        for key, value in node.attrib.items():
            if key.lower().startswith("on") or key.endswith("href") or "url(" in value.lower() or "javascript:" in value.lower():
                raise ValueError("Unsupported SVG external or executable content")


def unpack_publication(archive, published, tags_raw, metadata_raw):
    """No archive paths are extracted to disk. Only allowlisted regular files are read."""
    integrity = published["dist"]["integrity"]
    expected = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    if integrity != expected:
        raise ValueError("Official publication SRI mismatch")
    files = {}
    seen = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        for member in bundle:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("Unsafe package archive path")
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError("Package links are forbidden")
            total += member.size
            if total > 64 * 1024 * 1024 or member.size > 16 * 1024 * 1024:
                raise ValueError("Package unpacked size exceeds limit")
            name = path.as_posix()
            if name in seen:
                raise ValueError("Duplicate package archive member")
            seen.add(name)
            if name in ("package/package.json", "package/License") or re.fullmatch(r"package/icons/[^/]+/[a-z0-9-]+\.svg", name):
                files[name] = bundle.extractfile(member).read()
    package = json.loads(files["package/package.json"])
    if package["name"] != "remixicon" or package["version"] != published["version"]:
        raise ValueError("Archive identity does not match publication")
    tags = json.loads(tags_raw)
    if not isinstance(tags, dict):
        raise ValueError("Invalid official tags format")
    tag_map = {}
    for category, entries in tags.items():
        if category == "_comment":
            continue
        if not isinstance(entries, dict):
            raise ValueError("Invalid official tag category")
        for name, values in entries.items():
            if not isinstance(values, str):
                raise ValueError("Invalid official tag list")
            tag_map[(category, name)] = sorted(set(logical.terms(values)))
    icons, objects = {}, {}
    source_version = f"remixicon@{published['version']}+{published['gitHead']}"
    for path, raw in sorted(files.items()):
        if not path.endswith(".svg"):
            continue
        validate_svg(raw)
        source_path = path.removeprefix("package/")
        category, name = PurePosixPath(source_path).parts[1], PurePosixPath(source_path).stem
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError(f"Unsupported official icon name: {name}")
        icon_id = "remix." + name
        if icon_id in icons:
            raise ValueError("Duplicate official icon identity")
        svg_hash = sha(raw)
        objects[svg_hash] = raw
        suffix = name.rsplit("-", 1)[-1]
        style = suffix if suffix in ("line", "fill") else "neutral"
        base_name = name.rsplit("-", 1)[0] if style != "neutral" else name
        icons[icon_id] = {"name": name, "category": category, "style": style,
                          "status": "source-ready", "svgSha256": svg_hash, "sourcePath": source_path,
                          "sourceVersion": source_version, "officialTags": tag_map.get((category, base_name), []),
                          "customTags": [], "history": []}
    if not icons:
        raise ValueError("Official publication has no supported SVG icons")
    lock = {"lockVersion": "0.1.0", "repository": REPOSITORY, "packageVersion": published["version"],
            "gitCommit": published["gitHead"], "sourceVersion": source_version,
            "tarballUrl": published["dist"]["tarball"], "integrity": integrity,
            "tarballSha256": sha(archive), "npmMetadataSha256": sha(metadata_raw),
            "tagsUrl": f"https://raw.githubusercontent.com/Remix-Design/RemixIcon/{published['gitHead']}/tags.json",
            "officialTagsSha256": sha(tags_raw), "license": package.get("license"),
            "licenseSha256": sha(files["package/License"]),
            "iconCount": len(icons), "svgManifestSha256": logical.digest({k: v["svgSha256"] for k, v in icons.items()})}
    return {"lock": lock, "icons": icons, "objects": objects, "licenseBytes": files["package/License"],
            "archiveBytes": archive, "tagsBytes": tags_raw, "metadataBytes": metadata_raw}


def fetch(version):
    published, metadata_raw = metadata(version)
    expected_url = f"https://registry.npmjs.org/remixicon/-/remixicon-{published['version']}.tgz"
    if published["dist"]["tarball"] != expected_url:
        raise ValueError("Unexpected tarball source")
    archive = read_url(expected_url)
    tags_raw = read_url(f"https://raw.githubusercontent.com/Remix-Design/RemixIcon/{published['gitHead']}/tags.json", limit=2 * 1024 * 1024)
    return unpack_publication(archive, published, tags_raw, metadata_raw)


def build_snapshot(source, custom, previous=None, *, migration=False, scope="production"):
    if set(custom) != {"customTagsVersion", "description", "tags"} or custom["customTagsVersion"] != "0.1.0" or not isinstance(custom["tags"], dict):
        raise ValueError("Invalid custom semantic tags contract")
    if previous:
        logical.IconRegistry(previous, allow_test_fixtures=scope == "test-fixture")
        if previous["scope"] != scope:
            raise ValueError("Previous snapshot scope differs")
        if previous["sourceLockSha256"] != logical.digest(source["lock"]) and not migration:
            raise ValueError("Source version changes require explicit --migration")
    icons = deepcopy(source["icons"])
    for icon_id, tags in custom["tags"].items():
        if icon_id not in icons and (not previous or icon_id not in previous["icons"]):
            raise ValueError(f"Unknown icon in custom tags: {icon_id}")
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag.strip() for tag in tags) or len(set(tags)) != len(tags):
            raise ValueError("Custom tags must be unique nonempty strings")
    operations = {"create": [], "update": [], "deprecate": [], "unchanged": [], "reactivate": [], "reindex": []}
    old = previous["icons"] if previous else {}
    for icon_id, entry in icons.items():
        entry["customTags"] = sorted(custom["tags"].get(icon_id, []))
        if icon_id not in old:
            operations["create"].append(icon_id)
            continue
        prior = old[icon_id]
        entry["history"] = deepcopy(prior["history"])
        if prior["status"] == "deprecated":
            operations["reactivate"].append(icon_id)
        if prior["svgSha256"] != entry["svgSha256"]:
            revision = {"sourceVersion": prior["sourceVersion"], "svgSha256": prior["svgSha256"]}
            if revision not in entry["history"]:
                entry["history"].append(revision)
            operations["update"].append(icon_id)
        elif prior["status"] != "deprecated":
            operations["unchanged"].append(icon_id)
        if prior["customTags"] != entry["customTags"] or prior["officialTags"] != entry["officialTags"]:
            operations["reindex"].append(icon_id)
    for icon_id in sorted(set(old) - set(icons)):
        icons[icon_id] = deepcopy(old[icon_id])
        icons[icon_id]["status"] = "deprecated"
        if old[icon_id]["status"] != "deprecated":
            operations["deprecate"].append(icon_id)
    data = {"registryVersion": "0.1.0", "scope": scope, "sourceVersion": source["lock"]["sourceVersion"],
            "sourceLockSha256": logical.digest(source["lock"]), "customTagsSha256": logical.digest(custom),
            "icons": dict(sorted(icons.items()))}
    registry = logical.IconRegistry(data, allow_test_fixtures=scope == "test-fixture")
    diff = {"diffVersion": "0.1.0", "fromRegistrySha256": logical.digest(previous) if previous else None,
            "toRegistrySha256": registry.fingerprint, "migration": migration,
            "operations": {key: sorted(values) for key, values in operations.items()},
            "nativePlatformApplication": "NOT_RUN"}
    return data, registry.semantic_index, diff


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def current(store=STORE):
    pointer = store / "current.json"
    if not pointer.exists():
        return None
    selected = load_json(pointer)
    return read_snapshot(store, selected.get("snapshotSha256", ""))


def read_snapshot(store, snapshot_hash):
    if not re.fullmatch(r"[a-f0-9]{64}", snapshot_hash):
        raise ValueError("Invalid icon snapshot pointer")
    folder = store / "snapshots" / snapshot_hash
    manifest = load_json(folder / "manifest.json")
    if logical.digest(manifest) != snapshot_hash:
        raise ValueError("Icon snapshot manifest changed")
    if set(manifest["files"]) != {"registry.json", "source-lock.json", "custom-tags.json", "semantic-index.json", "License"}:
        raise ValueError("Incomplete icon snapshot manifest")
    for name, expected in manifest["files"].items():
        if name not in ("registry.json", "source-lock.json", "custom-tags.json", "semantic-index.json", "License"):
            raise ValueError("Unknown snapshot file")
        if sha((folder / name).read_bytes()) != expected:
            raise ValueError(f"Icon snapshot file changed: {name}")
    data = load_json(folder / "registry.json")
    registry = logical.IconRegistry(data)
    lock = load_json(folder / "source-lock.json")
    if registry.fingerprint != manifest["registrySha256"] or data["sourceLockSha256"] != logical.digest(lock):
        raise ValueError("Icon registry/source lock mismatch")
    if data["sourceVersion"] != lock["sourceVersion"] or data["customTagsSha256"] != logical.digest(load_json(folder / "custom-tags.json")):
        raise ValueError("Icon semantic/source versions mismatch")
    active = {key: entry["svgSha256"] for key, entry in data["icons"].items() if entry["status"] != "deprecated"}
    if len(active) != lock["iconCount"] or logical.digest(active) != lock["svgManifestSha256"] or sha((folder / "License").read_bytes()) != lock["licenseSha256"]:
        raise ValueError("Official SVG inventory or license does not match source lock")
    if registry.semantic_index != load_json(folder / "semantic-index.json"):
        raise ValueError("Semantic index does not match registry")
    for entry in data["icons"].values():
        for svg_hash in [entry["svgSha256"]] + [revision["svgSha256"] for revision in entry["history"]]:
            raw = (store / "objects" / (svg_hash + ".svg")).read_bytes()
            if sha(raw) != svg_hash:
                raise ValueError("Registered SVG changed")
            validate_svg(raw)
    return data


def publish(source, custom, data, index, *, store=STORE):
    if data["scope"] != "production":
        raise ValueError("Cannot publish test fixtures")
    registry = logical.IconRegistry(data)
    if data["sourceLockSha256"] != logical.digest(source["lock"]) or data["customTagsSha256"] != logical.digest(custom) or registry.semantic_index != index:
        raise ValueError("Snapshot inputs are inconsistent")
    for svg_hash, raw in source["objects"].items():
        if sha(raw) != svg_hash:
            raise ValueError("SVG content hash mismatch")
        target = store / "objects" / (svg_hash + ".svg")
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError("Immutable SVG collision or corruption")
        else:
            atomic_write(target, raw)
    contents = {"registry.json": json_bytes(data), "source-lock.json": json_bytes(source["lock"]),
                "custom-tags.json": json_bytes(custom), "semantic-index.json": json_bytes(index),
                "License": source["licenseBytes"]}
    manifest = {"manifestVersion": "0.1.0", "registrySha256": logical.digest(data),
                "files": {name: sha(raw) for name, raw in sorted(contents.items())}}
    snapshot_hash = logical.digest(manifest)
    folder = store / "snapshots" / snapshot_hash
    for name, raw in {**contents, "manifest.json": json_bytes(manifest)}.items():
        target = folder / name
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError("Immutable snapshot changed")
        else:
            atomic_write(target, raw)
    # Validate the entire prospective snapshot, including historical assets, before activation.
    read_snapshot(store, snapshot_hash)
    atomic_write(store / "current.json", json_bytes({"snapshotSha256": snapshot_hash}))
    return snapshot_hash
