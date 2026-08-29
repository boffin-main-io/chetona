package io.devboffin.chetona

import android.content.Intent
import android.os.Bundle
import android.view.animation.AnimationUtils
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/**
 * TitleActivity — অ্যাপের প্রথম স্ক্রিন। একটা atmosphere তৈরি করে
 * ("তুমি ঘাঁটি ভাঙো না, তুমি মন ভাঙো") তারপর MainActivity-তে নিয়ে যায়।
 */
class TitleActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_title)

        val glyph = findViewById<TextView>(R.id.titleGlyph)
        glyph.startAnimation(AnimationUtils.loadAnimation(this, R.anim.pulse_glow))

        findViewById<Button>(R.id.enterButton).setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
}
