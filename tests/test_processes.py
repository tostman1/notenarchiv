"""Real owned child/grandchild cleanup on cancellation, deadline and normal exit."""

import sys
import time

import pytest

from core.processes import ProcessFailed, ProcessTimeout, run_process


@pytest.mark.parametrize("mode", ["timeout", "cancel", "normal"])
def test_process_tree_stops_before_return(tmp_path, mode):
    pulse = tmp_path / "synthetic-pulse"
    child = (
        "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
        "exec('while True:\\n p.write_text(str(time.monotonic()))\\n time.sleep(.02)')"
    )
    # The child and grandchild are both test-owned and started by this helper.
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r},sys.argv[1]]); " + (
        "time.sleep(.4)" if mode == "normal" else "time.sleep(30)"
    )

    class SyntheticCancellation(Exception):
        pass

    def checkpoint():
        if mode == "cancel" and pulse.exists():
            raise SyntheticCancellation

    expected = {"timeout": ProcessTimeout, "cancel": SyntheticCancellation}
    if mode in expected:
        with pytest.raises(expected[mode]):
            run_process([sys.executable, "-c", parent, str(pulse)], timeout=1.5, checkpoint=checkpoint)
    else:
        run_process([sys.executable, "-c", parent, str(pulse)], timeout=5, checkpoint=checkpoint)
    assert pulse.exists()
    before = pulse.read_bytes()
    time.sleep(0.15)
    assert pulse.read_bytes() == before


def test_process_failures_do_not_expose_output():
    with pytest.raises(ProcessFailed) as error:
        run_process([sys.executable, "-c", "import sys; print('synthetic-private'); sys.exit(1)"], timeout=5)
    assert "synthetic-private" not in str(error.value)


@pytest.mark.parametrize(
    "arguments,timeout", [("echo unsafe", 1), ([], 1), (["invalid"], 0), (["invalid"], float("inf"))]
)
def test_invalid_process_contract_is_rejected(arguments, timeout):
    with pytest.raises(ValueError):
        run_process(arguments, timeout=timeout)
