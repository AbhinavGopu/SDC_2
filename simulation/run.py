"""Real SUMO/TraCI on a generated, uncalibrated demonstration junction."""
import subprocess, tempfile
from pathlib import Path

def run_case(directory, seconds, seed, green):
    import traci
    label = "case-" + str(green)
    traci.start(["sumo", "-n", str(directory / "net.xml"), "-r", str(directory / "routes.xml"),
                 "--seed", str(seed), "--no-step-log", "true", "--duration-log.disable", "true",
                 "--time-to-teleport", "-1"], label=label)
    conn = traci.getConnection(label)
    speeds, halted, frames, arrived, co2_grams = [], [], [], 0, 0.0
    try:
        tls = conn.trafficlight.getIDList()[0]
        logic = conn.trafficlight.getAllProgramLogics(tls)[0]
        for phase in logic.phases:
            if "G" in phase.state or "g" in phase.state:
                phase.duration = green
        conn.trafficlight.setProgramLogic(tls, logic)
        for step in range(seconds):
            conn.simulationStep()
            ids = conn.vehicle.getIDList()
            speeds.extend(conn.vehicle.getSpeed(v) for v in ids)
            halted.append(sum(conn.vehicle.getSpeed(v) < 0.1 for v in ids))
            co2_grams += sum(conn.vehicle.getCO2Emission(v) for v in ids) / 1000
            arrived += conn.simulation.getArrivedNumber()
            if step % 10 == 0:
                frames.append({"time_seconds": step + 1, "vehicles": [{"id": v, "position": list(conn.vehicle.getPosition(v)), "speed_mps": conn.vehicle.getSpeed(v)} for v in ids[:100]],
                               "signal": conn.trafficlight.getRedYellowGreenState(tls)})
        return {"mean_speed_kmh": round(sum(speeds) / max(1, len(speeds)) * 3.6, 3),
                "mean_halting_vehicles": round(sum(halted) / len(halted), 3),
                "arrived_vehicles": arrived, "co2_grams": round(co2_grams, 3),
                "remaining_vehicles": conn.simulation.getMinExpectedNumber(), "frames": frames}
    finally:
        # Close through TraCI so its named-connection registry is cleared as well.
        # Closing only the connection leaves labels active on SUMO 1.15.
        traci.switch(label)
        traci.close()

def run_simulation(seconds=300, seed=42, green_seconds=25, **kwargs):
    with tempfile.TemporaryDirectory() as temp:
        p = Path(temp)
        p.joinpath("nodes.xml").write_text('<nodes><node id="c" x="300" y="300" type="traffic_light"/><node id="n" x="300" y="600"/><node id="s" x="300" y="0"/><node id="e" x="600" y="300"/><node id="w" x="0" y="300"/></nodes>')
        edges = ['<edges>']
        for d in "nsew":
            edges.extend([f'<edge id="{d}c" from="{d}" to="c" numLanes="1" speed="13.9"/>',
                          f'<edge id="c{d}" from="c" to="{d}" numLanes="1" speed="13.9"/>'])
        p.joinpath("edges.xml").write_text("".join(edges) + "</edges>")
        subprocess.run(["netconvert", "--node-files", str(p / "nodes.xml"), "--edge-files", str(p / "edges.xml"),
                        "--output-file", str(p / "net.xml"), "--tls.default-type", "static"], check=True, capture_output=True, timeout=30)
        routes = ['<routes><vType id="car" accel="2.6" decel="4.5" length="5" maxSpeed="13.9"/>']
        for index, (a, b) in enumerate([("n", "s"), ("s", "n"), ("e", "w"), ("w", "e")]):
            routes.append(f'<flow id="f{index}" type="car" begin="0" end="{seconds}" period="{3 if a in "ns" else 5}" departLane="best"><route edges="{a}c c{b}"/></flow>')
        p.joinpath("routes.xml").write_text("".join(routes) + "</routes>")
        baseline = run_case(p, seconds, seed, 40)
        intervention = run_case(p, seconds, seed, green_seconds)
        return {"engine": "SUMO/TraCI", "provenance": "simulated", "scenario": "generated four-arm junction; NOT a measured Hyderabad road",
                "seed": seed, "duration_seconds": seconds, "baseline_green_seconds": 40, "intervention_green_seconds": green_seconds,
                "limitations": ["Uncalibrated geometry and synthetic demand.", "Same seed and demand for both runs.", "Positive benefit is not guaranteed.", "Results apply only to the configured simulation horizon; unfinished vehicles are reported."],
                "baseline": baseline, "intervention": intervention}
