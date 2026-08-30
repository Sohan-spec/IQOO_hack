package com.relay.owner_app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import java.nio.ByteBuffer
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

private val Context.relayIdentityStore by preferencesDataStore(name = "relay_identity")

data class DeviceIdentity(val merchantId: String, val token: String)

class DeviceIdentityStore(private val context: Context) {
    fun hmacSecret(): String = runBlocking {
        val packed = context.relayIdentityStore.data.first()[HMAC] ?: return@runBlocking ""
        decrypt(packed).orEmpty()
    }

    fun saveHmacSecret(secret: String) {
        runBlocking {
            context.relayIdentityStore.edit { edit ->
                if (secret.isBlank()) {
                    edit.remove(HMAC)
                } else {
                    edit[HMAC] = encrypt(secret)
                }
            }
        }
    }

    fun secretConfigured(): Boolean = hmacSecret().isNotBlank()

    fun confirmSecret(): String = runBlocking {
        val packed = context.relayIdentityStore.data.first()[CONFIRM] ?: return@runBlocking ""
        decrypt(packed).orEmpty()
    }

    fun saveConfirmSecret(secret: String) {
        runBlocking {
            context.relayIdentityStore.edit { edit ->
                if (secret.isBlank()) {
                    edit.remove(CONFIRM)
                } else {
                    edit[CONFIRM] = encrypt(secret)
                }
            }
        }
    }

    fun confirmSecretConfigured(): Boolean = confirmSecret().isNotBlank()

    fun merchantIdOnly(): String = runBlocking {
        val prefs = context.relayIdentityStore.data.first()
        val storedId = prefs[MERCHANT]?.let { decrypt(it) }
        if (storedId != null) {
            return@runBlocking storedId
        }
        val merchantId = UUID.randomUUID().toString()
        context.relayIdentityStore.edit { edit ->
            edit[MERCHANT] = encrypt(merchantId)
        }
        merchantId
    }

    fun loadOrCreate(hmacSecret: String): DeviceIdentity = runBlocking {
        val prefs = context.relayIdentityStore.data.first()
        val storedId = prefs[MERCHANT]?.let { decrypt(it) }
        val storedToken = prefs[TOKEN]?.let { decrypt(it) }
        val merchantId = storedId ?: UUID.randomUUID().toString()
        val token = DeviceTokens.token(hmacSecret, merchantId)
        if (storedId != merchantId || storedToken != token) {
            context.relayIdentityStore.edit { edit ->
                edit[MERCHANT] = encrypt(merchantId)
                edit[TOKEN] = encrypt(token)
            }
        }
        DeviceIdentity(merchantId, token)
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existing = store.getKey(ALIAS, null) as? SecretKey
        if (existing != null) {
            return existing
        }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private fun encrypt(plain: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(plain.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(1 + iv.size + ciphertext.size)
            .put(iv.size.toByte())
            .put(iv)
            .put(ciphertext)
            .array()
        return Base64.encodeToString(packed, Base64.NO_WRAP)
    }

    private fun decrypt(packed: String): String? {
        return try {
            val bytes = Base64.decode(packed, Base64.NO_WRAP)
            val buffer = ByteBuffer.wrap(bytes)
            val ivLen = buffer.get().toInt() and 0xFF
            if (ivLen < 12 || ivLen > 32 || buffer.remaining() <= ivLen) {
                return null
            }
            val iv = ByteArray(ivLen)
            buffer.get(iv)
            val ciphertext = ByteArray(buffer.remaining())
            buffer.get(ciphertext)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(ciphertext), Charsets.UTF_8)
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val ALIAS = "relay_device_identity_aes"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private val MERCHANT = stringPreferencesKey("merchant_id")
        private val TOKEN = stringPreferencesKey("device_token")
        private val HMAC = stringPreferencesKey("hmac_secret")
        private val CONFIRM = stringPreferencesKey("checkout_confirm_secret")
    }
}
