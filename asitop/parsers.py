from typing import Any


def parse_thermal_pressure(powermetrics_parse: dict[str, Any]) -> str:
    """Parse thermal pressure from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Thermal pressure status string
    """
    thermal_pressure: str = powermetrics_parse["thermal_pressure"]
    return thermal_pressure


def parse_bandwidth_metrics(powermetrics_parse: dict[str, Any]) -> dict[str, float]:
    """Parse memory bandwidth metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with bandwidth metrics in GB/s
    """
    bandwidth_metrics = powermetrics_parse["bandwidth_counters"]
    bandwidth_metrics_dict: dict[str, float] = {}
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
    for metric in bandwidth_metrics:
        if metric["name"] in data_fields:
            bandwidth_metrics_dict[metric["name"]] = metric["value"] / (1e9)
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


def parse_cpu_metrics(powermetrics_parse: dict[str, Any]) -> dict[str, Any]:
    """Parse CPU cluster metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with CPU frequencies, utilization, and power metrics
    """
    e_core: list[int] = []
    p_core: list[int] = []
    cpu_metrics = powermetrics_parse["processor"]
    cpu_metric_dict: dict[str, Any] = {}

    # cpu_clusters
    cpu_clusters = cpu_metrics["clusters"]
    for cluster in cpu_clusters:
        name = cluster["name"]
        cpu_metric_dict[f"{name}_freq_Mhz"] = int(cluster["freq_hz"] / 1e6)
        cpu_metric_dict[f"{name}_active"] = round((1 - cluster["idle_ratio"]) * 100)

        for cpu in cluster["cpus"]:
            name = "E-Cluster" if name[0] == "E" else "P-Cluster"
            core = e_core if name[0] == "E" else p_core
            core.append(cpu["cpu"])
            cpu_metric_dict[f"{name}{cpu['cpu']}_freq_Mhz"] = int(cpu["freq_hz"] / 1e6)
            cpu_metric_dict[f"{name}{cpu['cpu']}_active"] = round((1 - cpu["idle_ratio"]) * 100)
    cpu_metric_dict["e_core"] = e_core
    cpu_metric_dict["p_core"] = p_core
    # Handle M1 Ultra dual E-clusters
    if "E-Cluster_active" not in cpu_metric_dict and "E0-Cluster_active" in cpu_metric_dict:
        cpu_metric_dict["E-Cluster_active"] = int(
            (cpu_metric_dict["E0-Cluster_active"] + cpu_metric_dict["E1-Cluster_active"]) / 2
        )
    if "E-Cluster_freq_Mhz" not in cpu_metric_dict and "E0-Cluster_freq_Mhz" in cpu_metric_dict:
        cpu_metric_dict["E-Cluster_freq_Mhz"] = max(
            cpu_metric_dict["E0-Cluster_freq_Mhz"], cpu_metric_dict["E1-Cluster_freq_Mhz"]
        )
    # Handle M1 Ultra quad P-clusters
    if "P-Cluster_active" not in cpu_metric_dict:
        if "P2-Cluster_active" in cpu_metric_dict:
            # M1 Ultra with 4 P-clusters
            cpu_metric_dict["P-Cluster_active"] = int(
                (
                    cpu_metric_dict["P0-Cluster_active"]
                    + cpu_metric_dict["P1-Cluster_active"]
                    + cpu_metric_dict["P2-Cluster_active"]
                    + cpu_metric_dict["P3-Cluster_active"]
                )
                / 4
            )
        elif "P0-Cluster_active" in cpu_metric_dict:
            # M1 Ultra with 2 P-clusters
            cpu_metric_dict["P-Cluster_active"] = int(
                (cpu_metric_dict["P0-Cluster_active"] + cpu_metric_dict["P1-Cluster_active"]) / 2
            )
    if "P-Cluster_freq_Mhz" not in cpu_metric_dict:
        if "P2-Cluster_freq_Mhz" in cpu_metric_dict:
            # M1 Ultra with 4 P-clusters
            freqs = [
                cpu_metric_dict["P0-Cluster_freq_Mhz"],
                cpu_metric_dict["P1-Cluster_freq_Mhz"],
                cpu_metric_dict["P2-Cluster_freq_Mhz"],
                cpu_metric_dict["P3-Cluster_freq_Mhz"],
            ]
            cpu_metric_dict["P-Cluster_freq_Mhz"] = max(freqs)
        elif "P0-Cluster_freq_Mhz" in cpu_metric_dict:
            # M1 Ultra with 2 P-clusters
            cpu_metric_dict["P-Cluster_freq_Mhz"] = max(
                cpu_metric_dict["P0-Cluster_freq_Mhz"], cpu_metric_dict["P1-Cluster_freq_Mhz"]
            )
    # power
    cpu_metric_dict["ane_W"] = cpu_metrics["ane_energy"] / 1000
    # cpu_metric_dict["dram_W"] = cpu_metrics["dram_energy"]/1000

    # powermetrics historically reports GPU rail energy under the processor sampler.
    # Newer builds also expose it in the GPU sampler. Prefer the GPU sampler when it
    # has data; otherwise fall back to the processor sampler so the GPU power chart
    # always gets a usable value.
    gpu_energy_proc = cpu_metrics.get("gpu_energy")
    gpu_energy_gpu = powermetrics_parse.get("gpu", {}).get("gpu_energy")
    gpu_energy = gpu_energy_gpu if gpu_energy_gpu not in (None, 0) else gpu_energy_proc
    gpu_energy = gpu_energy or 0

    cpu_metric_dict["cpu_W"] = cpu_metrics["cpu_energy"] / 1000
    cpu_metric_dict["gpu_W"] = gpu_energy / 1000
    cpu_metric_dict["package_W"] = cpu_metrics["combined_power"] / 1000
    return cpu_metric_dict


def parse_gpu_metrics(powermetrics_parse: dict[str, Any]) -> dict[str, int]:
    """Parse GPU metrics from powermetrics data.

    Args:
        powermetrics_parse: Parsed powermetrics plist dictionary

    Returns:
        Dictionary with GPU frequency in MHz and utilization percentage
    """
    gpu_metrics = powermetrics_parse["gpu"]
    raw_freq = gpu_metrics.get("freq_hz", 0) or 0

    try:
        freq_value = float(raw_freq)
    except (TypeError, ValueError):
        freq_value = 0.0

    # Newer powermetrics builds expose GPU frequency in MHz instead of Hz.
    # Accept either by detecting the magnitude and normalizing to MHz.
    if freq_value > 1e5:
        freq_mhz = int(freq_value / 1e6)
    else:
        freq_mhz = int(freq_value)

    # If frequency is still zero but DVFM residency is present, derive
    # an average from the residency table to avoid showing "N/A".
    if freq_mhz == 0 and "dvfm_states" in gpu_metrics:
        dvfm_states = gpu_metrics["dvfm_states"]
        weighted_freq = sum(
            state.get("freq", 0) * state.get("used_ratio", 0) for state in dvfm_states
        )
        total_ratio = sum(state.get("used_ratio", 0) for state in dvfm_states)
        if total_ratio > 0:
            freq_mhz = int(weighted_freq / total_ratio)

    active_percent = int((1 - gpu_metrics.get("idle_ratio", 0)) * 100)
    active_percent = max(0, min(active_percent, 100))
    gpu_metrics_dict = {
        "freq_MHz": freq_mhz,
        "active": active_percent,
    }
    return gpu_metrics_dict
