# Terracotta Linux ISO

archiso profile and build tooling for the Terracotta Linux live/install
medium.

## Prerequisites

On the build machine:

- `archiso` (`mkarchiso`)
- `git`
- `gh` (GitHub CLI), authenticated (`gh auth status`)
- `sudo` access (mkarchiso must run as root)
- `qemu-system-x86_64` and `edk2-ovmf`, for local testing with `test-qemu.sh`

Terracotta Linux packages are consumed as prebuilt GitHub release assets,
not built from source here:

- [Terracotta-Linux/kiln](https://github.com/Terracotta-Linux/kiln)
- [Terracotta-Linux/terracotta-installer](https://github.com/Terracotta-Linux/terracotta-installer)
- [Terracotta-Linux/terracotta-branding](https://github.com/Terracotta-Linux/terracotta-branding)

## Build flow

```sh
./build.sh
```

This:

1. Runs `fetch-packages.sh`, which downloads the latest `*.pkg.tar.zst`
   release assets for `kiln`, `terracotta-installer`, and
   `terracotta-branding` into `./local-repo/x86_64/` and runs `repo-add` to
   build the repo database there. `profile/pacman.conf` has a `[terracotta]`
   repo pointing at this directory via a `@@TERRACOTTA_REPO_PATH@@`
   placeholder — `build.sh` substitutes it with this repo's absolute path
   into a generated temp copy of `pacman.conf` (so no username/home path is
   ever hardcoded, and the checked-in `profile/pacman.conf` is never
   modified on disk) and passes that to `mkarchiso -C`.
2. Removes any existing `work/` directory.
3. Runs `sudo mkarchiso -v -w work/ -o out/ -C <generated pacman.conf> profile/`.
4. Prints the path to the resulting `.iso` in `out/`.

## Testing in QEMU

```sh
./test-qemu.sh
```

Boots the most recently built ISO in `out/` via UEFI (the ISO has no BIOS
boot support — see below). Requires `edk2-ovmf`; the script looks for its
`OVMF*.fd` firmware under the current and legacy Arch package paths and
errors out clearly (rather than failing silently) if it can't find one.

## Boot flow: network gate before the installer

`terracotta-installer` assumes network connectivity is already up when it
launches and does **no connectivity check of its own**. Since the live ISO
cannot assume the user is already online (Wi-Fi needs credentials, Ethernet
may be unplugged), root's `.bash_profile`
(`profile/airootfs/root/.bash_profile`) enforces this on tty1 as a hard
gate, before ever execing the installer:

1. Loop: check `nm-online -q -t 5` (via NetworkManager, enabled in the live
   image and covering both Wi-Fi and Ethernet through `nmtui`).
2. If there's no active connection, clear the screen, print a short banner,
   and launch `nmtui` so the user can configure Wi-Fi or Ethernet.
3. When `nmtui` exits, loop back and re-check — it does **not** fall through
   to the installer on a `nmtui` exit; only a confirmed live connection ends
   the loop.
4. Once online, `exec terracotta-installer` (using `exec`, not a plain
   call, so a shell remains available on tty1 if the installer crashes).

This is why `nmtui` may appear automatically at login before the installer
UI shows up — it's expected, not a stray tool launch.

Root autologins on tty1 via
`profile/airootfs/etc/systemd/system/getty@tty1.service.d/autologin.conf`,
which is what triggers `.bash_profile` on boot.

## Plymouth

`profile/airootfs/etc/plymouth/plymouthd.conf` sets `Theme=terracotta`. The
actual theme files (script, images) are **not** part of this profile — they
come from the `terracotta-branding-plymouth` package, listed in
`packages.x86_64` and installed into the live image at build time. If that
package doesn't ship a theme named `terracotta`, Plymouth silently falls
back to its default theme.

## Boot modes

UEFI-only, GRUB-only: `profile/profiledef.sh` sets `bootmodes` to
`uefi-x64.grub.esp` and `uefi-x64.grub.eltorito`. There is no legacy BIOS
boot support — plain `mkarchiso` has no `bios.grub` bootmode (BIOS boot is
only wired up via syslinux there), so BIOS support was dropped rather than
pulling in syslinux for it. This ISO will not boot on BIOS-only hardware or
BIOS-mode VMs.

## Known follow-up: verify in terracotta-installer

`terracotta-installer` depends on `kiln` (packaged as `terracotta-kiln`) at
runtime. This repo assumes `terracotta-installer`'s own `PKGBUILD` declares
`terracotta-kiln` in `depends=()` so that installing the
`terracotta-installer` package pulls it in via normal pacman dependency
resolution. **This has not been verified here** — check
`Terracotta-Linux/terracotta-installer`'s `PKGBUILD` and fix it in that repo
if `terracotta-kiln` is missing from `depends=()`. `terracotta-kiln` is also
listed explicitly in this profile's `packages.x86_64` as a safety net
regardless.
