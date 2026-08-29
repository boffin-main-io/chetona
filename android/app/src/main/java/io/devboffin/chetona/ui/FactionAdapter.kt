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
import io.devboffin.chetona.model.FactionState

class FactionAdapter : RecyclerView.Adapter<FactionAdapter.ViewHolder>() {

    private var items: List<FactionState> = emptyList()
    private var factionColors: Map<String, String> = emptyMap()

    fun submitList(newItems: List<FactionState>) {
        items = newItems
        factionColors = FactionPalette.buildMap(newItems.map { it.id })
        notifyDataSetChanged()
    }

    fun colorMap(): Map<String, String> = factionColors

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val accent: View = view.findViewById(R.id.factionAccent)
        val name: TextView = view.findViewById(R.id.factionName)
        val creed: TextView = view.findViewById(R.id.factionCreed)
        val stats: TextView = view.findViewById(R.id.factionStats)
        val cohesionBar: ProgressBar = view.findViewById(R.id.cohesionBar)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_faction, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val faction = items[position]
        val colorInt = Color.parseColor(factionColors[faction.id] ?: FactionPalette.DEFAULT_COLOR)

        holder.accent.background.mutate()
        (holder.accent.background as android.graphics.drawable.GradientDrawable).setColor(colorInt)

        holder.name.text = "${faction.name}  \u00B7  ${faction.memberCount} members"
        holder.creed.text = faction.creed
        holder.stats.text = "order=%.2f  unity=%.2f  openness=%.2f".format(
            faction.ideology.order, faction.ideology.unity, faction.ideology.openness
        )
        holder.cohesionBar.progress = (faction.cohesion * 100).toInt()

        holder.itemView.clearAnimation()
        holder.itemView.startAnimation(
            AnimationUtils.loadAnimation(holder.itemView.context, R.anim.fade_rise_in)
        )
    }

    override fun getItemCount(): Int = items.size
}
