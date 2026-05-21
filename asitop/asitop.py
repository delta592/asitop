import argparse
from collections import deque
import math
import select
import subprocess
import sys
import termios
import time
import tty
from types import SimpleNamespace

from dashing import HChart, HGauge, HSplit, VGauge, VSplit

from .parsers import CPUMetrics, GpuMetricsOut, display_power_watts, format_extended_status
from .utils import (
    cleanup_powermetrics,
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


def check_for_quit_key() -> bool:
    """Check if 'q' key was pressed without blocking.

    Returns:
        True if 'q' was pressed, False otherwise
    """
    if select.select([sys.stdin], [], [], 0)[0]:
        char = sys.stdin.read(1)
        if char.lower() == "q":
            return True
    return False


def calculate_gpu_usage(
    gpu_metrics: GpuMetricsOut,
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


def main() -> tuple[subprocess.Popen[bytes], str]:
    """Main application function for asitop performance monitor.

    Returns:
        Tuple of (Running powermetrics subprocess, timecode for temp file)
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
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Enable extra powermetrics samplers (SFI, battery, network, disk)",
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

    cpu_title = (
        f"{soc_info_dict['name']} "
        f"(cores: {soc_info_dict['e_core_count']}E+"
        f"{soc_info_dict['p_core_count']}P+"
        f"{soc_info_dict['gpu_core_count']}GPU)"
    )
    usage_gauges.title = cpu_title
    cpu_max_power = soc_info_dict["cpu_max_power"]
    gpu_max_power = soc_info_dict["gpu_max_power"]

    cpu_peak_power = 0.0
    gpu_peak_power = 0.0
    package_peak_power = 0.0
    last_gpu_freq_mhz: int | None = None

    print("\n[2/3] Starting powermetrics process\n")

    timecode = str(int(time.time()))

    sample_ms = max(MIN_SAMPLE_INTERVAL_MS, int(args.interval * 1000))
    powermetrics_process = run_powermetrics_process(
        timecode, interval=sample_ms, nice=args.nice, extended=args.extended
    )

    print("\n[3/3] Waiting for first reading...\n")

    def get_reading(
        wait: float = 0.1,
    ) -> tuple[CPUMetrics, GpuMetricsOut, str, None, int, dict[str, object]]:
        ready = parse_powermetrics(timecode=timecode)
        while not ready:
            time.sleep(wait)
            ready = parse_powermetrics(timecode=timecode)
        return ready

    ready = get_reading()
    last_timestamp = ready[4]

    def get_avg(inlist: deque[float]) -> float:
        return sum(inlist) / len(inlist)

    avg_package_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))
    avg_cpu_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))
    avg_gpu_power_list: deque[float] = deque(maxlen=int(args.avg / args.interval))

    clear_console()

    # Restart powermetrics periodically to prevent unbounded file growth
    # If user hasn't set max_count, default to restarting every DEFAULT_RESTART_INTERVAL iterations
    restart_interval = args.max_count if args.max_count > 0 else DEFAULT_RESTART_INTERVAL

    # Set terminal to raw mode for non-blocking keyboard input (if stdin is a TTY)
    old_settings = None
    keyboard_enabled = sys.stdin.isatty()
    if keyboard_enabled:
        old_settings = termios.tcgetattr(sys.stdin)

    loop = SimpleNamespace(
        count=0,
        timecode=timecode,
        powermetrics_process=powermetrics_process,
        last_timestamp=last_timestamp,
        last_gpu_freq_mhz=last_gpu_freq_mhz,
        cpu_peak_power=cpu_peak_power,
        gpu_peak_power=gpu_peak_power,
        package_peak_power=package_peak_power,
    )

    def run_display_loop() -> tuple[subprocess.Popen[bytes], str]:
        """Run the display refresh loop until quit."""
        while True:
            # Check if 'q' key was pressed (only when keyboard is enabled)
            if keyboard_enabled and check_for_quit_key():
                print("\nExiting asitop...")
                break
            if loop.count >= restart_interval:
                loop.count = 0
                loop.powermetrics_process.terminate()
                loop.timecode = str(int(time.time()))
                loop.powermetrics_process = run_powermetrics_process(
                    loop.timecode,
                    interval=max(MIN_SAMPLE_INTERVAL_MS, int(args.interval * 1000)),
                    nice=args.nice,
                    extended=args.extended,
                )
            loop.count += 1
            ready_result = parse_powermetrics(timecode=loop.timecode)
            if ready_result is not False:
                ready = ready_result
                (
                    cpu_metrics_dict,
                    gpu_metrics_dict,
                    thermal_pressure,
                    _bandwidth_metrics,
                    timestamp,
                    extended_metrics,
                ) = ready

                if timestamp > loop.last_timestamp:
                    loop.last_timestamp = timestamp
                    instant_power = bool(cpu_metrics_dict.get("_instant_power"))

                    if thermal_pressure == THERMAL_PRESSURE_NOMINAL:
                        thermal_throttle = "no"
                    else:
                        thermal_throttle = "yes"

                    cpu1_gauge.title = (
                        f"E-CPU Usage: {cpu_metrics_dict['E-Cluster_active']}% @ "
                        f"{cpu_metrics_dict['E-Cluster_freq_Mhz']} MHz"
                    )
                    cpu1_gauge.value = int(cpu_metrics_dict["E-Cluster_active"])

                    cpu2_gauge.title = (
                        f"P-CPU Usage: {cpu_metrics_dict['P-Cluster_active']}% @ "
                        f"{cpu_metrics_dict['P-Cluster_freq_Mhz']} MHz"
                    )
                    cpu2_gauge.value = int(cpu_metrics_dict["P-Cluster_active"])

                    if args.show_cores:
                        for core_count, i in enumerate(cpu_metrics_dict["e_core"]):
                            e_core_gauges[core_count % 4].title = (
                                f"Core-{i + 1} {cpu_metrics_dict[f'E-Cluster{i}_active']}%"
                            )
                            e_core_gauges[core_count % 4].value = int(
                                cpu_metrics_dict[f"E-Cluster{i}_active"]
                            )
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
                            core_gauges[gauge_idx].value = int(cpu_metrics_dict[core_key])

                    gpu_power_w = display_power_watts(
                        cpu_metrics_dict["gpu_W"],
                        instant=instant_power,
                        interval=args.interval,
                    )
                    gpu_util_percent, gpu_freq_mhz = calculate_gpu_usage(
                        gpu_metrics_dict,
                        gpu_power_w,
                        gpu_max_power,
                        loop.last_gpu_freq_mhz,
                    )
                    loop.last_gpu_freq_mhz = (
                        gpu_freq_mhz if gpu_freq_mhz is not None else loop.last_gpu_freq_mhz
                    )

                    gpu_freq_display = gpu_freq_mhz if gpu_freq_mhz is not None else "N/A"
                    gpu_gauge.title = f"GPU Usage: {gpu_util_percent}% @ {gpu_freq_display} MHz"
                    gpu_gauge.value = gpu_util_percent

                    ane_power = display_power_watts(
                        cpu_metrics_dict["ane_W"],
                        instant=instant_power,
                        interval=args.interval,
                    )
                    ane_active = cpu_metrics_dict.get("ane_active")
                    if ane_active is not None and ane_active > 0:
                        ane_util_percent = int(ane_active)
                    else:
                        ane_util_percent = int(ane_power / ANE_MAX_POWER_WATTS * 100)
                    ane_util_percent = max(0, min(ane_util_percent, 100))
                    ane_freq = cpu_metrics_dict.get("ane_freq_MHz")
                    if ane_freq:
                        ane_gauge.title = (
                            f"ANE Usage: {ane_util_percent}% @ {ane_power:.1f} W, {ane_freq} MHz"
                        )
                    else:
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
                    # Type assertion: free_percent is always int, not float
                    ram_gauge.value = int(ram_metrics_dict["free_percent"])

                    package_power_w = display_power_watts(
                        cpu_metrics_dict["package_W"],
                        instant=instant_power,
                        interval=args.interval,
                    )
                    loop.package_peak_power = max(loop.package_peak_power, package_power_w)
                    avg_package_power_list.append(package_power_w)
                    avg_package_power = get_avg(avg_package_power_list)
                    power_title = (
                        f"CPU+GPU+ANE Power: {package_power_w:.2f}W "
                        f"(avg: {avg_package_power:.2f}W peak: {loop.package_peak_power:.2f}W) "
                        f"throttle: {thermal_throttle}"
                    )
                    if extended_status := format_extended_status(extended_metrics):
                        power_title = f"{power_title} | {extended_status}"
                    power_charts.title = power_title

                    cpu_power_w = display_power_watts(
                        cpu_metrics_dict["cpu_W"],
                        instant=instant_power,
                        interval=args.interval,
                    )
                    cpu_power_percent = int(cpu_power_w / cpu_max_power * 100)
                    loop.cpu_peak_power = max(loop.cpu_peak_power, cpu_power_w)
                    avg_cpu_power_list.append(cpu_power_w)
                    avg_cpu_power = get_avg(avg_cpu_power_list)
                    cpu_power_chart.title = (
                        f"CPU: {cpu_power_w:.2f}W "
                        f"(avg: {avg_cpu_power:.2f}W peak: {loop.cpu_peak_power:.2f}W)"
                    )
                    cpu_power_chart.append(cpu_power_percent)

                    gpu_power_percent = int(gpu_power_w / gpu_max_power * 100)
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
                    loop.gpu_peak_power = max(loop.gpu_peak_power, gpu_power_w)
                    avg_gpu_power_list.append(gpu_power_w)
                    avg_gpu_power = get_avg(avg_gpu_power_list)
                    gpu_power_chart.title = (
                        f"GPU: {gpu_power_w:.2f}W "
                        f"(avg: {avg_gpu_power:.2f}W peak: {loop.gpu_peak_power:.2f}W)"
                    )
                    gpu_power_chart.append(gpu_power_percent)

            # Refresh UI and wait for the next interval (match powermetrics cadence)
            ui.display()
            time.sleep(max(0.05, args.interval))
        return loop.powermetrics_process, loop.timecode

    try:
        if keyboard_enabled:
            tty.setcbreak(sys.stdin.fileno())
        powermetrics_process, timecode = run_display_loop()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        # Restore terminal settings (if they were changed)
        if old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print("\033[?25h")

    return powermetrics_process, timecode


if __name__ == "__main__":
    powermetrics_process, timecode = main()
    cleanup_powermetrics(powermetrics_process, timecode)
    sys.exit(0)
