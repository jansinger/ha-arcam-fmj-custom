# Arcam FMJ Receivers (Fixed & Extended)

Custom Home Assistant integration for Arcam FMJ receivers with bug fixes and extended IP control features.

## Features

- **Mute fix:** Correctly synchronizes mute state on devices using RC5 commands (AV40, AVR series, etc.)
- **Availability tracking:** Shows "unavailable" when connection is lost (instead of "off")
- **Audio/Video info:** Exposes current audio format (Dolby Atmos, DTS:X, PCM...) and video parameters (resolution, HDR) as state attributes
- **Audio controls:** Bass, Treble, Balance, Subwoofer Trim, Lip Sync Delay as number entities
- **Room EQ:** Toggle Room Equalization on/off as switch entity
- **Display & Compression:** Display brightness and dynamic range compression as select entities
- **Device model detection:** Automatically detects the actual device model (e.g. "AV40") via AMX Duet

## Entities

| Entity Type | Name | Description |
|-------------|------|-------------|
| Media Player | Zone 1 / Zone 2 | Main control: power, volume, mute, source, sound mode, tuner |
| Number | Bass | -14 to +14 |
| Number | Treble | -14 to +14 |
| Number | Balance | -13 to +13 |
| Number | Subwoofer Trim | -14 to +14 dB |
| Number | Lip Sync Delay | 0 to 200 ms |
| Switch | Room EQ | Enable/disable room equalization |
| Select | Display Brightness | Off / Level 1 / Level 2 / Level 3 |
| Select | Compression | Off / Light / Medium / Heavy |

## Extra State Attributes (Media Player)

| Attribute | Example | Description |
|-----------|---------|-------------|
| `audio_format` | `DOLBY_ATMOS` | Current incoming audio format |
| `audio_config` | `STEREO_CENTER_SURR_LR_BACK_LR_LFE` | Audio channel configuration |
| `audio_sample_rate` | `48000` | Sample rate in Hz |
| `video_resolution` | `3840x2160` | Video resolution |
| `video_refresh_rate` | `60` | Refresh rate |
| `video_colorspace` | `HDR10` | HDR format |
| `video_interlaced` | `false` | Interlaced or progressive |

## Installation via HACS

1. Open HACS in Home Assistant
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

## Dashboard Example (Stack-in-Card)

Combine all entities into one card using [stack-in-card](https://github.com/custom-cards/stack-in-card):

```yaml
type: custom:stack-in-card
cards:
  - type: custom:mushroom-media-player-card
    entity: media_player.arcam_fmj_zone_1
    use_media_info: true
    show_volume_level: true
    volume_controls:
      - volume_mute
      - volume_set
      - volume_buttons
    media_controls:
      - on_off

  - type: markdown
    content: >
      {% set mp = states.media_player.arcam_fmj_zone_1 %}
      {% if mp.attributes.audio_format is defined %}
      **Audio:** {{ mp.attributes.audio_format }}
      {% if mp.attributes.audio_config is defined %}
      ({{ mp.attributes.audio_config }}){% endif %}
      {% endif %}
      {% if mp.attributes.video_colorspace is defined %}
      | **Video:** {{ mp.attributes.video_resolution }}
      {{ mp.attributes.video_colorspace }}
      {% endif %}

  - type: entities
    entities:
      - entity: number.arcam_fmj_bass
        name: Bass
      - entity: number.arcam_fmj_treble
        name: Treble
      - entity: number.arcam_fmj_balance
        name: Balance
      - entity: number.arcam_fmj_subwoofer_trim
        name: Subwoofer
      - entity: number.arcam_fmj_lipsync_delay
        name: Lip Sync

  - type: entities
    entities:
      - entity: switch.arcam_fmj_room_eq
        name: Room EQ
      - entity: select.arcam_fmj_display_brightness
        name: Display
      - entity: select.arcam_fmj_compression
        name: Compression
```

**Note:** Entity IDs may vary. Adjust to match your actual entity names.

## Affected Devices

All Arcam devices NOT in the MUTE_WRITE_SUPPORTED list:
- AV40, AV41
- AVR5, AVR10, AVR11, AVR20, AVR21, AVR30, AVR31
- AVR390, AVR450, AVR550, AVR600, AVR750, AVR850, AVR860

## Bug Fixes (vs. official integration)

1. **Mute state sync:** RC5 mute commands now query state after execution
2. **Client loop resilience:** Unexpected exceptions no longer permanently kill the connection
3. **Availability:** Entity correctly shows "unavailable" when TCP connection is lost
4. **Power state:** `None` power state no longer incorrectly shows "Off"
5. **Turn off:** State is immediately updated after power-off command

## Credits

- Original integration: [@elupus](https://github.com/elupus)
- Extended version: [@jansinger](https://github.com/jansinger)
