package sample.economy
import android.app.Activity
import android.os.Bundle
import android.widget.TextView
fun twice(value: Int): Int = value * 2
class MainActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val label = TextView(this)
        label.text = getString(R.string.app_name) + twice(21)
        setContentView(label)
    }
}
