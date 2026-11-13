"""The share-extension strip keeps the app sources and drops only the appex."""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load_stripper():
    path = ROOT / "tooling/ios/strip-share-extension.py"
    spec = importlib.util.spec_from_file_location("strip_share_extension", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stripper = _load_stripper()


class StripShareExtensionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="strip-share-")
        self.root = Path(self.temporary.name)
        for relative in (
            "app/ios/Runner.xcodeproj/project.pbxproj",
            "app/ios/Runner/Runner.entitlements",
            "app/ios/ShareExtension/ShareExtension.entitlements",
            "app/ios/PhoneRunner/PhoneRunner.entitlements",
        ):
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def tearDown(self):
        self.temporary.cleanup()

    def test_strip_removes_extension_and_is_idempotent(self):
        project_path = self.root / "app/ios/Runner.xcodeproj/project.pbxproj"
        project = project_path.read_text(encoding="utf-8")
        phone_before = (self.root / "app/ios/PhoneRunner/PhoneRunner.entitlements").read_text(encoding="utf-8")
        if "com.apple.product-type.app-extension" not in project:
            self.assertEqual(stripper.strip(self.root), [])
            self.assertIn("D5480000000000000000B005 /* ShareInbox.swift in Sources */", project)
            self.assertIn("com.apple.security.application-groups", phone_before)
            return

        changed = stripper.strip(self.root)

        self.assertCountEqual(
            changed,
            [
                "app/ios/Runner.xcodeproj/project.pbxproj",
                "app/ios/Runner/Runner.entitlements",
                "app/ios/ShareExtension/ShareExtension.entitlements",
            ],
        )
        updated = (self.root / "app/ios/Runner.xcodeproj/project.pbxproj").read_text(encoding="utf-8")
        self.assertNotIn("com.apple.product-type.app-extension", updated)
        self.assertNotIn("Embed Foundation Extensions", updated)
        self.assertNotIn("D5480000000000000000B010", updated)
        self.assertIn("D5480000000000000000B005 /* ShareInbox.swift in Sources */", updated)
        self.assertIn("D5480000000000000000B006 /* ShareChannel.swift in Sources */", updated)
        self.assertIn("D5480000000000000000B103 /* ShareInbox.swift in Sources */", updated)
        self.assertEqual(updated.count("{"), updated.count("}"))
        for relative in (
            "app/ios/Runner/Runner.entitlements",
            "app/ios/ShareExtension/ShareExtension.entitlements",
        ):
            self.assertNotIn(
                "com.apple.security.application-groups",
                (self.root / relative).read_text(encoding="utf-8"),
            )
        self.assertEqual(
            phone_before,
            (self.root / "app/ios/PhoneRunner/PhoneRunner.entitlements").read_text(encoding="utf-8"),
        )
        self.assertEqual(stripper.strip(self.root), [])


if __name__ == "__main__":
    unittest.main()
