package io.devboffin.chetona.ui

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.AnimationUtils
import android.widget.ProgressBar
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.devboffin.chetona.R
import io.devboffin.chetona.model.AgentState

class AgentAdapter(
    private val onAgentTapped: (AgentState) -> Unit,
) : RecyclerView.Adapter<AgentAdapter.ViewHolder>() {

    private var items: List<AgentState> = emptyList()
    private var factionColors: Map<String, String> = emptyMap()

    fun submitList(newItems: List<AgentState>, factionColorMap: Map<String, String>) {
        items = newItems
        factionColors = factionColorMap
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val avatar: TextView = view.findViewById(R.id.agentAvatar)
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
        val factionColor = agent.factionId?.let { factionColors[it] } ?: FactionPalette.DEFAULT_COLOR
        val colorInt = Color.parseColor(factionColor)

        holder.avatar.text = agent.name.take(1).uppercase()
        holder.avatar.background.mutate()
        (holder.avatar.background as android.graphics.drawable.GradientDrawable).setColor(colorInt)
        holder.avatar.alpha = if (agent.alive) 1.0f else 0.35f

        val statusPrefix = if (!agent.alive) "\u2620 " else ""
        holder.name.text = "$statusPrefix${agent.name}"
        holder.faction.text = if (agent.factionId != null) "loyal to a faction" else "defected — no faction"
        holder.stats.text = "trust=%.2f  loyalty=%.2f  curiosity=%.2f  awareness=%.2f  mem=%d".format(
            agent.traits.trust, agent.traits.loyalty, agent.traits.curiosity, agent.selfAwareness, agent.memoryCount
        )
        holder.paranoiaBar.progress = (agent.traits.paranoia * 100).toInt()
        holder.id.text = "id: ${agent.id}  \u00B7  tap to target"
        holder.itemView.setOnClickListener { onAgentTapped(agent) }

        holder.itemView.clearAnimation()
        holder.itemView.startAnimation(
            AnimationUtils.loadAnimation(holder.itemView.context, R.anim.fade_rise_in)
        )
    }

    override fun getItemCount(): Int = items.size
}
