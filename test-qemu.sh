#!/usr/bin/env bash
# Boots the most recently built Terracotta Linux ISO in out/ under QEMU.
# UEFI-only: the ISO is GRUB/UEFI-only and has no BIOS boot support.
#
# Usage: ./test-qemu.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${REPO_ROOT}/out"

if [[ $# -ne 0 ]]; then
    echo "Usage: $0" >&2
    exit 1
fi

ISO_PATH="$(find "${OUT_DIR}" -maxdepth 1 -name '*.iso' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n1 | cut -d' ' -f2-)"
if [[ -z "${ISO_PATH}" ]]; then
    echo "ERROR: no .iso found in ${OUT_DIR}. Run ./build.sh first." >&2
    exit 1
fi
echo "==> Using ISO: ${ISO_PATH}"

# terracotta-installer needs a target disk to install to. Without one it has
# nothing to partition and exits immediately after launching. Give it a
# persistent scratch virtio disk (created once, reused across test runs so
# repeated installs don't re-download/re-verify packages from scratch).
# Delete it to start a test install from a blank disk again.
DISK_PATH="${OUT_DIR}/test-disk.qcow2"
if [[ ! -f "${DISK_PATH}" ]]; then
    echo "==> Creating scratch install disk: ${DISK_PATH}"
    qemu-img create -f qcow2 "${DISK_PATH}" 20G >/dev/null
fi
echo "==> Using install disk: ${DISK_PATH}"

# Look for edk2-ovmf's firmware under the paths used by current and older
# Arch edk2-ovmf package layouts.
OVMF_CANDIDATES=(
    /usr/share/edk2/x64/OVMF_CODE.4m.fd
    /usr/share/edk2/x64/OVMF.4m.fd
    /usr/share/ovmf/x64/OVMF.fd
    /usr/share/OVMF/OVMF_CODE.fd
)
OVMF_CODE=""
for candidate in "${OVMF_CANDIDATES[@]}"; do
    if [[ -f "${candidate}" ]]; then
        OVMF_CODE="${candidate}"
        break
    fi
done
if [[ -z "${OVMF_CODE}" ]]; then
    echo "ERROR: could not find OVMF UEFI firmware. Install 'edk2-ovmf'" >&2
    echo "       (checked: ${OVMF_CANDIDATES[*]})" >&2
    exit 1
fi
echo "==> Using UEFI firmware: ${OVMF_CODE}"

QEMU_ARGS=(
    -m 2048
    -smp 2
    -cdrom "${ISO_PATH}"
    -boot d
    -drive "if=virtio,format=qcow2,file=${DISK_PATH}"
    -netdev user,id=net0
    -device virtio-net-pci,netdev=net0
    -drive "if=pflash,format=raw,readonly=on,file=${OVMF_CODE}"
)

echo "==> Launching qemu-system-x86_64 (uefi)"
qemu-system-x86_64 "${QEMU_ARGS[@]}"
