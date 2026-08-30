package com.relay.owner_app

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

class RelayIngressClient(private val context: Context) {
    @Volatile var connected: Boolean = false
        private set
    @Volatile var merchantId: String = ""
        private set

    private val running = AtomicBoolean(false)
    private val attempt = AtomicInteger(0)
    private val socket = AtomicReference<WebSocket?>(null)
    private var identity: DeviceIdentity? = null
    private var worker: HandlerThread? = null
    private var handler: Handler? = null
    private var connectivity: ConnectivityManager? = null

    private val http = OkHttpClient.Builder()
        .pingInterval(25, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private val networks = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            handler?.post { connectNow("network available") }
        }

        override fun onLost(network: Network) {
            handler?.post { markDead("network lost") }
        }
    }

    fun applyHmacSecret(secret: String) {
        DeviceIdentityStore(context).saveHmacSecret(secret.trim())
        handler?.post { reloadIdentity("secret saved") }
    }

    @Volatile var secretConfigured: Boolean = false
        private set

    fun start() {
        if (!running.compareAndSet(false, true)) {
            return
        }
        val thread = HandlerThread("relay-ingress").apply { start() }
        worker = thread
        handler = Handler(thread.looper)
        connectivity = context.getSystemService(ConnectivityManager::class.java)
        connectivity?.registerDefaultNetworkCallback(networks)
        handler?.post {
            reloadIdentity("start")
        }
    }

    fun stop() {
        running.set(false)
        try {
            connectivity?.unregisterNetworkCallback(networks)
        } catch (_: Exception) {
        }
        handler?.post {
            socket.getAndSet(null)?.cancel()
            connected = false
        }
        worker?.quitSafely()
        worker = null
        handler = null
    }

    private fun reloadIdentity(reason: String) {
        val store = DeviceIdentityStore(context)
        val secret = store.hmacSecret()
        secretConfigured = secret.isNotBlank()
        if (secret.isBlank()) {
            identity = null
            merchantId = store.merchantIdOnly()
            socket.getAndSet(null)?.cancel()
            connected = false
            Log.w(TAG, "RELAY_SECRET not set; not connecting")
            return
        }
        identity = store.loadOrCreate(secret)
        merchantId = identity?.merchantId ?: ""
        connectNow(reason)
    }

    private val reconnect = Runnable { connectNow("backoff") }

    private fun connectNow(reason: String) {
        if (!running.get()) {
            return
        }
        handler?.removeCallbacks(reconnect)
        val token = identity?.token ?: return
        val url = BuildConfig.RELAY_WS_URL
        if (url.isBlank()) {
            Log.w(TAG, "RELAY_WS_URL is empty; not connecting")
            return
        }
        if (!url.startsWith("wss://")) {
            Log.e(TAG, "RELAY_WS_URL must be wss://")
            return
        }
        socket.getAndSet(null)?.cancel()
        connected = false
        Log.i(TAG, "connecting reason=$reason url=$url")
        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $token")
            .build()
        socket.set(http.newWebSocket(request, listener))
    }

    private fun markDead(reason: String) {
        val previous = socket.getAndSet(null)
        previous?.cancel()
        connected = false
        if (previous != null) {
            Log.w(TAG, "socket dead reason=$reason")
        }
        scheduleReconnect()
    }

    private fun scheduleReconnect() {
        if (!running.get()) {
            return
        }
        val n = attempt.getAndIncrement().coerceAtMost(5)
        val delay = minOf(30_000L, 1_000L shl n)
        Log.i(TAG, "reconnect in ${delay}ms")
        handler?.removeCallbacks(reconnect)
        handler?.postDelayed(reconnect, delay)
    }

    private val listener = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            handler?.post {
                if (socket.get() !== webSocket) {
                    webSocket.cancel()
                    return@post
                }
                attempt.set(0)
                connected = true
                Log.i(TAG, "connected merchant=$merchantId")
            }
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            handler?.post { handleMessage(webSocket, text) }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            handler?.post {
                if (socket.compareAndSet(webSocket, null)) {
                    connected = false
                    scheduleReconnect()
                }
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            handler?.post {
                if (socket.compareAndSet(webSocket, null)) {
                    connected = false
                    Log.w(TAG, "failure ${t.message}")
                    scheduleReconnect()
                }
            }
        }
    }

    private fun handleMessage(webSocket: WebSocket, text: String) {
        val message = try {
            JSONObject(text)
        } catch (_: Exception) {
            return
        }
        when (message.optString("type")) {
            "ping" -> {
                webSocket.send(JSONObject().put("type", "pong").toString())
            }
            "enqueue" -> {
                val correlationId = message.optString("correlation_id")
                val body = message.optJSONObject("body") ?: JSONObject()
                val result = replayEnqueue(body)
                val reply = JSONObject()
                    .put("type", "enqueue_result")
                    .put("correlation_id", correlationId)
                    .put("status", result.first)
                    .put("body", result.second)
                webSocket.send(reply.toString())
            }
        }
    }

    private fun replayEnqueue(body: JSONObject): Pair<Int, JSONObject> {
        var connection: HttpURLConnection? = null
        return try {
            connection = URL(LOOPBACK).openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json")
            connection.doOutput = true
            connection.connectTimeout = 2000
            connection.readTimeout = 5000
            OutputStreamWriter(connection.outputStream).use { it.write(body.toString()) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val raw = stream?.bufferedReader()?.readText().orEmpty()
            val parsed = try {
                JSONObject(raw.ifBlank { "{}" })
            } catch (_: Exception) {
                JSONObject().put("error", "invalid local response")
            }
            Pair(code, parsed)
        } catch (exc: Exception) {
            Pair(502, JSONObject().put("error", "local backend unreachable"))
        } finally {
            connection?.disconnect()
        }
    }

    companion object {
        const val TAG = "RelayIngress"
        const val LOOPBACK = "http://127.0.0.1:8787/v1/transactions"
    }
}

object RelayIngress {
    @Volatile
    private var client: RelayIngressClient? = null

    val connected: Boolean
        get() = client?.connected == true

    val merchantId: String
        get() = client?.merchantId.orEmpty()

    val secretConfigured: Boolean
        get() = client?.secretConfigured == true

    fun applyHmacSecret(secret: String) {
        client?.applyHmacSecret(secret)
    }

    fun start(context: Context) {
        synchronized(this) {
            if (client != null) {
                return
            }
            val created = RelayIngressClient(context.applicationContext)
            client = created
            created.start()
        }
    }

    fun stop() {
        synchronized(this) {
            client?.stop()
            client = null
        }
    }
}
