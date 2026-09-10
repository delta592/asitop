from typing import Any, Literal, TypedDict, cast

# Type alias for improved readability (Python 3.12+)
type PowermetricsDict = dict[str, Any]
type BandwidthMetrics = dict[str, float]
# CPUMetrics uses Any because it contains heterogeneous types that would require
# complex TypedDict to represent accurately. This is a pragmatic trade-off.
type CPUMetrics = dict[str, Any]


class BandwidthCounterMetric(TypedDict):
    """One bandwidth_counters row from powermetrics plist."""

    name: str
    value: float | int


class GpuMetricsOut(TypedDict):
    """Structured output of parse_gpu_metrics (fixed keys)."""

    freq_MHz: int
    active: int


def _freq_mhz_from_hz_and_dvfm(
    raw_freq_hz: float | None,
    dvfm_states: list[dict[str, Any]] | None,
) -> int:
    """Normalize cluster/GPU frequency to MHz; derive from DVFM when freq_hz is zero."""
    try:
        freq_value = float(raw_freq_hz or 0)
    except (TypeError, ValueError):
        freq_value = 0.0

    match freq_value:
        case freq if freq > 1e5:
            freq_mhz = int(freq / 1e6)
        case freq:
            freq_mhz = int(freq)

    if freq_mhz == 0 and dvfm_states:
        weighted_freq = sum(
            state.get("freq", 0) * state.get("used_ratio", 0) for state in dvfm_states
        )
        total_ratio = sum(state.get("used_ratio", 0) for state in dvfm_states)
        if total_ratio > 0:
            freq_mhz = int(weighted_freq / total_ratio)

    return freq_mhz


def _rail_watts(
    *,
    power_mw: float | None,
    energy_mj: float | None,
    elapsed_s: float,
) -> float:
    """Return average rail power in watts for the sample window."""
    if power_mw is not None:
        return float(power_mw) / 1000.0
    energy = float(energy_mj or 0)
    if elapsed_s > 0:
        return energy / 1000.0 / elapsed_s
    # Legacy powermetrics without elapsed_ns: store mJ/1000; UI divides by --interval.
    return energy / 1000.0


def display_power_watts(stored_value: float, *, instant: bool, interval: float) -> float:
    """Convert a stored rail value to watts for display."""
    if instant:
        return stored_value
    if interval > 0:
        return stored_value / interval
    return stored_value


def parse_ane_metrics(powermetrics_parse: PowermetricsDict) -> dict[str, int]:
    """Parse ANE frequency and utilization when powermetrics exposes an ANE block."""
    ane_block = powermetrics_parse.get("ane")
    if ane_block is None:
        ane_block = powermetrics_parse.get("processor", {}).get("ane")

    if not ane_block:
        return {}

    blocks: list[dict[str, Any]]
    if isinstance(ane_block, list):
        blocks = [b for b in ane_block if isinstance(b, dict)]
    elif isinstance(ane_block, dict):
        blocks = [ane_block]
    else:
        return {}

    if not blocks:
        return {}

    freq_values: list[int] = []
    active_values: list[int] = []
    for block in blocks:
        freq_mhz = _freq_mhz_from_hz_and_dvfm(
            block.get("freq_hz"),
            block.get("dvfm_states"),
        )
        if freq_mhz > 0:
            freq_values.append(freq_mhz)
        idle_ratio = block.get("idle_ratio")
        if idle_ratio is not None:
            active_values.append(max(0, min(100, int((1 - float(idle_ratio)) * 100))))

    result: dict[str, int] = {}
    if freq_values:
        result["ane_freq_MHz"] = max(freq_values)
    if active_values:
        result["ane_active"] = int(sum(active_values) / len(active_values))
    return result


def parse_extended_metrics(powermetrics_parse: PowermetricsDict) -> dict[str, Any]:
    """Parse optional extended powermetrics samplers (SFI, battery, network, disk)."""
    extended: dict[str, Any] = {}

    sfi = powermetrics_parse.get("sfi")
    if isinstance(sfi, dict):
        classes = sfi.get("sfi_classes", {})
        if isinstance(classes, dict):
            throttled = {name: value for name, value in classes.items() if value}
            if throttled:
                extended["sfi_throttle"] = throttled

    processor = powermetrics_parse.get("processor", {})
    if isinstance(processor, dict) and (zones := processor.get("cpu_power_zones_engaged")):
        try:
            zones_val = float(zones)
        except (TypeError, ValueError):
            zones_val = 0.0
        if zones_val > 0:
            extended["cpu_power_zones_engaged"] = zones_val

    battery = powermetrics_parse.get("battery")
    if isinstance(battery, dict):
        for key in ("discharge_rate", "discharge_rate_mw", "power_mw"):
            if key in battery:
                extended["battery_discharge_mw"] = battery[key]
                break

    network = powermetrics_parse.get("network")
    if isinstance(network, dict):
        extended["network"] = {
            "rx_mbps": float(network.get("ibyte_rate", 0) or 0) * 8 / 1e6,
            "tx_mbps": float(network.get("obyte_rate", 0) or 0) * 8 / 1e6,
        }

    disk = powermetrics_parse.get("disk")
    if isinstance(disk, dict):
        extended["disk"] = {
            "read_mbps": float(disk.get("rbytes_per_s", 0) or 0) / 1e6,
            "write_mbps": float(disk.get("wbytes_per_s", 0) or 0) / 1e6,
        }

    return extended


def format_extended_status(extended: dict[str, Any]) -> str:
    """Build a compact status suffix for extended powermetrics fields."""
    parts: list[str] = []
    if zones := extended.get("cpu_power_zones_engaged"):
        parts.append(f"zones:{zones:.0%}")
    if sfi := extended.get("sfi_throttle"):
        parts.append(f"SFI:{len(sfi)}")
    if discharge := extended.get("battery_discharge_mw"):
        parts.append(f"bat:{float(discharge) / 1000:.1f}W")
    if net := extended.get("network"):
        parts.append(f"net↓{net['rx_mbps']:.0f}↑{net['tx_mbps']:.0f}Mb/s")
    if disk := extended.get("disk"):
        parts.append(f"disk R{disk['read_mbps']:.0f}/W{disk['write_mbps']:.0f}MB/s")
    return " | ".join(parts)


def parse_thermal_pressure(powermetrics_parse: PowermetricsDict) -> str:
    """Parse thermal pressure from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Thermal pressure status string
    """
    return str(powermetrics_parse["thermal_pressure"])


def parse_bandwidth_metrics(powermetrics_parse: PowermetricsDict) -> BandwidthMetrics:
    """Parse memory bandwidth metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with bandwidth metrics in GB/s
    """
    bandwidth_metrics = cast(
        "list[BandwidthCounterMetric]",
        powermetrics_parse["bandwidth_counters"],
    )
    bandwidth_metrics_dict: BandwidthMetrics = {}
    data_fields = [
        "PCPU0 DCS RD",
        "PCPU0 DCS WR",
        "PCPU1 DCS RD",
        "PCPU1 DCS WR",
        "PCPU2 DCS RD",
        "PCPU2 DCS WR",
        "PCPU3 DCS RD",
        "PCPU3 DCS WR",
        "PCPU DCS RD",
        "PCPU DCS WR",
        "ECPU0 DCS RD",
        "ECPU0 DCS WR",
        "ECPU1 DCS RD",
        "ECPU1 DCS WR",
        "ECPU DCS RD",
        "ECPU DCS WR",
        "GFX DCS RD",
        "GFX DCS WR",
        "ISP DCS RD",
        "ISP DCS WR",
        "STRM CODEC DCS RD",
        "STRM CODEC DCS WR",
        "PRORES DCS RD",
        "PRORES DCS WR",
        "VDEC DCS RD",
        "VDEC DCS WR",
        "VENC0 DCS RD",
        "VENC0 DCS WR",
        "VENC1 DCS RD",
        "VENC1 DCS WR",
        "VENC2 DCS RD",
        "VENC2 DCS WR",
        "VENC3 DCS RD",
        "VENC3 DCS WR",
        "VENC DCS RD",
        "VENC DCS WR",
        "JPG0 DCS RD",
        "JPG0 DCS WR",
        "JPG1 DCS RD",
        "JPG1 DCS WR",
        "JPG2 DCS RD",
        "JPG2 DCS WR",
        "JPG3 DCS RD",
        "JPG3 DCS WR",
        "JPG DCS RD",
        "JPG DCS WR",
        "DCS RD",
        "DCS WR",
    ]
    for h in data_fields:
        bandwidth_metrics_dict[h] = 0
    for row in bandwidth_metrics:
        if row["name"] in data_fields:
            bandwidth_metrics_dict[row["name"]] = row["value"] / (1e9)
    bandwidth_metrics_dict["PCPU DCS RD"] = (
        bandwidth_metrics_dict["PCPU DCS RD"]
        + bandwidth_metrics_dict["PCPU0 DCS RD"]
        + bandwidth_metrics_dict["PCPU1 DCS RD"]
        + bandwidth_metrics_dict["PCPU2 DCS RD"]
        + bandwidth_metrics_dict["PCPU3 DCS RD"]
    )
    bandwidth_metrics_dict["PCPU DCS WR"] = (
        bandwidth_metrics_dict["PCPU DCS WR"]
        + bandwidth_metrics_dict["PCPU0 DCS WR"]
        + bandwidth_metrics_dict["PCPU1 DCS WR"]
        + bandwidth_metrics_dict["PCPU2 DCS WR"]
        + bandwidth_metrics_dict["PCPU3 DCS WR"]
    )
    bandwidth_metrics_dict["JPG DCS RD"] = (
        bandwidth_metrics_dict["JPG DCS RD"]
        + bandwidth_metrics_dict["JPG0 DCS RD"]
        + bandwidth_metrics_dict["JPG1 DCS RD"]
        + bandwidth_metrics_dict["JPG2 DCS RD"]
        + bandwidth_metrics_dict["JPG3 DCS RD"]
    )
    bandwidth_metrics_dict["JPG DCS WR"] = (
        bandwidth_metrics_dict["JPG DCS WR"]
        + bandwidth_metrics_dict["JPG0 DCS WR"]
        + bandwidth_metrics_dict["JPG1 DCS WR"]
        + bandwidth_metrics_dict["JPG2 DCS WR"]
        + bandwidth_metrics_dict["JPG3 DCS WR"]
    )
    bandwidth_metrics_dict["VENC DCS RD"] = (
        bandwidth_metrics_dict["VENC DCS RD"]
        + bandwidth_metrics_dict["VENC0 DCS RD"]
        + bandwidth_metrics_dict["VENC1 DCS RD"]
        + bandwidth_metrics_dict["VENC2 DCS RD"]
        + bandwidth_metrics_dict["VENC3 DCS RD"]
    )
    bandwidth_metrics_dict["VENC DCS WR"] = (
        bandwidth_metrics_dict["VENC DCS WR"]
        + bandwidth_metrics_dict["VENC0 DCS WR"]
        + bandwidth_metrics_dict["VENC1 DCS WR"]
        + bandwidth_metrics_dict["VENC2 DCS WR"]
        + bandwidth_metrics_dict["VENC3 DCS WR"]
    )
    bandwidth_metrics_dict["MEDIA DCS"] = sum(
        [
            bandwidth_metrics_dict["ISP DCS RD"],
            bandwidth_metrics_dict["ISP DCS WR"],
            bandwidth_metrics_dict["STRM CODEC DCS RD"],
            bandwidth_metrics_dict["STRM CODEC DCS WR"],
            bandwidth_metrics_dict["PRORES DCS RD"],
            bandwidth_metrics_dict["PRORES DCS WR"],
            bandwidth_metrics_dict["VDEC DCS RD"],
            bandwidth_metrics_dict["VDEC DCS WR"],
            bandwidth_metrics_dict["VENC DCS RD"],
            bandwidth_metrics_dict["VENC DCS WR"],
            bandwidth_metrics_dict["JPG DCS RD"],
            bandwidth_metrics_dict["JPG DCS WR"],
        ]
    )
    return bandwidth_metrics_dict


type ClusterRole = Literal["E", "P", "S"]


def _cluster_letter(name: str) -> str:
    """Return the powermetrics cluster-family letter (E, P, S, M, ...)."""
    if name.lower().startswith("super"):
        return "S"
    return name[0].upper() if name else "?"


def _cluster_role(name: str, *, p_is_super: bool) -> ClusterRole:
    """Map a powermetrics cluster name to E, P, or S.

    M5 Max/Ultra expose Super cores as ``S-Cluster`` (macOS 26.4+) or still as
    ``P-Cluster``, and the new Performance cores as ``M0-Cluster`` / ``M1-Cluster``.
    When M-clusters are present and no S-cluster is, treat P-clusters as Super.
    """
    letter = _cluster_letter(name)
    if letter == "E":
        return "E"
    if letter == "S":
        return "S"
    if letter == "M":
        return "P"
    if letter == "P":
        return "S" if p_is_super else "P"
    return "P"


def _apply_role_aggregates(
    cpu_metric_dict: CPUMetrics,
    role_actives: dict[ClusterRole, list[int]],
    role_freqs: dict[ClusterRole, list[int]],
    cores: dict[ClusterRole, list[int]],
) -> None:
    """Write per-role core lists and averaged cluster gauges."""
    for role in ("E", "P", "S"):
        cpu_metric_dict[f"{role.lower()}_core"] = cores[role]
        actives = role_actives[role]
        freqs = role_freqs[role]
        cpu_metric_dict[f"{role}-Cluster_active"] = (
            int(sum(actives) / len(actives)) if actives else 0
        )
        cpu_metric_dict[f"{role}-Cluster_freq_Mhz"] = max(freqs) if freqs else 0


def parse_cpu_metrics(powermetrics_parse: PowermetricsDict) -> CPUMetrics:
    """Parse CPU cluster metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with CPU frequencies, utilization, and power metrics
    """
    cpu_metrics = powermetrics_parse["processor"]
    cpu_metric_dict: CPUMetrics = {}

    elapsed_s = float(powermetrics_parse.get("elapsed_ns") or 0) / 1e9
    instant_power = "cpu_power" in cpu_metrics

    cpu_clusters = cpu_metrics["clusters"]
    letters = [_cluster_letter(cluster["name"]) for cluster in cpu_clusters]
    p_is_super = "M" in letters and "S" not in letters

    role_actives: dict[ClusterRole, list[int]] = {"E": [], "P": [], "S": []}
    role_freqs: dict[ClusterRole, list[int]] = {"E": [], "P": [], "S": []}
    cores: dict[ClusterRole, list[int]] = {"E": [], "P": [], "S": []}

    for cluster in cpu_clusters:
        cluster_name = cluster["name"]
        role = _cluster_role(cluster_name, p_is_super=p_is_super)
        prefix = f"{role}-Cluster"
        cluster_freq_mhz = _freq_mhz_from_hz_and_dvfm(
            cluster.get("freq_hz"),
            cluster.get("dvfm_states"),
        )
        cluster_active = round((1 - cluster["idle_ratio"]) * 100)
        cpu_metric_dict[f"{cluster_name}_freq_Mhz"] = cluster_freq_mhz
        cpu_metric_dict[f"{cluster_name}_active"] = cluster_active
        role_actives[role].append(cluster_active)
        role_freqs[role].append(cluster_freq_mhz)

        for cpu in cluster["cpus"]:
            cores[role].append(cpu["cpu"])
            cpu_metric_dict[f"{prefix}{cpu['cpu']}_freq_Mhz"] = _freq_mhz_from_hz_and_dvfm(
                cpu.get("freq_hz"),
                cpu.get("dvfm_states"),
            )
            cpu_metric_dict[f"{prefix}{cpu['cpu']}_active"] = round((1 - cpu["idle_ratio"]) * 100)

    _apply_role_aggregates(cpu_metric_dict, role_actives, role_freqs, cores)
    # Power: prefer instantaneous mW rails (macOS 15+/26.x); fall back to energy / elapsed.
    gpu_sampler = powermetrics_parse.get("gpu", {})
    gpu_energy_proc = cpu_metrics.get("gpu_energy")
    gpu_energy_gpu = gpu_sampler.get("gpu_energy")
    gpu_energy = gpu_energy_gpu if gpu_energy_gpu not in {None, 0} else gpu_energy_proc
    gpu_energy = gpu_energy or 0
    gpu_power_mw = gpu_sampler.get("gpu_power")
    if gpu_power_mw in {None, 0}:
        gpu_power_mw = cpu_metrics.get("gpu_power")

    cpu_metric_dict["cpu_W"] = _rail_watts(
        power_mw=cpu_metrics.get("cpu_power"),
        energy_mj=cpu_metrics.get("cpu_energy"),
        elapsed_s=elapsed_s,
    )
    cpu_metric_dict["gpu_W"] = _rail_watts(
        power_mw=gpu_power_mw,
        energy_mj=gpu_energy,
        elapsed_s=elapsed_s,
    )
    cpu_metric_dict["ane_W"] = _rail_watts(
        power_mw=cpu_metrics.get("ane_power"),
        energy_mj=cpu_metrics.get("ane_energy"),
        elapsed_s=elapsed_s,
    )
    cpu_metric_dict["package_W"] = _rail_watts(
        power_mw=cpu_metrics.get("combined_power"),
        energy_mj=None,
        elapsed_s=elapsed_s,
    )
    cpu_metric_dict["_instant_power"] = instant_power
    cpu_metric_dict.update(parse_ane_metrics(powermetrics_parse))
    return cpu_metric_dict


def parse_gpu_metrics(powermetrics_parse: PowermetricsDict) -> GpuMetricsOut:
    """Parse GPU metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with GPU frequency in MHz and utilization percentage
    """
    gpu_metrics = powermetrics_parse["gpu"]
    freq_mhz = _freq_mhz_from_hz_and_dvfm(
        gpu_metrics.get("freq_hz"),
        gpu_metrics.get("dvfm_states"),
    )

    active_percent = int((1 - gpu_metrics.get("idle_ratio", 0)) * 100)
    active_percent = max(0, min(active_percent, 100))
    return {
        "freq_MHz": freq_mhz,
        "active": active_percent,
    }
