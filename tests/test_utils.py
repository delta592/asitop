"""
Unit tests for the utils module.

This module tests utility functions including powermetrics parsing,
RAM metrics collection, SOC information gathering, and file operations.
"""

import pathlib
import plistlib
import tempfile
from typing import Any
import unittest
from unittest.mock import MagicMock, patch


class TestConvertToGB(unittest.TestCase):
    """Test cases for convert_to_gb function."""

    def test_convert_to_gb_basic(self) -> None:
        """
        Test basic byte to GB conversion.

        Verifies correct conversion using factor of 1024^3 and
        rounding to 1 decimal place.
        """
        from asitop.utils import convert_to_gb

        bytes_value = 1073741824
        result = convert_to_gb(bytes_value)
        assert result == 1.0

    def test_convert_to_gb_zero(self) -> None:
        """
        Test conversion with zero bytes.

        Edge case: Ensures function handles zero input correctly.
        """
        from asitop.utils import convert_to_gb

        result = convert_to_gb(0)
        assert result == 0.0

    def test_convert_to_gb_large_value(self) -> None:
        """
        Test conversion with large byte values.

        Validates correct handling of large memory sizes (e.g., 64GB).
        """
        from asitop.utils import convert_to_gb

        bytes_value = 68719476736
        result = convert_to_gb(bytes_value)
        assert result == 64.0

    def test_convert_to_gb_fractional(self) -> None:
        """
        Test conversion resulting in fractional GB values.

        Ensures proper rounding for non-integer GB results.
        """
        from asitop.utils import convert_to_gb

        bytes_value = 1610612736
        result = convert_to_gb(bytes_value)
        self.assertAlmostEqual(result, 1.5, places=1)


class TestClearConsole(unittest.TestCase):
    """Test cases for clear_console function."""

    @patch("subprocess.run")
    def test_clear_console_calls_system(self, mock_run: MagicMock) -> None:
        """
        Test that clear_console calls subprocess.run with ['clear'] command.

        Verifies the function executes the correct system command
        to clear the terminal screen.
        """
        from asitop.utils import clear_console

        clear_console()
        mock_run.assert_called_once_with(["clear"], check=False)


class TestParsePowermetrics(unittest.TestCase):
    """Test cases for parse_powermetrics function."""

    def test_parse_powermetrics_valid_data(self) -> None:
        """
        Test parsing valid powermetrics plist data.

        Creates a temporary file with valid plist data and verifies
        all metrics are correctly extracted.
        """
        from asitop.utils import parse_powermetrics

        mock_plist_data: dict[str, Any] = {
            "timestamp": 1234567890,
            "thermal_pressure": "Nominal",
            "processor": {
                "clusters": [
                    {"name": "E-Cluster", "freq_hz": 2064000000, "idle_ratio": 0.5, "cpus": []}
                ],
                "ane_energy": 1000,
                "cpu_energy": 5000,
                "gpu_energy": 3000,
                "combined_power": 9000,
            },
            "gpu": {
                "freq_hz": 1296000000,
                "idle_ratio": 0.3,
            },
        }

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="_test") as tf:
            try:
                plistlib.dump(mock_plist_data, tf)
                tf.flush()

                # Parse the file directly using the full path as base_path and empty timecode
                result = parse_powermetrics(path=tf.name, timecode="")

                assert result is not None
                assert isinstance(result, tuple)
                assert len(result) == 5

                cpu_metrics, gpu_metrics, thermal, bandwidth, timestamp = result
                assert thermal == "Nominal"
                assert timestamp == 1234567890
                assert cpu_metrics is not None
                assert gpu_metrics is not None
            finally:
                pathlib.Path(tf.name).unlink()

    def test_parse_powermetrics_file_not_found(self) -> None:
        """
        Test parsing when powermetrics file doesn't exist.

        Edge case: Ensures function returns False when file is missing
        rather than raising an exception.
        """
        from asitop.utils import parse_powermetrics

        result = parse_powermetrics(timecode="nonexistent_test")
        assert not result

    def test_parse_powermetrics_multiple_entries(self) -> None:
        """
        Test parsing powermetrics file with multiple plist entries.

        Verifies that the function correctly reads the most recent
        entry from a file containing multiple null-separated plists.
        """
        from asitop.utils import parse_powermetrics

        mock_plist_1: dict[str, Any] = {
            "timestamp": 1000,
            "thermal_pressure": "Nominal",
            "processor": {
                "clusters": [
                    {"name": "E-Cluster", "freq_hz": 2000000000, "idle_ratio": 0.5, "cpus": []}
                ],
                "ane_energy": 1000,
                "cpu_energy": 5000,
                "gpu_energy": 3000,
                "combined_power": 9000,
            },
            "gpu": {"freq_hz": 1200000000, "idle_ratio": 0.3},
        }

        mock_plist_2: dict[str, Any] = {
            "timestamp": 2000,
            "thermal_pressure": "Moderate",
            "processor": {
                "clusters": [
                    {"name": "E-Cluster", "freq_hz": 2100000000, "idle_ratio": 0.4, "cpus": []}
                ],
                "ane_energy": 2000,
                "cpu_energy": 6000,
                "gpu_energy": 4000,
                "combined_power": 12000,
            },
            "gpu": {"freq_hz": 1300000000, "idle_ratio": 0.2},
        }

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="_test") as tf:
            try:
                plistlib.dump(mock_plist_1, tf)
                tf.write(b"\x00")
                plistlib.dump(mock_plist_2, tf)
                tf.flush()

                # Parse the file directly using the full path as base_path and empty timecode
                result = parse_powermetrics(path=tf.name, timecode="")

                assert result is not None
                _, _, thermal, _, timestamp = result
                assert timestamp == 2000
                assert thermal == "Moderate"
            finally:
                pathlib.Path(tf.name).unlink()


class TestGetRamMetricsDict(unittest.TestCase):
    """Test cases for get_ram_metrics_dict function."""

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_get_ram_metrics_dict_basic(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """
        Test basic RAM and swap metrics collection.

        Mocks psutil calls to verify correct calculation of total,
        used, free memory and percentages.
        """
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(
            total=17179869184,
            available=8589934592,
        )
        mock_swap.return_value = MagicMock(
            total=2147483648,
            used=1073741824,
        )

        result = get_ram_metrics_dict()

        assert result["total_GB"] == 16.0
        assert result["free_GB"] == 8.0
        assert result["used_GB"] == 8.0
        assert result["free_percent"] == 50
        assert result["swap_total_GB"] == 2.0
        assert result["swap_used_GB"] == 1.0

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_get_ram_metrics_dict_no_swap(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """
        Test RAM metrics when swap is disabled.

        Edge case: Ensures correct handling when swap_total is 0,
        resulting in 0 for swap_free_percent (changed from None for type consistency).
        """
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(
            total=17179869184,
            available=8589934592,
        )
        mock_swap.return_value = MagicMock(
            total=0,
            used=0,
        )

        result = get_ram_metrics_dict()

        assert result["swap_total_GB"] == 0.0
        assert result["swap_free_percent"] == 0  # Changed from None to 0 for type consistency

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_get_ram_metrics_dict_full_ram(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """
        Test RAM metrics when memory is nearly full.

        Edge case: Validates correct percentage calculation when
        available memory is very low.
        """
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(
            total=17179869184,
            available=171798691,
        )
        mock_swap.return_value = MagicMock(
            total=2147483648,
            used=2000000000,
        )

        result = get_ram_metrics_dict()

        assert result["free_percent"] > 98
        assert result["free_percent"] < 100


class TestGetCPUInfo(unittest.TestCase):
    """Test cases for get_cpu_info function."""

    @patch("subprocess.run")
    def test_get_cpu_info_basic(self, mock_run: MagicMock) -> None:
        """
        Test extraction of CPU information from sysctl.

        Mocks sysctl output to verify correct parsing of CPU brand
        string and core count.
        """
        from asitop.utils import get_cpu_info

        mock_output = (
            "machdep.cpu.brand_string: Apple M1\n"
            "machdep.cpu.core_count: 8\n"
            "machdep.cpu.other_field: value\n"
        )
        mock_run.return_value.stdout = mock_output

        result = get_cpu_info()

        assert result["machdep.cpu.brand_string"] == "Apple M1"
        assert result["machdep.cpu.core_count"] == "8"

    @patch("subprocess.run")
    def test_get_cpu_info_m1_max(self, mock_run: MagicMock) -> None:
        """
        Test CPU info extraction for M1 Max chip.

        Validates parsing for higher-end Apple Silicon variants.
        """
        from asitop.utils import get_cpu_info

        mock_output = "machdep.cpu.brand_string: Apple M1 Max\nmachdep.cpu.core_count: 10\n"
        mock_run.return_value.stdout = mock_output

        result = get_cpu_info()

        assert result["machdep.cpu.brand_string"] == "Apple M1 Max"
        assert result["machdep.cpu.core_count"] == "10"


class TestGetCoreCounts(unittest.TestCase):
    """Test cases for get_core_counts function."""

    @patch("subprocess.run")
    def test_get_core_counts_basic(self, mock_run: MagicMock) -> None:
        """
        Test extraction of performance and efficiency core counts.

        Mocks sysctl perflevel output to verify correct parsing of
        E-core and P-core counts.
        """
        from asitop.utils import get_core_counts

        mock_output = (
            "hw.perflevel0.logicalcpu: 6\nhw.perflevel1.logicalcpu: 2\nhw.perflevel0.name: P-Core\n"
        )
        mock_run.return_value.stdout = mock_output

        result = get_core_counts()

        assert result["hw.perflevel0.logicalcpu"] == 6
        assert result["hw.perflevel1.logicalcpu"] == 2

    @patch("subprocess.run")
    def test_get_core_counts_m1_ultra(self, mock_run: MagicMock) -> None:
        """
        Test core count extraction for M1 Ultra.

        Validates parsing for the dual-die M1 Ultra configuration
        with higher core counts.
        """
        from asitop.utils import get_core_counts

        mock_output = "hw.perflevel0.logicalcpu: 16\nhw.perflevel1.logicalcpu: 4\n"
        mock_run.return_value.stdout = mock_output

        result = get_core_counts()

        assert result["hw.perflevel0.logicalcpu"] == 16
        assert result["hw.perflevel1.logicalcpu"] == 4


class TestGetGPUCores(unittest.TestCase):
    """Test cases for get_gpu_cores function."""

    @patch("subprocess.run")
    def test_get_gpu_cores_basic(self, mock_run: MagicMock) -> None:
        """
        Test extraction of GPU core count from system_profiler.

        Verifies correct parsing of GPU core information from
        system display data.
        """
        from asitop.utils import get_gpu_cores

        mock_output = "      Total Number of Cores: 8\n"
        mock_run.return_value.stdout = mock_output

        result = get_gpu_cores()

        assert result == 8

    @patch("subprocess.run")
    def test_get_gpu_cores_high_count(self, mock_run: MagicMock) -> None:
        """
        Test GPU core extraction for high-end configurations.

        Validates parsing for GPUs with higher core counts
        (e.g., M1 Max/Ultra).
        """
        from asitop.utils import get_gpu_cores

        mock_output = "      Total Number of Cores: 32\n"
        mock_run.return_value.stdout = mock_output

        result = get_gpu_cores()

        assert result == 32

    @patch("subprocess.run")
    def test_get_gpu_cores_parse_error(self, mock_run: MagicMock) -> None:
        """
        Test GPU core extraction when parsing fails.

        Edge case: Ensures function returns '?' when system_profiler
        output cannot be parsed.
        """
        from asitop.utils import get_gpu_cores

        mock_output = "Invalid output\n"
        mock_run.return_value.stdout = mock_output

        result = get_gpu_cores()

        assert result == "?"


class TestGetSOCInfo(unittest.TestCase):
    """Test cases for get_soc_info function."""

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_m1(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info extraction for base M1 chip.

        Verifies correct power and bandwidth specifications are
        returned for the M1 configuration.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M1",
            "machdep.cpu.core_count": "8",
        }
        mock_core_counts.return_value = {
            "hw.perflevel0.logicalcpu": 4,
            "hw.perflevel1.logicalcpu": 4,
        }
        mock_gpu_cores.return_value = 8

        result = get_soc_info()

        assert result["name"] == "Apple M1"
        assert result["core_count"] == 8
        assert result["e_core_count"] == 4
        assert result["p_core_count"] == 4
        assert result["gpu_core_count"] == 8
        assert result["cpu_max_power"] == 20
        assert result["gpu_max_power"] == 20
        assert result["cpu_max_bw"] == 70
        assert result["gpu_max_bw"] == 70

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_m1_max(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info extraction for M1 Max chip.

        Validates higher TDP and bandwidth specs for M1 Max.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M1 Max",
            "machdep.cpu.core_count": "10",
        }
        mock_core_counts.return_value = {
            "hw.perflevel0.logicalcpu": 8,
            "hw.perflevel1.logicalcpu": 2,
        }
        mock_gpu_cores.return_value = 32

        result = get_soc_info()

        assert result["name"] == "Apple M1 Max"
        assert result["cpu_max_power"] == 30
        assert result["gpu_max_power"] == 60
        assert result["cpu_max_bw"] == 250
        assert result["gpu_max_bw"] == 400

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_m1_ultra(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info extraction for M1 Ultra chip.

        Validates doubled specs for the dual-die M1 Ultra.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M1 Ultra",
            "machdep.cpu.core_count": "20",
        }
        mock_core_counts.return_value = {
            "hw.perflevel0.logicalcpu": 16,
            "hw.perflevel1.logicalcpu": 4,
        }
        mock_gpu_cores.return_value = 64

        result = get_soc_info()

        assert result["name"] == "Apple M1 Ultra"
        assert result["cpu_max_power"] == 60
        assert result["gpu_max_power"] == 120
        assert result["cpu_max_bw"] == 500
        assert result["gpu_max_bw"] == 800

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_m2(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info extraction for M2 chip.

        Verifies M2-specific power and bandwidth specifications.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M2",
            "machdep.cpu.core_count": "8",
        }
        mock_core_counts.return_value = {
            "hw.perflevel0.logicalcpu": 4,
            "hw.perflevel1.logicalcpu": 4,
        }
        mock_gpu_cores.return_value = 10

        result = get_soc_info()

        assert result["name"] == "Apple M2"
        assert result["cpu_max_power"] == 25
        assert result["gpu_max_power"] == 15
        assert result["cpu_max_bw"] == 100
        assert result["gpu_max_bw"] == 100

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_unknown_chip(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info extraction for unknown/future chips.

        Edge case: Ensures default values are used for unrecognized
        Apple Silicon chips.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M5",
            "machdep.cpu.core_count": "12",
        }
        mock_core_counts.return_value = {
            "hw.perflevel0.logicalcpu": 8,
            "hw.perflevel1.logicalcpu": 4,
        }
        mock_gpu_cores.return_value = 16

        result = get_soc_info()

        # Should use default values for unknown chips
        assert result["cpu_max_power"] == 20
        assert result["gpu_max_power"] == 20
        assert result["cpu_max_bw"] == 70
        assert result["gpu_max_bw"] == 70

    @patch("asitop.utils.get_gpu_cores")
    @patch("asitop.utils.get_core_counts")
    @patch("asitop.utils.get_cpu_info")
    def test_get_soc_info_missing_core_counts(
        self, mock_cpu_info: MagicMock, mock_core_counts: MagicMock, mock_gpu_cores: MagicMock
    ) -> None:
        """
        Test SOC info when perflevel data is unavailable.

        Edge case: Ensures function handles missing sysctl data
        gracefully by returning '?' for core counts.
        """
        from asitop.utils import get_soc_info

        mock_cpu_info.return_value = {
            "machdep.cpu.brand_string": "Apple M1",
            "machdep.cpu.core_count": "8",
        }
        mock_core_counts.return_value = {}
        mock_gpu_cores.return_value = 8

        result = get_soc_info()

        assert result["e_core_count"] == "?"
        assert result["p_core_count"] == "?"


class TestRunPowermetricsProcess(unittest.TestCase):
    """Test cases for run_powermetrics_process function."""

    @patch("glob.glob")
    @patch("os.remove")
    @patch("subprocess.Popen")
    def test_run_powermetrics_process_basic(
        self, mock_popen: MagicMock, mock_remove: MagicMock, mock_glob: MagicMock
    ) -> None:
        """
        Test starting powermetrics process with default parameters.

        Verifies that the function correctly constructs the command,
        cleans up old files, and spawns the subprocess.
        """
        from asitop.utils import run_powermetrics_process

        mock_glob.return_value = []
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = run_powermetrics_process(timecode="123", nice=10, interval=1000)

        assert result == mock_process
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "powermetrics" in call_args
        assert "--samplers" in call_args
        assert "cpu_power,gpu_power,thermal" in call_args

    @patch("glob.glob")
    @patch("pathlib.Path.unlink")
    @patch("subprocess.Popen")
    def test_run_powermetrics_process_cleanup(
        self, mock_popen: MagicMock, mock_unlink: MagicMock, mock_glob: MagicMock
    ) -> None:
        """
        Test that old powermetrics files are cleaned up.

        Ensures the function removes existing temporary files before
        starting a new powermetrics process.
        """
        from asitop.utils import run_powermetrics_process

        old_files = ["/tmp/asitop_powermetrics123", "/tmp/asitop_powermetrics456"]
        mock_glob.return_value = old_files
        mock_popen.return_value = MagicMock()

        run_powermetrics_process(timecode="789")

        assert mock_unlink.call_count == len(old_files)
        # Verify unlink was called with missing_ok=True
        mock_unlink.assert_called_with(missing_ok=True)

    @patch("glob.glob")
    @patch("os.remove")
    @patch("subprocess.Popen")
    def test_run_powermetrics_process_custom_interval(
        self, mock_popen: MagicMock, mock_remove: MagicMock, mock_glob: MagicMock
    ) -> None:
        """
        Test powermetrics with custom sampling interval.

        Verifies that custom interval parameter is correctly passed
        to the powermetrics command.
        """
        from asitop.utils import run_powermetrics_process

        mock_glob.return_value = []
        mock_popen.return_value = MagicMock()

        run_powermetrics_process(timecode="123", interval=5000)

        call_args = mock_popen.call_args[0][0]
        assert "5000" in call_args


class TestParsePowermetricsErrors(unittest.TestCase):
    """Test error handling in parse_powermetrics function."""

    def test_parse_powermetrics_corrupted_plist(self) -> None:
        """
        Test parsing when plist data is corrupted.

        Ensures function returns False when all plist entries
        in the file are corrupted or invalid.
        """
        import tempfile

        from asitop.utils import parse_powermetrics

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="_test") as tf:
            try:
                # Write invalid plist data
                tf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                tf.write(b"<plist>\n")
                tf.write(b"<dict>\n")
                tf.write(b"CORRUPTED DATA HERE\n")
                tf.flush()

                result = parse_powermetrics(path=tf.name, timecode="")

                assert not result
            finally:
                pathlib.Path(tf.name).unlink()

    def test_parse_powermetrics_empty_parts(self) -> None:
        """
        Test parsing when file contains only empty null-separated parts.

        Edge case: File has null bytes but no valid plist data.
        """
        import tempfile

        from asitop.utils import parse_powermetrics

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="_test") as tf:
            try:
                # Write only null bytes
                tf.write(b"\x00\x00\x00\x00")
                tf.flush()

                result = parse_powermetrics(path=tf.name, timecode="")

                assert not result
            finally:
                pathlib.Path(tf.name).unlink()

    def test_parse_powermetrics_partial_valid_data(self) -> None:
        """
        Test parsing with mixture of corrupted and valid plist entries.

        Verifies function skips corrupted entries and successfully
        parses the first valid one it finds.
        """
        import plistlib
        import tempfile

        from asitop.utils import parse_powermetrics

        mock_plist_data: dict[str, Any] = {
            "timestamp": 9999,
            "thermal_pressure": "Heavy",
            "processor": {
                "clusters": [
                    {"name": "E-Cluster", "freq_hz": 2500000000, "idle_ratio": 0.3, "cpus": []}
                ],
                "ane_energy": 3000,
                "cpu_energy": 7000,
                "gpu_energy": 5000,
                "combined_power": 15000,
            },
            "gpu": {"freq_hz": 1400000000, "idle_ratio": 0.1},
        }

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix="_test") as tf:
            try:
                # Write corrupted data first
                tf.write(b"CORRUPTED")
                tf.write(b"\x00")
                # Then write valid plist
                plistlib.dump(mock_plist_data, tf)
                tf.flush()

                result = parse_powermetrics(path=tf.name, timecode="")

                assert result is not None
                assert isinstance(result, tuple)
                _, _, thermal, _, timestamp = result
                assert timestamp == 9999
                assert thermal == "Heavy"
            finally:
                pathlib.Path(tf.name).unlink()


if __name__ == "__main__":
    unittest.main()
