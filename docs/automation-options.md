# No-ID Lab Automation Options

## Recommended approach: hybrid local lab

Use an Android emulator as the first automated platform and a physical iPhone as the authoritative iOS tier.

### Android emulator

- Use an Android Studio AVD with Google Play services.
- Automate with Appium and UiAutomator2.
- Install the target app from Google Play where available.
- Capture screenshots, UI trees, notification state, app settings, and device logs.
- Use synthetic personas and controlled accounts.
- Add a physical Android device later to validate emulator behavior.

### Physical iPhone

- Use Appium with XCUITest and a physical iOS device.
- Treat iOS Simulator as a development convenience only, not an evidence source.
- Capture UI, notification, and settings state through a controlled device harness.
- Record iOS app version, device version, and parental-control state.

### Why not rely on iOS Simulator

App Store builds of third-party apps are not practically installable in iOS Simulator, and simulator behavior is not sufficiently faithful for age signals, push notifications, or parental-control behavior.

### Evidence capture

- UI screenshots and accessibility trees
- Notification-center captures
- App settings and parental-control state
- Device logs where available
- Optional network capture where technically and legally feasible

Network capture may be blocked by TLS pinning or app security controls. It should not be treated as the only evidence source.

## Alternative approaches

### Android-only local lab

This is the easiest automation path, but it would miss iOS-specific notification, parental-control, and engagement behavior. It is insufficient for a cross-platform AG-facing investigation.

### Physical-device lab only

Physical devices provide the highest fidelity for Android and iOS. They are slower to configure and less repeatable than emulators. They are best used as a validation tier after the evidence model works.

### Mobile-web-only lab

A mobile-web harness such as Playwright is easy to automate, but it misses native push notifications, native settings, and many app-specific engagement mechanisms. It is not suitable as the primary source.

## Recommended automation stack

- Python for orchestration and analysis
- Appium for Android and iOS UI automation
- UiAutomator2 for Android
- XCUITest for iOS
- YAML or JSON for app, persona, and parental-control configurations
- SQLite or JSONL for structured observation records
- pytest for schema and harness validation

## Sequencing

1. Prove the evidence schema with manual observations.
2. Automate one Android app and one parental-control profile.
3. Expand to all Android apps and available control profiles.
4. Add physical iPhone validation.
5. Add physical Android validation.
6. Generate comparative matrices and statutory summaries.
