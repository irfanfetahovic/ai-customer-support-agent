# Smartwatch X — Troubleshooting Guide

## Battery and Charging Issues

### Watch Not Charging
1. Clean the charging contacts on the back of the watch and on the magnetic charger with a dry cotton swab.
2. Ensure the charger is securely snapped onto the watch — you should feel a slight magnetic click.
3. Try a different USB power source (wall adapter, not a laptop USB port, which may supply insufficient current).
4. If the watch screen is completely blank, charge for at least 30 minutes before attempting to power on.

**Expected behaviour:** A charging icon appears on screen within 10 seconds of connecting a working charger.

### Battery Draining Faster Than Expected
Normal battery life is up to 10 days with typical use. Battery drains faster when:
- Always-on display is enabled (expect ~5 days)
- GPS is used continuously (expect ~25 hours)
- Heart rate monitoring is set to continuous at 1-minute intervals
- Wi-Fi is enabled (turns off automatically after 30 minutes of inactivity, but re-enabling it frequently drains battery)

**To extend battery life:**
- Disable always-on display: Settings → Display → Always-on → Off
- Set workout GPS to auto-start only
- Enable Battery Saver mode during long events: Settings → Battery → Battery Saver

---

## Connectivity Issues

### Watch Not Pairing with Phone
1. On the phone, go to Bluetooth settings and forget/unpair any previous "Smartwatch X" entries.
2. On the watch, go to Settings → Connectivity → Bluetooth → Reset Bluetooth.
3. Open the HealthSync app → Add Device → Smartwatch X and follow the pairing prompt.
4. Keep the phone and watch within 30 cm during the pairing process.
5. Ensure HealthSync has Bluetooth, Location, and Nearby Devices permissions (required on Android 12+).

### Watch Not Syncing Data to App
1. Force-quit the HealthSync app and reopen it.
2. Pull down on the app home screen to trigger a manual sync.
3. Check that Background App Refresh is enabled for HealthSync (iOS: Settings → HealthSync → Background App Refresh).
4. Confirm Bluetooth is enabled on the phone — the watch cannot sync over Wi-Fi alone.

### GPS Not Locking
- Go to an open outdoor area (clear sky, away from tall buildings).
- First-time GPS lock after a factory reset or long period without use can take up to 3 minutes.
- Do not start a GPS workout while indoors — begin the workout once GPS shows a lock signal (solid GPS icon).

---

## Health Sensor Issues

### Heart Rate Not Recording
1. Ensure the watch is worn snugly, about one finger-width above the wrist bone.
2. Clean the optical sensor on the back of the watch with a soft, lint-free cloth.
3. Avoid having the watch too loose — movement artifacts can prevent readings.
4. Check Settings → Health → Heart Rate Monitoring is set to "Continuous" or "Every 10 minutes."

### SpO2 Readings Unavailable
- SpO2 spot readings require the wearer to remain still for 30 seconds.
- Cold hands or poor circulation can affect readings — warm up before measuring.
- Nail polish or tattoos over the sensor area may interfere with optical readings.

---

## Software and App Issues

### Watch Frozen or Unresponsive
- **Soft reset:** Hold the side button for 12 seconds until the screen goes dark, then release. The watch will restart.
- This does not erase any data.

### Firmware Update Failed
1. Ensure the watch battery is above 30% before updating.
2. Keep the watch close to the phone (within 1 metre) and connected to Bluetooth throughout the update.
3. Do not use the watch during the update process.
4. If the update fails twice, perform a factory reset: Settings → System → Factory Reset. Note: this erases all local data (cloud-synced health data is preserved in the HealthSync app).

### Watch Shows Wrong Time or Time Zone
- Go to HealthSync app → Device Settings → Time → Sync Time from Phone.
- If automatic sync does not work, set time zone manually: Settings → System → Date & Time → Time Zone.

---

## Factory Reset
**Warning:** A factory reset erases all local settings, workout history stored on the watch, and customisations. Health data already synced to the HealthSync app is not affected.

Steps:
1. Settings → System → Factory Reset → Confirm
2. The watch will restart and display the setup screen.
3. Re-pair with your phone using the HealthSync app.

## When to Contact Support
Contact support if the issue persists after following the above steps, or if:
- The screen has dead pixels or severe discolouration
- The watch does not power on after 1 hour of charging
- The watch has not been physically damaged but a sensor has stopped working
- You believe the issue is covered under warranty
