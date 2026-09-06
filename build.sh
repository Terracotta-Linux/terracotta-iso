#!/usr/bin/env bash
# Builds the Terracotta Linux ISO with mkarchiso.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="${REPO_ROOT}/profile"
WORK_DIR="${REPO_ROOT}/work"
OUT_DIR="${REPO_ROOT}/out"
LOCAL_REPO_PATH="${REPO_ROOT}/local-repo/x86_64"

"${REPO_ROOT}/fetch-packages.sh"

# profile/pacman.conf carries a @@TERRACOTTA_REPO_PATH@@ placeholder instead
# of a hardcoded absolute path (which would bake in a username's home dir).
# Substitute it into a generated copy and hand that to mkarchiso via -C,
# so the profile directory on disk is never modified.
GENERATED_PACMAN_CONF="$(mktemp -t terracotta-pacman.conf.XXXXXX)"
trap 'rm -f "${GENERATED_PACMAN_CONF}"' EXIT
sed "s|@@TERRACOTTA_REPO_PATH@@|${LOCAL_REPO_PATH}|g" \
    "${PROFILE_DIR}/pacman.conf" >"${GENERATED_PACMAN_CONF}"

if [[ -d "${WORK_DIR}" ]]; then
    echo "==> Removing existing work dir: ${WORK_DIR}"
    # mkarchiso runs as root below, so a work dir left over from a previous
    # build is root-owned; a plain rm -rf as this user would fail on it.
    sudo rm -rf "${WORK_DIR}"
fi

echo "==> Running mkarchiso"
sudo mkarchiso -v -w "${WORK_DIR}" -o "${OUT_DIR}" -C "${GENERATED_PACMAN_CONF}" "${PROFILE_DIR}"

# mkarchiso creates out/ as root; hand it back to the invoking user so
# later steps (test-qemu.sh, git, manual cleanup) don't need sudo either.
sudo chown -R "$(id -u):$(id -g)" "${OUT_DIR}"

ISO_PATH="$(find "${OUT_DIR}" -maxdepth 1 -name '*.iso' -printf '%T@ %p\n' | sort -rn | head -n1 | cut -d' ' -f2-)"
if [[ -z "${ISO_PATH}" ]]; then
    echo "ERROR: mkarchiso finished but no .iso was found in ${OUT_DIR}" >&2
    exit 1
fi

echo "==> Build complete: ${ISO_PATH}"
