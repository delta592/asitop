"""Entry point for running asitop as a module (python -m asitop)."""

from .asitop import main


if __name__ == "__main__":
    powermetrics_process, timecode = main()
    # Cleanup is handled by asitop.py when run as a script
    # When run as a module, we need to handle cleanup here
    import contextlib
    import pathlib
    import subprocess
    import sys

    from .utils import get_powermetrics_path

    exit_code = 0
    try:
        if powermetrics_process.poll() is None:  # Process is still running
            # Terminate the process
            powermetrics_process.terminate()

            try:
                powermetrics_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Process didn't terminate gracefully, force kill it
                powermetrics_process.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    powermetrics_process.wait(timeout=2)

        # Additional cleanup: kill any orphaned powermetrics processes
        # This handles the sudo process chain that may not terminate with the parent
        # Use sudo pkill to ensure we have permissions to kill powermetrics
        with contextlib.suppress(Exception):
            subprocess.run(
                ["sudo", "pkill", "-f", "^powermetrics.*asitop_powermetrics"],
                timeout=2,
                check=False,
                capture_output=True,
            )

        # Clean up the temporary powermetrics output file
        temp_file = pathlib.Path(get_powermetrics_path(timecode))
        with contextlib.suppress(FileNotFoundError, PermissionError):
            temp_file.unlink()
    except Exception:
        # Final fallback: try to kill forcefully and ignore errors
        with contextlib.suppress(Exception):
            powermetrics_process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                powermetrics_process.wait(timeout=1)

    sys.exit(exit_code)
