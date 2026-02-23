# Contract: UI Data Packets and Control Messages (Phase 1)

This contract defines the packet schemas for the planned non-blocking UI stream
between the simulation core and a navigator-style map viewer.

## Goals

- Core simulation loop remains non-blocking
- UI receives structured, versioned data packets
- Packet emission supports throttling and downsampling
- Minimal controls (day/time toggles) are supported

## Transport Model (Planning)

- Transport: WebSocket (planned default UI path)
- Direction:
  - Simulation -> UI: snapshot/metrics/event packets
  - UI -> Simulation: control commands (day/time toggles, snapshot request)
- All packets include a `type` and `schema_version`

## Common Envelope

```json
{
  "type": "ui.snapshot",
  "schema_version": 1,
  "run_id": "string",
  "tick": 12345,
  "sim_time": {
    "day_type": "weekday",
    "time_band": "morning"
  },
  "payload": {}
}
```

Common fields:
- `type`: packet type identifier
- `schema_version`: integer schema version
- `run_id`: simulation run/session identifier
- `tick`: simulation tick index for ordering
- `sim_time`: current day type and time band
- `payload`: packet-specific body

## Simulation -> UI Packets

### 1. `ui.topology_snapshot` (low frequency / on connect / on scenario reset)

Purpose:
- Send road geometry and zone overlays required to render the base map

Payload fields:
- `network_geometry_version`
- `nodes`: sampled or full node coordinates and kinds
- `links`: polylines or simplified segments with `link_id`, class, bridge flag
- `zones`: polygons or centroids with zone type labels
- `bridges`: bridge group metadata (ids, names, corridor labels)

Emission rules:
- Sent on initial connection and whenever topology changes
- NOT emitted every tick

### 2. `ui.congestion_frame` (throttled high-frequency packet)

Purpose:
- Update congestion layer for navigator-style display

Payload fields:
- `frame_seq`
- `sampling_mode` (`full`, `top_k_hotspots`, `corridor_focus`, `downsampled`)
- `link_congestion`: array of `{link_id, congestion_level, travel_time_ratio}`
- `active_agent_count`
- `dropped_frame_count_since_last` (for observability)

Emission rules:
- Emitted at most `ui_stream_hz_limit`
- May downsample links or switch sampling mode under load
- Skipping frame emission MUST NOT stall simulation tick progression

### 3. `ui.event_overlay`

Purpose:
- Show active/scheduled incidents and construction zones

Payload fields:
- `events`: array of `{event_id, event_type, status, severity, target_scope}`

Emission rules:
- Sent when event state changes
- May be coalesced with congestion frame if transport batching is enabled

### 4. `ui.metrics_summary`

Purpose:
- Display compact run metrics and debugging counters in UI

Payload fields:
- `trip_generated_total`
- `trip_completed_total`
- `trip_failed_total`
- `capacity_violation_count`
- `policy_mix_lambda`
- `adaptive_fallback_active`
- `tick_rate_recent_hz`

Emission rules:
- Low to medium frequency (e.g., 1-2 Hz) independent of congestion frames

## UI -> Simulation Control Packets

### 5. `ui.control_command`

Payload fields:
- `command_id` (client-generated id for correlation)
- `action` (`set_day_type`, `set_time_band`, `inject_event`, `clear_event`, `request_snapshot`)
- `arguments` (object; shape depends on action)

Examples:
- `set_day_type`: `{ "day_type": "weekend" }`
- `set_time_band`: `{ "time_band": "evening" }`
- `request_snapshot`: `{ "force": true }`

Rules:
- Commands are requests; simulation may reject invalid commands safely
- Command processing must occur on step boundaries to preserve deterministic state

### 6. `ui.control_ack`

Purpose:
- Confirm acceptance/rejection of UI commands

Payload fields:
- `command_id`
- `accepted` (bool)
- `reason` (optional string)
- `applied_tick` (optional int)

## Throttling and Downsampling Contract

- UI packet generation MUST be decoupled from core flow update timing
- When the UI cannot keep up, the system MUST prefer dropping/coalescing UI
  frames over delaying simulation steps
- Packet payloads may be downsampled, but summary metrics and control acks MUST
  remain logically consistent with the underlying simulation state
- Packet consumers MUST treat missing intermediate `ui.congestion_frame` packets
  as normal behavior

## Determinism and Reproducibility Notes

- UI emission cadence may vary without invalidating simulation determinism, as
  long as simulation state and run-summary outputs remain unchanged under the
  same seed and control/event sequence
- Control commands affecting day/time/event state should be captured in the run
  log with tick application timing for reproducible replay
