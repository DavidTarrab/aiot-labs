"""Package the handout p.13 code categories alongside the p.14 report."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from lab_status import pending_evidence

# Preserve working source files in place; organize their archive destinations by task.
GROUPS = {
    'task1': ['har_dataset.py', 'download_data.py'],
    'task2': ['har_gemini.py', 'lab6_dt2811_ms7635_rnb2135_check1.py'],
    'task3/desktop': ['lab6_dt2811_ms7635_rnb2135_check2_app.py', 'lab5_interpreter.py', 'collect_activities.py'],
    'task3/esp32': ['har_device.py', 'lab5_watch.py', 'ssd1306.py', 'lab6_dt2811_ms7635_rnb2135_check2_esp32.py'],
    'task4': ['lab6_dt2811_ms7635_rnb2135_server.py'],
    'task4/esp32': ['lab6_dt2811_ms7635_rnb2135_check3_esp32.py'],
    'task5': ['task5_zero_shot.py', 'task5_linear_probe.py', 'har_normwear.py', 'setup_normwear.py'],
    'task5/esp32': ['lab6_dt2811_ms7635_rnb2135_check4_esp32.py'],
    'shared': ['har_common.py', 'har_client.py', 'lab_status.py'],
    'tools': ['dashboard.py', 'dashboard.html', 'usb_tool.py', 'record_cloud_demo.py', 'make_report.py',
              'verify_cloud_results.py', 'verify_live_cloud.py', 'audit_encoder_cache.py',
              'cloud_api_smoke.py', 'cloud_smoke.py'],
    'tests': ['test_lab6.py', 'test_dashboard.py'],
    'report': ['lab6_dt2811_ms7635_rnb2135_report.pdf', 'lab6_dt2811_ms7635_rnb2135_report.md'],
}


def package(root, destination):
    root = Path(root).resolve()
    pending = pending_evidence(root)
    if destination is None:
        destination = root / ('lab6_dt2811_ms7635_rnb2135' + ('_draft' if pending else '') + '.zip')
    destination = Path(destination).resolve()
    if pending and not destination.stem.endswith('_draft'):
        destination = destination.with_stem(destination.stem + '_draft')
    files = {'README.md': root / 'SUBMISSION_README.md', 'run.py': root / 'submission_run.py'}
    for group, names in GROUPS.items():
        for name in names:
            files[group + '/' + name] = root / name
    for name in ('requirements.txt', 'requirements-cloud.txt', 'requirements-normwear.txt', 'cloud-constraints.txt'):
        files[name] = root / name
    for path in sorted((root / 'results').glob('*')):
        if path.is_file() and path.suffix in ('.json', '.jsonl', '.png', '.jpg'):
            files['results/' + path.name] = path
    for name in ('cloud_run.log', 'server.log'):
        path = root / 'logs' / name
        if path.is_file():
            files['logs/' + name] = path
    for name in ('linear_probe.pt', 'embeddings.pt'):
        path = root / 'artifacts' / name
        if path.is_file():
            files['artifacts/' + name] = path
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError('Required submission files missing: ' + ', '.join(missing))
    manifest = {'specification': 'Lab 6 (1).pdf, code list p.13; report checklist p.14',
                'report_task_order': ['2', '3', '5.1', '5.2', '5.3'],
                'required_code_categories': ['task1', 'task2', 'task3', 'task4', 'task5'],
                'pending_evidence': pending,
                'files': {name: {'source': path.relative_to(root).as_posix(),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                          for name, path in sorted(files.items())}}
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, 'lab6/' + name)
        archive.writestr('lab6/submission_manifest.json', json.dumps(manifest, indent=2) + '\n')
    print('Draft package:' if pending else 'Submission:', destination, 'files:', len(files) + 1)
    if pending:
        print('Pending:', '; '.join(pending))
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--output')
    args = parser.parse_args()
    package(args.root, args.output)
