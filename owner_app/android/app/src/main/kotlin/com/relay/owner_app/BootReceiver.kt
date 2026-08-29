package com.relay.owner_app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Application.onCreate (RelayApplication) starts KeepAliveService + Python HTTP.
 * This receiver re-starts KeepAliveService on BOOT_COMPLETED / LOCKED_BOOT_COMPLETED.
 * Live reboot-without-open has not been measured on the demo iQOO (Phase 3 blocked).
 * OriginOS Autostart may still drop the broadcast.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED &&
            action != Intent.ACTION_LOCKED_BOOT_COMPLETED
        ) {
            return
        }
        try {
            KeepAliveService.start(context)
        } catch (_: Exception) {
            return
        }
    }
}
