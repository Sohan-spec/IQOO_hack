package com.relay.owner_app

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant

class RelayNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName != PHONEPE) {
            return
        }
        val extras = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        Thread {
            postNotification(sbn.packageName, title, text)
        }.start()
    }

    private fun postNotification(packageName: String, title: String, text: String) {
        val payload = JSONObject()
            .put("package", packageName)
            .put("title", title)
            .put("text", text)
            .put("posted_at", Instant.now().toString())
            .toString()
        repeat(5) { attempt ->
            try {
                val connection = URL(INGEST).openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                connection.connectTimeout = 2000
                connection.readTimeout = 5000
                OutputStreamWriter(connection.outputStream).use { it.write(payload) }
                connection.responseCode
                connection.disconnect()
                return
            } catch (_: Exception) {
                Thread.sleep(200L * (attempt + 1))
            }
        }
    }

    companion object {
        const val PHONEPE = "com.phonepe.app"
        const val INGEST = "http://127.0.0.1:8787/v1/internal/notifications"
    }
}
