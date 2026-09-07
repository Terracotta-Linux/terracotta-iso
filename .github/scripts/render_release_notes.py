#!/usr/bin/env python3
"""Render release notes from the important-package update data produced by
package_versions.py. Only important-package changes are ever listed here -
ordinary dependency updates are intentionally omitted (see README / CLAUDE.md
for the important-vs-ordinary distinction).

Usage: render_release_notes.py '<json array of {name,label,old,new}>'
An empty array (or empty string) means "manual release, no update data" and
produces generic notes instead of an update list.
"""
import json
import os
import sys


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else "[]"
    updates = json.loads(raw) if raw.strip() else []
    iso_version = os.environ.get("ISO_VERSION", "")

    lines = [f"# Terracotta Linux {iso_version}", ""]

    if updates:
        lines.append("## Important updates")
        lines.append("")
        for u in updates:
            label = u.get("label", u["name"])
            lines.append(f"- **{label}** (`{u['name']}`): {u['old']} → {u['new']}")
        lines.append("")
        lines.append(
            "This release was triggered automatically because at least one "
            "important package (kernel, firmware, bootloader, Kiln, or "
            "another release-critical component) was updated upstream."
        )
    else:
        lines.append(
            "Manually triggered release. No important-package update data "
            "was supplied, so this build simply picks up whatever is "
            "currently latest for every dependency."
        )
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append("A `.sha256` checksum file is attached alongside the ISO. Verify with:")
    lines.append("")
    lines.append("```sh")
    lines.append("sha256sum -c terracotta-*.iso.sha256")
    lines.append("```")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
