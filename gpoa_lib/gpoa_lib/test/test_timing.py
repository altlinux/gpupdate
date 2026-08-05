import time

from gpoa_lib.util.timing import TimedExecution


def test_timedexecution_records_elapsed_time():
    with TimedExecution('test') as t:
        time.sleep(0.01)

    assert t.name == 'test'
    assert t.elapsed > 0.0
    assert t.elapsed < 1.0
    assert round(t.elapsed, 3)
