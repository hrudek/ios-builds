# Hex iPhone test build

## Source and identity

- Local source: `~/dev/hex` (upstream checkout, unmodified).
- Public source: `anomalyco/hex`, pinned in `apps/hex.json`.
- Native iOS app in `ios/`, generated using XcodeGen >=2.46 and Xcode >=26.2.
- Scheme: `HEXMobile`; app product: `HEX`.
- App: `com.bearylabs.hex`.
- Keyboard: `com.bearylabs.hex.keyboard`.
- Widget / Live Activity: `com.bearylabs.hex.widgets`.
- Shared storage for app + keyboard: `group.com.bearylabs.hex`.
- Personal deep link: `bearylabs-hex://`.

The preparation hook changes identities, shared-storage references and deep links
only in the disposable CI checkout, including keyboard discovery and tests.
It does not change the desktop app, remove extensions, or use upstream signing
credentials. The widget has no App Group entitlement in the reviewed source.

## Current status

Ad Hoc build and signing passed:
<https://github.com/hrudek/ios-builds/actions/runs/41423652545>.
The installable IPA is available locally at
`~/dev/ios-builds/downloads/hex-41423652545/HEX.ipa`.
Actual signed entitlements were verified on the macOS runner; local checks also
verified the complete bundle set and embedded distribution profiles. No device
installation or hardware behavior test has been performed.

## Apple setup

The three App IDs have been created through the existing local Apple API helper.
App Groups capability is enabled for the app and keyboard. The existing Apple
Distribution certificate is reused; unrelated certificates/profiles are untouched.

**Manual portal step completed for this account.** The following instructions
are retained for future setup: the public App Store Connect API does not expose
App Group creation or association.

1. Open <https://developer.apple.com/account/resources/identifiers/list/applicationGroup>.
2. Register App Group `group.com.bearylabs.hex` (description: Hex).
3. Under App IDs, edit `com.bearylabs.hex` → App Groups → Configure, select that
   group and save.
4. Repeat for `com.bearylabs.hex.keyboard`. The widget does not need it.

Then create and validate the three Ad Hoc profiles and upload the protected secret:

```sh
cd ~/dev/ios-builds
python3 scripts/provision-hex.py
```

This local-only script loads the private helper from
`~/.local/share/ios-build-signing/apple-api.py`, reuses the existing distribution
certificate and exactly the devices in the existing Ad Hoc profile, and stores
profiles privately outside Git. It refuses to upload profiles without the exact
required App Group. It never revokes or deletes Apple resources. If capability
changes invalidate a profile, it creates a new revision with a unique name,
leaving the invalid profile untouched. Active profiles with outdated groups must
be regenerated in the portal before rerunning the script.

The GitHub environment `ios-hex-ad-hoc` is restricted to `main`, requires owner
approval and disables administrator bypass. Certificate, password and artifact
decryption identity and validated `IOS_PROFILES_ZIP_BASE64` are configured.
Do not approve future signing jobs before reviewing the source and provenance.

## Unit tests (simulator)

`test-ios.yml` runs `xcodebuild test` for the `HEXMobile` scheme on the newest
available iPhone simulator of a `macos-26` runner. It has no signing environment
or secrets and runs the source as-is (no identity rewrite). The default
`only_testing` runs the autocorrect suites; pass an empty value to run every test.

```sh
cd ~/dev/ios-builds
gh workflow run test-ios.yml -f app=hex -f source_ref=BRANCH
gh workflow run test-ios.yml -f app=hex -f source_ref=BRANCH -f only_testing=
gh run watch RUN_ID   # summary lists passed/failed test cases
gh run download RUN_ID --name hex-tests --dir downloads/hex-tests-RUN_ID
```

Simulator tests cover the engine logic; they do not prove keyboard-extension
behavior on a device.

## Build and install

```sh
cd ~/dev/ios-builds
# Compile only; no profile required:
gh workflow run build-ios.yml -f app=hex -f distribution=unsigned

# Once provisioning is complete:
gh workflow run build-ios.yml -f app=hex -f distribution=ad-hoc
gh run list --workflow build-ios.yml
gh run watch RUN_ID
# Approve the ios-hex-ad-hoc environment on the run page after reviewing the SHA.
gh run download RUN_ID --pattern 'hex-ad-hoc-*' --dir downloads/hex-RUN_ID
encrypted_ipa=$(find downloads/hex-RUN_ID -name 'HEX.ipa.age' -print -quit)
umask 077
~/.local/share/ios-build-signing/age-tools/age/age --decrypt \
  --identity ~/.local/share/ios-build-signing/artifacts.agekey \
  --output downloads/hex-RUN_ID/HEX.ipa "$encrypted_ipa"
~/dev/apple-dev-setup/iphone-wifi install "$PWD/downloads/hex-RUN_ID/HEX.ipa"
~/dev/apple-dev-setup/iphone-wifi launch com.bearylabs.hex
```

Installation is a separate explicit action; preparing/building does not replace
an installed app. iPhone Developer Mode, pairing and connectivity are required.
In iOS Settings enable Hex Keyboard and allow Full Access for app-group exchange.
Allow microphone and speech permissions when prompted. iOS 18+ is supported;
Apple SpeechTranscriber needs iOS 26+, while FluidAudio Parakeet supports iOS 18+.
Models may need downloading on first use.

TestFlight is not configured for Hex: it additionally needs an App Store Connect
app record, App Store profiles, its own protected environment and upload secrets.
Ad Hoc is sufficient for the registered personal iPhone.

## Verification limits

All 27 local tests and the GitHub infrastructure checks (including workflow lint)
passed. The first unsigned device archive passed on macOS:
<https://github.com/hrudek/ios-builds/actions/runs/41421395787>.
It includes the app, keyboard and widget extension and is published encrypted.
The subsequent Ad Hoc run linked above also passed signing/export and actual
Mach-O entitlement verification for all three bundles. That proves the checked
signatures and capabilities, not successful installation or hardware behavior.
Real microphone capture, background sessions, keyboard handoff and transcription
still need an installed-device test; see `~/dev/hex/ios/README.md`.
