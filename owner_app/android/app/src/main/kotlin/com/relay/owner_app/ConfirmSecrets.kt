package com.relay.owner_app

import android.content.Context
import android.util.Log
import com.chaquo.python.Python

object ConfirmSecrets {
    fun apply(context: Context, secret: String) {
        DeviceIdentityStore(context).saveConfirmSecret(secret)
        pushToPython(secret)
    }

    fun loadIntoPython(context: Context) {
        pushToPython(DeviceIdentityStore(context).confirmSecret())
    }

    private fun pushToPython(secret: String) {
        try {
            Python.getInstance()
                .getModule("app.confirm")
                .callAttr("set_confirm_secret", secret)
        } catch (exc: Exception) {
            // Python may still be starting; RelayApplication injects again before serve.
            Log.e(TAG, "failed to push confirm secret into Python", exc)
        }
    }

    private const val TAG = "ConfirmSecrets"
}
