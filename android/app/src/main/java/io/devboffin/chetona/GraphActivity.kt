package io.devboffin.chetona

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

/**
 * GraphActivity — সভ্যতার relationship graph দেখায় (agent সবুজ/লাল edge,
 * faction অনুযায়ী রঙ, self-awareness অনুযায়ী node-এর আকার)।
 *
 * graph.html কোনো CDN/library আনে না — সম্পূর্ণ offline-এ কাজ করে, যেহেতু
 * ফোন হয়তো শুধু LAN-এ সার্ভারের সাথে কানেক্টেড, internet ছাড়া।
 */
class GraphActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    companion object {
        const val EXTRA_GRAPH_JSON = "graph_json"

        fun start(context: Context, graphJson: String) {
            val intent = Intent(context, GraphActivity::class.java)
            intent.putExtra(EXTRA_GRAPH_JSON, graphJson)
            context.startActivity(intent)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        val graphJson = intent.getStringExtra(EXTRA_GRAPH_JSON) ?: "{}"

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                // safely pass the JSON string into the page's JS scope
                val escaped = org.json.JSONObject.quote(graphJson)
                view.evaluateJavascript("renderGraph($escaped)", null)
            }
        }
        webView.loadUrl("file:///android_asset/graph.html")
    }
}
