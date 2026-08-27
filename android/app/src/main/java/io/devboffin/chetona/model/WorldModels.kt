package io.devboffin.chetona.model

import org.json.JSONObject

data class Traits(
    val courage: Double,
    val trust: Double,
    val curiosity: Double,
    val paranoia: Double,
    val loyalty: Double,
    val ambition: Double,
    val empathy: Double,
) {
    companion object {
        fun fromJson(j: JSONObject) = Traits(
            courage = j.optDouble("courage", 0.0),
            trust = j.optDouble("trust", 0.0),
            curiosity = j.optDouble("curiosity", 0.0),
            paranoia = j.optDouble("paranoia", 0.0),
            loyalty = j.optDouble("loyalty", 0.0),
            ambition = j.optDouble("ambition", 0.0),
            empathy = j.optDouble("empathy", 0.0),
        )
    }
}

data class Ideology(val order: Double, val unity: Double, val openness: Double) {
    companion object {
        fun fromJson(j: JSONObject) = Ideology(
            order = j.optDouble("order", 0.5),
            unity = j.optDouble("unity", 0.5),
            openness = j.optDouble("openness", 0.5),
        )
    }
}

data class AgentState(
    val id: String,
    val name: String,
    val traits: Traits,
    val selfAwareness: Double,
    val memoryCount: Int,
    val alive: Boolean,
    val factionId: String?,
    val ideology: Ideology,
) {
    companion object {
        fun fromJson(j: JSONObject) = AgentState(
            id = j.getString("id"),
            name = j.getString("name"),
            traits = Traits.fromJson(j.getJSONObject("traits")),
            selfAwareness = j.optDouble("self_awareness", 0.0),
            memoryCount = j.optInt("memory_count", 0),
            alive = j.optBoolean("alive", true),
            factionId = if (j.isNull("faction_id")) null else j.optString("faction_id", null),
            ideology = Ideology.fromJson(j.getJSONObject("ideology")),
        )
    }
}

data class FactionState(
    val id: String,
    val name: String,
    val creed: String,
    val ideology: Ideology,
    val cohesion: Double,
    val memberCount: Int,
) {
    companion object {
        fun fromJson(j: JSONObject) = FactionState(
            id = j.getString("id"),
            name = j.getString("name"),
            creed = j.optString("creed", ""),
            ideology = Ideology.fromJson(j.getJSONObject("ideology")),
            cohesion = j.optDouble("cohesion", 0.0),
            memberCount = j.optInt("member_count", 0),
        )
    }
}

data class WorldSnapshot(
    val worldId: String,
    val tick: Int,
    val uptimeSeconds: Int,
    val avgParanoia: Double,
    val avgSelfAwareness: Double,
    val agents: List<AgentState>,
    val factions: List<FactionState>,
) {
    companion object {
        fun fromJson(j: JSONObject): WorldSnapshot {
            val agentsJson = j.getJSONArray("agents")
            val agents = (0 until agentsJson.length()).map { AgentState.fromJson(agentsJson.getJSONObject(it)) }
            val factionsJson = j.getJSONArray("factions")
            val factions = (0 until factionsJson.length()).map { FactionState.fromJson(factionsJson.getJSONObject(it)) }
            return WorldSnapshot(
                worldId = j.optString("world_id", "default"),
                tick = j.optInt("tick", 0),
                uptimeSeconds = j.optInt("uptime_seconds", 0),
                avgParanoia = j.optDouble("avg_paranoia", 0.0),
                avgSelfAwareness = j.optDouble("avg_self_awareness", 0.0),
                agents = agents,
                factions = factions,
            )
        }
    }
}
