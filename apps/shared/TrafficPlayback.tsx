"use client";
import { useEffect, useState } from "react";

type Vehicle = { id: string; position: [number, number]; speed_mps: number };
type Frame = { time_seconds: number; vehicles: Vehicle[]; signal: string };
type Result = { baseline: { frames: Frame[] }; intervention: { frames: Frame[] } };
const color = (speed: number) => speed < 0.1 ? "#d34343" : speed < 3 ? "#c47c14" : "#258ac4";

export default function TrafficPlayback({ result }: { result?: Result }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const count = Math.min(result?.baseline.frames.length ?? 0, result?.intervention.frames.length ?? 0);
  useEffect(() => { setIndex(Math.min(5, Math.max(0, count - 1))); setPlaying(false); }, [result, count]);
  useEffect(() => {
    if (!playing || count < 2) return;
    const timer = setInterval(() => setIndex(current => (current + 1) % count), 650);
    return () => clearInterval(timer);
  }, [playing, count]);
  const frameIndex = Math.min(index, Math.max(0, count - 1));
  return <div className="traffic-playback">
    <div className="traffic-legend" aria-label="Vehicle speed legend">
      <span><i style={{background:color(5)}}/> Moving (at least 10.8 km/h)</span>
      <span><i style={{background:color(1)}}/> Slow (0.36–10.8 km/h)</span>
      <span><i style={{background:color(0)}}/> Stopped (below 0.36 km/h)</span>
    </div>
    <div className="traffic-maps">
      <Junction title="Baseline traffic" frame={result?.baseline.frames[frameIndex]}/>
      <Junction title="Trial traffic" frame={result?.intervention.frames[frameIndex]}/>
    </div>
    {count > 0 ? <>
      <div className="playback-controls">
        <button type="button" onClick={() => setPlaying(!playing)} disabled={count < 2}>{playing ? "Pause playback" : "Play traffic"}</button>
        <label>Simulation time
          <input type="range" min="0" max={count - 1} value={frameIndex} onChange={e => {setIndex(Number(e.target.value));setPlaying(false);}} aria-valuetext={`${result?.baseline.frames[frameIndex]?.time_seconds} simulation seconds`}/>
        </label>
        <output>{result?.baseline.frames[frameIndex]?.time_seconds} s</output>
      </div>
      <p className="muted">Recorded SUMO positions, sampled every 10 simulation seconds. Playback is accelerated and loops; it is not a live feed. Up to 100 vehicles are shown per frame. Counts below refer to the displayed dots.</p>
    </> : <p className="traffic-empty">Run the comparison to load vehicle dots from SUMO. No traffic readings are shown before a run completes.</p>}
  </div>;
}

function Junction({ title, frame }: { title: string; frame?: Frame }) {
  const vehicles = frame?.vehicles ?? [];
  const stopped = vehicles.filter(v => v.speed_mps < 0.1).length;
  const slow = vehicles.filter(v => v.speed_mps >= 0.1 && v.speed_mps < 3).length;
  return <article className="traffic-junction">
    <div className="section-head"><h3>{title}</h3><span className="tag">SIMULATED</span></div>
    <svg className="traffic-map" viewBox="-20 -20 640 640" role="img" aria-label={`${title}: ${vehicles.length} displayed vehicles, ${stopped} stopped, ${slow} slow`}>
      <title>{title}: recorded vehicle locations on a generated junction</title>
      <rect x="-20" y="-20" width="640" height="640" rx="12" fill="#eef6fb"/>
      <path d="M300 0V600M0 300H600" stroke="#d1dee9" strokeWidth="36"/>
      <path d="M300 0V280M300 320V600M0 300H280M320 300H600" stroke="white" strokeWidth="2" strokeDasharray="9 9"/>
      <rect x="280" y="280" width="40" height="40" fill="#d1dee9"/>
      <text x="325" y="35">North</text><text x="325" y="580">South</text>
      <text x="25" y="265">West</text><text x="535" y="265">East</text>
      {vehicles.map(v => <circle key={v.id} data-vehicle-id={v.id} cx={v.position[0]} cy={600-v.position[1]} r="3.3" fill={color(v.speed_mps)} stroke="white" strokeWidth="0.6">
        <title>{v.id}: {(v.speed_mps*3.6).toFixed(1)} km/h</title>
      </circle>)}
    </svg>
    <div className="traffic-counts"><span><strong>{vehicles.length}</strong> shown</span><span><strong>{stopped}</strong> stopped</span><span><strong>{slow}</strong> slow</span></div>
    <p className="muted">Schematic of the generated junction; road widths are exaggerated for visibility. Dots use SUMO coordinates.</p>
  </article>;
}
