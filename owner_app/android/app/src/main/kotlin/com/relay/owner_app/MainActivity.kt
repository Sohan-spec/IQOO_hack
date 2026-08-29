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
                        requestIgnoreBatteryOptimizations()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onResume() {
        super.onResume()
        requestPostNotifications()
        KeepAliveService.start(this)
    }

    private fun isBatteryOptimizationIgnored(): Boolean {
        val power = getSystemService(PowerManager::class.java)
        return power.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestIgnoreBatteryOptimizations() {
        if (isBatteryOptimizationIgnored()) {
            return
        }
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

    companion object {
        const val CHANNEL = "com.relay.owner/device"
        const val REQUEST_POST_NOTIFICATIONS = 31
    }
}
