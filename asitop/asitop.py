import argparse
from collections import deque
import math
import subprocess
import time
from typing import Any

from dashing import HChart, HGauge, HSplit, VGauge, VSplit

from .utils import (
    clear_console,
    get_ram_metrics_dict,
    get_soc_info,
    parse_powermetrics,
    run_powermetrics_process,
)


# Constants for power limits and thresholds
ANE_MAX_POWER_WATTS = 8.0
THERMAL_PRESSURE_NOMINAL = "Nominal"
DEFAULT_RESTART_INTERVAL = 300
MAX_CHART_POINTS = 200
DEFAULT_NICE_PRIORITY = 10
DEFAULT_INTERVAL_SECONDS = 1.0
DEFAULT_AVG_WINDOW_SECONDS = 30
DEFAULT_COLOR_SCHEME = 2
MIN_SAMPLE_INTERVAL_MS = 100
MAX_P_CORES_SINGLE_ROW = 8
MIN_P_CORES_ABBREVIATED = 6


def calculate_gpu_usage(
    gpu_metrics: dict[str, Any],
    gpu_power_watts: float,
    gpu_max_power: float,
    last_gpu_freq_mhz: int | None,
) -> tuple[int, int | None]:
    """Derive GPU utilization percentage and frequency with power-based fallback."""
    freq_mhz = int(gpu_metrics.get("freq_MHz", 0) or 0)
    active_percent = int(gpu_metrics.get("active", 0) or 0)

    power_based_percent = 0
    if gpu_max_power > 0:
        power_based_percent = int(gpu_power_watts / gpu_max_power * 100)

    gpu_percent = active_percent if active_percent > 0 else power_based_percent
    gpu_percent = max(0, min(gpu_percent, 100))
    display_freq_mhz = freq_mhz or last_gpu_freq_mhz

    return gpu_percent, display_freq_mhz


def main() -> subprocess.Popen[bytes]:
    """Main application function for asitop performance monitor.

    Returns:
        Running powermetrics subprocess
    """
    parser = argparse.ArgumentParser(
        description="asitop: Performance monitoring CLI tool for Apple Silicon"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Display interval and sampling interval for powermetrics (seconds, float OK)",
    )
    parser.add_argument(
        "--color", type=int, default=DEFAULT_COLOR_SCHEME, help="Choose display color (0~8)"
    )
    parser.add_argument(
        "--avg",
        type=int,
        default=DEFAULT_AVG_WINDOW_SECONDS,
        help="Interval for averaged values (seconds)",
    )
    parser.add_argument("--show_cores", type=bool, default=False, help="Choose show cores mode")
    parser.add_argument(
        "--max_count", type=int, default=0, help="Max show count to restart powermetrics"
    )
    parser.add_argument(
        "--nice",
        type=int,
        default=DEFAULT_NICE_PRIORITY,
        help="nice value for powermetrics (lower is higher priority, default 10)",
    )
    args = parser.parse_args()
    print("\nASITOP - Performance monitoring CLI tool for Apple Silicon")
    print("You can update ASITOP by running `pip install asitop --upgrade`")
    print("Get help at `https://github.com/tlkh/asitop`")
    print("P.S. You are recommended to run ASITOP with `sudo asitop`\n")
    print("\n[1/3] Loading ASITOP\n")
    print("\033[?25l")

    cpu1_gauge = HGauge(title="E-CPU Usage", val=0, color=args.color)
    cpu2_gauge = HGauge(title="P-CPU Usage", val=0, color=args.color)
    gpu_gauge = HGauge(title="GPU Usage", val=0, color=args.color)
    ane_gauge = HGauge(title="ANE", val=0, color=args.color)
    gpu_ane_gauges = [gpu_gauge, ane_gauge]

    soc_info_dict = get_soc_info()
    e_core_count = soc_info_dict["e_core_count"]
    e_core_gauges = [
        VGauge(val=0, color=args.color, border_color=args.color) for _ in range(e_core_count)
    ]
    p_core_count = soc_info_dict["p_core_count"]
    p_core_gauges = [
        VGauge(val=0, color=args.color, border_color=args.color)
        for _ in range(min(p_core_count, MAX_P_CORES_SINGLE_ROW))
    ]
    p_core_split = [
        HSplit(
            *p_core_gauges,
        )
    ]
    if p_core_count > MAX_P_CORES_SINGLE_ROW:
        p_core_gauges_ext = [
            VGauge(val=0, color=args.color, border_color=args.color)
            for _ in range(p_core_count - MAX_P_CORES_SINGLE_ROW)
        ]
        p_core_split.append(
            HSplit(
                *p_core_gauges_ext,
            )
        )
    processor_gauges = (
        [cpu1_gauge, HSplit(*e_core_gauges), cpu2_gauge, *p_core_split, *gpu_ane_gauges]
        if args.show_cores
        else [HSplit(cpu1_gauge, cpu2_gauge), HSplit(*gpu_ane_gauges)]
    )
    processor_split = VSplit(
        *processor_gauges,
        title="Processor Utilization",
        border_color=args.color,
    )

    ram_gauge = HGauge(title="RAM Usage", val=0, color=args.color)
    # Note: Bandwidth visualization removed - Apple removed memory bandwidth metrics
    # from newer powermetrics versions, making this feature non-functional
    memory_gauges = VSplit(
        ram_gauge,
        border_color=args.color,
        title="Memory",
    )

    cpu_power_chart = HChart(title="CPU Power", color=args.color, val=0)
    gpu_power_chart = HChart(title="GPU Power", color=args.color, val=0)

    # Limit chart history to prevent memory leak (HChart default is 500)
    # Reduce to MAX_CHART_POINTS (about 3-5 minutes of data at 1s interval)
    cpu_power_chart.datapoints = deque(cpu_power_chart.datapoints, maxlen=MAX_CHART_POINTS)
    gpu_power_chart.datapoints = deque(gpu_power_chart.datapoints, maxlen=MAX_CHART_POINTS)
    power_charts = (
        VSplit(
            cpu_power_chart,
            gpu_power_chart,
            title="Power Chart",
            border_color=args.color,
        )
        if args.show_cores
        else HSplit(
            cpu_power_chart,
            gpu_power_chart,
            title="Power Chart",
            border_color=args.color,
        )
    )

    ui = (
        HSplit(
            processor_split,
            VSplit(
                memory_gauges,
                power_charts,
            ),
        )
        if args.show_cores
        else VSplit(
            processor_split,
            memory_gauges,
            power_charts,
        )
    )

    usage_gauges = ui.items[0]
    # bw_gauges = memory_gauges.items[1]

    cpu_title = (
        f"{soc_info_dict['name']} "
        f"(cores: {soc_info_dict['e_core_count']}E+"
        f"{soc_info_dict['p_core_count']}P+"
        f"{soc_info_dict['gpu_core_count']}GPU)"
    )
    usage_gauges.title = cpu_title
    cpu_max_power = soc_info_dict["cpu_max_power"]
    gpu_max_power = soc_info_dict["gpu_max_power"]

    cpu_peak_power = 0
    gpu_peak_power = 0
    package_peak_power = 0
    last_gpu_freq_mhz: int | None = None

    print("\n[2/3] Starting powermetrics process\n")

    timecode = str(int(time.time()))

    sample_ms = max(MIN_SAMPLE_INTERVAL_MS, int(args.interval * 1000))
    powermetrics_process = run_powermetrics_process(timecode, interval=sample_ms, nice=args.nice)

    print("\n[3/3] Waiting for first reading...\n")

    def get_reading(wait: float = 0.1) -> tuple[dict[str, Any], dict[str, Any], str, None, int]:
        ready = parse_powermetrics(timecode=timecode)
        while not ready:
            time.sleep(wait)
            ready = parse_powermetrics(timecode=timecode)
        return ready

    ready = get_reading()
    last_timestamp = ready[-1]

    def get_avg(inlist: deque[float]) -> float:
        return sum(inlist) / len(inlist)

    avg_package_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))
    avg_cpu_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))
    avg_gpu_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))

    clear_console()

    count = 0
    # Restart powermetrics periodically to prevent unbounded file growth
    # If user hasn't set max_count, default to restarting every DEFAULT_RESTART_INTERVAL iterations
    restart_interval = args.max_count if args.max_count > 0 else DEFAULT_RESTART_INTERVAL

    try:
        while True:
            if count >= restart_interval:
                count = 0
                powermetrics_process.terminate()
                timecode = str(int(time.time()))
                powermetrics_process = run_powermetrics_process(
                    timecode,
                    interval=max(MIN_SAMPLE_INTERVAL_MS, int(args.interval * 1000)),
                    nice=args.nice,
                )
            count += 1
            ready_result = parse_powermetrics(timecode=timecode)
            if ready_result is not False:
                ready = ready_result
                (
                    cpu_metrics_dict,
                    gpu_metrics_dict,
                    thermal_pressure,
                    _bandwidth_metrics,
                    timestamp,
                ) = ready

                if timestamp > last_timestamp:
                    last_timestamp = timestamp

                    if thermal_pressure == THERMAL_PRESSURE_NOMINAL:
                        thermal_throttle = "no"
                    else:
                        thermal_throttle = "yes"

                    cpu1_gauge.title = (
                        f"E-CPU Usage: {cpu_metrics_dict['E-Cluster_active']}% @ "
                        f"{cpu_metrics_dict['E-Cluster_freq_Mhz']} MHz"
                    )
                    cpu1_gauge.value = cpu_metrics_dict["E-Cluster_active"]

                    cpu2_gauge.title = (
                        f"P-CPU Usage: {cpu_metrics_dict['P-Cluster_active']}% @ "
                        f"{cpu_metrics_dict['P-Cluster_freq_Mhz']} MHz"
                    )
                    cpu2_gauge.value = cpu_metrics_dict["P-Cluster_active"]

                    if args.show_cores:
                        for core_count, i in enumerate(cpu_metrics_dict["e_core"]):
                            e_core_gauges[core_count % 4].title = (
                                f"Core-{i + 1} {cpu_metrics_dict[f'E-Cluster{i}_active']}%"
                            )
                            e_core_gauges[core_count % 4].value = cpu_metrics_dict[
                                f"E-Cluster{i}_active"
                            ]
                        for core_count, i in enumerate(cpu_metrics_dict["p_core"]):
                            core_gauges = (
                                p_core_gauges
                                if core_count < MAX_P_CORES_SINGLE_ROW
                                else p_core_gauges_ext
                            )
                            prefix = "Core-" if p_core_count < MIN_P_CORES_ABBREVIATED else "C-"
                            gauge_idx = core_count % MAX_P_CORES_SINGLE_ROW
                            core_key = f"P-Cluster{i}_active"
                            core_gauges[gauge_idx].title = (
                                f"{prefix}{i + 1} {cpu_metrics_dict[core_key]}%"
                            )
                            core_gauges[gauge_idx].value = cpu_metrics_dict[core_key]

                    gpu_power_w = cpu_metrics_dict["gpu_W"] / args.interval
                    gpu_util_percent, gpu_freq_mhz = calculate_gpu_usage(
                        gpu_metrics_dict, gpu_power_w, gpu_max_power, last_gpu_freq_mhz
                    )
                    last_gpu_freq_mhz = (
                        gpu_freq_mhz if gpu_freq_mhz is not None else last_gpu_freq_mhz
                    )

                    gpu_freq_display = gpu_freq_mhz if gpu_freq_mhz is not None else "N/A"
                    gpu_gauge.title = f"GPU Usage: {gpu_util_percent}% @ {gpu_freq_display} MHz"
                    gpu_gauge.value = gpu_util_percent

                    ane_util_percent = int(
                        cpu_metrics_dict["ane_W"] / args.interval / ANE_MAX_POWER_WATTS * 100
                    )
                    ane_power = cpu_metrics_dict["ane_W"] / args.interval
                    ane_gauge.title = f"ANE Usage: {ane_util_percent}% @ {ane_power:.1f} W"
                    ane_gauge.value = ane_util_percent

                    ram_metrics_dict = get_ram_metrics_dict()

                    swap_total = ram_metrics_dict["swap_total_GB"]
                    if swap_total is not None and swap_total < 0.1:
                        ram_gauge.title = (
                            f"RAM Usage: {ram_metrics_dict['used_GB']}/"
                            f"{ram_metrics_dict['total_GB']}GB - swap inactive"
                        )
                    else:
                        ram_gauge.title = (
                            f"RAM Usage: {ram_metrics_dict['used_GB']}/"
                            f"{ram_metrics_dict['total_GB']}GB - swap:"
                            f"{ram_metrics_dict['swap_used_GB']}/"
                            f"{ram_metrics_dict['swap_total_GB']}GB"
                        )
                    ram_gauge.value = ram_metrics_dict["free_percent"]

                    package_power_w = cpu_metrics_dict["package_W"] / args.interval
                    package_peak_power = max(package_peak_power, package_power_w)
                    avg_package_power_list.append(package_power_w)
                    avg_package_power = get_avg(avg_package_power_list)
                    power_charts.title = (
                        f"CPU+GPU+ANE Power: {package_power_w:.2f}W "
                        f"(avg: {avg_package_power:.2f}W peak: {package_peak_power:.2f}W) "
                        f"throttle: {thermal_throttle}"
                    )

                    cpu_power_percent = int(
                        cpu_metrics_dict["cpu_W"] / args.interval / cpu_max_power * 100
                    )
                    cpu_power_w = cpu_metrics_dict["cpu_W"] / args.interval
                    cpu_peak_power = max(cpu_peak_power, cpu_power_w)
                    avg_cpu_power_list.append(cpu_power_w)
                    avg_cpu_power = get_avg(avg_cpu_power_list)
                    cpu_power_chart.title = (
                        f"CPU: {cpu_power_w:.2f}W "
                        f"(avg: {avg_cpu_power:.2f}W peak: {cpu_peak_power:.2f}W)"
                    )
                    cpu_power_chart.append(cpu_power_percent)

                    gpu_power_percent = (
                        cpu_metrics_dict["gpu_W"] / args.interval / gpu_max_power * 100
                    )
                    gpu_power_w = cpu_metrics_dict["gpu_W"] / args.interval
                    # Some powermetrics versions omit GPU energy in the processor sampler.
                    # If we have no rail reading, estimate power from utilization so the chart
                    # still shows activity.
                    if gpu_power_w <= 0 and gpu_util_percent > 0:
                        gpu_power_w = gpu_util_percent / 100 * gpu_max_power
                        gpu_power_percent = gpu_power_w / gpu_max_power * 100
                    # Avoid rounding tiny non-zero power to 0% which hides the chart
                    if 0 < gpu_power_percent < 1:
                        gpu_power_percent = 1
                    gpu_power_percent = min(100, max(0, math.ceil(gpu_power_percent)))
                    gpu_peak_power = max(gpu_peak_power, gpu_power_w)
                    avg_gpu_power_list.append(gpu_power_w)
                    avg_gpu_power = get_avg(avg_gpu_power_list)
                    gpu_power_chart.title = (
                        f"GPU: {gpu_power_w:.2f}W "
                        f"(avg: {avg_gpu_power:.2f}W peak: {gpu_peak_power:.2f}W)"
                    )
                    gpu_power_chart.append(gpu_power_percent)

            # Refresh UI and wait for the next interval (match powermetrics cadence)
            ui.display()
            time.sleep(max(0.05, args.interval))

    except KeyboardInterrupt:
        print("Stopping...")
        print("\033[?25h")

    return powermetrics_process


if __name__ == "__main__":
    powermetrics_process = main()
    try:
        powermetrics_process.terminate()
        print("Successfully terminated powermetrics process")
    except Exception as e:
        print(e)
        powermetrics_process.terminate()
        print("Successfully terminated powermetrics process")
