package com.relay.owner_app

import java.util.regex.Pattern
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object DeviceTokens {
    private val MERCHANT = Pattern.compile(
        "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )

    fun token(secret: String, merchantId: String): String {
        require(MERCHANT.matcher(merchantId).matches()) { "merchant_id must be a UUID" }
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val digest = mac.doFinal(merchantId.toByteArray(Charsets.UTF_8))
        return "$merchantId.${digest.joinToString("") { b -> "%02x".format(b.toInt() and 0xFF) }}"
    }
}
