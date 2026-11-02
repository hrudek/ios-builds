#!/usr/bin/env python3
"""Local-only provisioning using the existing private Apple API helper.

No credentials are stored in this repository. App Group creation/assignment
must first be completed in Apple's Developer portal. Never revokes resources.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import zipfile

from config import load_app


def main():
    os.umask(0o077)
    root = Path.home() / '.local/share/ios-build-signing'
    spec = importlib.util.spec_from_file_location('local_apple', root / 'apple-api.py')
    apple = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(apple)
    config = load_app('hex')
    # Reuse precisely the registered devices from the existing Ad Hoc profile,
    # without exposing their UDIDs in logs or GitHub variables.
    old_profiles = sorted((root / 'ad-hoc').glob('*.mobileprovision'))
    if not old_profiles:
        raise ValueError('No existing Ad Hoc profile found to select the test device')
    raw = subprocess.check_output(['openssl', 'cms', '-verify', '-inform', 'DER',
                                   '-in', str(old_profiles[0]), '-noverify'], stderr=subprocess.DEVNULL)
    old = plistlib.loads(raw)
    devices = apple.request('GET', '/v1/devices?filter[platform]=IOS&limit=200')
    if devices.get('links', {}).get('next'):
        raise ValueError('Device pagination needs review')
    selected = [d['id'] for d in devices['data']
                if d['attributes']['udid'] in old['ProvisionedDevices']
                and d['attributes']['status'] == 'ENABLED']
    if len(selected) != len(old['ProvisionedDevices']):
        raise ValueError('Existing test device is not enabled in the Apple account')
    certificate = (root / 'distribution-certificate-id.txt').read_text().strip()
    destination = root / 'hex-ad-hoc'
    destination.mkdir(mode=0o700, exist_ok=True)
    paths = []
    missing = []
    for bundle in config['bundle_ids']:
        # Apple identifier/name filters can return prefix matches.
        response = apple.request('GET', '/v1/bundleIds?filter[identifier]=' + bundle + '&limit=200')
        if response.get('links', {}).get('next'):
            raise ValueError('Bundle ID pagination needs review')
        ids = [item for item in response['data'] if item['attributes']['identifier'] == bundle]
        if len(ids) != 1:
            raise ValueError('Expected registered bundle ID: ' + bundle)
        name = 'Hex Ad Hoc ' + bundle
        existing = apple.request('GET', '/v1/profiles?filter[name]=' + name.replace(' ', '%20') + '&limit=100')['data']
        existing = [p for p in existing if p['attributes']['profileState'] == 'ACTIVE'
                    and p['attributes']['name'] == name]
        if len(existing) > 1:
            raise ValueError('Multiple active profiles; review in portal: ' + bundle)
        if existing:
            profile = existing[0]
        else:
            profile = apple.request('POST', '/v1/profiles', {'data': {
                'type': 'profiles',
                'attributes': {'name': name, 'profileType': 'IOS_APP_ADHOC'},
                'relationships': {
                    'bundleId': {'data': {'type': 'bundleIds', 'id': ids[0]['id']}},
                    'certificates': {'data': [{'type': 'certificates', 'id': certificate}]},
                    'devices': {'data': [{'type': 'devices', 'id': d} for d in selected]},
                },
            }})['data']
        content = base64.b64decode(profile['attributes']['profileContent'])
        path = destination / (bundle + '.mobileprovision')
        path.write_bytes(content)
        decoded = subprocess.check_output(['openssl', 'cms', '-verify', '-inform', 'DER',
                                          '-in', str(path), '-noverify'], stderr=subprocess.DEVNULL)
        data = plistlib.loads(decoded)
        if data['TeamIdentifier'] != old['TeamIdentifier']:
            raise ValueError('Wrong profile team')
        if data['Entitlements']['application-identifier'].split('.', 1)[1] != bundle:
            raise ValueError('Wrong profile bundle ID')
        if not bundle.endswith('.widgets') and data['Entitlements'].get('com.apple.security.application-groups') != ['group.' + config['bundle_id']]:
            missing.append(bundle)
        paths.append(path)
        print('Prepared profile:', bundle)
    if missing:
        raise SystemExit('App Group missing for: ' + ', '.join(missing) +
                         '. Create/assign group.com.bearylabs.hex in the Developer portal, '
                         'regenerate these profiles there, then rerun this script. Secrets were NOT uploaded.')
    archive = root / 'hex-ad-hoc-profiles.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for path in paths:
            output.write(path, path.name)
    subprocess.run(['gh', 'secret', 'set', 'IOS_PROFILES_ZIP_BASE64', '--repo',
                    'bearylabs/ios-builds', '--env', 'ios-hex-ad-hoc'],
                   input=base64.b64encode(archive.read_bytes()), check=True)
    print('Validated all profiles and uploaded protected provisioning secret.')


if __name__ == '__main__':
    main()
