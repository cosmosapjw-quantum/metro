# Contract: UI Data Packets and Control Messages (Phase 1)

This contract defines the packet schemas for the planned non-blocking UI stream
between the simulation core and a navigator-style map viewer.

## Goals

- Core simulation loop remains non-blocking
- UI receives structured, versioned data packets
- Packet emission supports throttling and downsampling
- Minimal controls (day/time toggles) are supported
- Transit/metro observability remains phase-gated so road-only mode can omit
  transit payloads entirely without schema ambiguity

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

Extension compatibility notes:
- Road-only runs MAY omit transit-specific packet types entirely
- Multimodal runs MUST still preserve the same common envelope shape
- Phase-gated transit payloads SHOULD prefer empty arrays / omitted optional
  fields over blocking the base `ui.congestion_frame` path

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

### 4a. `ui.transit_overlay` (optional low-frequency extension packet)

Purpose:
- Render stations, lines, and access connectors when transit observability is
  enabled without changing the road-only base map contract

Payload fields:
- `overlay_version`
- `phase_gate` (`phase9_static`, `phase10_passenger`, `phase11_multimodal`)
- `stations`: array of `{station_id, station_name, x, y, station_kind, serving_line_ids}`
- `lines`: array of `{line_id, line_name, line_mode, station_sequence}`
- `connectors`: array of `{connector_id, station_id, anchor_node_id, anchor_zone_id, walk_time_ticks}`
- `highlight_mode` (`network`, `station_focus`, `line_focus`)

Emission rules:
- Optional packet; SHOULD NOT be emitted in `road_only` mode
- Emitted on connect, topology reset, or transit overlay toggle changes
- In Phase 9, this packet may contain static topology only and MUST NOT require
  passenger-flow metrics to be populated

### 4b. `ui.station_congestion_summary` (optional low/medium-frequency extension packet)

Purpose:
- Expose station-level boarding/waiting/transfer/crowding summaries in a
  transport-friendly aggregate form

Payload fields:
- `summary_window` (`current_tick`, `time_band_rollup`, `recent_n_ticks`)
- `phase_gate` (`phase9_static`, `phase10_passenger`, `phase11_multimodal`)
- `stations`: array of
  `{station_id, time_band, entries, boardings, alightings, transfer_count, avg_wait_ticks, crowding_ratio, served_line_ids}`
- `dropped_summary_count_since_last` (for observability under throttling)

Emission rules:
- Optional packet; SHOULD NOT be emitted in `road_only` mode
- In Phase 9 static-wiring scenarios, stations MAY be emitted with zero-filled
  counts so the UI can validate schema presence before passenger flow exists
- In Phase 10+, packet emission SHOULD be decoupled from per-tick congestion
  frames and may be throttled independently

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
- Extension transit packets MUST follow the same non-blocking rule; dropping a
  `ui.transit_overlay` refresh or `ui.station_congestion_summary` update is
  preferable to delaying simulation steps

## Phase-Gating Rules

- `road_only` mode: only baseline road/event/control packets are required;
  transit packets MAY be absent and UI consumers MUST treat that as normal
- `phase9_static`: `ui.transit_overlay` MAY be enabled with station/line/
  connector metadata while station congestion counts remain empty or zero-filled
- `phase10_passenger`: station summary packets add boarding/alighting/waiting/
  transfer aggregates without yet requiring road-vs-transit candidate overlays
- `phase11_multimodal`: transit overlay and station summary packets may be
  combined with multimodal comparison views, but they still remain optional
  adjuncts to the baseline congestion frame rather than replacements for it

## Determinism and Reproducibility Notes

- UI emission cadence may vary without invalidating simulation determinism, as
  long as simulation state and run-summary outputs remain unchanged under the
  same seed and control/event sequence
- Control commands affecting day/time/event state should be captured in the run
  log with tick application timing for reproducible replay
- Transit packet cadence and dropped overlay/summary packets MUST NOT change
  road-only or multimodal run-summary totals under the same seed and control
  sequence
