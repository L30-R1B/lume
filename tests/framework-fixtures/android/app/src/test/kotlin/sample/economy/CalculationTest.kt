package sample.economy
import org.junit.Assert.assertEquals
import org.junit.Test
class CalculationTest {
    @Test fun checksTwice() { assertEquals(42, twice(21)); assertEquals(-6, twice(-3)) }
}
