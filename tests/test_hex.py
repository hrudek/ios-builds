import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from config import load_app

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

prepare = module('prepare_hex', 'prepare-hex.py')
signing = module('hex_signing', 'signing-entitlements.py')


class HexTests(unittest.TestCase):
    def test_manifest(self):
        config = load_app('hex')
        self.assertEqual(config['adapter'], 'xcodegen')
        self.assertEqual(config['bundle_ids'], ['com.bearylabs.hex',
                                              'com.bearylabs.hex.keyboard',
                                              'com.bearylabs.hex.widgets'])
        self.assertEqual(len(config['default_ref']), 40)

    def test_entitlements_per_target(self):
        config = load_app('hex')
        for bid in config['bundle_ids'][:2]:
            self.assertEqual(signing.required_entitlements(config, bid),
                             {'com.apple.security.application-groups': ['group.com.bearylabs.hex']})
        self.assertEqual(signing.required_entitlements(config, config['bundle_ids'][2]), {})
        with self.assertRaises(ValueError):
            signing.required_entitlements(config, 'com.unreviewed.app')

    def test_personalize_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'project.yml').write_text(
                'bundleIdPrefix: com.kitlangton.hex\n'
                'DEVELOPMENT_TEAM: QC99C9JE59\n'
                'PRODUCT_BUNDLE_IDENTIFIER: com.kitlangton.hex.mobile\n')
            (root / 'Bridge.swift').write_text(
                'group.com.kitlangton.hex.mobile hex-dictation com.kitlangton.hex.mobile.keyboard')
            (root / 'app.entitlements').write_bytes(plistlib.dumps({
                'com.apple.security.application-groups': ['group.com.kitlangton.hex.mobile']}))
            prepare.prepare(root, load_app('hex'), 'TEAM123456')
            self.assertIn('DEVELOPMENT_TEAM: TEAM123456', (root / 'project.yml').read_text())
            self.assertNotIn('kitlangton', (root / 'project.yml').read_text())
            self.assertEqual((root / 'Bridge.swift').read_text(),
                             'group.com.bearylabs.hex bearylabs-hex com.bearylabs.hex.keyboard')
            self.assertEqual(plistlib.loads((root / 'app.entitlements').read_bytes()),
                             {'com.apple.security.application-groups': ['group.com.bearylabs.hex']})

    def test_fail_closed_on_upstream_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'project.yml').write_text('unreviewed project')
            with self.assertRaises(ValueError):
                prepare.prepare(tmp, load_app('hex'), 'TEAM123456')

    def test_reject_invalid_team(self):
        with self.assertRaises(ValueError):
            prepare.prepare('.', load_app('hex'), 'bad\nTEAM')


if __name__ == '__main__':
    unittest.main()
