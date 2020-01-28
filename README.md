# Automatic Version Pinner

This script updates version.json in our NixOS overlay. It scans all existing
branches named 'nixpkgs' or 'nixos-*' and updates both revisions and sha256
hashes accordingly. A pull request is created if anything has changed.
