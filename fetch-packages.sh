#!/usr/bin/env bash
# Downloads the latest prebuilt Terracotta Linux packages from GitHub
# releases and (re)builds the local pacman repo database consumed by
# profile/pacman.conf's [terracotta] repo.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_ROOT}/local-repo/x86_64"
REPO_DB_NAME="terracotta"

REPOS=(
    "Terracotta-Linux/kiln"
    "Terracotta-Linux/terracotta-installer"
    "Terracotta-Linux/terracotta-branding"
)

mkdir -p "${REPO_DIR}"

for repo in "${REPOS[@]}"; do
    echo "==> Fetching latest release assets from ${repo}"
    gh release download --repo "${repo}" --pattern '*.pkg.tar.zst' -D "${REPO_DIR}" --clobber
done

echo "==> Rebuilding pacman repo database at ${REPO_DIR}/${REPO_DB_NAME}.db.tar.gz"
(
    cd "${REPO_DIR}"
    repo-add "${REPO_DB_NAME}.db.tar.gz" ./*.pkg.tar.zst
)

echo "==> Done. Local repo ready at ${REPO_DIR}"
