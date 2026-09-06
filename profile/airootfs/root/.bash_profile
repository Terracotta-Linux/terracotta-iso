# Terracotta Linux live environment: on tty1, gate the installer launch on a
# confirmed working network connection. terracotta-installer assumes network
# connectivity is already present and performs no connectivity check of its
# own, so this is a hard requirement, not a skippable convenience step.
if [ "$(tty)" = "/dev/tty1" ]; then
    while ! nm-online -q -t 5; do
        clear
        echo "=== Terracotta Linux — Network Setup ==="
        echo "Connect via Wi-Fi or Ethernet to continue."
        echo
        nmtui
        # Loop back and re-check; do not fall through to the installer
        # until nm-online confirms a live connection.
    done

    exec terracotta-installer
fi
