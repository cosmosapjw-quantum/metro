__all__ = [
    "SimulationInitBundle",
    "build_baseline_run_summary",
    "build_initial_simulation_state",
]


def __getattr__(name: str):
    if name in {"SimulationInitBundle", "build_initial_simulation_state"}:
        from metroflow.sim.init import SimulationInitBundle, build_initial_simulation_state

        return {
            "SimulationInitBundle": SimulationInitBundle,
            "build_initial_simulation_state": build_initial_simulation_state,
        }[name]
    if name == "build_baseline_run_summary":
        from metroflow.sim.run_summary import build_baseline_run_summary

        return build_baseline_run_summary
    raise AttributeError(name)
