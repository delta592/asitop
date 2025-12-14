import glob
import os
import plistlib
import subprocess
from subprocess import PIPE
from typing import Any, Literal

import psutil

from .parsers import (
    parse_cpu_metrics,
    parse_gpu_metrics,
    parse_thermal_pressure,
)

# SOC specifications database for Apple Silicon chips
# Power values in Watts, Bandwidth in GB/s
SOC_SPECS = {
    "Apple M1": {
        "cpu_max_power": 20,
        "gpu_max_power": 20,
        "cpu_max_bw": 70,
        "gpu_max_bw": 70,
    },
    "Apple M1 Pro": {
        "cpu_max_power": 30,
        "gpu_max_power": 30,
        "cpu_max_bw": 200,
        "gpu_max_bw": 200,
    },
    "Apple M1 Max": {
        "cpu_max_power": 30,
        "gpu_max_power": 60,
        "cpu_max_bw": 250,
        "gpu_max_bw": 400,
    },
    "Apple M1 Ultra": {
        "cpu_max_power": 60,
        "gpu_max_power": 120,
        "cpu_max_bw": 500,
        "gpu_max_bw": 800,
    },
    "Apple M2": {
        "cpu_max_power": 25,
        "gpu_max_power": 15,
        "cpu_max_bw": 100,
        "gpu_max_bw": 100,
    },
    "Apple M2 Pro": {
        "cpu_max_power": 30,
        "gpu_max_power": 35,
        "cpu_max_bw": 200,
        "gpu_max_bw": 200,
    },
    "Apple M2 Max": {
        "cpu_max_power": 30,
        "gpu_max_power": 65,
        "cpu_max_bw": 400,
        "gpu_max_bw": 400,
    },
    "Apple M2 Ultra": {
        "cpu_max_power": 60,
        "gpu_max_power": 130,
        "cpu_max_bw": 800,
        "gpu_max_bw": 800,
    },
    "Apple M3": {
        "cpu_max_power": 22,
        "gpu_max_power": 18,
        "cpu_max_bw": 100,
        "gpu_max_bw": 100,
    },
    "Apple M3 Pro": {
        "cpu_max_power": 35,
        "gpu_max_power": 40,
        "cpu_max_bw": 150,
        "gpu_max_bw": 150,
    },
    "Apple M3 Max": {
        "cpu_max_power": 40,
        "gpu_max_power": 70,
        "cpu_max_bw": 300,
        "gpu_max_bw": 400,
    },
    "Apple M3 Ultra": {
        "cpu_max_power": 80,
        "gpu_max_power": 140,
        "cpu_max_bw": 600,
        "gpu_max_bw": 800,
    },
    "Apple M4": {
        "cpu_max_power": 22,
        "gpu_max_power": 20,
        "cpu_max_bw": 120,
        "gpu_max_bw": 120,
    },
    "Apple M4 Pro": {
        "cpu_max_power": 35,
        "gpu_max_power": 45,
        "cpu_max_bw": 273,
        "gpu_max_bw": 273,
    },
    "Apple M4 Max": {
        "cpu_max_power": 45,
        "gpu_max_power": 80,
        "cpu_max_bw": 546,
        "gpu_max_bw": 546,
    },
    "Apple M4 Ultra": {
        "cpu_max_power": 90,
        "gpu_max_power": 160,
        "cpu_max_bw": 1092,
        "gpu_max_bw": 1092,
    },
    # Default fallback for unknown chips
    "_default": {
        "cpu_max_power": 20,
        "gpu_max_power": 20,
        "cpu_max_bw": 70,
        "gpu_max_bw": 70,
    },
}


def parse_powermetrics(
    path: str = "/tmp/asitop_powermetrics", timecode: str = "0"
) -> tuple[dict, dict, str, None, int] | Literal[False]:
    """Parse powermetrics plist file and extract metrics.

    Args:
        path: Path to powermetrics output file
        timecode: Timecode suffix for file

    Returns:
        Tuple of (cpu_metrics, gpu_metrics, thermal_pressure, bandwidth_metrics, timestamp)
        or False if parsing fails
    """
    try:
        with open(path + timecode, "rb") as fp:
            # Instead of reading entire file, seek to end and read last chunk
            # This prevents memory from growing as file grows
            fp.seek(0, 2)  # Seek to end
            file_size = fp.tell()

            # Read last 50KB which should contain the latest plist entries
            # Adjust if needed, but this prevents unbounded memory growth
            chunk_size = min(50000, file_size)
            fp.seek(max(0, file_size - chunk_size))
            data = fp.read()

        # Split by null bytes to get plist entries
        data_parts = data.split(b"\x00")

        # Try to parse the last entry
        for i in range(len(data_parts) - 1, -1, -1):
            if len(data_parts[i]) > 0:
                try:
                    powermetrics_parse = plistlib.loads(data_parts[i])
                    thermal_pressure = parse_thermal_pressure(powermetrics_parse)
                    cpu_metrics_dict = parse_cpu_metrics(powermetrics_parse)
                    gpu_metrics_dict = parse_gpu_metrics(powermetrics_parse)
                    bandwidth_metrics = None
                    timestamp = powermetrics_parse["timestamp"]
                    return (
                        cpu_metrics_dict,
                        gpu_metrics_dict,
                        thermal_pressure,
                        bandwidth_metrics,
                        timestamp,
                    )
                except (KeyError, plistlib.InvalidFileException, Exception):
                    # Try previous entry if current one is corrupted/incomplete
                    continue

        return False
    except OSError:
        return False


def clear_console() -> None:
    """Clear the terminal console using subprocess."""
    subprocess.run(["clear"], check=False)


def convert_to_gb(value: float) -> float:
    """Convert bytes to gigabytes.

    Args:
        value: Value in bytes

    Returns:
        Value in gigabytes, rounded to 1 decimal place
    """
    return round(value / 1024 / 1024 / 1024, 1)


def run_powermetrics_process(
    timecode: str, nice: int = 10, interval: int = 1000
) -> subprocess.Popen:
    """Start powermetrics subprocess to collect system metrics.

    Args:
        timecode: Unique identifier for output file
        nice: Process priority (higher = lower priority)
        interval: Sampling interval in milliseconds

    Returns:
        Running Popen process object
    """
    # Clean up old powermetrics files
    for tmpf in glob.glob("/tmp/asitop_powermetrics*"):
        os.remove(tmpf)

    output_file = f"/tmp/asitop_powermetrics{timecode}"

    command = [
        "sudo",
        "nice",
        "-n",
        str(nice),
        "powermetrics",
        "--samplers",
        "cpu_power,gpu_power,thermal",
        "-o",
        output_file,
        "-f",
        "plist",
        "-i",
        str(interval),
    ]

    process = subprocess.Popen(command, stdin=PIPE, stdout=PIPE)
    return process


def get_ram_metrics_dict() -> dict[str, float | int | None]:
    """Get RAM and swap memory metrics.

    Returns:
        Dictionary with memory statistics in GB and percentages
    """
    ram_metrics = psutil.virtual_memory()
    swap_metrics = psutil.swap_memory()

    total_gb = convert_to_gb(ram_metrics.total)
    free_gb = convert_to_gb(ram_metrics.available)
    used_gb = convert_to_gb(ram_metrics.total - ram_metrics.available)
    swap_total_gb = convert_to_gb(swap_metrics.total)
    swap_used_gb = convert_to_gb(swap_metrics.used)
    swap_free_gb = convert_to_gb(swap_metrics.total - swap_metrics.used)

    if swap_total_gb > 0:
        swap_free_percent = int(100 - (swap_free_gb / swap_total_gb * 100))
    else:
        swap_free_percent = None

    ram_metrics_dict = {
        "total_GB": round(total_gb, 1),
        "free_GB": round(free_gb, 1),
        "used_GB": round(used_gb, 1),
        "free_percent": int(100 - (ram_metrics.available / ram_metrics.total * 100)),
        "swap_total_GB": swap_total_gb,
        "swap_used_GB": swap_used_gb,
        "swap_free_GB": swap_free_gb,
        "swap_free_percent": swap_free_percent,
    }

    return ram_metrics_dict


def get_cpu_info() -> dict[str, str]:
    """Get CPU information using sysctl.

    Returns:
        Dictionary with machdep.cpu.brand_string and machdep.cpu.core_count
    """
    result = subprocess.run(
        ["sysctl", "-a"],
        capture_output=True,
        text=True,
        check=False,
    )

    cpu_info_lines = result.stdout.split("\n")
    data_fields = ["machdep.cpu.brand_string", "machdep.cpu.core_count"]
    cpu_info_dict = {}

    for line in cpu_info_lines:
        for field in data_fields:
            if field in line and ":" in line:
                value = line.split(":", 1)[1].strip()
                cpu_info_dict[field] = value

    return cpu_info_dict


def get_core_counts() -> dict[str, int]:
    """Get E-core and P-core counts using sysctl.

    Returns:
        Dictionary with hw.perflevel0.logicalcpu and hw.perflevel1.logicalcpu
    """
    result = subprocess.run(
        ["sysctl", "-a"],
        capture_output=True,
        text=True,
        check=False,
    )

    cores_info_lines = result.stdout.split("\n")
    data_fields = ["hw.perflevel0.logicalcpu", "hw.perflevel1.logicalcpu"]
    cores_info_dict = {}

    for line in cores_info_lines:
        for field in data_fields:
            if field in line and ":" in line:
                try:
                    value = int(line.split(":", 1)[1].strip())
                    cores_info_dict[field] = value
                except (ValueError, IndexError):
                    continue

    return cores_info_dict


def get_gpu_cores() -> int | str:
    """Get GPU core count using system_profiler.

    Returns:
        Number of GPU cores or "?" if unavailable
    """
    try:
        result = subprocess.run(
            ["system_profiler", "-detailLevel", "basic", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            check=False,
        )

        for line in result.stdout.split("\n"):
            if "Total Number of Cores" in line:
                cores_str = line.split(":")[-1].strip()
                return int(cores_str)

        return "?"
    except (ValueError, IndexError, OSError):
        return "?"


def get_soc_info() -> dict[str, Any]:
    """Get SoC information including core counts and power/bandwidth specs.

    Returns:
        Dictionary containing SoC name, core counts, and specifications
    """
    cpu_info_dict = get_cpu_info()
    core_counts_dict = get_core_counts()

    try:
        e_core_count = core_counts_dict["hw.perflevel1.logicalcpu"]
        p_core_count = core_counts_dict["hw.perflevel0.logicalcpu"]
    except KeyError:
        e_core_count = "?"
        p_core_count = "?"

    soc_name = cpu_info_dict.get("machdep.cpu.brand_string", "Unknown")
    core_count_str = cpu_info_dict.get("machdep.cpu.core_count", "0")

    try:
        core_count = int(core_count_str)
    except (ValueError, TypeError):
        core_count = 0

    # Get specs from SOC_SPECS dictionary, with fallback to default
    specs = SOC_SPECS.get(soc_name, SOC_SPECS["_default"])

    soc_info = {
        "name": soc_name,
        "core_count": core_count,
        "cpu_max_power": specs["cpu_max_power"],
        "gpu_max_power": specs["gpu_max_power"],
        "cpu_max_bw": specs["cpu_max_bw"],
        "gpu_max_bw": specs["gpu_max_bw"],
        "e_core_count": e_core_count,
        "p_core_count": p_core_count,
        "gpu_core_count": get_gpu_cores(),
    }

    return soc_info
