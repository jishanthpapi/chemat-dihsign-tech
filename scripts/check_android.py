"""Record native tooling readiness without installing SDKs or accepting licenses."""
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    flutter = shutil.which('flutter') or str(ROOT / '.tools/flutter/bin/flutter.bat')
    destination = ROOT / 'reports/android-readiness'
    destination.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, arguments in (
        ('doctor', ['doctor', '-v']),
        ('devices', ['devices', '--machine']),
    ):
        try:
            result = subprocess.run(
                [flutter, *arguments], cwd=ROOT / 'mobile',
                capture_output=True, text=True, encoding='utf-8',
                errors='replace', timeout=120,
            )
            (destination / f'{name}.log').write_text(
                result.stdout + result.stderr, encoding='utf-8',
            )
            results[name] = {'exit_code': result.returncode}
            if name == 'devices' and result.returncode == 0:
                devices = json.loads(result.stdout)
                results['android_devices'] = [
                    {'id': device['id'], 'name': device['name']}
                    for device in devices
                    if device.get('targetPlatform', '').startswith('android')
                ]
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            results[name] = {'error': str(error)}
    # Doctor may exit zero with missing toolchains; its log needs review.
    results['native_acceptance_verified'] = False
    results['next_command'] = (
        'flutter test integration_test/native_storage_test.dart -d <android-device-id>'
    )
    (destination / 'summary.json').write_text(
        json.dumps(results, indent=2), encoding='utf-8',
    )
    print(json.dumps(results, indent=2))
    return int(any('error' in results[name] or results[name]['exit_code'] != 0
                   for name in ('doctor', 'devices')))


if __name__ == '__main__':
    raise SystemExit(main())
