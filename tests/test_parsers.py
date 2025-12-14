"""
Unit tests for the parsers module.

This module tests all parsing functions that extract metrics from
powermetrics output, including thermal pressure, bandwidth, CPU, and GPU data.
"""

import unittest
from typing import Dict, Any


class TestParseThermalPressure(unittest.TestCase):
    """Test cases for parse_thermal_pressure function."""

    def test_parse_thermal_pressure_nominal(self) -> None:
        """
        Test parsing thermal pressure when status is Nominal.

        Verifies that the function correctly extracts the thermal pressure
        value from the powermetrics data structure.
        """
        from asitop.parsers import parse_thermal_pressure

        mock_data: Dict[str, str] = {"thermal_pressure": "Nominal"}
        result = parse_thermal_pressure(mock_data)
        self.assertEqual(result, "Nominal")

    def test_parse_thermal_pressure_moderate(self) -> None:
        """
        Test parsing thermal pressure when status is Moderate.

        Ensures the function handles non-Nominal thermal states correctly.
        """
        from asitop.parsers import parse_thermal_pressure

        mock_data: Dict[str, str] = {"thermal_pressure": "Moderate"}
        result = parse_thermal_pressure(mock_data)
        self.assertEqual(result, "Moderate")

    def test_parse_thermal_pressure_heavy(self) -> None:
        """
        Test parsing thermal pressure when status is Heavy.

        Validates handling of high thermal pressure scenarios.
        """
        from asitop.parsers import parse_thermal_pressure

        mock_data: Dict[str, str] = {"thermal_pressure": "Heavy"}
        result = parse_thermal_pressure(mock_data)
        self.assertEqual(result, "Heavy")


class TestParseBandwidthMetrics(unittest.TestCase):
    """Test cases for parse_bandwidth_metrics function."""

    def test_parse_bandwidth_metrics_basic(self) -> None:
        """
        Test basic bandwidth metrics parsing.

        Verifies that the function correctly initializes all bandwidth
        counters and parses basic read/write metrics.
        """
        from asitop.parsers import parse_bandwidth_metrics

        mock_data: Dict[str, Any] = {
            "bandwidth_counters": [
                {"name": "DCS RD", "value": 1000000000},
                {"name": "DCS WR", "value": 2000000000},
            ]
        }
        result = parse_bandwidth_metrics(mock_data)

        self.assertIn("DCS RD", result)
        self.assertIn("DCS WR", result)
        self.assertAlmostEqual(result["DCS RD"], 1.0, places=2)
        self.assertAlmostEqual(result["DCS WR"], 2.0, places=2)

    def test_parse_bandwidth_metrics_cpu(self) -> None:
        """
        Test CPU bandwidth metrics parsing and aggregation.

        Ensures that individual PCPU counters are correctly aggregated
        into the total PCPU DCS RD/WR values.
        """
        from asitop.parsers import parse_bandwidth_metrics

        mock_data: Dict[str, Any] = {
            "bandwidth_counters": [
                {"name": "PCPU0 DCS RD", "value": 1000000000},
                {"name": "PCPU1 DCS RD", "value": 2000000000},
                {"name": "PCPU0 DCS WR", "value": 500000000},
                {"name": "PCPU1 DCS WR", "value": 1500000000},
            ]
        }
        result = parse_bandwidth_metrics(mock_data)

        self.assertAlmostEqual(result["PCPU DCS RD"], 3.0, places=2)
        self.assertAlmostEqual(result["PCPU DCS WR"], 2.0, places=2)

    def test_parse_bandwidth_metrics_gpu(self) -> None:
        """
        Test GPU bandwidth metrics parsing.

        Validates correct extraction and conversion of GPU DCS counters.
        """
        from asitop.parsers import parse_bandwidth_metrics

        mock_data: Dict[str, Any] = {
            "bandwidth_counters": [
                {"name": "GFX DCS RD", "value": 5000000000},
                {"name": "GFX DCS WR", "value": 3000000000},
            ]
        }
        result = parse_bandwidth_metrics(mock_data)

        self.assertAlmostEqual(result["GFX DCS RD"], 5.0, places=2)
        self.assertAlmostEqual(result["GFX DCS WR"], 3.0, places=2)

    def test_parse_bandwidth_metrics_media_aggregation(self) -> None:
        """
        Test media bandwidth aggregation from multiple sources.

        Verifies that MEDIA DCS correctly sums bandwidth from ISP, VDEC,
        VENC, JPEG, ProRes, and STRM CODEC components.
        """
        from asitop.parsers import parse_bandwidth_metrics

        mock_data: Dict[str, Any] = {
            "bandwidth_counters": [
                {"name": "ISP DCS RD", "value": 1000000000},
                {"name": "ISP DCS WR", "value": 1000000000},
                {"name": "VDEC DCS RD", "value": 2000000000},
                {"name": "VDEC DCS WR", "value": 2000000000},
            ]
        }
        result = parse_bandwidth_metrics(mock_data)

        expected_media = (1.0 + 1.0 + 2.0 + 2.0)
        self.assertAlmostEqual(result["MEDIA DCS"], expected_media, places=2)

    def test_parse_bandwidth_metrics_empty(self) -> None:
        """
        Test bandwidth parsing with empty counters.

        Edge case: Ensures all metrics are initialized to 0 when no
        bandwidth counters are present in the data.
        """
        from asitop.parsers import parse_bandwidth_metrics

        mock_data: Dict[str, Any] = {"bandwidth_counters": []}
        result = parse_bandwidth_metrics(mock_data)

        self.assertEqual(result["DCS RD"], 0)
        self.assertEqual(result["DCS WR"], 0)
        self.assertEqual(result["MEDIA DCS"], 0)


class TestParseCPUMetrics(unittest.TestCase):
    """Test cases for parse_cpu_metrics function."""

    def test_parse_cpu_metrics_single_cluster(self) -> None:
        """
        Test parsing CPU metrics with single E and P clusters.

        Validates correct extraction of frequency, active ratio, and
        cluster information for standard M1/M2 configurations.
        """
        from asitop.parsers import parse_cpu_metrics

        mock_data: Dict[str, Any] = {
            "processor": {
                "clusters": [
                    {
                        "name": "E-Cluster",
                        "freq_hz": 2064000000,
                        "idle_ratio": 0.8,
                        "cpus": [
                            {"cpu": 0, "freq_hz": 2064000000, "idle_ratio": 0.7},
                            {"cpu": 1, "freq_hz": 2064000000, "idle_ratio": 0.9},
                        ]
                    },
                    {
                        "name": "P-Cluster",
                        "freq_hz": 3228000000,
                        "idle_ratio": 0.3,
                        "cpus": [
                            {"cpu": 2, "freq_hz": 3228000000, "idle_ratio": 0.2},
                            {"cpu": 3, "freq_hz": 3228000000, "idle_ratio": 0.4},
                        ]
                    }
                ],
                "ane_energy": 1000,
                "cpu_energy": 5000,
                "gpu_energy": 3000,
                "combined_power": 9000,
            }
        }
        result = parse_cpu_metrics(mock_data)

        self.assertEqual(result["E-Cluster_freq_Mhz"], 2064)
        self.assertEqual(result["E-Cluster_active"], 20)
        self.assertEqual(result["P-Cluster_freq_Mhz"], 3228)
        self.assertEqual(result["P-Cluster_active"], 70)
        self.assertIn(0, result["e_core"])
        self.assertIn(1, result["e_core"])
        self.assertIn(2, result["p_core"])
        self.assertIn(3, result["p_core"])

    def test_parse_cpu_metrics_m1_ultra(self) -> None:
        """
        Test parsing CPU metrics for M1 Ultra configuration.

        The M1 Ultra has dual E-clusters and quad P-clusters which
        require averaging to get overall cluster metrics.
        """
        from asitop.parsers import parse_cpu_metrics

        mock_data: Dict[str, Any] = {
            "processor": {
                "clusters": [
                    {
                        "name": "E0-Cluster",
                        "freq_hz": 2064000000,
                        "idle_ratio": 0.5,
                        "cpus": [{"cpu": 0, "freq_hz": 2064000000, "idle_ratio": 0.5}]
                    },
                    {
                        "name": "E1-Cluster",
                        "freq_hz": 2064000000,
                        "idle_ratio": 0.7,
                        "cpus": [{"cpu": 1, "freq_hz": 2064000000, "idle_ratio": 0.7}]
                    },
                    {
                        "name": "P0-Cluster",
                        "freq_hz": 3000000000,
                        "idle_ratio": 0.2,
                        "cpus": [{"cpu": 2, "freq_hz": 3000000000, "idle_ratio": 0.2}]
                    },
                    {
                        "name": "P1-Cluster",
                        "freq_hz": 3100000000,
                        "idle_ratio": 0.3,
                        "cpus": [{"cpu": 3, "freq_hz": 3100000000, "idle_ratio": 0.3}]
                    },
                    {
                        "name": "P2-Cluster",
                        "freq_hz": 3200000000,
                        "idle_ratio": 0.4,
                        "cpus": [{"cpu": 4, "freq_hz": 3200000000, "idle_ratio": 0.4}]
                    },
                    {
                        "name": "P3-Cluster",
                        "freq_hz": 3300000000,
                        "idle_ratio": 0.5,
                        "cpus": [{"cpu": 5, "freq_hz": 3300000000, "idle_ratio": 0.5}]
                    }
                ],
                "ane_energy": 2000,
                "cpu_energy": 10000,
                "gpu_energy": 6000,
                "combined_power": 18000,
            }
        }
        result = parse_cpu_metrics(mock_data)

        # M1 Ultra averages the dual E-clusters
        # E0: idle 0.5 -> active 50%, E1: idle 0.7 -> active 30%, avg = (50+30)/2 = 40%
        self.assertEqual(result["E-Cluster_active"], 40)
        # M1 Ultra takes max frequency from E-clusters
        self.assertEqual(result["E-Cluster_freq_Mhz"], 2064)
        # M1 Ultra averages quad P-clusters
        expected_p_active = int((80 + 70 + 60 + 50) / 4)
        self.assertEqual(result["P-Cluster_active"], expected_p_active)
        # M1 Ultra takes max frequency from P-clusters
        self.assertEqual(result["P-Cluster_freq_Mhz"], 3300)

    def test_parse_cpu_metrics_power(self) -> None:
        """
        Test parsing of power/energy metrics.

        Verifies correct extraction and conversion of ANE, CPU, GPU,
        and package power values from milliwatts to watts.
        """
        from asitop.parsers import parse_cpu_metrics

        mock_data: Dict[str, Any] = {
            "processor": {
                "clusters": [
                    {
                        "name": "E-Cluster",
                        "freq_hz": 2000000000,
                        "idle_ratio": 0.5,
                        "cpus": []
                    }
                ],
                "ane_energy": 5000,
                "cpu_energy": 10000,
                "gpu_energy": 8000,
                "combined_power": 23000,
            }
        }
        result = parse_cpu_metrics(mock_data)

        self.assertEqual(result["ane_W"], 5.0)
        self.assertEqual(result["cpu_W"], 10.0)
        self.assertEqual(result["gpu_W"], 8.0)
        self.assertEqual(result["package_W"], 23.0)

    def test_parse_cpu_metrics_individual_cores(self) -> None:
        """
        Test parsing of individual core metrics.

        Ensures per-core frequency and active ratio are correctly
        extracted for detailed monitoring.
        """
        from asitop.parsers import parse_cpu_metrics

        mock_data: Dict[str, Any] = {
            "processor": {
                "clusters": [
                    {
                        "name": "P-Cluster",
                        "freq_hz": 3000000000,
                        "idle_ratio": 0.5,
                        "cpus": [
                            {"cpu": 0, "freq_hz": 2800000000, "idle_ratio": 0.3},
                            {"cpu": 1, "freq_hz": 3200000000, "idle_ratio": 0.7},
                        ]
                    }
                ],
                "ane_energy": 1000,
                "cpu_energy": 5000,
                "gpu_energy": 3000,
                "combined_power": 9000,
            }
        }
        result = parse_cpu_metrics(mock_data)

        self.assertEqual(result["P-Cluster0_freq_Mhz"], 2800)
        self.assertEqual(result["P-Cluster0_active"], 70)
        self.assertEqual(result["P-Cluster1_freq_Mhz"], 3200)
        self.assertEqual(result["P-Cluster1_active"], 30)


class TestParseGPUMetrics(unittest.TestCase):
    """Test cases for parse_gpu_metrics function."""

    def test_parse_gpu_metrics_active(self) -> None:
        """
        Test parsing GPU metrics when GPU is active.

        Verifies correct extraction of GPU frequency and utilization
        from idle ratio calculation.
        """
        from asitop.parsers import parse_gpu_metrics

        mock_data: Dict[str, Any] = {
            "gpu": {
                "freq_hz": 1296000000,
                "idle_ratio": 0.25,
            }
        }
        result = parse_gpu_metrics(mock_data)

        self.assertEqual(result["freq_MHz"], 1296000000)
        self.assertEqual(result["active"], 75)

    def test_parse_gpu_metrics_idle(self) -> None:
        """
        Test parsing GPU metrics when GPU is completely idle.

        Edge case: Ensures correct handling when idle_ratio is 1.0.
        """
        from asitop.parsers import parse_gpu_metrics

        mock_data: Dict[str, Any] = {
            "gpu": {
                "freq_hz": 0,
                "idle_ratio": 1.0,
            }
        }
        result = parse_gpu_metrics(mock_data)

        self.assertEqual(result["freq_MHz"], 0)
        self.assertEqual(result["active"], 0)

    def test_parse_gpu_metrics_full_load(self) -> None:
        """
        Test parsing GPU metrics at maximum utilization.

        Edge case: Validates handling when idle_ratio is 0.0
        (100% active).
        """
        from asitop.parsers import parse_gpu_metrics

        mock_data: Dict[str, Any] = {
            "gpu": {
                "freq_hz": 1398000000,
                "idle_ratio": 0.0,
            }
        }
        result = parse_gpu_metrics(mock_data)

        self.assertEqual(result["freq_MHz"], 1398000000)
        self.assertEqual(result["active"], 100)


if __name__ == '__main__':
    unittest.main()
