#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="terracotta"
iso_label="TERRACOTTA_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="Terracotta Linux <https://github.com/Terracotta-Linux>"
iso_application="Terracotta Linux Live/Install Medium"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="terracotta"
buildmodes=('iso')
# UEFI-only, GRUB-only. Plain mkarchiso has no bios.grub bootmode (legacy
# BIOS boot is only wired up via syslinux there), so BIOS support is
# dropped rather than pulling in syslinux for it.
bootmodes=('uefi-x64.grub.esp'
           'uefi-x64.grub.eltorito')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '19')
bootstrap_tarball_compression=(xz -9e)
file_permissions=(
  ["/etc/shadow"]="0:0:400"
)
