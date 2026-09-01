package io.devboffin.chetona.ui

import android.graphics.Color
import android.graphics.Typeface
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.devboffin.chetona.R
import io.devboffin.chetona.model.RecentEvent

/**
 * EventAdapter — "World Pulse" ফিড। এটাই player-কে সরাসরি AI-এর
 * ভেতরটা দেখায়: agent-রা কী ভাবছে, কার প্রতি সন্দেহ জাগছে, কে
 * defect করলো — সংখ্যা নয়, ঘটনা হিসেবে।
 */
class EventAdapter : RecyclerView.Adapter<EventAdapter.ViewHolder>() {

    private var items: List<RecentEvent> = emptyList()

    fun submitList(newItems: List<RecentEvent>) {
        items = newItems
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val accent: View = view.findViewById(R.id.eventAccent)
        val text: TextView = view.findViewById(R.id.eventText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_event, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val event = items[position]
        val (color, prefix, italic) = when (event.kind) {
            "reflection" -> Triple("#81B29A", "\u2726", true)   // ✦ teal, italic — a genuine thought
            "defection" -> Triple("#E63946", "\u2620", false)   // ☠ red — major consequence
            "faction" -> Triple("#F2CC8F", "\u26A0", false)     // ⚠ gold — structural warning
            "rumor" -> Triple("#9B5DE5", "\u2192", false)       // → violet — your action landed
            "infiltration" -> Triple("#3D5A80", "\u21AF", false) // ↯ steel blue — cross-world
            "stage" -> Triple("#F0EDE5", "\u25C6", false)       // ◆ bright — objective progressed
            else -> Triple("#65637A", "\u2022", false)
        }
        holder.accent.setBackgroundColor(Color.parseColor(color))
        holder.text.text = "$prefix  ${event.text}"
        holder.text.setTextColor(Color.parseColor(if (event.kind == "reflection") color else "#A8A6B8"))
        holder.text.setTypeface(null, if (italic) Typeface.ITALIC else Typeface.NORMAL)
    }

    override fun getItemCount(): Int = items.size
}
