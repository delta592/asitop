import glob
import os
import plistlib
import subprocess
from subprocess import PIPE

import psutil

from .parsers import *


def parse_powermetrics(path="/tmp/asitop_powermetrics", timecode="0"):
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
                except Exception:
                    # Try previous entry if current one is corrupted/incomplete
                    continue

        return False
    except Exception:
        return False


def clear_console():
    command = "clear"
    os.system(command)


def convert_to_gb(value):
    return round(value / 1024 / 1024 / 1024, 1)


def run_powermetrics_process(timecode, nice=10, interval=1000):
    # ver, *_ = platform.mac_ver()
    # major_ver = int(ver.split(".")[0])
    for tmpf in glob.glob("/tmp/asitop_powermetrics*"):
        os.remove(tmpf)
    output_file_flag = "-o"
    command = " ".join(
        [
            "sudo nice -n",
            str(nice),
            "powermetrics",
            "--samplers cpu_power,gpu_power,thermal",
            output_file_flag,
            "/tmp/asitop_powermetrics" + timecode,
            "-f plist",
            "-i",
            str(interval),
        ]
    )
    process = subprocess.Popen(command.split(" "), stdin=PIPE, stdout=PIPE)
    return process


def get_ram_metrics_dict():
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


def get_cpu_info():
    cpu_info = os.popen("sysctl -a | grep machdep.cpu").read()
    cpu_info_lines = cpu_info.split("\n")
    data_fields = ["machdep.cpu.brand_string", "machdep.cpu.core_count"]
    cpu_info_dict = {}
    for line in cpu_info_lines:
        for h in data_fields:
            if h in line:
                value = line.split(":")[1].strip()
                cpu_info_dict[h] = value
    return cpu_info_dict


def get_core_counts():
    cores_info = os.popen("sysctl -a | grep hw.perflevel").read()
    cores_info_lines = cores_info.split("\n")
    data_fields = ["hw.perflevel0.logicalcpu", "hw.perflevel1.logicalcpu"]
    cores_info_dict = {}
    for line in cores_info_lines:
        for h in data_fields:
            if h in line:
                value = int(line.split(":")[1].strip())
                cores_info_dict[h] = value
    return cores_info_dict


def get_gpu_cores():
    try:
        cores = os.popen(
            "system_profiler -detailLevel basic SPDisplaysDataType | grep 'Total Number of Cores'"
        ).read()
        cores = int(cores.split(": ")[-1])
    except (ValueError, IndexError, OSError):
        cores = "?"
    return cores


def get_soc_info():
    cpu_info_dict = get_cpu_info()
    core_counts_dict = get_core_counts()
    try:
        e_core_count = core_counts_dict["hw.perflevel1.logicalcpu"]
        p_core_count = core_counts_dict["hw.perflevel0.logicalcpu"]
    except KeyError:
        e_core_count = "?"
        p_core_count = "?"
    soc_info = {
        "name": cpu_info_dict["machdep.cpu.brand_string"],
        "core_count": int(cpu_info_dict["machdep.cpu.core_count"]),
        "cpu_max_power": None,
        "gpu_max_power": None,
        "cpu_max_bw": None,
        "gpu_max_bw": None,
        "e_core_count": e_core_count,
        "p_core_count": p_core_count,
        "gpu_core_count": get_gpu_cores(),
    }
    # TDP (power)
    if soc_info["name"] == "Apple M1 Max":
        soc_info["cpu_max_power"] = 30
        soc_info["gpu_max_power"] = 60
    elif soc_info["name"] == "Apple M1 Pro":
        soc_info["cpu_max_power"] = 30
        soc_info["gpu_max_power"] = 30
    elif soc_info["name"] == "Apple M1":
        soc_info["cpu_max_power"] = 20
        soc_info["gpu_max_power"] = 20
    elif soc_info["name"] == "Apple M1 Ultra":
        soc_info["cpu_max_power"] = 60
        soc_info["gpu_max_power"] = 120
    elif soc_info["name"] == "Apple M2":
        soc_info["cpu_max_power"] = 25
        soc_info["gpu_max_power"] = 15
    else:
        soc_info["cpu_max_power"] = 20
        soc_info["gpu_max_power"] = 20
    # bandwidth
    if soc_info["name"] == "Apple M1 Max":
        soc_info["cpu_max_bw"] = 250
        soc_info["gpu_max_bw"] = 400
    elif soc_info["name"] == "Apple M1 Pro":
        soc_info["cpu_max_bw"] = 200
        soc_info["gpu_max_bw"] = 200
    elif soc_info["name"] == "Apple M1":
        soc_info["cpu_max_bw"] = 70
        soc_info["gpu_max_bw"] = 70
    elif soc_info["name"] == "Apple M1 Ultra":
        soc_info["cpu_max_bw"] = 500
        soc_info["gpu_max_bw"] = 800
    elif soc_info["name"] == "Apple M2":
        soc_info["cpu_max_bw"] = 100
        soc_info["gpu_max_bw"] = 100
    else:
        soc_info["cpu_max_bw"] = 70
        soc_info["gpu_max_bw"] = 70
    return soc_info
