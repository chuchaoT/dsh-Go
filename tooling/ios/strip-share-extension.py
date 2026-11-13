#!/usr/bin/env python3
"""Drop the iOS share extension so a free Apple ID can sideload the unsigned IPA.

The default project keeps the extension. Run this on a fork, commit the result,
and let the existing iOS compile workflow rebuild ios-unsigned-ipa.

Removes the ShareExtension target, the embed phase, and that target's
dependency. ShareInbox.swift stays in the app and in RunnerTests. Clears the
App Group from Runner.entitlements and ShareExtension.entitlements only.
PhoneRunner.entitlements is a UI-test target and is not in the IPA.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Objects that exist only to build or embed ShareExtension.appex.
# ShareInbox.swift (B004) and ShareViewController.swift (B002) stay: RunnerTests
# still compiles them, and the app still compiles ShareInbox.swift (B005).
DROP_IDS = (
    "D5480000000000000000B001",  # extension Sources build file
    "D5480000000000000000B003",  # extension Sources build file
    "D5480000000000000000B008",  # embed appex
    "D5480000000000000000B009",  # product reference
    "D5480000000000000000B00A",  # target proxy
    "D5480000000000000000B00B",  # Embed Foundation Extensions
    "D5480000000000000000B00F",  # extension Frameworks phase
    "D5480000000000000000B010",  # ShareExtension target
    "D5480000000000000000B012",  # extension configuration list
    "D5480000000000000000B013",  # extension Sources phase
    "D5480000000000000000B014",  # extension Resources phase
    "D5480000000000000000B015",  # Runner -> ShareExtension dependency
    "D5480000000000000000B016",  # extension Debug
    "D5480000000000000000B017",  # extension Release
    "D5480000000000000000B018",  # extension Profile
)

APP_GROUP_BLOCK = re.compile(
    r"\t<key>com\.apple\.security\.application-groups</key>\s*"
    r"<array>.*?</array>\s*",
    re.DOTALL,
)

ENTITLEMENTS = (
    Path("app/ios/Runner/Runner.entitlements"),
    Path("app/ios/ShareExtension/ShareExtension.entitlements"),
)


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[2]


def _object_span(text: str, object_id: str) -> tuple[int, int] | None:
    token = f"\n\t\t{object_id} "
    start = text.find(token)
    if start < 0:
        return None
    start += 1
    brace = text.find("{", start)
    line_end = text.find("\n", start)
    if brace < 0 or (line_end != -1 and brace > line_end and "{" not in text[start:line_end]):
        if line_end < 0:
            raise SystemExit(f"{object_id} has no closing line")
        return start, line_end + 1
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = text.find("\n", index)
                if end < 0:
                    end = len(text) - 1
                return start, end + 1
    raise SystemExit(f"{object_id} has unbalanced braces")


def strip_pbxproj(text: str) -> str:
    if "com.apple.product-type.app-extension" not in text:
        return text
    for object_id in DROP_IDS:
        span = _object_span(text, object_id)
        if span is None:
            raise SystemExit(f"missing pbxproj object {object_id}")
        text = text[: span[0]] + text[span[1] :]
    for object_id in DROP_IDS:
        text = re.sub(
            rf"\n\t\t\t\t{object_id} /\*.*?\*/,",
            "",
            text,
        )
    leftover = [object_id for object_id in DROP_IDS if object_id in text]
    if leftover:
        raise SystemExit("still referenced after strip: " + ", ".join(leftover))
    if "com.apple.product-type.app-extension" in text:
        raise SystemExit("share extension product type is still in the project")
    if text.count("{") != text.count("}"):
        raise SystemExit("pbxproj braces no longer balance")
    return text


def strip_entitlements(text: str) -> str:
    return APP_GROUP_BLOCK.sub("", text)


def strip(root: Path) -> list[str]:
    """Return repo-relative paths whose contents changed."""
    changed: list[str] = []
    project = root / "app/ios/Runner.xcodeproj/project.pbxproj"
    original = project.read_text(encoding="utf-8")
    updated = strip_pbxproj(original)
    if updated != original:
        project.write_text(updated, encoding="utf-8", newline="\n")
        changed.append(project.relative_to(root).as_posix())
    for relative in ENTITLEMENTS:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        updated = strip_entitlements(original)
        if "com.apple.security.application-groups" in updated:
            raise SystemExit(f"App Group remains in {relative.as_posix()}")
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(relative.as_posix())
    phone = root / "app/ios/PhoneRunner/PhoneRunner.entitlements"
    if "com.apple.security.application-groups" not in phone.read_text(encoding="utf-8"):
        raise SystemExit("PhoneRunner.entitlements lost its App Group; this script must not edit it")
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=repo_root_from_here(),
        help="repository root (default: this script's repo)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    changed = strip(root)
    if changed:
        print("stripped:")
        for path in changed:
            print(f"  {path}")
    else:
        print("already stripped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
