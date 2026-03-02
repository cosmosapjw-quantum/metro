__all__ = [
    "SimulationInitBundle",
    "build_baseline_run_summary",
    "build_run_summary_comparison",
    "format_run_summary_comparison_markdown",
    "run_summary_comparison_deltas_core",
    "build_initial_simulation_state",
]


def __getattr__(name: str):
    if name in {"SimulationInitBundle", "build_initial_simulation_state"}:
        from metroflow.sim.init import SimulationInitBundle, build_initial_simulation_state

        return {
            "SimulationInitBundle": SimulationInitBundle,
            "build_initial_simulation_state": build_initial_simulation_state,
        }[name]
    if name in {
        "build_baseline_run_summary",
        "build_run_summary_comparison",
        "format_run_summary_comparison_markdown",
        "run_summary_comparison_deltas_core",
    }:
        from metroflow.sim.run_summary import (
            build_baseline_run_summary,
            build_run_summary_comparison,
            format_run_summary_comparison_markdown,
            run_summary_comparison_deltas_core,
        )

        return {
            "build_baseline_run_summary": build_baseline_run_summary,
            "build_run_summary_comparison": build_run_summary_comparison,
            "format_run_summary_comparison_markdown": format_run_summary_comparison_markdown,
            "run_summary_comparison_deltas_core": run_summary_comparison_deltas_core,
        }[name]
    raise AttributeError(name)
