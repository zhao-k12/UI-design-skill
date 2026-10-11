"""Offline semantic/diff tests and temporary persistence simulations, never native icons."""
import base64
from copy import deepcopy
import hashlib
from importlib import import_module
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from jsonschema import ValidationError

m = import_module("icon-manager.remix-sync.manager")
logical = m.logical
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0L1 1"/></svg>'
CHANGED = SVG.replace(b'L1 1', b'L2 2')


def fixture_source(names=("search-line", "add-line"), *, version="fixture-v1", changed=()):
    icons, objects = {}, {}
    for name in names:
        raw = CHANGED if name in changed else SVG
        svg_hash = m.sha(raw)
        suffix = name.rsplit("-", 1)[-1]
        icons["remix." + name] = {"name": name, "category": "System", "style": suffix if suffix in ("line", "fill") else "neutral",
                                 "status": "source-ready", "svgSha256": svg_hash, "sourcePath": "icons/System/" + name + ".svg",
                                 "sourceVersion": version, "officialTags": ["search"] if name.startswith("search-") else [],
                                 "customTags": [], "history": []}
        objects[svg_hash] = raw
    lock = {"sourceVersion": version, "iconCount": len(icons), "svgManifestSha256": logical.digest({k: v["svgSha256"] for k, v in icons.items()}),
            "licenseSha256": m.sha(b"test license")}
    return {"lock": lock, "icons": icons, "objects": objects, "licenseBytes": b"test license"}


def custom(tags=None):
    return {"customTagsVersion": "0.1.0", "description": "test-only labels", "tags": tags or {"remix.search-line": ["搜索"]}}


class IconTests(unittest.TestCase):
    def fixture(self, source=None, labels=None):
        return m.build_snapshot(source or fixture_source(), labels or custom(), scope="test-fixture")

    def test_fixture_scope_rejected_in_production(self):
        data, index, _ = self.fixture()
        with self.assertRaises(logical.IconError):
            logical.IconRegistry(data)
        with self.assertRaises(ValueError):
            m.publish(fixture_source(), custom(), data, index)

    def test_exact_custom_semantics_and_unknown_no_icon(self):
        data, _, _ = self.fixture()
        registry = logical.IconRegistry(data, allow_test_fixtures=True)
        self.assertEqual(registry.search("搜索")["iconId"], "remix.search-line")
        self.assertEqual(registry.search("never-mentioned")["status"], "no_icon")
        self.assertEqual(registry.search("")["status"], "no_icon")

    def test_ambiguity_and_partial_terms_do_not_guess(self):
        data, _, _ = self.fixture(fixture_source(("search-line", "search-2-line")))
        registry = logical.IconRegistry(data, allow_test_fixtures=True)
        self.assertEqual(registry.search("search")["reason"], "ambiguous_semantic_match")
        self.assertEqual(registry.search("搜索 未知条件")["reason"], "low_confidence")
        self.assertEqual(registry.search("搜索", style="fill")["status"], "no_icon")

    def test_snapshots_and_resolution_are_isolated(self):
        data, index, _ = self.fixture()
        registry = logical.IconRegistry(data, allow_test_fixtures=True)
        data["icons"].clear()
        result = registry.resolve("remix.search-line")
        result["descriptor"]["officialTags"].clear()
        index.clear()
        snapshot = registry.snapshot
        snapshot["icons"].clear()
        self.assertEqual(registry.search("search")["iconId"], "remix.search-line")
        with self.assertRaises(logical.IconError) as caught:
            registry.resolve("remix.unknown-line")
        self.assertEqual(caught.exception.code, "missing_icon")

    def test_identity_style_and_platform_fields_rejected(self):
        for change in ({"name": "bad-line"}, {"style": "fill"}, {"figmaNodeId": "test"}):
            data, _, _ = self.fixture()
            data["icons"]["remix.search-line"].update(change)
            with self.assertRaises((logical.IconError, ValidationError)):
                logical.IconRegistry(data, allow_test_fixtures=True)

    def test_neutral_official_names_are_not_assigned_invented_variants(self):
        data, _, _ = self.fixture(fixture_source(("a-b", "search-line")), custom({"remix.a-b": ["对比"]}))
        registry = logical.IconRegistry(data, allow_test_fixtures=True)
        self.assertEqual(registry.search("对比", style="neutral")["iconId"], "remix.a-b")
        self.assertEqual(registry.search("对比")["status"], "no_icon")

    def test_same_source_is_noop_and_deterministic(self):
        data, _, _ = self.fixture()
        result, index, diff = m.build_snapshot(fixture_source(), custom(), data, scope="test-fixture")
        self.assertEqual(result, data)
        self.assertEqual(index, logical.build_index(data))
        self.assertEqual(diff["operations"]["unchanged"], ["remix.add-line", "remix.search-line"])
        self.assertFalse(diff["operations"]["create"])
        self.assertEqual(self.fixture(), self.fixture())

    def test_source_changes_require_migration(self):
        data, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "migration"):
            m.build_snapshot(fixture_source(version="fixture-v2"), custom(), data, scope="test-fixture")

    def test_incremental_update_create_deprecate_preserves_history(self):
        old, _, _ = self.fixture()
        new, _, diff = m.build_snapshot(fixture_source(("search-line", "delete-bin-line"), version="fixture-v2", changed=("search-line",)),
                                        custom(), old, migration=True, scope="test-fixture")
        self.assertEqual(diff["operations"]["update"], ["remix.search-line"])
        self.assertEqual(diff["operations"]["create"], ["remix.delete-bin-line"])
        self.assertEqual(diff["operations"]["deprecate"], ["remix.add-line"])
        self.assertEqual(new["icons"]["remix.add-line"]["svgSha256"], old["icons"]["remix.add-line"]["svgSha256"])
        self.assertEqual(new["icons"]["remix.search-line"]["history"][0]["svgSha256"], old["icons"]["remix.search-line"]["svgSha256"])
        registry = logical.IconRegistry(new, allow_test_fixtures=True)
        with self.assertRaises(logical.IconError) as caught:
            registry.resolve("remix.add-line")
        self.assertEqual(caught.exception.code, "deprecated_icon")
        self.assertEqual(registry.resolve("remix.add-line", historical=True)["descriptor"]["status"], "deprecated")

    def test_deleted_icon_stays_deprecated_without_repeated_operation_and_can_return(self):
        old, _, _ = self.fixture()
        removed, _, _ = m.build_snapshot(fixture_source(("search-line",), version="fixture-v2"), custom(), old, migration=True, scope="test-fixture")
        repeated, _, diff = m.build_snapshot(fixture_source(("search-line",), version="fixture-v2"), custom(), removed, scope="test-fixture")
        self.assertFalse(diff["operations"]["deprecate"])
        returned, _, diff = m.build_snapshot(fixture_source(version="fixture-v3"), custom(), repeated, migration=True, scope="test-fixture")
        self.assertEqual(diff["operations"]["reactivate"], ["remix.add-line"])
        self.assertEqual(returned["icons"]["remix.add-line"]["status"], "source-ready")

    def test_label_change_only_reindexes_without_svg_update(self):
        old, _, _ = self.fixture()
        new, _, diff = m.build_snapshot(fixture_source(), custom({"remix.search-line": ["查询"]}), old, scope="test-fixture")
        self.assertEqual(diff["operations"]["reindex"], ["remix.search-line"])
        self.assertFalse(diff["operations"]["update"])
        self.assertEqual(new["icons"]["remix.search-line"]["svgSha256"], old["icons"]["remix.search-line"]["svgSha256"])

    def test_unknown_and_malformed_custom_tags_fail(self):
        for labels in (custom({"remix.missing-line": ["未知"]}), custom({"remix.search-line": [""]}), custom({"remix.search-line": ["搜索", "搜索"]})):
            with self.assertRaises(ValueError):
                self.fixture(labels=labels)

    def test_svg_validation_forbids_scripts_entities_external_links(self):
        m.validate_svg(SVG)
        for raw in (b'<!DOCTYPE svg>' + SVG, SVG.replace(b'<path', b'<script'), SVG.replace(b'<path', b'<path onload="x()"'), SVG.replace(b'<path', b'<path href="https://x"')):
            with self.assertRaises(ValueError):
                m.validate_svg(raw)

    def test_temporary_publication_pointer_is_atomic_and_assets_are_preserved(self):
        # Production protocol simulation in a disposable store; never uses the project registry.
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            source = fixture_source()
            data, index, _ = m.build_snapshot(source, custom())
            first = m.publish(source, custom(), data, index, store=store)
            self.assertEqual(m.current(store), data)
            next_source = fixture_source(("search-line",), version="fixture-v2", changed=("search-line",))
            new, index, _ = m.build_snapshot(next_source, custom(), data, migration=True)
            second = m.publish(next_source, custom(), new, index, store=store)
            self.assertNotEqual(first, second)
            self.assertTrue((store / "snapshots" / first / "registry.json").exists())
            self.assertTrue((store / "objects" / (m.sha(SVG) + ".svg")).exists())
            pointer = (store / "current.json").read_bytes()
            next_source["objects"][m.sha(CHANGED)] = SVG
            with self.assertRaises(ValueError):
                m.publish(next_source, custom(), new, index, store=store)
            self.assertEqual((store / "current.json").read_bytes(), pointer)

    def test_offline_manifest_and_svg_tamper_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            source = fixture_source()
            data, index, _ = m.build_snapshot(source, custom())
            snapshot = m.publish(source, custom(), data, index, store=store)
            svg_path = store / "objects" / (m.sha(SVG) + ".svg")
            svg_path.write_bytes(CHANGED)
            with self.assertRaises(ValueError):
                m.current(store)
            svg_path.write_bytes(SVG)
            (store / "snapshots" / snapshot / "semantic-index.json").write_text("{}")
            with self.assertRaises(ValueError):
                m.current(store)

    def test_inconsistent_prospective_source_lock_never_switches_pointer(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            source = fixture_source()
            data, index, _ = m.build_snapshot(source, custom())
            m.publish(source, custom(), data, index, store=store)
            pointer = (store / "current.json").read_bytes()
            bad_source = fixture_source(version="fixture-v2")
            bad_source["lock"]["iconCount"] = 99
            bad_data, bad_index, _ = m.build_snapshot(bad_source, custom(), data, migration=True)
            with self.assertRaises(ValueError):
                m.publish(bad_source, custom(), bad_data, bad_index, store=store)
            self.assertEqual((store / "current.json").read_bytes(), pointer)

    def test_snapshot_pointer_cannot_escape_store(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            (store / "current.json").write_text('{"snapshotSha256":"../outside"}')
            with self.assertRaises(ValueError):
                m.current(store)

    def test_package_integrity_and_unsafe_archive_paths_rejected(self):
        published = {"dist": {"integrity": "sha512-invalid"}}
        with self.assertRaisesRegex(ValueError, "SRI"):
            m.unpack_publication(b"bad bytes", published, b"{}", b"{}")
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            member = tarfile.TarInfo("../outside.svg")
            member.size = len(SVG)
            archive.addfile(member, io.BytesIO(SVG))
        archive_bytes = buffer.getvalue()
        published["dist"]["integrity"] = "sha512-" + base64.b64encode(hashlib.sha512(archive_bytes).digest()).decode()
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            m.unpack_publication(archive_bytes, published, b"{}", b"{}")

    def test_official_checked_in_source_and_five_semantics(self):
        data = m.current()
        self.assertIsNotNone(data)
        registry = logical.IconRegistry(data)
        expected = {"搜索": "remix.search-line", "删除": "remix.delete-bin-line", "新增": "remix.add-line",
                    "导出": "remix.download-line", "设置": "remix.settings-3-line"}
        for query, icon_id in expected.items():
            self.assertEqual(registry.search(query)["iconId"], icon_id)
        self.assertEqual(registry.search("无法确定的业务含义")["status"], "no_icon")
        self.assertTrue(any(entry["officialTags"] for entry in data["icons"].values()))
        self.assertEqual(registry.resolve("remix.download-line")["descriptor"]["status"], "source-ready")
