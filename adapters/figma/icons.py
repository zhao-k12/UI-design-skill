import hashlib
import json
from pathlib import Path


def source_import_script(registry, object_dir, icon_ids, *, file_reference, page_reference):
    if registry.snapshot["scope"] != "production":
        raise ValueError("Test icons cannot be imported into a production file")
    if len(icon_ids) != len(set(icon_ids)):
        raise ValueError("Duplicate icon inventory")
    inventory = []
    for icon_id in icon_ids:
        entry = registry.resolve(icon_id)["descriptor"]
        raw = (Path(object_dir) / (entry["svgSha256"] + ".svg")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["svgSha256"]:
            raise ValueError("Official SVG changed before native import")
        inventory.append({"iconId": icon_id, "svgSha256": entry["svgSha256"], "svg": raw.decode("utf-8")})
    payload = {"fileReference": file_reference, "pageReference": page_reference, "registrySha256": registry.fingerprint,
               "sourceVersion": registry.snapshot["sourceVersion"], "icons": inventory}
    runtime = (Path(__file__).parent / "icon_library.js").read_text(encoding="utf-8")
    return "const payload = " + json.dumps(payload, ensure_ascii=False) + ";\n" + runtime + "\nreturn await importOfficialIcons(figma,payload);\n"
