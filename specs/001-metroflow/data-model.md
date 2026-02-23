# Data Model (draft)

## Graph
- `V`: number of nodes
- `E`: number of directed edges
- Arrays:
  - `edge_src[E]`, `edge_dst[E]`
  - `edge_length[E]`, `edge_capacity[E]`, `edge_ff_time[E]`
  - `out_ptr[V+1]`, `out_edges[E]` (CSR)

## Edge dynamic state
- `queue[E]` (vehicles)
- `flow[E]` (veh/s over dt)
- `speed[E]` (optional derived)

## Agent (active)
- `A_max`: max active agents
- arrays size `A_max`:
  - `alive[A]` bool
  - `edge_id[A]` int32
  - `progress[A]` float32 in [0,1]
  - `dest_zone[A]` int32
  - `mem_h[A,H]`, `mem_c[A,H]` (LSTM hidden/cell)
  - `pref[A,P]` (driver heterogeneity)

## Demand
- `population = 100_000`
- per person:
  - `home_zone`, `work_zone`, `type` (student/worker/etc)
  - schedule template id
- spawn buffer:
  - ring buffer of trip requests (origin_node, dest_zone, depart_minute)

