package com.relay.owner_app

import android.content.Intent
import com.chaquo.python.Python
import com.chaquo.python.android.PyApplication

class RelayApplication : PyApplication() {
    override fun onCreate() {
        super.onCreate()
        try {
            KeepAliveService.start(this)
        } catch (_: Exception) {
            // Android 16 may deny FGS start until the user has opened the app.
        }
        Thread({
            Python.getInstance().getModule("app.main").callAttr("start")
        }, "relay-http").start()
    }
}
