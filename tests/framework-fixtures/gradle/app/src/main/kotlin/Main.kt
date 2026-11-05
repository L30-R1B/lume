import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
fun twice(n: Int): Int = n * 2
fun main(args: Array<String>) {
    check(twice(21) == 42)
    val factory = DocumentBuilderFactory.newInstance()
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
    val xml = factory.newDocumentBuilder().parse(File(args[0]))
    check(xml.getElementsByTagName("string").item(0).textContent.isNotBlank())
    println("Kotlin and Android resource fixture verified")
}
