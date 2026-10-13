import base64
from copy import deepcopy
import hashlib
import struct
import unittest

from adapters.default_font_profile_v02 import build_profile

PNG = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 100, 30) + bytes(9)


def fixture(platform="figma"):
    family = "NativeDefault" if platform == "figma" else "another-native-default"
    default = {"family": family, "fontId": "native"}
    variants, samples, review = [], [], {}
    for role, weight, size, style in (("body", 400, 14, "Regular"), ("heading", 600, 20, "Semi Bold")):
        binding = {"family": family, "style": style}
        variant = dict(binding, weight=weight, fontStyle=style.upper())
        if platform == "penpot":
            binding = dict(family=family, fontId="native", fontVariantId=str(weight), weight=weight, style="normal")
            variant = dict(binding)
        variants.append(variant)
        samples.append(dict(role=role, weight=weight, fontSize=size, text="用户 User", binding=binding,
                            width=100, height=30, nativePngBase64=base64.b64encode(PNG).decode()))
        review[role] = dict(pngSha256=hashlib.sha256(PNG).hexdigest(), status="PASS", detail="Sample checked")
    return dict(scope="platform-default-font-observation", version="0.2.0", platform=platform,
                fileReference="file", pageReference="page", status="PASS", issues=[],
                createdNodeIds=["temporary"], removedNodeIds=["temporary"], mutatedNodeIds=[],
                cleanupVerified=True, nativeAcceptance="NOT_RUN", releaseReady=False,
                defaultFont=default, variants=variants, samples=samples), review


class DefaultFontProfileTests(unittest.TestCase):
    def build(self, record, review):
        return build_profile(record, review, record["platform"], "file", "page")

    def test_platform_defaults_are_independent_and_input_is_not_mutated(self):
        for platform in ("figma", "penpot"):
            record, review = fixture(platform)
            before = deepcopy(record)
            result = self.build(record, review)
            self.assertEqual(result["defaultFont"]["family"], record["defaultFont"]["family"])
            self.assertTrue(result["fontBindingReady"])
            self.assertFalse(result["readyForPageGeneration"])
            self.assertFalse(result["releaseReady"])
            self.assertEqual(before, record)

    def test_foreign_file_and_page_rejected(self):
        for key in ("fileReference", "pageReference"):
            record, review = fixture()
            record[key] = "foreign"
            with self.assertRaisesRegex(ValueError, "identity"):
                self.build(record, review)

    def test_cleanup_or_existing_mutation_rejected(self):
        for key, value in (("cleanupVerified", False), ("removedNodeIds", []),
                           ("mutatedNodeIds", ["existing"]), ("createdNodeIds", ["a", "a"])):
            record, review = fixture()
            record[key] = value
            with self.assertRaisesRegex(ValueError, "cleanup"):
                self.build(record, review)

    def test_missing_weight_and_italic_rejected(self):
        for platform in ("figma", "penpot"):
            record, review = fixture(platform)
            record["variants"] = record["variants"][:1]
            with self.assertRaisesRegex(ValueError, "unobserved"):
                self.build(record, review)

    def test_tampered_png_review_rejected(self):
        record, review = fixture()
        review["body"]["pngSha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "review_not_bound"):
            self.build(record, review)

    def test_invalid_png_rejected(self):
        record, review = fixture()
        record["samples"][0]["nativePngBase64"] = base64.b64encode(b"not png").decode()
        with self.assertRaisesRegex(ValueError, "invalid_native_png"):
            self.build(record, review)

    def test_visual_omission_remains_review(self):
        record, review = fixture()
        review["body"].update(status="FAIL", detail="Missing final Chinese phrase")
        result = self.build(record, review)
        self.assertEqual(result["status"], "REVIEW")
        self.assertTrue(result["fontBindingReady"])
        self.assertEqual(result["textSampleReview"], "FAIL")

    def test_geometry_and_duplicate_roles_rejected(self):
        for field, value in (("width", float("nan")), ("height", 0), ("role", "heading")):
            record, review = fixture()
            record["samples"][0][field] = value
            with self.assertRaises(ValueError):
                self.build(record, review)


if __name__ == "__main__":
    unittest.main()
