package com.relay.owner_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder

class KeepAliveService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        val manager = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Relay verification",
            NotificationManager.IMPORTANCE_LOW,
        )
        manager.createNotificationChannel(channel)
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Relay is verifying payments")
            .setContentText("Notification access stays active for matching.")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .build()
        startForeground(
            NOTIFICATION_ID,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    companion object {
        const val CHANNEL_ID = "relay_keepalive"
        const val NOTIFICATION_ID = 17
    }
}
