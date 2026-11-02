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

## Apple setup

The three App IDs have been created through the existing local Apple API helper.
App Groups capability is enabled for the app and keyboard. The existing Apple
Distribution certificate is reused; unrelated certificates/profiles are untouched.

**Manual portal step required:** the public App Store Connect API does not expose
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
required App Group. It never revokes or deletes Apple resources. If profiles were
created before association, regenerate those Hex profiles in the portal before
rerunning the script.

The GitHub environment `ios-hex-ad-hoc` is restricted to `main`, requires owner
approval and disables administrator bypass. Certificate, password and artifact
decryption identity are configured. `IOS_PROFILES_ZIP_BASE64` is installed only
after the profiles validate. Do not approve signing before this setup completes.

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
~/.local/share/ios-build-signing/age-tools/age/age --decrypt \
  --identity ~/.local/share/ios-build-signing/artifacts.agekey \
  --output downloads/hex-RUN_ID/HEX.ipa downloads/hex-RUN_ID/HEX.ipa.age
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

Local manifest/preparation/entitlement tests are automated. A successful unsigned
CI build proves compilation/archive layout, not valid signing or hardware behavior.
Real microphone capture, background sessions, keyboard handoff and transcription
still need an installed-device test; see `~/dev/hex/ios/README.md`.
