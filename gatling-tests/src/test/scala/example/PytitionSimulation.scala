package example

import io.gatling.core.Predef._
import io.gatling.http.Predef._

class PytitionSimulation extends Simulation {

  // Local Pytition dev instance (python pytition/manage.py runserver).
  // Start it first; the base URL can be overridden with -DbaseUrl=...
  val baseUrl: String = System.getProperty("baseUrl", "http://localhost:8000")

  val httpProtocol = http
    .baseUrl(baseUrl)
    .acceptHeader("text/html,application/xhtml+xml")
    .userAgentHeader("Gatling Pytition smoke test")

  private val scenario1 = scenario("Pytition smoke")
    .exec(http("Index").get("/").check(status.is(200)))
    .pause(1)
    .exec(http("Petition list").get("/petition/").check(status.is(200)))

  private val assertion = global.failedRequests.count.lt(1)

  setUp(
    scenario1.inject(atOnceUsers(1))
  ).assertions(assertion).protocols(httpProtocol)
}
