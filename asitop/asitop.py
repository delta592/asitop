import argparse
import subprocess
import time
from collections import deque

from dashing import HChart, HGauge, HSplit, VGauge, VSplit

from .utils import (
    clear_console,
    get_ram_metrics_dict,
    get_soc_info,
    parse_powermetrics,
    run_powermetrics_process,
)


def main() -> subprocess.Popen:
    """Main application function for asitop performance monitor.

    Returns:
        Running powermetrics subprocess
    """
    parser = argparse.ArgumentParser(
        description="asitop: Performance monitoring CLI tool for Apple Silicon"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Display interval and sampling interval for powermetrics (seconds)",
    )
    parser.add_argument("--color", type=int, default=2, help="Choose display color (0~8)")
    parser.add_argument(
        "--avg", type=int, default=30, help="Interval for averaged values (seconds)"
    )
    parser.add_argument("--show_cores", type=bool, default=False, help="Choose show cores mode")
    parser.add_argument(
        "--max_count", type=int, default=0, help="Max show count to restart powermetrics"
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
        for _ in range(min(p_core_count, 8))
    ]
    p_core_split = [
        HSplit(
            *p_core_gauges,
        )
    ]
    if p_core_count > 8:
        p_core_gauges_ext = [
            VGauge(val=0, color=args.color, border_color=args.color)
            for _ in range(p_core_count - 8)
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
    """
    ecpu_bw_gauge = HGauge(title="E-CPU B/W", val=50, color=args.color)
    pcpu_bw_gauge = HGauge(title="P-CPU B/W", val=50, color=args.color)
    gpu_bw_gauge = HGauge(title="GPU B/W", val=50, color=args.color)
    media_bw_gauge = HGauge(title="Media B/W", val=50, color=args.color)
    bw_gauges = [HSplit(
        ecpu_bw_gauge,
        pcpu_bw_gauge,
    ),
        HSplit(
            gpu_bw_gauge,
            media_bw_gauge,
        )] if args.show_cores else [
        HSplit(
            ecpu_bw_gauge,
            pcpu_bw_gauge,
            gpu_bw_gauge,
            media_bw_gauge,
        )]
    """
    memory_gauges = VSplit(
        ram_gauge,
        # *bw_gauges,
        border_color=args.color,
        title="Memory",
    )

    cpu_power_chart = HChart(title="CPU Power", color=args.color, val=0)
    gpu_power_chart = HChart(title="GPU Power", color=args.color, val=0)

    # Limit chart history to prevent memory leak (HChart default is 500)
    # Reduce to 200 points (about 3-5 minutes of data at 1s interval)
    max_chart_points = 200
    cpu_power_chart.datapoints = deque(cpu_power_chart.datapoints, maxlen=max_chart_points)
    gpu_power_chart.datapoints = deque(gpu_power_chart.datapoints, maxlen=max_chart_points)
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
    ane_max_power = 8.0
    """max_cpu_bw = soc_info_dict["cpu_max_bw"]
    max_gpu_bw = soc_info_dict["gpu_max_bw"]
    max_media_bw = 7.0"""

    cpu_peak_power = 0
    gpu_peak_power = 0
    package_peak_power = 0

    print("\n[2/3] Starting powermetrics process\n")

    timecode = str(int(time.time()))

    powermetrics_process = run_powermetrics_process(timecode, interval=args.interval * 1000)

    print("\n[3/3] Waiting for first reading...\n")

    def get_reading(wait=0.1):
        ready = parse_powermetrics(timecode=timecode)
        while not ready:
            time.sleep(wait)
            ready = parse_powermetrics(timecode=timecode)
        return ready

    ready = get_reading()
    last_timestamp = ready[-1]

    def get_avg(inlist):
        avg = sum(inlist) / len(inlist)
        return avg

    avg_package_power_list = deque([], maxlen=int(args.avg / args.interval))
    avg_cpu_power_list = deque([], maxlen=int(args.avg / args.interval))
    avg_gpu_power_list = deque([], maxlen=int(args.avg / args.interval))

    clear_console()

    count = 0
    # Restart powermetrics periodically to prevent unbounded file growth
    # If user hasn't set max_count, default to restarting every 300 iterations
    restart_interval = args.max_count if args.max_count > 0 else 300

    # Track wall-clock time for consistent 2-second refresh
    display_interval = 2.0  # Fixed 2 second wall-clock refresh
    next_display_time = time.time() + display_interval

    try:
        while True:
            if count >= restart_interval:
                count = 0
                powermetrics_process.terminate()
                timecode = str(int(time.time()))
                powermetrics_process = run_powermetrics_process(
                    timecode, interval=args.interval * 1000
                )
            count += 1
            ready = parse_powermetrics(timecode=timecode)
            if ready is not False:
                (
                    cpu_metrics_dict,
                    gpu_metrics_dict,
                    thermal_pressure,
                    _bandwidth_metrics,
                    timestamp,
                ) = ready

                if timestamp > last_timestamp:
                    last_timestamp = timestamp

                    if thermal_pressure == "Nominal":
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
                            core_gauges = p_core_gauges if core_count < 8 else p_core_gauges_ext
                            prefix = "Core-" if p_core_count < 6 else "C-"
                            core_gauges[core_count % 8].title = (
                                f"{prefix}{i + 1} {cpu_metrics_dict[f'P-Cluster{i}_active']}%"
                            )
                            core_gauges[core_count % 8].value = cpu_metrics_dict[
                                f"P-Cluster{i}_active"
                            ]

                    gpu_gauge.title = (
                        f"GPU Usage: {gpu_metrics_dict['active']}% @ "
                        f"{gpu_metrics_dict['freq_MHz']} MHz"
                    )
                    gpu_gauge.value = gpu_metrics_dict["active"]

                    ane_util_percent = int(
                        cpu_metrics_dict["ane_W"] / args.interval / ane_max_power * 100
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

                    """

                    ecpu_bw_percent = int(
                        (bandwidth_metrics["ECPU DCS RD"] + bandwidth_metrics[
                            "ECPU DCS WR"]) / args.interval / max_cpu_bw * 100)
                    ecpu_read_GB = bandwidth_metrics["ECPU DCS RD"] / \
                                   args.interval
                    ecpu_write_GB = bandwidth_metrics["ECPU DCS WR"] / \
                                    args.interval
                    ecpu_bw_gauge.title = "".join([
                        "E-CPU: ",
                        '{0:.1f}'.format(ecpu_read_GB + ecpu_write_GB),
                        "GB/s"
                    ])
                    ecpu_bw_gauge.value = ecpu_bw_percent

                    pcpu_bw_percent = int(
                        (bandwidth_metrics["PCPU DCS RD"] + bandwidth_metrics[
                            "PCPU DCS WR"]) / args.interval / max_cpu_bw * 100)
                    pcpu_read_GB = bandwidth_metrics["PCPU DCS RD"] / \
                                   args.interval
                    pcpu_write_GB = bandwidth_metrics["PCPU DCS WR"] / \
                                    args.interval
                    pcpu_bw_gauge.title = "".join([
                        "P-CPU: ",
                        '{0:.1f}'.format(pcpu_read_GB + pcpu_write_GB),
                        "GB/s"
                    ])
                    pcpu_bw_gauge.value = pcpu_bw_percent

                    gpu_bw_total = bandwidth_metrics["GFX DCS RD"] + bandwidth_metrics["GFX DCS WR"]
                    gpu_bw_percent = int(gpu_bw_total / max_gpu_bw * 100)
                    gpu_read_GB = bandwidth_metrics["GFX DCS RD"]
                    gpu_write_GB = bandwidth_metrics["GFX DCS WR"]
                    gpu_bw_gauge.title = "".join([
                        "GPU: ",
                        '{0:.1f}'.format(gpu_read_GB + gpu_write_GB),
                        "GB/s"
                    ])
                    gpu_bw_gauge.value = gpu_bw_percent

                    media_bw_percent = int(
                        bandwidth_metrics["MEDIA DCS"] / args.interval / max_media_bw * 100)
                    media_bw_gauge.title = "".join([
                        "Media: ",
                        '{0:.1f}'.format(
                            bandwidth_metrics["MEDIA DCS"] / args.interval),
                        "GB/s"
                    ])
                    media_bw_gauge.value = media_bw_percent

                    total_bw = bandwidth_metrics["DCS RD"] + bandwidth_metrics["DCS WR"]
                    total_bw_gb = total_bw / args.interval
                    bw_gauges.title = "".join([
                        "Memory Bandwidth: ",
                        '{0:.2f}'.format(total_bw_gb),
                        " GB/s (R:",
                        '{0:.2f}'.format(
                            bandwidth_metrics["DCS RD"] / args.interval),
                        "/W:",
                        '{0:.2f}'.format(
                            bandwidth_metrics["DCS WR"] / args.interval),
                        " GB/s)"
                    ])
                    if args.show_cores:
                        bw_gauges_ext = memory_gauges.items[2]
                        bw_gauges_ext.title = "Memory Bandwidth:"
                    """

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

                    gpu_power_percent = int(
                        cpu_metrics_dict["gpu_W"] / args.interval / gpu_max_power * 100
                    )
                    gpu_power_w = cpu_metrics_dict["gpu_W"] / args.interval
                    gpu_peak_power = max(gpu_peak_power, gpu_power_w)
                    avg_gpu_power_list.append(gpu_power_w)
                    avg_gpu_power = get_avg(avg_gpu_power_list)
                    gpu_power_chart.title = (
                        f"GPU: {gpu_power_w:.2f}W "
                        f"(avg: {avg_gpu_power:.2f}W peak: {gpu_peak_power:.2f}W)"
                    )
                    gpu_power_chart.append(gpu_power_percent)

                    # Only update display at fixed wall-clock intervals
                    current_time = time.time()
                    if current_time >= next_display_time:
                        ui.display()
                        next_display_time = current_time + display_interval

            # Sleep briefly to avoid busy-waiting
            time.sleep(0.1)

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
