"""Test type contracts to ensure compatibility with typed libraries like dashing.

These tests validate that return values match the expected types for library
contracts, catching issues that static type checkers find but runtime tests
might miss.
"""

from typing import Any
from unittest.mock import MagicMock, patch


def get_sample_powermetrics_data() -> dict[str, Any]:
    """Create sample powermetrics data for testing.

    Returns a realistic powermetrics dictionary structure with all required
    fields for testing CPU and GPU parsing.
    """
    return {
        "processor": {
            "clusters": [
                {
                    "name": "E-Cluster",
                    "freq_hz": 2064000000,
                    "idle_ratio": 0.8,
                    "cpus": [
                        {"cpu": 0, "freq_hz": 2064000000, "idle_ratio": 0.75},
                        {"cpu": 1, "freq_hz": 2064000000, "idle_ratio": 0.85},
                        {"cpu": 2, "freq_hz": 2064000000, "idle_ratio": 0.80},
                        {"cpu": 3, "freq_hz": 2064000000, "idle_ratio": 0.80},
                    ],
                },
                {
                    "name": "P-Cluster",
                    "freq_hz": 3228000000,
                    "idle_ratio": 0.5,
                    "cpus": [
                        {"cpu": 4, "freq_hz": 3228000000, "idle_ratio": 0.45},
                        {"cpu": 5, "freq_hz": 3228000000, "idle_ratio": 0.50},
                        {"cpu": 6, "freq_hz": 3228000000, "idle_ratio": 0.55},
                        {"cpu": 7, "freq_hz": 3228000000, "idle_ratio": 0.50},
                    ],
                },
            ],
            "ane_energy": 100,
            "cpu_energy": 5000,
            "gpu_energy": 3000,
            "combined_power": 8500,
        },
        "gpu": {"freq_hz": 1296000000, "idle_ratio": 0.25, "gpu_energy": 3000},
    }


class TestGaugeValueTypes:
    """Test that all gauge values are properly typed as int for dashing.HGauge/VGauge."""

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_ram_gauge_value_is_int(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """RAM gauge values must be int for dashing.HGauge compatibility.

        The dashing library's HGauge.value expects int, not float or None.
        This test ensures get_ram_metrics_dict() returns proper types.
        """
        from asitop.utils import get_ram_metrics_dict

        # Setup realistic mocks
        mock_ram.return_value = MagicMock(
            total=17179869184,  # 16 GB
            available=8589934592,  # 8 GB
        )
        mock_swap.return_value = MagicMock(
            total=1073741824,  # 1 GB
            used=536870912,  # 0.5 GB
        )

        metrics = get_ram_metrics_dict()

        # free_percent must be int, not float
        assert isinstance(
            metrics["free_percent"], int
        ), f"free_percent must be int, got {type(metrics['free_percent'])}"

        # swap_free_percent must be int when swap exists
        assert isinstance(
            metrics["swap_free_percent"], int
        ), f"swap_free_percent must be int, got {type(metrics['swap_free_percent'])}"

        # Verify the value is in valid range
        assert 0 <= metrics["free_percent"] <= 100
        assert 0 <= metrics["swap_free_percent"] <= 100

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_ram_gauge_value_is_int_no_swap(
        self, mock_swap: MagicMock, mock_ram: MagicMock
    ) -> None:
        """RAM gauge values must be int even when swap is disabled.

        Edge case: When swap_total is 0, swap_free_percent should be 0 (int),
        not None, to maintain type consistency.
        """
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(
            total=17179869184,  # 16 GB
            available=8589934592,  # 8 GB
        )
        mock_swap.return_value = MagicMock(
            total=0,  # No swap
            used=0,
        )

        metrics = get_ram_metrics_dict()

        # swap_free_percent must still be int (0), not None
        assert isinstance(metrics["swap_free_percent"], int), (
            f"swap_free_percent must be int even with no swap, "
            f"got {type(metrics['swap_free_percent'])}"
        )
        assert metrics["swap_free_percent"] == 0

    def test_cpu_gauge_values_are_int(self) -> None:
        """CPU gauge values must be int for dashing.HGauge compatibility.

        parse_cpu_metrics() returns various *_active and *_freq_Mhz values that
        are assigned to HGauge.value. All must be int, not float.
        """
        from asitop.parsers import parse_cpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_cpu_metrics(sample_data)

        # All *_active values must be int (these are percentages)
        active_keys = [k for k in metrics if k.endswith("_active")]
        assert len(active_keys) > 0, "Should have at least one *_active key"

        for key in active_keys:
            value = metrics[key]
            assert isinstance(
                value, int
            ), f"{key} must be int, got {type(value)} with value {value}"
            assert 0 <= value <= 100, f"{key} percentage must be 0-100, got {value}"

        # All *_freq_Mhz values must be int (these are frequencies)
        freq_keys = [k for k in metrics if k.endswith("_freq_Mhz")]
        assert len(freq_keys) > 0, "Should have at least one *_freq_Mhz key"

        for key in freq_keys:
            value = metrics[key]
            assert isinstance(
                value, int
            ), f"{key} must be int, got {type(value)} with value {value}"
            assert value >= 0, f"{key} frequency must be non-negative, got {value}"

    def test_gpu_gauge_values_are_int(self) -> None:
        """GPU gauge values must be int for dashing.HGauge compatibility.

        parse_gpu_metrics() returns 'active' and 'freq_MHz' that are assigned
        to HGauge.value. Both must be int, not float.
        """
        from asitop.parsers import parse_gpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_gpu_metrics(sample_data)

        # GPU active percentage must be int
        assert isinstance(
            metrics["active"], int
        ), f"GPU active must be int, got {type(metrics['active'])}"
        assert 0 <= metrics["active"] <= 100, f"GPU active must be 0-100, got {metrics['active']}"

        # GPU frequency must be int
        assert isinstance(
            metrics["freq_MHz"], int
        ), f"GPU freq_MHz must be int, got {type(metrics['freq_MHz'])}"
        assert (
            metrics["freq_MHz"] >= 0
        ), f"GPU freq_MHz must be non-negative, got {metrics['freq_MHz']}"

    def test_calculate_gpu_usage_returns_int(self) -> None:
        """calculate_gpu_usage must return int for utilization percentage.

        The gpu_util_percent value is assigned to HGauge.value, so it must be int.
        """
        from asitop.asitop import calculate_gpu_usage

        # Test with active GPU
        gpu_metrics = {"freq_MHz": 1296, "active": 75}
        gpu_util, gpu_freq = calculate_gpu_usage(
            gpu_metrics, gpu_power_watts=15.0, gpu_max_power=50.0, last_gpu_freq_mhz=None
        )

        assert isinstance(gpu_util, int), f"GPU utilization must be int, got {type(gpu_util)}"
        assert 0 <= gpu_util <= 100, f"GPU utilization must be 0-100, got {gpu_util}"

        # freq can be int or None
        assert gpu_freq is None or isinstance(
            gpu_freq, int
        ), f"GPU frequency must be int or None, got {type(gpu_freq)}"

        # Test with power-based fallback
        gpu_metrics_idle = {"freq_MHz": 0, "active": 0}
        gpu_util, gpu_freq = calculate_gpu_usage(
            gpu_metrics_idle,
            gpu_power_watts=10.0,
            gpu_max_power=50.0,
            last_gpu_freq_mhz=1200,
        )

        assert isinstance(
            gpu_util, int
        ), f"GPU utilization (power-based) must be int, got {type(gpu_util)}"
        assert 0 <= gpu_util <= 100, f"GPU utilization must be 0-100, got {gpu_util}"


class TestNumericValueRanges:
    """Test that numeric values are within expected ranges.

    Beyond just type checking, these tests validate that values make sense
    for the domain (e.g., percentages are 0-100, frequencies are positive).
    """

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_ram_metrics_reasonable_values(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """RAM metrics should have reasonable values."""
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(
            total=17179869184,  # 16 GB
            available=8589934592,  # 8 GB
        )
        mock_swap.return_value = MagicMock(
            total=2147483648,  # 2 GB
            used=1073741824,  # 1 GB
        )

        metrics = get_ram_metrics_dict()

        # GB values should be positive floats
        assert metrics["total_GB"] > 0
        assert metrics["free_GB"] >= 0
        assert metrics["used_GB"] >= 0
        assert isinstance(metrics["total_GB"], float)
        assert isinstance(metrics["free_GB"], float)
        assert isinstance(metrics["used_GB"], float)

        # Used + Free should approximately equal Total
        # (using approximate because of rounding)
        assert abs(metrics["used_GB"] + metrics["free_GB"] - metrics["total_GB"]) < 0.2

        # Percentages should be 0-100
        assert 0 <= metrics["free_percent"] <= 100
        assert 0 <= metrics["swap_free_percent"] <= 100

    def test_cpu_metrics_reasonable_values(self) -> None:
        """CPU metrics should have reasonable values."""
        from asitop.parsers import parse_cpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_cpu_metrics(sample_data)

        # Frequencies should be reasonable (typically 600-3500 MHz for Apple Silicon)
        for key in metrics:
            if key.endswith("_freq_Mhz"):
                freq = metrics[key]
                # Allow 0 for idle, otherwise should be in reasonable range
                assert (
                    freq == 0 or 100 <= freq <= 5000
                ), f"{key} frequency {freq} MHz seems unreasonable"

        # Power values should be positive floats
        assert metrics["cpu_W"] >= 0
        assert metrics["gpu_W"] >= 0
        assert metrics["ane_W"] >= 0
        assert isinstance(metrics["cpu_W"], float)
        assert isinstance(metrics["gpu_W"], float)
        assert isinstance(metrics["ane_W"], float)

        # Core lists should contain valid core numbers
        assert isinstance(metrics["e_core"], list)
        assert isinstance(metrics["p_core"], list)
        assert len(metrics["e_core"]) > 0  # All Apple Silicon has E cores
        assert len(metrics["p_core"]) > 0  # All Apple Silicon has P cores

    def test_gpu_metrics_reasonable_values(self) -> None:
        """GPU metrics should have reasonable values."""
        from asitop.parsers import parse_gpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_gpu_metrics(sample_data)

        # Frequency should be 0 (idle) or in reasonable range (typically 300-1500 MHz)
        freq = metrics["freq_MHz"]
        assert freq == 0 or 100 <= freq <= 3000, f"GPU frequency {freq} MHz seems unreasonable"

        # Active percentage should be clamped to 0-100
        assert 0 <= metrics["active"] <= 100


class TestTypeConsistency:
    """Test that types are consistent across different code paths.

    These tests ensure that edge cases (empty data, zero values, etc.)
    don't return different types than normal cases.
    """

    def test_gpu_metrics_type_consistency_with_zero_freq(self) -> None:
        """GPU metrics should return int even when frequency is 0."""
        from asitop.parsers import parse_gpu_metrics

        # Test with zero frequency (idle GPU)
        gpu_data = {"gpu": {"freq_hz": 0, "idle_ratio": 1.0}}

        metrics = parse_gpu_metrics(gpu_data)

        # Should still return int, not None
        assert isinstance(metrics["freq_MHz"], int)
        assert metrics["freq_MHz"] == 0

    def test_gpu_metrics_type_consistency_with_dvfm_states(self) -> None:
        """GPU metrics should derive int frequency from DVFM states."""
        from asitop.parsers import parse_gpu_metrics

        # Test with DVFM states (newer powermetrics format)
        gpu_data = {
            "gpu": {
                "freq_hz": 0,
                "idle_ratio": 0.5,
                "dvfm_states": [
                    {"freq": 396, "used_ratio": 0.2},
                    {"freq": 792, "used_ratio": 0.3},
                    {"freq": 1296, "used_ratio": 0.5},
                ],
            }
        }

        metrics = parse_gpu_metrics(gpu_data)

        # Should calculate weighted average and return int
        assert isinstance(metrics["freq_MHz"], int)
        assert metrics["freq_MHz"] > 0  # Should have calculated from DVFM

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_ram_metrics_type_consistency_edge_cases(
        self, mock_swap: MagicMock, mock_ram: MagicMock
    ) -> None:
        """RAM metrics should maintain type consistency in edge cases."""
        from asitop.utils import get_ram_metrics_dict

        # Test with zero available RAM (extreme case)
        mock_ram.return_value = MagicMock(
            total=17179869184,
            available=0,  # All RAM used
        )
        mock_swap.return_value = MagicMock(total=0, used=0)

        metrics = get_ram_metrics_dict()

        # Should still return int for percentages
        assert isinstance(metrics["free_percent"], int)
        assert metrics["free_percent"] == 100  # 100% used = 100% not free

        # Test with full RAM available
        mock_ram.return_value = MagicMock(total=17179869184, available=17179869184)  # All RAM free

        metrics = get_ram_metrics_dict()

        assert isinstance(metrics["free_percent"], int)
        assert metrics["free_percent"] == 0  # 0% used = 0% not free


class TestReturnValueStructure:
    """Test that return values have the expected structure.

    These tests validate dictionary keys and types, ensuring consistent
    API contracts across the codebase.
    """

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_ram_metrics_dict_structure(self, mock_swap: MagicMock, mock_ram: MagicMock) -> None:
        """Validate complete structure of RAM metrics dictionary."""
        from asitop.utils import get_ram_metrics_dict

        mock_ram.return_value = MagicMock(total=17179869184, available=8589934592)
        mock_swap.return_value = MagicMock(total=1073741824, used=536870912)

        metrics = get_ram_metrics_dict()

        # Required keys
        required_keys = {
            "total_GB",
            "free_GB",
            "used_GB",
            "free_percent",
            "swap_total_GB",
            "swap_used_GB",
            "swap_free_GB",
            "swap_free_percent",
        }
        assert (
            set(metrics.keys()) == required_keys
        ), f"Missing or extra keys: {set(metrics.keys()) ^ required_keys}"

        # Type validation for each key
        expected_types = {
            "total_GB": float,
            "free_GB": float,
            "used_GB": float,
            "free_percent": int,
            "swap_total_GB": float,
            "swap_used_GB": float,
            "swap_free_GB": float,
            "swap_free_percent": int,
        }

        for key, expected_type in expected_types.items():
            actual_type = type(metrics[key])
            assert actual_type == expected_type, (
                f"{key} should be {expected_type.__name__}, " f"got {actual_type.__name__}"
            )

    def test_gpu_metrics_dict_structure(self) -> None:
        """Validate complete structure of GPU metrics dictionary."""
        from asitop.parsers import parse_gpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_gpu_metrics(sample_data)

        # Required keys
        required_keys = {"freq_MHz", "active"}
        assert (
            set(metrics.keys()) == required_keys
        ), f"Missing or extra keys: {set(metrics.keys()) ^ required_keys}"

        # Type validation
        assert isinstance(metrics["freq_MHz"], int)
        assert isinstance(metrics["active"], int)

    def test_cpu_metrics_dict_has_required_keys(self) -> None:
        """Validate CPU metrics dictionary has minimum required keys."""
        from asitop.parsers import parse_cpu_metrics

        sample_data = get_sample_powermetrics_data()
        metrics = parse_cpu_metrics(sample_data)

        # Minimum required keys (actual keys vary by chip)
        required_keys = {
            "E-Cluster_active",
            "E-Cluster_freq_Mhz",
            "P-Cluster_active",
            "P-Cluster_freq_Mhz",
            "cpu_W",
            "gpu_W",
            "ane_W",
            "package_W",
            "e_core",
            "p_core",
        }

        missing_keys = required_keys - set(metrics.keys())
        assert not missing_keys, f"CPU metrics missing required keys: {missing_keys}"
