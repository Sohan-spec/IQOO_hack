# iQOO / vivo demo-device setup (R2)

Relay's wake lock, foreground service, and the Android "ignore battery optimizations" prompt are not enough on this phone. Funtouch / OriginOS (FuTu OS) has a second battery manager that can still freeze the app when the screen is off. These toggles cannot be granted from the app. Do them once on the demo iQOO before presenting.

## Must do in-app (first launch)

1. Allow **notifications** (`POST_NOTIFICATIONS`) when Android asks.
2. **Notification access** — operator UI is red until granted. Tap it, enable Relay Owner. Required before any live PhonePe test.
3. **Ignore battery optimizations** — system dialog: Allow Relay Owner to ignore battery optimizations. This is the same setup pass as notification access; grant it before the demo, not during a live pay.

## Must do in iQOO settings (no API)

Wording varies slightly by OriginOS / Funtouch version. Look under **Settings**, **i Manager**, or **Battery**.

1. **Autostart**
   - Settings → Apps → **Autostart** (or i Manager → App manager → Autostart)
   - Turn **on** for **Relay Owner**

2. **Background power**
   - Settings → Battery → **App battery management** (or High background power consumption / Background power consumption)
   - Relay Owner → **Unrestricted** / allow high background power / do **not** restrict background activity

3. **Lock in recents**
   - Open recents, find Relay Owner, tap the menu → **Lock**
   - Do not swipe it away

4. **Doze / standby**
   - If there is a "Smart freeze", "Background freeze", or "App hibernation" list, exclude Relay Owner

## After reboot

Open Relay Owner once so the foreground service and Python listener start. Confirm the persistent notification "Relay is verifying payments" is visible, then you may turn the screen off.

## Confirm screen-off still serves HTTP

With USB:

```bash
adb forward tcp:18787 tcp:8787
adb shell input keyevent KEYCODE_SLEEP
sleep 3
curl -m 5 http://127.0.0.1:18787/v1/internal/snapshot
adb shell dumpsys power | grep -i 'Relay::BackendWakeLock'
```
