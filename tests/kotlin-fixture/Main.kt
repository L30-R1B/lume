package fixture
fun twice(value: Int): Int = value * 2
fun main() { check(twice(21) == 42); println("verified") }
