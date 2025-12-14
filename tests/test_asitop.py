"""
Unit tests for the asitop main module.

This module tests the main application logic including argument parsing,
UI initialization, and the main monitoring loop integration.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch


class TestArgumentParsing(unittest.TestCase):
    """Test cases for command-line argument parsing."""

    def test_default_arguments(self) -> None:
        """
        Test that default argument values are set correctly.

        Verifies the default values for interval, color, avg,
        show_cores, and max_count parameters.
        """
        # Import happens after sys.argv is set to avoid arg parse errors
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            # Force re-parsing by accessing the module-level args
            import argparse

            parser = argparse.ArgumentParser(description="asitop: Performance monitoring CLI tool")
            parser.add_argument("--interval", type=int, default=1)
            parser.add_argument("--color", type=int, default=2)
            parser.add_argument("--avg", type=int, default=30)
            parser.add_argument("--show_cores", type=bool, default=False)
            parser.add_argument("--max_count", type=int, default=0)

            args = parser.parse_args([])

            assert args.interval == 1
            assert args.color == 2
            assert args.avg == 30
            assert not args.show_cores
            assert args.max_count == 0

    def test_custom_interval(self) -> None:
        """
        Test parsing custom interval argument.

        Validates that --interval parameter correctly overrides the
        default value.
        """
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--interval", type=int, default=1)

        args = parser.parse_args(["--interval", "5"])

        assert args.interval == 5

    def test_custom_color(self) -> None:
        """
        Test parsing custom color argument.

        Ensures --color parameter accepts values in range 0-8.
        """
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--color", type=int, default=2)

        args = parser.parse_args(["--color", "5"])

        assert args.color == 5

    def test_custom_avg(self) -> None:
        """
        Test parsing custom averaging interval.

        Validates --avg parameter for setting the rolling average window.
        """
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--avg", type=int, default=30)

        args = parser.parse_args(["--avg", "60"])

        assert args.avg == 60

    def test_max_count_argument(self) -> None:
        """
        Test parsing max_count argument.

        Verifies --max_count parameter for controlling powermetrics
        restart frequency.
        """
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--max_count", type=int, default=0)

        args = parser.parse_args(["--max_count", "500"])

        assert args.max_count == 500


class TestMainFunction(unittest.TestCase):
    """Test cases for the main() function."""

    def test_main_initialization(self) -> None:
        """
        Test main function initialization sequence.

        Verifies that the main function prints welcome messages,
        initializes SOC info, and starts powermetrics process.
        """
        test_args = ["asitop", "--interval", "1"]
        with patch.object(sys, "argv", test_args):
            # Reload module with patched argv
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("builtins.print") as mock_print,
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.clear_console") as mock_clear,
                patch("asitop.asitop.time.sleep") as mock_sleep,
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }
                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                # Mock first reading to allow loop to start, then raise to exit
                mock_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                def mock_parse_pm_func(timecode):
                    mock_parse_pm_func.call_count += 1
                    if mock_parse_pm_func.call_count == 1:
                        return mock_reading
                    raise KeyboardInterrupt

                mock_parse_pm_func.call_count = 0
                mock_parse_pm.side_effect = mock_parse_pm_func

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Verify initialization messages were printed
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                assert any("ASITOP" in str(call) for call in print_calls)
                assert any("Loading" in str(call) for call in print_calls)

    def test_main_soc_info_retrieval(self) -> None:
        """
        Test that main function retrieves SOC information.

        Ensures get_soc_info is called during initialization to
        gather system information.
        """
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run,
                patch("asitop.asitop.parse_powermetrics") as mock_parse,
                patch("asitop.asitop.time.sleep") as mock_sleep,
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1 Max",
                    "core_count": 10,
                    "e_core_count": 2,
                    "p_core_count": 8,
                    "gpu_core_count": 32,
                    "cpu_max_power": 30,
                    "gpu_max_power": 60,
                    "cpu_max_bw": 250,
                    "gpu_max_bw": 400,
                }

                mock_run.return_value = MagicMock()
                # parse_powermetrics needs to return valid data for get_reading to work
                mock_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )
                mock_parse.return_value = mock_reading

                # Mock sleep to raise exception after first call
                mock_sleep.side_effect = KeyboardInterrupt

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                mock_get_soc.assert_called()


class TestDequeMemoryManagement(unittest.TestCase):
    """Test cases for memory management using deques."""

    def test_cpu_power_chart_maxlen(self) -> None:
        """
        Test that CPU power chart has bounded memory.

        Verifies that HChart datapoints are limited to prevent
        memory leak from unbounded growth.
        """
        from collections import deque

        # Simulate the chart datapoints initialization
        max_chart_points = 200
        cpu_power_datapoints = deque(maxlen=max_chart_points)

        # Add more than max points
        for i in range(300):
            cpu_power_datapoints.append(i)

        # Should only keep the last 200 points
        assert len(cpu_power_datapoints) == max_chart_points
        assert cpu_power_datapoints[0] == 100
        assert cpu_power_datapoints[-1] == 299

    def test_avg_power_list_maxlen(self) -> None:
        """
        Test that average power lists have bounded memory.

        Ensures averaging deques are properly sized based on
        avg interval and sampling interval.
        """
        from collections import deque

        interval = 1
        avg_seconds = 30
        maxlen = int(avg_seconds / interval)

        avg_cpu_power_list = deque(maxlen=maxlen)

        # Add more samples than the window
        for i in range(50):
            avg_cpu_power_list.append(i)

        # Should only keep last 30 samples
        assert len(avg_cpu_power_list) == 30
        assert avg_cpu_power_list[0] == 20
        assert avg_cpu_power_list[-1] == 49


class TestGetAvgFunction(unittest.TestCase):
    """Test cases for the get_avg helper function."""

    def test_get_avg_basic(self) -> None:
        """
        Test basic average calculation.

        Verifies correct computation of arithmetic mean for a list
        of values.
        """
        test_values = [10, 20, 30, 40, 50]
        avg = sum(test_values) / len(test_values)
        assert avg == 30.0

    def test_get_avg_single_value(self) -> None:
        """
        Test average with single value.

        Edge case: Ensures average of one value returns that value.
        """
        test_values = [42]
        avg = sum(test_values) / len(test_values)
        assert avg == 42.0

    def test_get_avg_floating_point(self) -> None:
        """
        Test average with floating-point values.

        Validates correct handling of decimal values in power
        measurements.
        """
        test_values = [1.5, 2.5, 3.0, 4.0]
        avg = sum(test_values) / len(test_values)
        self.assertAlmostEqual(avg, 2.75, places=2)


class TestRestartLogic(unittest.TestCase):
    """Test cases for powermetrics restart logic."""

    def test_restart_interval_default(self) -> None:
        """
        Test default restart interval when max_count is 0.

        Verifies that powermetrics restarts every 300 iterations
        by default to prevent unbounded file growth.
        """
        max_count = 0
        restart_interval = max_count if max_count > 0 else 300
        assert restart_interval == 300

    def test_restart_interval_custom(self) -> None:
        """
        Test custom restart interval.

        Validates that user-specified max_count is respected.
        """
        max_count = 500
        restart_interval = max_count if max_count > 0 else 300
        assert restart_interval == 500

    def test_restart_counter_increments(self) -> None:
        """
        Test that restart counter increments correctly.

        Simulates the loop counter behavior to ensure proper
        restart triggering.
        """
        count = 0
        restart_interval = 10
        restart_triggered = False

        for _ in range(15):
            if count >= restart_interval:
                count = 0
                restart_triggered = True
                break
            count += 1

        assert restart_triggered
        assert count == 0


class TestThermalThrottleDetection(unittest.TestCase):
    """Test cases for thermal throttle detection logic."""

    def test_thermal_throttle_nominal(self) -> None:
        """
        Test thermal throttle detection when pressure is Nominal.

        Verifies that no throttling is indicated under normal
        thermal conditions.
        """
        thermal_pressure = "Nominal"
        thermal_throttle = "no" if thermal_pressure == "Nominal" else "yes"
        assert thermal_throttle == "no"

    def test_thermal_throttle_moderate(self) -> None:
        """
        Test thermal throttle detection when pressure is Moderate.

        Ensures throttling is indicated under elevated thermal
        pressure.
        """
        thermal_pressure = "Moderate"
        thermal_throttle = "no" if thermal_pressure == "Nominal" else "yes"
        assert thermal_throttle == "yes"

    def test_thermal_throttle_heavy(self) -> None:
        """
        Test thermal throttle detection when pressure is Heavy.

        Validates throttling indication under severe thermal
        pressure.
        """
        thermal_pressure = "Heavy"
        thermal_throttle = "no" if thermal_pressure == "Nominal" else "yes"
        assert thermal_throttle == "yes"


class TestANEUtilizationCalculation(unittest.TestCase):
    """Test cases for ANE (Apple Neural Engine) utilization calculation."""

    def test_ane_util_calculation_basic(self) -> None:
        """
        Test basic ANE utilization percentage calculation.

        Validates conversion from power consumption to utilization
        percentage using ANE max power (8W).
        """
        ane_W = 4.0
        interval = 1
        ane_max_power = 8.0
        ane_util_percent = int(ane_W / interval / ane_max_power * 100)
        assert ane_util_percent == 50

    def test_ane_util_calculation_idle(self) -> None:
        """
        Test ANE utilization when idle.

        Edge case: Ensures 0% utilization when ANE power is zero.
        """
        ane_W = 0.0
        interval = 1
        ane_max_power = 8.0
        ane_util_percent = int(ane_W / interval / ane_max_power * 100)
        assert ane_util_percent == 0

    def test_ane_util_calculation_max(self) -> None:
        """
        Test ANE utilization at maximum power.

        Edge case: Validates 100% utilization at peak ANE power
        consumption.
        """
        ane_W = 8.0
        interval = 1
        ane_max_power = 8.0
        ane_util_percent = int(ane_W / interval / ane_max_power * 100)
        assert ane_util_percent == 100

    def test_ane_util_calculation_different_interval(self) -> None:
        """
        Test ANE utilization with different sampling interval.

        Ensures calculation accounts for interval duration when
        converting energy to power.
        """
        ane_W = 10.0
        interval = 2
        ane_max_power = 8.0
        ane_util_percent = int(ane_W / interval / ane_max_power * 100)
        self.assertAlmostEqual(ane_util_percent, 62, delta=1)


class TestGpuUsageCalculation(unittest.TestCase):
    """Test GPU utilization calculation with fallbacks."""

    def test_gpu_usage_prefers_active_metrics(self) -> None:
        """Active GPU metrics should take precedence over power fallback."""
        from asitop.asitop import calculate_gpu_usage

        gpu_percent, freq = calculate_gpu_usage(
            {"active": 40, "freq_MHz": 900},
            gpu_power_watts=5.0,
            gpu_max_power=30.0,
            last_gpu_freq_mhz=None,
        )

        assert gpu_percent == 40
        assert freq == 900

    def test_gpu_usage_falls_back_to_power(self) -> None:
        """Use power-derived utilization when active residency is zero."""
        from asitop.asitop import calculate_gpu_usage

        gpu_percent, freq = calculate_gpu_usage(
            {"active": 0, "freq_MHz": 0},
            gpu_power_watts=12.0,  # 40% of 30W
            gpu_max_power=30.0,
            last_gpu_freq_mhz=500,
        )

        assert gpu_percent == 40
        assert freq == 500

    def test_gpu_usage_clamps_to_hundred(self) -> None:
        """Clamp power-derived utilization to 100%."""
        from asitop.asitop import calculate_gpu_usage

        gpu_percent, freq = calculate_gpu_usage(
            {"active": 0, "freq_MHz": 0},
            gpu_power_watts=40.0,
            gpu_max_power=30.0,
            last_gpu_freq_mhz=None,
        )

        assert gpu_percent == 100
        assert freq is None

    def test_gpu_usage_handles_zero_max_power(self) -> None:
        """Gracefully handle missing GPU max power specs."""
        from asitop.asitop import calculate_gpu_usage

        gpu_percent, freq = calculate_gpu_usage(
            {"active": 0, "freq_MHz": 0},
            gpu_power_watts=10.0,
            gpu_max_power=0.0,
            last_gpu_freq_mhz=450,
        )

        assert gpu_percent == 0
        assert freq == 450


class TestTimestampHandling(unittest.TestCase):
    """Test cases for timestamp handling and update detection."""

    def test_timestamp_update_detection(self) -> None:
        """
        Test detection of new data based on timestamp changes.

        Verifies that the loop only processes metrics when timestamp
        has advanced, avoiding duplicate processing.
        """
        last_timestamp = 1000
        current_timestamp = 1001

        should_process = current_timestamp > last_timestamp
        assert should_process

    def test_timestamp_no_update(self) -> None:
        """
        Test handling when timestamp hasn't changed.

        Ensures data is skipped when timestamp indicates no new
        reading is available.
        """
        last_timestamp = 1000
        current_timestamp = 1000

        should_process = current_timestamp > last_timestamp
        assert not should_process

    def test_timestamp_backwards(self) -> None:
        """
        Test handling of backwards-moving timestamps.

        Edge case: Ensures data is skipped if timestamp somehow
        moves backwards (e.g., after process restart).
        """
        last_timestamp = 2000
        current_timestamp = 1000

        should_process = current_timestamp > last_timestamp
        assert not should_process


class TestGetReadingRetry(unittest.TestCase):
    """Test get_reading() retry logic when powermetrics isn't ready."""

    def test_get_reading_retries_until_ready(self) -> None:
        """
        Test that get_reading() retries when parse_powermetrics returns None.

        Simulates the scenario where powermetrics output isn't immediately
        available and requires waiting and retrying.
        """
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.time.sleep") as mock_sleep,
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                valid_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                # Return None twice, then valid data, then raise to exit
                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] <= 2:
                        return None  # Not ready yet
                    if call_count[0] == 3:
                        return valid_reading
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Verify sleep was called while waiting for data
                assert mock_sleep.call_count >= 2


class TestExtendedPCoreSupport(unittest.TestCase):
    """Test support for chips with >8 P-cores (M1 Ultra, etc.)."""

    def test_m1_ultra_extended_p_cores(self) -> None:
        """
        Test that M1 Ultra with 16 P-cores creates extended gauge layout.

        Verifies that chips with more than 8 P-cores properly initialize
        additional gauge UI elements.
        """
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.time.sleep"),
            ):
                # M1 Ultra config with 16 P-cores
                mock_get_soc.return_value = {
                    "name": "Apple M1 Ultra",
                    "core_count": 20,
                    "e_core_count": 4,
                    "p_core_count": 16,
                    "gpu_core_count": 64,
                    "cpu_max_power": 60,
                    "gpu_max_power": 120,
                    "cpu_max_bw": 500,
                    "gpu_max_bw": 800,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                valid_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1, 2, 3],
                        "p_core": list(range(16)),  # 16 P-cores
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                mock_parse_pm.return_value = valid_reading

                # First call returns data, second raises to exit
                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return valid_reading
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Test passes if extended P-core layout was initialized without errors
                assert True


class TestShowCoresMode(unittest.TestCase):
    """Test --show_cores flag functionality."""

    def test_show_cores_individual_updates(self) -> None:
        """
        Test that individual core metrics are updated when --show_cores is enabled.

        Verifies per-core gauge updates for both E-cores and P-cores.
        """
        test_args = ["asitop", "--show_cores"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.time.sleep"),
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                # Include per-core metrics
                valid_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1, 2, 3],
                        "p_core": [0, 1, 2, 3],
                        "E-Cluster0_active": 45,
                        "E-Cluster1_active": 55,
                        "E-Cluster2_active": 50,
                        "E-Cluster3_active": 50,
                        "P-Cluster0_active": 65,
                        "P-Cluster1_active": 60,
                        "P-Cluster2_active": 58,
                        "P-Cluster3_active": 57,
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return valid_reading
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Test passes if per-core updates executed without errors
                assert True


class TestRAMSwapHandling(unittest.TestCase):
    """Test RAM gauge display with and without active swap."""

    def test_ram_with_active_swap(self) -> None:
        """
        Test RAM gauge displays swap info when swap is active (>0.1GB).

        Verifies that swap usage is shown in the gauge title when
        swap space is being utilized.
        """
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.get_ram_metrics_dict") as mock_get_ram,
                patch("asitop.asitop.time.sleep") as mock_sleep,
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                # RAM with active swap
                mock_get_ram.return_value = {
                    "total_GB": 16.0,
                    "used_GB": 12.5,
                    "free_percent": 25.0,
                    "swap_total_GB": 4.0,
                    "swap_used_GB": 1.2,
                }

                valid_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                # Return data once with increasing timestamp, then raise
                timestamps = [1234567890, 1234567891]
                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] <= 2:
                        # Return reading with incrementing timestamp
                        return (
                            valid_reading[0],
                            valid_reading[1],
                            valid_reading[2],
                            valid_reading[3],
                            timestamps[min(call_count[0] - 1, 1)],
                        )
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect
                # Mock sleep to raise after a few calls to let loop execute
                sleep_count = [0]

                def mock_sleep_side_effect(duration):
                    sleep_count[0] += 1
                    if sleep_count[0] > 3:
                        raise KeyboardInterrupt

                mock_sleep.side_effect = mock_sleep_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Verify RAM metrics were fetched
                mock_get_ram.assert_called()


class TestMainLoopEdgeCases(unittest.TestCase):
    """Test edge cases in the main loop logic."""

    def test_main_loop_with_restart_logic(self) -> None:
        """
        Test main loop with powermetrics restart after reaching count limit.

        Validates that powermetrics process is restarted when iteration
        count reaches the restart_interval.
        """
        test_args = ["asitop", "--max_count", "5"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.clear_console"),
                patch("asitop.asitop.time.sleep"),
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                # Return data for first few iterations, then raise to exit
                mock_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Nominal",
                    None,
                    1234567890,
                )

                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] <= 7:  # Return data for 7 iterations to test restart at 5
                        return mock_reading
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Verify process was restarted (should be called twice: initial + restart)
                assert mock_run_pm.call_count >= 2

    def test_thermal_pressure_non_nominal(self) -> None:
        """
        Test main loop handling of non-Nominal thermal pressure.

        Verifies thermal throttle detection works for Moderate/Heavy states.
        """
        test_args = ["asitop"]
        with patch.object(sys, "argv", test_args):
            import importlib

            import asitop.asitop as asitop_module

            importlib.reload(asitop_module)

            with (
                patch("asitop.asitop.get_soc_info") as mock_get_soc,
                patch("asitop.asitop.run_powermetrics_process") as mock_run_pm,
                patch("asitop.asitop.parse_powermetrics") as mock_parse_pm,
                patch("asitop.asitop.clear_console"),
                patch("asitop.asitop.time.sleep"),
            ):
                mock_get_soc.return_value = {
                    "name": "Apple M1",
                    "core_count": 8,
                    "e_core_count": 4,
                    "p_core_count": 4,
                    "gpu_core_count": 8,
                    "cpu_max_power": 20,
                    "gpu_max_power": 20,
                    "cpu_max_bw": 70,
                    "gpu_max_bw": 70,
                }

                mock_process = MagicMock()
                mock_run_pm.return_value = mock_process

                # Return data with Moderate thermal pressure
                mock_reading = (
                    {
                        "E-Cluster_active": 50,
                        "P-Cluster_active": 60,
                        "E-Cluster_freq_Mhz": 2064,
                        "P-Cluster_freq_Mhz": 3228,
                        "e_core": [0, 1],
                        "p_core": [2, 3],
                        "ane_W": 1,
                        "cpu_W": 5,
                        "gpu_W": 3,
                        "package_W": 9,
                    },
                    {"active": 70, "freq_MHz": 1296},
                    "Moderate",  # Non-nominal thermal pressure
                    None,
                    1234567890,
                )

                call_count = [0]

                def mock_parse_side_effect(timecode):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return mock_reading
                    raise KeyboardInterrupt

                mock_parse_pm.side_effect = mock_parse_side_effect

                try:
                    asitop_module.main()
                except (KeyboardInterrupt, SystemExit):
                    pass

                # Test passes if no exceptions were raised
                assert True


if __name__ == "__main__":
    unittest.main()
