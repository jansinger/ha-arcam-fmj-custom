# Arcam FMJ Receivers (Fixed)

Custom Home Assistant integration for Arcam FMJ receivers with a fix for the mute state synchronization issue.

## The Problem

The official `arcam_fmj` integration has a bug where the mute state doesn't update correctly after toggling mute on AV receivers (AV40, AVR series, etc.).

**Root Cause:** When using `set_mute()` on devices that don't support direct mute write, the library sends an RC5 IR command but never updates the internal mute state. The `get_mute()` function reads from a different state key that remains stale.

## The Fix

This custom integration uses a [forked arcam-fmj library](https://github.com/jansinger/arcam_fmj) that queries the mute state after sending an RC5 command, ensuring the state is always synchronized.

## Installation via HACS

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) → **Custom repositories**
3. Add: `https://github.com/jansinger/ha-arcam-fmj-custom`
4. Category: **Integration**
5. Click **Add**
6. Search for "Arcam FMJ Receivers (Fixed)" and install
7. Restart Home Assistant
8. Remove the old Arcam FMJ integration and re-add it

## Manual Installation

1. Download this repository
2. Copy `custom_components/arcam_fmj` to your HA `config/custom_components/` folder
3. Restart Home Assistant

## Affected Devices

All Arcam devices NOT in the MUTE_WRITE_SUPPORTED list:
- AV40, AV41
- AVR5, AVR10, AVR11, AVR20, AVR21, AVR30, AVR31
- AVR390, AVR450, AVR550, AVR600, AVR750, AVR850, AVR860

## Credits

- Original integration: [@elupus](https://github.com/elupus)
- Fix: [@jansinger](https://github.com/jansinger)
