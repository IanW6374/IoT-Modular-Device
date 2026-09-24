#!/usr/bin/env python3
"""Run the non-qualifying simulated fault and recovery regression campaign."""

import argparse
import io
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'
SUITES = (
    'test_recovery_boot', 'test_app_update', 'test_firmware_update',
    'test_universal_update', 'test_v3_cutover',
    'test_v3_identity_fleet_migration', 'test_v3_operational_qualification',
    'test_v3_qualification_runner', 'test_qualification_control',
    'test_device_api',
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(TESTS))
    started = time.time()
    suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES)
    detail = io.StringIO()
    result = unittest.TextTestRunner(stream=detail, verbosity=2).run(suite)
    report = {
        'format_version': 1,
        'evidence_class': 'simulated-regression',
        'qualifying': False,
        'started_at': int(started),
        'duration_s': round(time.time() - started, 3),
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'passed': result.wasSuccessful(),
        'suites': list(SUITES),
        'detail': detail.getvalue()[-12000:],
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
