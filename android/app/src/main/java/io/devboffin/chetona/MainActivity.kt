package io.devboffin.chetona

import android.content.SharedPreferences
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import io.devboffin.chetona.model.AgentState
import io.devboffin.chetona.model.WorldSnapshot
import io.devboffin.chetona.net.ChetonaConnection
import io.devboffin.chetona.ui.AgentAdapter
import io.devboffin.chetona.ui.EventAdapter
import io.devboffin.chetona.ui.FactionAdapter
import org.json.JSONObject
import java.util.regex.Pattern

/**
 * Chetona game client — লোকাল সার্ভারে চলা civilization-এর সাথে
 * WebSocket দিয়ে কথা বলে। সংযোগ ব্যবস্থাপনা [ChetonaConnection]-এ,
 * এখানে UI বাইন্ডিং + per-world owner_token persistence (auth)।
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusView: TextView
    private lateinit var serverAddressInput: EditText
    private lateinit var targetIdInput: EditText
    private lateinit var rumorInput: EditText

    private lateinit var agentAdapter: AgentAdapter
    private lateinit var factionAdapter: FactionAdapter
    private lateinit var eventAdapter: EventAdapter
    private lateinit var objectiveStage: TextView
    private lateinit var objectiveDescription: TextView
    private lateinit var objectiveProgress: android.widget.ProgressBar

    private lateinit var connection: ChetonaConnection
    private lateinit var prefs: SharedPreferences

    private var currentWorldId: String = "default"
    private var lastObjectiveStage: Int? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences("chetona_tokens", MODE_PRIVATE)

        statusView = findViewById(R.id.statusView)
        serverAddressInput = findViewById(R.id.serverAddressInput)
        targetIdInput = findViewById(R.id.targetIdInput)
        rumorInput = findViewById(R.id.rumorInput)

        agentAdapter = AgentAdapter(onAgentTapped = ::onAgentTapped)
        val agentsRecyclerView = findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.agentsRecyclerView)
        agentsRecyclerView.layoutManager = LinearLayoutManager(this)
        agentsRecyclerView.adapter = agentAdapter

        factionAdapter = FactionAdapter()
        val factionsRecyclerView = findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.factionsRecyclerView)
        factionsRecyclerView.layoutManager = LinearLayoutManager(this)
        factionsRecyclerView.adapter = factionAdapter

        objectiveStage = findViewById(R.id.objectiveStage)
        objectiveDescription = findViewById(R.id.objectiveDescription)
        objectiveProgress = findViewById(R.id.objectiveProgress)

        eventAdapter = EventAdapter()
        val eventsRecyclerView = findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.eventsRecyclerView)
        eventsRecyclerView.layoutManager = LinearLayoutManager(this)
        eventsRecyclerView.adapter = eventAdapter

        connection = ChetonaConnection(
            onStateChange = ::renderConnectionState,
            onMessage = ::handleMessage,
        )

        findViewById<Button>(R.id.connectButton).setOnClickListener { connectWithSavedToken() }
        findViewById<Button>(R.id.whisperButton).setOnClickListener { sendWhisper() }
        findViewById<Button>(R.id.defectionButton).setOnClickListener { sendInciteDefection() }
        findViewById<Button>(R.id.graphButton).setOnClickListener {
            connection.send(JSONObject().apply { put("action", "graph") }.toString())
        }
    }

    // ---- connection + auth -----------------------------------------------

    private fun connectWithSavedToken() {
        val rawAddress = serverAddressInput.text.toString().ifBlank { return }
        currentWorldId = extractWorldId(rawAddress)
        val savedToken = prefs.getString(tokenKey(currentWorldId), null)
        val addressWithToken = withTokenParam(rawAddress, savedToken)
        connection.connect(addressWithToken)
    }

    private fun extractWorldId(address: String): String {
        val m = Pattern.compile("[?&]world=([^&]+)").matcher(address)
        return if (m.find()) m.group(1) ?: "default" else "default"
    }

    private fun withTokenParam(address: String, token: String?): String {
        if (token.isNullOrBlank()) return address
        if (address.contains("token=")) return address
        val separator = if (address.contains("?")) "&" else "?"
        return "$address${separator}token=$token"
    }

    private fun tokenKey(worldId: String) = "token_$worldId"

    private fun onAgentTapped(agent: AgentState) {
        targetIdInput.setText(agent.id)
    }

    private fun renderConnectionState(state: ChetonaConnection.State) {
        statusView.text = when (state) {
            is ChetonaConnection.State.Disconnected -> "disconnected"
            is ChetonaConnection.State.Connecting -> "connecting..."
            is ChetonaConnection.State.Connected -> "connected: ${state.address}"
            is ChetonaConnection.State.Reconnecting ->
                "connection lost — retry #${state.attempt} in ${state.inSeconds}s"
            is ChetonaConnection.State.Failed -> "failed: ${state.reason}"
        }
    }

    // ---- player actions -----------------------------------------------

    private fun sendWhisper() {
        val targetId = targetIdInput.text.toString()
        val content = rumorInput.text.toString()
        if (targetId.isBlank() || content.isBlank()) return

        val payload = JSONObject().apply {
            put("action", "whisper_rumor")
            put("target_id", targetId)
            put("content", content)
            put("credibility", 0.6)
        }
        connection.send(payload.toString())
    }

    private fun sendInciteDefection() {
        val targetId = targetIdInput.text.toString()
        if (targetId.isBlank()) return

        val payload = JSONObject().apply {
            put("action", "incite_defection")
            put("agent_id", targetId)
            put("credibility", 0.7)
        }
        connection.send(payload.toString())
    }

    // ---- incoming messages -----------------------------------------------

    private fun handleMessage(text: String) {
        val json = JSONObject(text)
        when (json.optString("type")) {
            "snapshot" -> {
                if (json.has("claim_token")) {
                    val token = json.getString("claim_token")
                    prefs.edit().putString(tokenKey(currentWorldId), token).apply()
                    statusView.text = "claimed world '$currentWorldId' — reconnecting with credentials"
                    // this connection predates the token; reconnect once so
                    // subsequent mutating actions authenticate correctly
                    val rawAddress = serverAddressInput.text.toString()
                    connection.connect(withTokenParam(rawAddress, token))
                    return
                }
                val snapshot = WorldSnapshot.fromJson(json.getJSONObject("data"))
                renderSnapshot(snapshot)
            }
            "action_result" -> {
                val data = json.optJSONObject("data")
                if (data != null && data.has("graph")) {
                    GraphActivity.start(this, data.getJSONObject("graph").toString())
                } else if (data != null && data.optBoolean("defected", false)) {
                    vibrate()
                    android.widget.Toast.makeText(this, "A citizen has defected.", android.widget.Toast.LENGTH_SHORT).show()
                } else if (data != null && !data.optBoolean("ok", true)) {
                    statusView.text = "action failed: ${data.optString("error")}"
                }
            }
            "error" -> {
                statusView.text = "error: ${json.optString("error")}"
            }
        }
    }

    private fun renderSnapshot(snapshot: WorldSnapshot) {
        factionAdapter.submitList(snapshot.factions)
        agentAdapter.submitList(snapshot.agents, factionAdapter.colorMap())
        eventAdapter.submitList(snapshot.recentEvents)
        title = "Chetona — ${snapshot.worldId} — tick ${snapshot.tick}"

        snapshot.objective?.let { obj ->
            if (lastObjectiveStage != null && obj.stage > lastObjectiveStage!!) {
                vibrate()
                android.widget.Toast.makeText(
                    this, "Stage advanced: ${obj.stageName}", android.widget.Toast.LENGTH_SHORT
                ).show()
            }
            lastObjectiveStage = obj.stage
            objectiveStage.text = "Stage ${obj.stage}: ${obj.stageName}"
            objectiveDescription.text = obj.description
            objectiveProgress.progress = (obj.progress * 100).toInt()
        }
    }

    private fun vibrate() {
        val vibrator = getSystemService(VIBRATOR_SERVICE) as? android.os.Vibrator ?: return
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            vibrator.vibrate(android.os.VibrationEffect.createOneShot(180, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(180)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        connection.close()
    }
}
