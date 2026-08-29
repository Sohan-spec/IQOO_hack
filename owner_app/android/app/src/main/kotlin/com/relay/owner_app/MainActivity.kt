package com.relay.owner_app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "notificationAccessGranted" ->
                        result.success(isNotificationAccessGranted())
                    "openNotificationAccessSettings" -> {
                        startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                        result.success(null)
                    }
                    "getInterruptionFilter" ->
                        result.success(DndStatus.currentInterruptionFilter(this))
                    "requestPostNotifications" -> {
                        requestPostNotifications()
                        result.success(null)
                    }
                    "batteryOptimizationIgnored" ->
                        result.success(isBatteryOptimizationIgnored())
                    "requestIgnoreBatteryOptimizations" -> {
                        requestIgnoreBatteryOptimizations(once = false)
                        result.success(null)
                    }
                    "runSetupPrompts" -> {
                        runSetupPrompts()
                        result.success(null)
                    }
                    "getDefaultCallbackUrl" ->
                        result.success(getDefaultCallbackUrl())
                    "setDefaultCallbackUrl" -> {
                        setDefaultCallbackUrl(call.argument<String>("url") ?: "")
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onResume() {
        super.onResume()
        runSetupPrompts()
        KeepAliveService.start(this)
    }

    private fun runSetupPrompts() {
        requestPostNotifications()
        if (!isNotificationAccessGranted()) {
            return
        }
        requestIgnoreBatteryOptimizations(once = true)
    }

    private fun isBatteryOptimizationIgnored(): Boolean {
        val power = getSystemService(PowerManager::class.java)
        return power.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestIgnoreBatteryOptimizations(once: Boolean = false) {
        if (isBatteryOptimizationIgnored()) {
            return
        }
        val prefs = getSharedPreferences(SETUP_PREFS, MODE_PRIVATE)
        if (once && prefs.getBoolean(BATTERY_PROMPTED, false)) {
            return
        }
        prefs.edit().putBoolean(BATTERY_PROMPTED, true).apply()
        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:$packageName")
        }
        startActivity(intent)
    }

    private fun requestPostNotifications() {
        if (Build.VERSION.SDK_INT < 33) {
            return
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            == PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
            REQUEST_POST_NOTIFICATIONS,
        )
    }

    private fun isNotificationAccessGranted(): Boolean {
        val enabled = NotificationManagerCompat.getEnabledListenerPackages(this)
        return enabled.contains(packageName)
    }

    private fun getDefaultCallbackUrl(): String {
        val prefs = getSharedPreferences(SETUP_PREFS, MODE_PRIVATE)
        return prefs.getString(DEFAULT_CALLBACK_URL, "") ?: ""
    }

    private fun setDefaultCallbackUrl(url: String) {
        getSharedPreferences(SETUP_PREFS, MODE_PRIVATE)
            .edit()
            .putString(DEFAULT_CALLBACK_URL, url)
            .apply()
    }

    companion object {
        const val CHANNEL = "com.relay.owner/device"
        const val REQUEST_POST_NOTIFICATIONS = 31
        const val SETUP_PREFS = "relay_setup"
        const val BATTERY_PROMPTED = "battery_prompted"
        const val DEFAULT_CALLBACK_URL = "default_callback_url"
    }
}
