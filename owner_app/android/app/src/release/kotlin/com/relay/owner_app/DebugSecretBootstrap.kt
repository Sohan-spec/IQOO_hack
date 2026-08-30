package com.relay.owner_app

import android.content.Context

/** Release builds never auto-fill secrets. */
object DebugSecretBootstrap {
    @Suppress("UNUSED_PARAMETER")
    fun installIfNeeded(context: Context) {
    }
}
