package io.devboffin.chetona.net

import android.os.Handler
import android.os.Looper
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

/**
 * ChetonaConnection — production-grade WebSocket ক্লায়েন্ট।
 *
 * - LAN-এ ফোন/সার্ভার সংযোগ মাঝে মাঝে drop হবেই (wifi sleep, roaming);
 *   তাই এক্সপোনেনশিয়াল ব্যাকঅফ দিয়ে auto-reconnect করে (1s, 2s, 4s ... 30s ক্যাপ)।
 * - প্রতি 15s পর heartbeat ping পাঠায়; pong না পেলে (মৃত সংযোগ) reconnect ট্রিগার করে।
 * - কল করা কোড শুধু connect()/send()/close() ব্যবহার করবে; বাকিটা এখানে হ্যান্ডেল হয়।
 */
class ChetonaConnection(
    private val onStateChange: (State) -> Unit,
    private val onMessage: (String) -> Unit,
) {
    sealed class State {
        object Disconnected : State()
        object Connecting : State()
        data class Connected(val address: String) : State()
        data class Reconnecting(val attempt: Int, val inSeconds: Int) : State()
        data class Failed(val reason: String) : State()
    }

    private val client = OkHttpClient.Builder()
        .pingInterval(15, TimeUnit.SECONDS) // OkHttp handles ws-level ping/pong for us
        .build()

    private val mainHandler = Handler(Looper.getMainLooper())
    private var socket: WebSocket? = null
    private var address: String = ""
    private var reconnectAttempt = 0
    private var manuallyClosed = false
    private var reconnectRunnable: Runnable? = null

    fun connect(address: String) {
        this.address = address
        manuallyClosed = false
        reconnectAttempt = 0
        openSocket()
    }

    fun send(payload: String): Boolean = socket?.send(payload) ?: false

    fun close() {
        manuallyClosed = true
        reconnectRunnable?.let { mainHandler.removeCallbacks(it) }
        socket?.close(1000, "client closed")
        socket = null
        onStateChange(State.Disconnected)
    }

    private fun openSocket() {
        if (address.isBlank()) return
        onStateChange(if (reconnectAttempt == 0) State.Connecting else State.Reconnecting(reconnectAttempt, 0))

        val request = Request.Builder().url(address).build()
        socket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                reconnectAttempt = 0
                mainHandler.post { onStateChange(State.Connected(address)) }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                mainHandler.post { onMessage(text) }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                mainHandler.post { scheduleReconnect(t.message ?: "connection failed") }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (!manuallyClosed) {
                    mainHandler.post { scheduleReconnect("closed: $reason") }
                }
            }
        })
    }

    private fun scheduleReconnect(reason: String) {
        if (manuallyClosed) {
            onStateChange(State.Disconnected)
            return
        }
        reconnectAttempt += 1
        val delaySeconds = minOf(30, 1 shl minOf(reconnectAttempt, 5)) // 2,4,8,16,32->capped 30
        onStateChange(State.Reconnecting(reconnectAttempt, delaySeconds))

        val runnable = Runnable { openSocket() }
        reconnectRunnable = runnable
        mainHandler.postDelayed(runnable, delaySeconds * 1000L)
    }
}
