package com.relay.owner_app

import com.chaquo.python.Python
import com.chaquo.python.android.PyApplication

class RelayApplication : PyApplication() {
    override fun onCreate() {
        super.onCreate()
        Thread({
            Python.getInstance().getModule("app.main").callAttr("start")
        }, "relay-http").start()
    }
}
