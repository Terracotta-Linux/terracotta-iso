#!/usr/bin/env python3
"""Resolve and diff important-package versions for Terracotta ISO releases.

The list of "important" packages (kernel, firmware, bootloader, Kiln, ...)
lives in .github/important-packages.json - that file is the single source of
truth, shared by the daily update-check workflow and the release workflow.
Everything else listed in profile/packages.x86_64 is treated as an ordinary
dependency and is only ever reported for visibility, never used to decide
whether to release.

Subcommands:
  diff      Compare current upstream versions of important packages against
            the versions recorded in the latest GitHub release's
            versions.json asset. Used by the daily checker (and, again, by
            the release workflow itself as a race-safe duplicate guard).
  snapshot  Print the current versions of all important packages as
            {"generated_at": ..., "iso_version": ..., "packages": {...}}.
            Used by the release workflow to produce the versions.json asset
            that ships with every release and becomes the next "shipped"
            baseline.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMPORTANT_PACKAGES_FILE = os.path.join(REPO_ROOT, ".github", "important-packages.json")
PACKAGES_X86_64_FILE = os.path.join(REPO_ROOT, "profile", "packages.x86_64")


def load_important_packages():
    with open(IMPORTANT_PACKAGES_FILE) as f:
        return json.load(f)["packages"]


def load_ordinary_package_names(important_names):
    names = []
    with open(PACKAGES_X86_64_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line not in important_names:
                names.append(line)
    return names


def archlinux_version(pkgname):
    url = f"https://archlinux.org/packages/search/json/?name={pkgname}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"warning: failed to query archlinux.org for {pkgname!r}: {exc}", file=sys.stderr)
        return None
    for result in data.get("results", []):
        if result.get("pkgname") == pkgname and result.get("arch") in ("x86_64", "any"):
            return f"{result['pkgver']}-{result['pkgrel']}"
    print(f"warning: {pkgname!r} not found via archlinux.org package search", file=sys.stderr)
    return None


def github_latest_release_tag(repo):
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases/latest", "--jq", ".tag_name"],
            check=True, capture_output=True, text=True,
        )
        return proc.stdout.strip() or None
    except subprocess.CalledProcessError as exc:
        print(f"warning: failed to query latest release for {repo}: {exc.stderr.strip()}", file=sys.stderr)
        return None


def current_version(pkg):
    if pkg["source"] == "archlinux":
        return archlinux_version(pkg["name"])
    if pkg["source"] == "github-release":
        return github_latest_release_tag(pkg["github_repo"])
    raise ValueError(f"unknown source for package {pkg['name']!r}: {pkg['source']!r}")


def current_versions_map(packages):
    return {pkg["name"]: current_version(pkg) for pkg in packages}


def shipped_versions():
    """Versions recorded in the latest release of *this* repo, or {} if none."""
    this_repo = os.environ.get("GITHUB_REPOSITORY")
    if not this_repo:
        return {}
    try:
        tag = subprocess.run(
            ["gh", "release", "view", "latest", "-R", this_repo, "--json", "tagName", "-q", ".tagName"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return {}
    if not tag:
        return {}
    try:
        content = subprocess.run(
            ["gh", "release", "download", tag, "-R", this_repo, "-p", "versions.json", "-O", "-"],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(f"warning: release {tag} has no usable versions.json asset: {exc.stderr.strip()}", file=sys.stderr)
        return {}
    try:
        return json.loads(content).get("packages", {})
    except json.JSONDecodeError:
        return {}


def cmd_diff(_args):
    important = load_important_packages()
    ordinary_names = load_ordinary_package_names({p["name"] for p in important})

    current = current_versions_map(important)
    shipped = shipped_versions()

    important_changes = []
    for pkg in important:
        name = pkg["name"]
        new = current.get(name)
        old = shipped.get(name)
        if new is not None and new != old:
            important_changes.append({
                "name": name,
                "label": pkg.get("label", name),
                "old": old or "(none)",
                "new": new,
            })

    ordinary_changes = []
    for name in ordinary_names:
        new = archlinux_version(name)
        old = shipped.get(name)
        if new is not None and new != old:
            ordinary_changes.append({"name": name, "old": old or "(none)", "new": new})

    result = {
        "has_important_update": len(important_changes) > 0,
        "important_changes": important_changes,
        "ordinary_changes": ordinary_changes,
    }
    print(json.dumps(result, indent=2))

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"has_important_update={'true' if result['has_important_update'] else 'false'}\n")
            f.write("important_updates_json<<EOF_IMPORTANT_UPDATES\n")
            f.write(json.dumps(important_changes))
            f.write("\nEOF_IMPORTANT_UPDATES\n")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## Package update check\n\n")
            f.write("### Important packages (trigger a release)\n\n")
            f.write("| Package | Old | New |\n|---|---|---|\n")
            for pkg in important:
                name = pkg["name"]
                new = current.get(name) or "(unknown)"
                old = shipped.get(name) or "(none)"
                f.write(f"| {name} | {old} | {new} |\n")
            f.write("\n### Ordinary dependencies (informational only)\n\n")
            if ordinary_changes:
                f.write("| Package | Old | New |\n|---|---|---|\n")
                for c in ordinary_changes:
                    f.write(f"| {c['name']} | {c['old']} | {c['new']} |\n")
            else:
                f.write("_(no ordinary package updates detected)_\n")

    return 0


def cmd_snapshot(_args):
    important = load_important_packages()
    current = current_versions_map(important)
    output = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iso_version": os.environ.get("ISO_VERSION", ""),
        "packages": current,
    }
    print(json.dumps(output, indent=2))
    return 0


COMMANDS = {"diff": cmd_diff, "snapshot": cmd_snapshot}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: {sys.argv[0]} {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        return 2
    return COMMANDS[sys.argv[1]](sys.argv[2:]) or 0


if __name__ == "__main__":
    sys.exit(main())
