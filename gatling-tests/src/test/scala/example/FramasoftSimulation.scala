package example

import io.gatling.core.Predef._
import io.gatling.http.Predef._

class FramasoftSimulation extends Simulation {

  // Smoke test only: one virtual user, a few requests.
  // Do not raise this number against a third-party site without permission.
  val httpProtocol = http
    .baseUrl("https://framasoft.org")
    .acceptHeader("text/html,application/xhtml+xml")
    .userAgentHeader("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")

  private val scenario1 = scenario("Framasoft smoke")
    .exec(http("Homepage").get("/").check(status.is(200)))
    .pause(2)
    .exec(http("Homepage again").get("/").check(status.is(200)))

  private val assertion = global.failedRequests.count.lt(1)

  setUp(
    scenario1.inject(atOnceUsers(1))
  ).assertions(assertion).protocols(httpProtocol)
}
