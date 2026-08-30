package com.relay.owner_app

import android.content.Context
import android.util.Log

/** Debug-only: seed Keystore DataStore from BuildConfig if the store is empty. */
object DebugSecretBootstrap {
    fun installIfNeeded(context: Context) {
        val store = DeviceIdentityStore(context)
        val relay = BuildConfig.DEBUG_RELAY_SECRET
        if (relay.isNotBlank() && store.hmacSecret() != relay) {
            store.saveHmacSecret(relay)
            Log.i(TAG, "stored debug RELAY_SECRET")
        }
        val confirm = BuildConfig.DEBUG_CONFIRM_SECRET
        if (confirm.isNotBlank() && store.confirmSecret() != confirm) {
            store.saveConfirmSecret(confirm)
            Log.i(TAG, "stored debug CHECKOUT_CONFIRM_SECRET")
        }
    }

    private const val TAG = "DebugSecretBootstrap"
}
