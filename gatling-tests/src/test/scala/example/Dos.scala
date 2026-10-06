package example

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class Dos extends Simulation {

  val httpProtocol = http
    .baseUrl("http://127.0.0.1:8000")
    .acceptHeader("application/json")
    .userAgentHeader("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")

  val scn = scenario("Dos test")
    .exec(http("Home").get("/"))

  private val assertion = global.failedRequests.count.lt(1)

  // Open model (default) or closed model with -Dclosed=true:
  //   mvn gatling:test -Dgatling.simulationClass=example.Dos
  //   mvn gatling:test -Dgatling.simulationClass=example.Dos -Dclosed=true
  val useClosedModel: Boolean = java.lang.Boolean.getBoolean("closed")

  // Optional custom load: -Dusers=<N> -Dseconds=<S> ramps N users over S seconds
  // instead of the default staged profile below.
  val customUsers: Option[Int] = Option(System.getProperty("users")).map(_.toInt)
  val customSeconds: Option[Int] = Option(System.getProperty("seconds")).map(_.toInt)

  (customUsers, customSeconds) match {
    case (Some(users), Some(seconds)) =>
      // custom: ramp the requested number of users over the requested duration
      if (!useClosedModel) {
        setUp(
          scn.inject(
            rampUsers(users).during(seconds.seconds)
          )
        ).assertions(assertion).protocols(httpProtocol)
      } else {
        setUp(
          scn.inject(
            rampConcurrentUsers(0).to(users).during(seconds.seconds)
          )
        ).assertions(assertion).protocols(httpProtocol)
      }

    case _ =>
      if (!useClosedModel) {
        // open model: step up concurrent load in stages, pausing between steps.
        // This finds the service's real breaking point (errors/latency climbing)
        // without ever holding 50k connections open on the local load generator at once.
        setUp(
          scn.inject(
            atOnceUsers(500),
            nothingFor(10.seconds),
            atOnceUsers(2000),
            nothingFor(10.seconds),
            atOnceUsers(5000),
            nothingFor(10.seconds),
            atOnceUsers(10000),
            nothingFor(10.seconds),
            atOnceUsers(20000),
            nothingFor(10.seconds),
            atOnceUsers(50000)
          )
        ).assertions(assertion).protocols(httpProtocol)
      } else {
        // closed model: ramp concurrent users up through the same stages
        setUp(
          scn.inject(
            rampConcurrentUsers(0).to(500).during(10.seconds),
            rampConcurrentUsers(500).to(2000).during(10.seconds),
            rampConcurrentUsers(2000).to(5000).during(10.seconds),
            rampConcurrentUsers(5000).to(10000).during(10.seconds),
            rampConcurrentUsers(10000).to(20000).during(10.seconds),
            rampConcurrentUsers(20000).to(50000).during(10.seconds)
          )
        ).assertions(assertion).protocols(httpProtocol)
      }
  }
}

