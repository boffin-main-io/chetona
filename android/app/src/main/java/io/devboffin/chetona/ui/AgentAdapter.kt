package io.devboffin.chetona.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.devboffin.chetona.R
import io.devboffin.chetona.model.AgentState

class AgentAdapter(
    private val onAgentTapped: (AgentState) -> Unit,
) : RecyclerView.Adapter<AgentAdapter.ViewHolder>() {

    private var items: List<AgentState> = emptyList()

    fun submitList(newItems: List<AgentState>) {
        items = newItems
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val name: TextView = view.findViewById(R.id.agentName)
        val faction: TextView = view.findViewById(R.id.agentFaction)
        val stats: TextView = view.findViewById(R.id.agentStats)
        val paranoiaBar: ProgressBar = view.findViewById(R.id.paranoiaBar)
        val id: TextView = view.findViewById(R.id.agentId)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_agent, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val agent = items[position]
        val statusIcon = if (agent.alive) "" else "\u2620 "
        holder.name.text = "$statusIcon${agent.name}"
        holder.faction.text = if (agent.factionId != null) "faction: ${agent.factionId}" else "faction: none (defected)"
        holder.stats.text = "trust=%.2f  loyalty=%.2f  curiosity=%.2f  self-awareness=%.2f  memories=%d".format(
            agent.traits.trust, agent.traits.loyalty, agent.traits.curiosity, agent.selfAwareness, agent.memoryCount
        )
        holder.paranoiaBar.progress = (agent.traits.paranoia * 100).toInt()
        holder.id.text = "id: ${agent.id}  (tap to target)"
        holder.itemView.setOnClickListener { onAgentTapped(agent) }
    }

    override fun getItemCount(): Int = items.size
}
