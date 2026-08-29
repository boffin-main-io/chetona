package io.devboffin.chetona.ui

/**
 * FactionPalette — faction_id-কে একটা রঙে ম্যাপ করে, index অনুযায়ী।
 * graph.html-এর palette-এর সাথে মিলিয়ে রাখা হয়েছে যাতে agent card,
 * faction card, আর relationship graph — সব জায়গায় একই faction একই রঙ পায়।
 */
object FactionPalette {
    private val colors = listOf(
        "#E07A5F", // ember orange — matches The Ember Circle
        "#81B29A", // loom teal — matches Wandering Loom
        "#F2CC8F",
        "#3D5A80",
        "#9B5DE5",
        "#F15BB5",
    )

    fun buildMap(factionIdsInOrder: List<String>): Map<String, String> =
        factionIdsInOrder.withIndex().associate { (i, id) -> id to colors[i % colors.size] }

    const val DEFAULT_COLOR = "#65637A"
}
