# Arcam FMJ Receivers (Fixed & Extended)

[![GitHub Release](https://img.shields.io/github/v/release/jansinger/ha-arcam-fmj-custom?style=flat-square)](https://github.com/jansinger/ha-arcam-fmj-custom/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6+-41BDF5?style=flat-square&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/jansinger/ha-arcam-fmj-custom?style=flat-square)](LICENSE)

Custom Home Assistant integration for Arcam FMJ receivers with bug fixes and extended IP control features.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jansinger&repository=ha-arcam-fmj-custom&category=integration)

## Features

- **Push-based architecture:** Real-time state updates via persistent TCP connection (`local_push`). No polling for power, volume, mute, source, or decode mode changes.
- **Device model detection:** Automatically detects the actual device model (e.g. "AV40") via AMX Duet protocol for short, clean entity names
- **Source images:** SVG icons for non-streaming sources (AV, BD, SAT, GAME, etc.) displayed in the media player card
- **Album artwork:** Automatic cover art lookup via iTunes Search API for music and podcasts on network sources (NET, USB, BT), with fallback to Cast/DLNA companion entities
- **Media state:** Shows Playing/Paused/On states — streaming sources reflect actual playback status
- **Now Playing Info:** Shows media title, artist, and album from network sources
- **Dashboard-ready:** Short entity names, works with [maxi-media-player](https://github.com/punxaphil/maxi-media-player), [stack-in-card](https://github.com/custom-cards/stack-in-card), and standard Lovelace cards
- **Diagnostic sensors:** Audio format, video resolution, network playback status, and more
- **Audio controls:** Bass, Treble, Balance, Subwoofer Trim, Lip Sync Delay as number entities
- **Room EQ:** Select between Off and 3 presets (shows actual preset names from device)
- **Dolby Audio:** Select Dolby mode (Off / Movie / Music / Night)
- **Display & Compression:** Display brightness and dynamic range compression as select entities
- **Options Flow:** Configure poll interval for now-playing metadata and enable/disable Zone 2
- **Availability tracking:** Shows "unavailable" when connection is lost (instead of "off")
- **Mute fix:** Correctly synchronizes mute state on devices using RC5 commands

## Entities

### Media Player

| Name | Default | Description |
|------|---------|-------------|
| Zone 1 | Enabled | Power, volume, mute, source, sound mode, now playing, artwork, source images |
| Zone 2 | Disabled | Power, volume, mute, source (can be disabled entirely via Options) |

### Controls (Number)

| Name | Default | Category | Range | Description |
|------|---------|----------|-------|-------------|
| Bass | Enabled | — | -12 to +12 dB (1 dB) | Bass equalization |
| Treble | Enabled | — | -12 to +12 dB (1 dB) | Treble equalization |
| Balance | Enabled | — | -6 to +6 (1) | Left/right balance |
| Subwoofer Trim | Disabled | Config | -10.0 to +10.0 dB (0.5 dB) | Subwoofer level trim |
| Lip Sync Delay | Disabled | Config | 0 to 250 ms (5 ms) | Audio delay compensation |

### Controls (Select)

| Name | Default | Category | Options | Description |
|------|---------|----------|---------|-------------|
| Display Brightness | Enabled | Config | Off / Level 1 / Level 2 | Front panel display brightness |
| Room EQ | Enabled | Config | Off / Preset 1 / Preset 2 / Preset 3 | Room correction presets (shows device names) |
| Compression | Disabled | Config | Off / Light / Medium | Dynamic range compression |
| Dolby Audio | Disabled | Config | Off / Movie / Music / Night | Dolby audio processing mode |
| Sound Mode | Enabled | — | Stereo, Dolby Surround, DTS Neural:X, etc. | Decode mode (dynamic, based on input format) |
| Zone 1 Source | Enabled | — | STB, AV, BD, SAT, GAME, etc. | Input source selection |
| Zone 2 Source | Disabled | — | STB, AV, BD, SAT, GAME, etc. | Input source for Zone 2 |

### Sensors (Diagnostic)

All sensors have `entity_category: diagnostic`.

| Name | Default | Description |
|------|---------|-------------|
| Audio Input Format | Enabled | PCM, Dolby Digital, Dolby Atmos, DTS:X, etc. |
| Audio Channels | Enabled | Channel configuration (e.g. STEREO_ONLY, 3/2.1) |
| Video Resolution | Enabled | e.g. 3840x2160, 1920x1080 |
| Video Refresh Rate | Disabled | e.g. 60 Hz |
| Video Colorspace | Disabled | SDR, HDR10, Dolby Vision, HLG, etc. |
| Video Scan Mode | Disabled | Progressive / Interlaced |
| Audio Sample Rate | Disabled | e.g. 48000 Hz |
| Network Playback | Disabled | Stopped / Playing / Paused for network sources |
| Bluetooth Status | Disabled | Bluetooth connection state |
| Room EQ Names | Disabled | Custom preset names (attributes: eq1, eq2, eq3) |
| HDMI Settings | Disabled | CEC, ARC, OSD settings (as attributes) |
| Zone Settings | Disabled | Zone 2 input, volume, status (as attributes) |

> **Entity categories:** Entities marked "Config" appear under the device's configuration section in HA and are hidden from the default entity picker. Primary controls (Bass, Treble, Balance, Sound Mode, Source) have no category and appear in the main UI. All sensors are "Diagnostic" and appear in the diagnostics section.

## Configuration Options

After adding the integration, you can configure these options via **Settings → Devices & Services → Arcam FMJ → Configure**:

| Option | Default | Description |
|--------|---------|-------------|
| Poll interval | 10 seconds | How often to poll now-playing metadata for network sources (5–60s). The Arcam device pushes all standard state changes in real-time, but does not push track metadata for streaming sources — this requires periodic polling. |
| Zone 2 enabled | Yes | Whether to create Zone 2 entities. Disable if you don't use Zone 2 to reduce clutter. |

## Installation via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jansinger&repository=ha-arcam-fmj-custom&category=integration)

1. Open HACS in Home Assistant (or click the button above)
2. Click the three dots menu (top right) -> **Custom repositories**
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

## Dashboard Examples

### Maxi Media Player + Controls (Stack-in-Card)

Use [maxi-media-player](https://github.com/punxaphil/maxi-media-player) for playback and add audio controls below with [stack-in-card](https://github.com/custom-cards/stack-in-card):

```yaml
type: custom:stack-in-card
cards:
  - type: custom:maxi-media-player
    entities:
      - media_player.arcam_av40_zone_1

  - type: entities
    entities:
      - entity: select.arcam_av40_zone_1_source
        name: Source
      - entity: select.arcam_av40_sound_mode
        name: Sound Mode
      - entity: select.arcam_av40_room_eq
        name: Room EQ
      - entity: number.arcam_av40_bass
        name: Bass
      - entity: number.arcam_av40_treble
        name: Treble
      - entity: number.arcam_av40_balance
        name: Balance
      - entity: select.arcam_av40_display_brightness
        name: Display
```

### Mushroom Media Player + Controls

Alternative using [mushroom-media-player-card](https://github.com/piitaya/lovelace-mushroom):

```yaml
type: custom:stack-in-card
cards:
  - type: custom:mushroom-media-player-card
    entity: media_player.arcam_av40_zone_1
    use_media_info: true
    show_volume_level: true
    volume_controls:
      - volume_mute
      - volume_set
      - volume_buttons
    media_controls:
      - on_off

  - type: entities
    entities:
      - entity: select.arcam_av40_zone_1_source
        name: Source
      - entity: select.arcam_av40_sound_mode
        name: Sound Mode
      - entity: select.arcam_av40_room_eq
        name: Room EQ
      - entity: number.arcam_av40_bass
        name: Bass
      - entity: number.arcam_av40_treble
        name: Treble
      - entity: number.arcam_av40_balance
        name: Balance
      - entity: select.arcam_av40_display_brightness
        name: Display
```

> **Note:** Entity IDs depend on your device model (e.g. `arcam_av40`, `arcam_avr30`). Adjust to match your setup. Audio controls (number/select) are separate entities and must be added to the card explicitly — media player cards only show their own controls (volume, source, sound mode).

### Custom Source Names (Template Select Helper)

The source select entity exposes the technical Arcam input names (e.g. `SAT`, `HDMI1`, `BD`). You can create a **Template Select** helper to show only the sources you actually use and give them friendly names.

Add the following to your Home Assistant **main `configuration.yaml`** (typically at `/homeassistant/configuration.yaml` or `config/configuration.yaml` — the same file where you configure other HA integrations, not a file within this custom component):

```yaml
template:
  - select:
      - name: "AV40 Eingang"
        unique_id: av40_source_friendly
        state: >
          {% set mapping = {
            'SAT': 'Apple TV',
            'HDMI1': 'Fire TV',
            'HDMI2': 'Playstation',
            'BD': 'Blu-ray',
          } %}
          {% set current = states('select.arcam_av40_zone_1_source') %}
          {{ mapping.get(current, current) }}
        options: "{{ ['Apple TV', 'Fire TV', 'Playstation', 'Blu-ray'] }}"
        select_option:
          - variables:
              reverse_mapping:
                Apple TV: SAT
                Fire TV: HDMI1
                Playstation: HDMI2
                Blu-ray: BD
          - action: select.select_option
            target:
              entity_id: select.arcam_av40_zone_1_source
            data:
              option: "{{ reverse_mapping[option] }}"
```

**How to customize:**
- Check **Developer Tools → States** in HA for `select.arcam_av40_zone_1_source` to see the available source names (e.g. `SAT`, `HDMI1`, `HDMI2`, `BD`, `AV`, `STB`, `PVR`, `AUX`, `NET`, `USB`, `BT`)
- Replace the left side of the mapping (`SAT`, `HDMI1`, ...) with the sources you use
- Replace the right side (`Apple TV`, `Fire TV`, ...) with your preferred display names
- Only include the sources you want to see — the rest will be hidden
- After editing, reload Template entities via **Developer Tools → YAML → Template entities** (no restart required)

Then use `select.av40_eingang` instead of `select.arcam_av40_zone_1_source` in your dashboard cards.

## Affected Devices

All Arcam devices with IP control:
- AV40, AV41
- AVR5, AVR10, AVR11, AVR20, AVR21, AVR30, AVR31
- AVR390, AVR450, AVR550, AVR600, AVR750, AVR850, AVR860

## Changelog

### v3.0.1
- **Documentation** — Fix entity option counts (Display Brightness: 3 levels, Compression: 3 levels), add Diagnostic category to sensors, split entity tables by type.
- **CI/CD** — Add GitHub Actions for automatic releases on tag push and HACS/Hassfest validation on push/PR. Add version badge, HACS badge, and "Add to HACS" button.
- **Manifest** — Add `after_dependencies: ["http"]`, `issue_tracker`, fix key ordering for hassfest compliance.

### v3.0.0
- **Source images** — SVG icons for non-streaming sources (AV, BD, CD, SAT, GAME, FM, DAB, etc.) displayed in the media player card. Network sources continue to show album artwork via iTunes.
- **Options Flow** — Configure poll interval (5–60s) and enable/disable Zone 2 via Settings → Devices & Services → Configure.
- **Entity categories** — Display brightness, compression, Dolby Audio, Room EQ, subwoofer trim, and lip sync delay are now correctly categorized as `Config` entities. Primary controls (bass, treble, balance, sound mode, source) remain in the main UI.
- **Media state** — Media player now shows Playing/Paused for network sources with active playback (via `NetworkPlaybackStatus`), instead of always showing "On".
- **IoT class** — Changed from `local_polling` to `local_push`. The integration uses a persistent TCP connection with push-based state updates. Only now-playing metadata for network sources requires polling (configurable interval).
- **Dynamic image accessibility** — `media_image_remotely_accessible` is now a dynamic property: `True` for remote artwork URLs (iTunes), `False` for local SVG icons.

### v2.7.0
- **Live device tests** — New `--device` option for pytest to run read-only integration tests against a real Arcam device
- **Library update** — arcam-fmj 2.4.0 with priority queue, request deduplication, and CancelledError handling

### v2.6.0
- **Album artwork via iTunes** — Automatic cover art lookup for music albums and podcasts on network sources (NET, USB, BT). Uses the iTunes Search API (no authentication required). Results are cached in memory (24h for hits, 1h for misses). Falls back to companion media player artwork (Cast/DLNA) when iTunes has no result.
- **Fix: Sound mode with multichannel PCM** — Multichannel PCM (e.g. PCM 3/2.1) was incorrectly classified as 2-channel, causing wrong decode mode display (e.g. "Stereo" instead of "Dolby Surround"). Now checks the actual channel configuration.

### v2.5.0
- **Source select entity** — Zone 1 and Zone 2 input source as separate select entities for dashboard cards

### v2.4.0
- **Room EQ preset names** — Room EQ select shows actual preset names from device (e.g. "Music") instead of generic "Preset 1/2/3". Duplicate names are disambiguated automatically.

### v2.3.1
- **Fix: API model detection** — Device API model (HDA/860/450 series) is now resolved from detected model name before creating State objects, fixing wrong sound mode lists on HDA series devices (AV40, AVR30, etc.)

### v2.3.0
- **Fix: Sound mode list** — Mode list now matches active decode mode type (MCH vs 2CH), fixing "unknown" mode when MCH is active with PCM audio
- **Fix: MCH mode naming** — MCH 0x03 correctly displayed as "Dts Neural X" instead of "Dolby D Ex Or Dts Es"
- **Fix: Sound mode fallback** — Current mode always appears in dropdown, even when it comes from fallback enum

### v2.2.0
- **Fix: Bass/Treble/Balance values** — Correct sign-magnitude decoding per Arcam protocol (was showing -14 instead of 0 at neutral)
- **Fix: Value ranges** — Bass/Treble: -12 to +12 dB, Balance: -6 to +6, Sub Trim: -10 to +10 dB (0.5 steps), Lipsync: 0-250 ms
- **Fix: Entity category** — Number and select entities no longer hidden as "config" entities, making them visible in Lovelace entity pickers
- **Sound Mode select entity** — Decode mode (Stereo Downmix, Multi Channel, Dolby Surround, etc.) as separate select entity for dashboard cards
- **Dashboard examples** — Maxi Media Player and Mushroom card setups with audio controls

### v2.1.1
- **Fix: Device model detection** — `process()` must run as background task for AMX Duet response to be received

### v2.1.0
- **Fix: Entity names use device model** instead of IP address (e.g. `arcam_av40_bass` instead of `arcam_fmj_192_168_1_100_bass`)
- **Fix: Update storm eliminated** — state is updated once centrally instead of per-entity (was causing 10+ second hangs)
- **Fix: Config flow timeout** for UPnP device description fetch (dd.xml)

### v2.0.0
- **Room EQ:** Changed from switch to select entity with Off / Preset 1-3
- **Dolby Audio:** New select entity for Dolby mode control
- **Diagnostic sensors:** Audio format, video resolution, network playback, Bluetooth status, Room EQ names, HDMI settings, zone settings
- **Now Playing Info:** Media title, artist, album from network sources (NET, USB, BT)
- **Companion artwork:** Album art from Cast/DLNA entities on the same host
- **Sensor rename:** `audio_format` renamed to `audio_input_format` to avoid conflicts
- **Device naming:** Dynamic device name using detected model (e.g. "Arcam AV40")

### v1.3.0
- Major refactor with base entity class, sensors, best practices

### v1.2.0
- Share State objects to fix setup hanging

### v1.1.1
- Fix Zone 2 timeouts when zone is off

### v1.1.0
- Audio/video info as state attributes
- Audio controls (bass, treble, balance, sub trim, lipsync)
- Room EQ switch, display brightness and compression select
- Bug fixes: client loop resilience, availability tracking, power state, turn off

## Credits

- Original integration: [@elupus](https://github.com/elupus)
- Extended version: [@jansinger](https://github.com/jansinger)
