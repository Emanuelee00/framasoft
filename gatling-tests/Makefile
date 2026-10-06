MVN := PATH="$(HOME)/.local/jdk-27/bin:$(HOME)/.local/apache-maven-3.10.0/bin:$(PATH)" mvn

# Runs all Gatling simulations under src/test/scala
# "-" lets make continue to the analysis step even if Gatling's assertions
# fail the build (which they will, on purpose, for a test designed to break
# the server) — that's exactly the run we most want analyzed.
test:
	-$(MVN) gatling:test
	@python3 analyze_results.py

# Runs a single simulation, e.g.: make test-one SIM=example.PytitionSimulation
test-one:
	-$(MVN) gatling:test -Dgatling.simulationClass=$(SIM)
	@python3 analyze_results.py

# Shows an interactive menu (questionary) to pick which simulation to run
choose:
	@PATH="$(HOME)/.local/jdk-27/bin:$(HOME)/.local/apache-maven-3.10.0/bin:$(PATH)" python3 choose_test.py
	@python3 analyze_results.py

.PHONY: test test-one choose
