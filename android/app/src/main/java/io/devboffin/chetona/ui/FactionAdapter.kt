package io.devboffin.chetona.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ProgressBar
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.devboffin.chetona.R
import io.devboffin.chetona.model.FactionState

class FactionAdapter : RecyclerView.Adapter<FactionAdapter.ViewHolder>() {

    private var items: List<FactionState> = emptyList()

    fun submitList(newItems: List<FactionState>) {
        items = newItems
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
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
        holder.name.text = "${faction.name}  (${faction.memberCount} members)"
        holder.creed.text = faction.creed
        holder.stats.text = "order=%.2f  unity=%.2f  openness=%.2f".format(
            faction.ideology.order, faction.ideology.unity, faction.ideology.openness
        )
        holder.cohesionBar.progress = (faction.cohesion * 100).toInt()
    }

    override fun getItemCount(): Int = items.size
}
