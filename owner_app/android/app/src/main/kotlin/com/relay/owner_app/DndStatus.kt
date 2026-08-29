package com.relay.owner_app

import android.app.NotificationManager
import android.content.Context

object DndStatus {
    fun currentInterruptionFilter(context: Context): Int {
        val manager = context.getSystemService(NotificationManager::class.java)
        return manager.currentInterruptionFilter
    }
}
