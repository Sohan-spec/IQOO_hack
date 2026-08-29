package com.relay.owner_app

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant

class RelayNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE) ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        // Unmodified title/body for every package so GPay/bank can be captured from logcat.
        Log.i(RAW_TAG, "package=${sbn.packageName} title=$title text=$text")
        if (sbn.packageName != PHONEPE) {
            return
        }
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
            var connection: HttpURLConnection? = null
            try {
                connection = URL(INGEST).openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                connection.connectTimeout = 2000
                connection.readTimeout = 5000
                OutputStreamWriter(connection.outputStream).use { it.write(payload) }
                connection.responseCode
                return
            } catch (_: Exception) {
                Thread.sleep(200L * (attempt + 1))
            } finally {
                connection?.disconnect()
            }
        }
        Log.w(RAW_TAG, "ingest POST failed after retries")
    }

    companion object {
        const val PHONEPE = "com.phonepe.app"
        const val INGEST = "http://127.0.0.1:8787/v1/internal/notifications"
        const val RAW_TAG = "RelayRaw"
    }
}
