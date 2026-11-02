#!/usr/bin/env python3
"""Personalize the disposable Hex iOS checkout, never the upstream repository."""
import json
import os
from pathlib import Path
import re
import sys


def prepare(directory, config, team):
    if config['app'] != 'hex' or config['adapter'] != 'xcodegen':
        raise ValueError('This preparation hook is reviewed only for Hex')
    if not re.fullmatch(r'[A-Z0-9]{10}', team):
        raise ValueError('Configure a valid APPLE_TEAM_ID')
    directory = Path(directory)
    project = directory / 'project.yml'
    text = project.read_text()
    if 'com.kitlangton.hex.mobile' not in text or 'DEVELOPMENT_TEAM: QC99C9JE59' not in text:
        raise ValueError('Upstream identity changed; review preparation hook')
    for path in directory.rglob('*'):
        if not path.is_file() or path.suffix not in ('.swift', '.plist', '.entitlements', '.yml'):
            continue
        text = path.read_text()
        text = text.replace('com.kitlangton.hex.mobile', config['bundle_id'])
        text = text.replace('hex-dictation', config['url_scheme'])
        if path == project:
            text = text.replace('bundleIdPrefix: com.kitlangton.hex', 'bundleIdPrefix: ' + config['bundle_id'])
            text = text.replace('DEVELOPMENT_TEAM: QC99C9JE59', 'DEVELOPMENT_TEAM: ' + team)
        path.write_text(text)


if __name__ == '__main__':
    prepare(sys.argv[1], json.loads(os.environ['APP_CONFIG']), os.environ['APPLE_TEAM_ID'])
