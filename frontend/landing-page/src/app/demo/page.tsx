"use client";

import { useEffect, useRef, useState } from "react";
import { LocalSimulator, Mode, GridCell, AggregateMetrics } from "@/lib/localSimulator";
import { InsightsPanel } from "@/components/simulation/InsightsPanel";
import { TutorialOverlay } from "@/components/simulation/TutorialOverlay";
import { LiquidGlassCard } from "@/components/liquid-glass/LiquidGlassCard";
import { LiquidGlassButton } from "@/components/liquid-glass/LiquidGlassButton";
import {
  Play,
  Pause,
  RotateCcw,
  CloudRain,
  HelpCircle,
  TrendingDown,
  Sparkles,
  Zap,
  TrendingUp,
  Activity,
  AlertOctagon,
  CheckCircle2,
} from "lucide-react";
import dynamic from "next/dynamic";

const ParticleBackground = dynamic(
  () => import("@/components/ui/ParticleBackground").then(mod => mod.ParticleBackground),
  { ssr: false }
);

const MapSimulation = dynamic(
  () => import("@/components/simulation/MapSimulation"),
  { ssr: false }
);

interface Challenge {
  id: string;
  name: string;
  description: string;
  objective: string;
  setup: (sim: LocalSimulator) => void;
  checkGoal: (metrics: AggregateMetrics, disabledMetroLines: Set<string>, busCapacity: number, fuelTax: number) => boolean;
}

const CHALLENGES: Challenge[] = [
  {
    id: "monsoon",
    name: "Challenge 1: Monsoon Storm",
    description: "Heavy rain is causing gridlock. Citizens are abandoning bikes and walking.",
    objective: "Enact a public transit boost (set Bus Capacity to 150%) to absorb commuters and keep the Congestion Index under 0.65.",
    setup: (sim) => {
      sim.reset();
      sim.rain = 0.85;
      sim.busCapacityPct = 1.0;
      sim.fuelPriceDeltaPaise = 0;
    },
    checkGoal: (metrics, _lines, busCap) => {
      return metrics.rain_intensity >= 0.8 && busCap >= 1.45 && metrics.road_congestion_index <= 0.65;
    },
  },
  {
    id: "decarbonize",
    name: "Challenge 2: Decarbonization",
    description: "Commuters driving combustion private cars are raising Rajiv Chowk's AQI estimate past healthy levels.",
    objective: "Trigger a shift to electric metro and micro-mobility by raising the Carbon Fuel Tax (set Fuel Levy ₹100 or above). Bring AQI below 150.",
    setup: (sim) => {
      sim.reset();
      sim.rain = 0.0;
      sim.busCapacityPct = 1.0;
      sim.fuelPriceDeltaPaise = 0;
    },
    checkGoal: (metrics, _lines, _busCap, fuelTax) => {
      return fuelTax >= 10000 && metrics.aqi_estimate <= 150;
    },
  },
  {
    id: "metro_resilience",
    name: "Challenge 3: Metro Line Outage",
    description: "The DMRC Yellow Line is undergoing emergency maintenance. Commuters are stranded.",
    objective: "Toggle the DMRC Yellow Line shutdown, and mitigate the delay by boosting bus capacity to 140% or above.",
    setup: (sim) => {
      sim.reset();
      sim.rain = 0.0;
      sim.busCapacityPct = 1.0;
      sim.disabledMetroLines.add("Yellow");
      sim.fuelPriceDeltaPaise = 0;
    },
    checkGoal: (_metrics, lines, busCap) => {
      return lines.has("Yellow") && busCap >= 1.35;
    },
  },
];

export default function DemoPage() {
  const simRef = useRef<LocalSimulator | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [tick, setTick] = useState(0);
  const [metrics, setMetrics] = useState<AggregateMetrics | null>(null);
  const [grid, setGrid] = useState<GridCell[]>([]);
  const [timeStr, setTimeStr] = useState("08:00 AM");

  // Policy state hooks for sliders
  const [rainInput, setRainInput] = useState(0);
  const [busCapInput, setBusCapInput] = useState(100);
  const [fuelInput, setFuelInput] = useState(0);
  const [yellowLineDisabled, setYellowLineDisabled] = useState(false);
  const [blueLineDisabled, setBlueLineDisabled] = useState(false);

  // Tutorial and challenge states
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [activeChallengeId, setActiveChallengeId] = useState<string | null>(null);
  const [challengeSuccess, setChallengeSuccess] = useState(false);

  // History for sparklines
  const [commuteHistory, setCommuteHistory] = useState<number[]>([]);
  const [aqiHistory, setAqiHistory] = useState<number[]>([]);

  // Initialize simulator
  useEffect(() => {
    const sim = new LocalSimulator(15000);
    simRef.current = sim;
    const snap = sim.snapshot();
    setMetrics(snap.metrics);
    setGrid(snap.grid);
    setTimeStr(sim.getFormattedTime());

    // Auto open tutorial on first load
    setIsTourOpen(true);
  }, []);

  // Tick step trigger
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      if (simRef.current) {
        const snap = simRef.current.step();
        setTick(snap.tick);
        setMetrics(snap.metrics);
        setGrid(snap.grid);
        setTimeStr(simRef.current.getFormattedTime());

        // Update history (cap at 20 data points)
        setCommuteHistory((prev) => [...prev.slice(-19), snap.metrics.avg_commute_minutes]);
        setAqiHistory((prev) => [...prev.slice(-19), snap.metrics.aqi_estimate]);
      }
    }, 450); // fast loop

    return () => clearInterval(interval);
  }, [isPlaying]);

  // Sync state parameters to simulator
  useEffect(() => {
    const sim = simRef.current;
    if (!sim) return;

    // Skip syncing parameters if a challenge is overriding setup (until manual changes occur)
    sim.rain = rainInput / 100;
    sim.busCapacityPct = busCapInput / 100;
    sim.fuelPriceDeltaPaise = fuelInput * 100; // Rs to Paise

    const disabled = new Set<string>();
    if (yellowLineDisabled) disabled.add("Yellow");
    if (blueLineDisabled) disabled.add("Blue");
    sim.disabledMetroLines = disabled;

    // Recalculate snap immediately
    const snap = sim.snapshot();
    setMetrics(snap.metrics);
    setGrid(snap.grid);
  }, [rainInput, busCapInput, fuelInput, yellowLineDisabled, blueLineDisabled]);

  // Evaluate challenge checks
  useEffect(() => {
    if (!activeChallengeId || !metrics) return;

    const challenge = CHALLENGES.find((c) => c.id === activeChallengeId);
    if (challenge && simRef.current) {
      const isSuccess = challenge.checkGoal(
        metrics,
        simRef.current.disabledMetroLines,
        simRef.current.busCapacityPct,
        simRef.current.fuelPriceDeltaPaise
      );
      setChallengeSuccess(isSuccess);
    }
  }, [metrics, activeChallengeId, yellowLineDisabled, blueLineDisabled, rainInput, busCapInput, fuelInput]);

  const togglePlay = () => setIsPlaying(!isPlaying);

  const triggerReset = () => {
    if (simRef.current) {
      simRef.current.reset();
      const snap = simRef.current.snapshot();
      setTick(snap.tick);
      setMetrics(snap.metrics);
      setGrid(snap.grid);
      setTimeStr(simRef.current.getFormattedTime());

      // Reset controls
      setRainInput(0);
      setBusCapInput(100);
      setFuelInput(0);
      setYellowLineDisabled(false);
      setBlueLineDisabled(false);
      setActiveChallengeId(null);
      setChallengeSuccess(false);
      setCommuteHistory([]);
      setAqiHistory([]);
    }
  };

  const loadChallenge = (challenge: Challenge) => {
    if (simRef.current) {
      challenge.setup(simRef.current);
      setActiveChallengeId(challenge.id);
      setChallengeSuccess(false);

      // Sync controls back
      setRainInput(simRef.current.rain * 100);
      setBusCapInput(simRef.current.busCapacityPct * 100);
      setFuelInput(simRef.current.fuelPriceDeltaPaise / 100);
      setYellowLineDisabled(simRef.current.disabledMetroLines.has("Yellow"));
      setBlueLineDisabled(simRef.current.disabledMetroLines.has("Blue"));

      // Refresh metrics
      const snap = simRef.current.snapshot();
      setTick(snap.tick);
      setMetrics(snap.metrics);
      setGrid(snap.grid);
      setTimeStr(simRef.current.getFormattedTime());
      setIsPlaying(true); // start playing for dynamic feedback
    }
  };

  return (
    <main className="relative w-full min-h-screen text-white font-sans overflow-x-hidden selection:bg-purple-500/30 bg-[#070505]">
      {/* GL particles backdrop */}
      <ParticleBackground />

      {/* Main dashboard grid container */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-4 md:px-8 py-8 flex flex-col gap-6">
        
        {/* Top Header Bar */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono tracking-widest text-purple-400 bg-purple-950/45 border border-purple-500/30">
                DECISION SANDBOX
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-mono text-stone-400">Offline Simulation Active</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-light tracking-tight mt-1 text-white">
              STRATA <span className="text-stone-500 font-extralight">| Command Center</span>
            </h1>
            <p className="text-xs text-stone-400 font-light mt-1">
              Rajiv Chowk (New Delhi) concentric policy evaluation simulator
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => {
                setTourStep(0);
                setIsTourOpen(true);
              }}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-stone-300 text-xs font-light transition-all border border-white/5"
            >
              <HelpCircle className="w-4 h-4 text-purple-400" />
              Guide Tour
            </button>
            <LiquidGlassButton
              onClick={triggerReset}
              className="rounded-xl px-4 py-2 text-xs font-semibold"
            >
              <span className="flex items-center gap-1">
                <RotateCcw className="w-3.5 h-3.5" />
                Reset Board
              </span>
            </LiquidGlassButton>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* LEFT PANEL: Policy Controls (lg:col-span-3) */}
          <section className="lg:col-span-3 flex flex-col gap-6">
            
            {/* Simulation Engine Controls */}
            <LiquidGlassCard className="p-5" variant="default">
              <h2 className="text-xs font-mono tracking-widest text-stone-400 uppercase mb-4 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-purple-400" />
                Engine Controls
              </h2>

              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between text-xs text-stone-300 bg-stone-900/60 p-3 rounded-2xl border border-white/5 font-mono">
                  <span>TICK: {tick}</span>
                  <span className="text-purple-400 font-medium">{timeStr}</span>
                </div>

                <div className="flex gap-2">
                  <LiquidGlassButton
                    onClick={togglePlay}
                    className="flex-1 rounded-2xl py-3 justify-center text-xs font-bold"
                  >
                    {isPlaying ? (
                      <span className="flex items-center gap-1.5">
                        <Pause className="w-4 h-4 fill-current" /> Pause
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <Play className="w-4 h-4 fill-current" /> Run Ticks
                      </span>
                    )}
                  </LiquidGlassButton>
                </div>
              </div>
            </LiquidGlassCard>

            {/* Environmental & Weather inputs */}
            <LiquidGlassCard className="p-5" variant="default">
              <h2 className="text-xs font-mono tracking-widest text-stone-400 uppercase mb-4 flex items-center gap-1.5">
                <CloudRain className="w-4 h-4 text-sky-400" />
                Environment Events
              </h2>

              <div className="space-y-5">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-light text-stone-300">Monsoon Rain Intensity</span>
                    <span className="font-mono text-purple-400 font-semibold">{rainInput}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={rainInput}
                    onChange={(e) => setRainInput(Number(e.target.value))}
                    className="w-full h-1 bg-stone-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
                  />
                  <div className="flex justify-between text-[10px] text-stone-500 mt-1 font-mono">
                    <span>Dry</span>
                    <span>Downpour</span>
                  </div>
                </div>
              </div>
            </LiquidGlassCard>

            {/* Policy Interventions */}
            <LiquidGlassCard className="p-5" variant="default">
              <h2 className="text-xs font-mono tracking-widest text-stone-400 uppercase mb-4 flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-purple-400" />
                Policy Interventions
              </h2>

              <div className="space-y-6">
                {/* Bus capacity boost */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-light text-stone-300">Bus Capacity Level</span>
                    <span className="font-mono text-purple-400 font-semibold">{busCapInput}%</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="150"
                    value={busCapInput}
                    onChange={(e) => setBusCapInput(Number(e.target.value))}
                    className="w-full h-1 bg-stone-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
                  />
                  <div className="flex justify-between text-[10px] text-stone-500 mt-1 font-mono">
                    <span>50% (Choked)</span>
                    <span>150% (Boosted)</span>
                  </div>
                </div>

                {/* Fuel tax */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-light text-stone-300">Carbon Fuel Levy</span>
                    <span className="font-mono text-purple-400 font-semibold">₹{fuelInput}/L</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={fuelInput}
                    onChange={(e) => setFuelInput(Number(e.target.value))}
                    className="w-full h-1 bg-stone-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
                  />
                  <div className="flex justify-between text-[10px] text-stone-500 mt-1 font-mono">
                    <span>No Levy</span>
                    <span>₹200/L Tax</span>
                  </div>
                </div>

                {/* Metro shutdown toggles */}
                <div className="pt-2 border-t border-white/5 space-y-3">
                  <span className="text-[11px] font-mono text-stone-500 uppercase block">Transit Line Health</span>
                  
                  <label className="flex items-center justify-between text-xs font-light text-stone-300 cursor-pointer p-1.5 rounded-lg hover:bg-white/5 transition-colors">
                    <span>DMRC Yellow Line Outage</span>
                    <input
                      type="checkbox"
                      checked={yellowLineDisabled}
                      onChange={(e) => setYellowLineDisabled(e.target.checked)}
                      className="rounded border-white/10 text-purple-500 focus:ring-0 focus:ring-offset-0 bg-stone-900 w-4 h-4 cursor-pointer accent-purple-500"
                    />
                  </label>

                  <label className="flex items-center justify-between text-xs font-light text-stone-300 cursor-pointer p-1.5 rounded-lg hover:bg-white/5 transition-colors">
                    <span>DMRC Blue Line Outage</span>
                    <input
                      type="checkbox"
                      checked={blueLineDisabled}
                      onChange={(e) => setBlueLineDisabled(e.target.checked)}
                      className="rounded border-white/10 text-purple-500 focus:ring-0 focus:ring-offset-0 bg-stone-900 w-4 h-4 cursor-pointer accent-purple-500"
                    />
                  </label>
                </div>
              </div>
            </LiquidGlassCard>

          </section>

          {/* CENTER PANEL: Canvas Map & Insights (lg:col-span-5) */}
          <section className="lg:col-span-5 flex flex-col gap-6 items-center">
            
            {/* Visual network simulator */}
            <MapSimulation
              grid={grid}
              rainIntensity={rainInput / 100}
              roadCongestion={metrics?.road_congestion_index || 0}
              isPlaying={isPlaying}
              timeOfDay={timeStr}
            />

            {/* Simulated AI insights explaining causality */}
            {metrics && (
              <InsightsPanel
                metrics={metrics}
                disabledMetroLines={
                  new Set(
                    [yellowLineDisabled ? "Yellow" : "", blueLineDisabled ? "Blue" : ""].filter(Boolean)
                  )
                }
                busCapacityPct={busCapInput / 100}
                fuelPriceDeltaPaise={fuelInput * 100}
              />
            )}

          </section>

          {/* RIGHT PANEL: Live Telemetry Metrics & Challenges (lg:col-span-4) */}
          <section className="lg:col-span-4 flex flex-col gap-6">
            
            {/* Core gauges */}
            <LiquidGlassCard className="p-5" variant="default">
              <h2 className="text-xs font-mono tracking-widest text-stone-400 uppercase mb-4 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-purple-400" />
                Live City Telemetry
              </h2>

              {metrics && (
                <div className="grid grid-cols-2 gap-4">
                  {/* Commute time metric */}
                  <div className="p-3.5 bg-stone-900/60 rounded-2xl border border-white/5 flex flex-col justify-between">
                    <span className="text-[10px] font-mono text-stone-500 uppercase">Avg Commute</span>
                    <div className="my-2">
                      <span className="text-2xl font-light text-white font-mono">
                        {metrics.avg_commute_minutes}
                      </span>
                      <span className="text-[10px] text-stone-400 font-light ml-1">mins</span>
                    </div>
                    {/* Commute sparkline */}
                    <div className="h-6 flex items-end gap-0.5 pt-1.5">
                      {commuteHistory.map((val, i) => (
                        <div
                          key={i}
                          style={{ height: `${Math.min(100, (val / 80) * 100)}%` }}
                          className="flex-1 min-w-[2px] bg-purple-400/60 rounded-sm"
                        />
                      ))}
                    </div>
                  </div>

                  {/* AQI metric */}
                  <div className="p-3.5 bg-stone-900/60 rounded-2xl border border-white/5 flex flex-col justify-between">
                    <span className="text-[10px] font-mono text-stone-500 uppercase">AQI Estimate</span>
                    <div className="my-2 flex items-baseline justify-between">
                      <span className="text-2xl font-light text-white font-mono">
                        {metrics.aqi_estimate}
                      </span>
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                          metrics.aqi_estimate > 200
                            ? "bg-red-950/45 text-red-400 border border-red-500/20"
                            : metrics.aqi_estimate > 100
                            ? "bg-amber-950/45 text-amber-400 border border-amber-500/20"
                            : "bg-emerald-950/45 text-emerald-400 border border-emerald-500/20"
                        }`}
                      >
                        {metrics.aqi_estimate > 200 ? "POOR" : metrics.aqi_estimate > 100 ? "MODERATE" : "GOOD"}
                      </span>
                    </div>
                    {/* AQI sparkline */}
                    <div className="h-6 flex items-end gap-0.5 pt-1.5">
                      {aqiHistory.map((val, i) => (
                        <div
                          key={i}
                          style={{ height: `${Math.min(100, (val / 350) * 100)}%` }}
                          className={`flex-1 min-w-[2px] rounded-sm ${
                            val > 200 ? "bg-red-400/60" : val > 100 ? "bg-amber-400/60" : "bg-emerald-400/60"
                          }`}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Road Congestion metric */}
                  <div className="p-3.5 bg-stone-900/60 rounded-2xl border border-white/5 col-span-2">
                    <div className="flex justify-between items-center text-[10px] font-mono text-stone-500 uppercase mb-2">
                      <span>Road Congestion Index</span>
                      <span className="text-white font-semibold font-mono">
                        {Math.round(metrics.road_congestion_index * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-stone-800 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${metrics.road_congestion_index * 100}%` }}
                        className={`h-full transition-all duration-300 ${
                          metrics.road_congestion_index > 0.65
                            ? "bg-red-500"
                            : metrics.road_congestion_index > 0.4
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                      />
                    </div>
                  </div>

                  {/* Metro and Bus loads */}
                  <div className="p-3.5 bg-stone-900/60 rounded-2xl border border-white/5">
                    <div className="flex justify-between items-center text-[10px] font-mono text-stone-500 uppercase mb-1">
                      <span>Metro Load</span>
                      <span className="text-sky-400 font-mono font-medium">
                        {Math.round(metrics.metro_load_pct)}%
                      </span>
                    </div>
                    <div className="w-full h-1 bg-stone-850 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${Math.min(100, metrics.metro_load_pct)}%` }}
                        className={`h-full ${metrics.metro_load_pct > 90 ? "bg-red-400" : "bg-sky-400"}`}
                      />
                    </div>
                  </div>

                  <div className="p-3.5 bg-stone-900/60 rounded-2xl border border-white/5">
                    <div className="flex justify-between items-center text-[10px] font-mono text-stone-500 uppercase mb-1">
                      <span>Bus Load</span>
                      <span className="text-emerald-400 font-mono font-medium">
                        {Math.round(metrics.bus_load_pct)}%
                      </span>
                    </div>
                    <div className="w-full h-1 bg-stone-850 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${Math.min(100, metrics.bus_load_pct)}%` }}
                        className={`h-full ${metrics.bus_load_pct > 90 ? "bg-red-400" : "bg-emerald-400"}`}
                      />
                    </div>
                  </div>
                </div>
              )}
            </LiquidGlassCard>

            {/* Mode share distribution */}
            <LiquidGlassCard className="p-5" variant="default">
              <h2 className="text-xs font-mono tracking-widest text-stone-400 uppercase mb-4 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-purple-400" />
                Mode Share Distribution
              </h2>

              {metrics && (
                <div className="space-y-3">
                  {[
                    { label: "DMRC Metro", val: metrics.mode_share[Mode.metro] || 0, color: "bg-blue-400" },
                    { label: "Municipal Bus", val: metrics.mode_share[Mode.bus] || 0, color: "bg-emerald-400" },
                    { label: "Private Auto", val: metrics.mode_share[Mode.car] || 0, color: "bg-red-400" },
                    { label: "Auto-Rickshaw", val: metrics.mode_share[Mode.auto] || 0, color: "bg-amber-400" },
                    { label: "Walking/Micro", val: (metrics.mode_share[Mode.walk] || 0) + (metrics.mode_share[Mode.bike] || 0) + (metrics.mode_share[Mode.bike_share] || 0) + (metrics.mode_share[Mode.e_rickshaw] || 0), color: "bg-purple-400" },
                  ]
                    .sort((a, b) => b.val - a.val)
                    .map((item, i) => (
                      <div key={i} className="text-xs">
                        <div className="flex justify-between font-light mb-1">
                          <span className="text-stone-300">{item.label}</span>
                          <span className="font-mono text-stone-400">{Math.round(item.val * 100)}%</span>
                        </div>
                        <div className="w-full h-1 bg-stone-900 rounded-full overflow-hidden">
                          <div style={{ width: `${item.val * 100}%` }} className={`h-full ${item.color}`} />
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </LiquidGlassCard>

            {/* Curated Challenges preset box */}
            <LiquidGlassCard className="p-5 border-purple-500/20" variant="chrome">
              <h2 className="text-xs font-mono tracking-widest text-purple-400 uppercase mb-4 flex items-center gap-1.5 font-bold">
                <Zap className="w-4 h-4 text-purple-400" />
                Policy Challenges
              </h2>

              <div className="flex flex-col gap-4">
                {CHALLENGES.map((challenge) => {
                  const isActive = activeChallengeId === challenge.id;
                  return (
                    <button
                      key={challenge.id}
                      onClick={() => loadChallenge(challenge)}
                      className={`text-left p-3.5 rounded-2xl border transition-all cursor-pointer ${
                        isActive
                          ? "bg-purple-950/40 border-purple-500/40"
                          : "bg-stone-900/40 border-white/5 hover:bg-stone-900/60 hover:border-white/10"
                      }`}
                    >
                      <h3 className="text-xs font-semibold text-white mb-1 font-mono">
                        {challenge.name}
                      </h3>
                      <p className="text-[11px] text-stone-400 font-light leading-relaxed mb-2">
                        {challenge.description}
                      </p>
                      {isActive && (
                        <div className="mt-2.5 pt-2.5 border-t border-purple-500/20 bg-purple-950/30 -mx-3.5 -mb-3.5 p-3.5 rounded-b-2xl">
                          <span className="text-[10px] font-mono text-purple-300 uppercase block font-bold mb-1">
                            OBJECTIVE:
                          </span>
                          <span className="text-[11px] font-light text-stone-300 leading-relaxed block">
                            {challenge.objective}
                          </span>

                          <div className="mt-3 flex items-center gap-1.5">
                            {challengeSuccess ? (
                              <div className="flex items-center gap-1 text-emerald-400 text-xs font-bold font-mono">
                                <CheckCircle2 className="w-4 h-4 shrink-0" />
                                Goal Met! Success.
                              </div>
                            ) : (
                              <div className="flex items-center gap-1 text-amber-400 text-xs font-bold font-mono animate-pulse">
                                <AlertOctagon className="w-4 h-4 shrink-0" />
                                Monitoring criteria...
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </LiquidGlassCard>

          </section>

        </div>

      </div>

      {/* Guided Walkthrough Overlay */}
      <TutorialOverlay
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        currentStep={tourStep}
        setCurrentStep={setTourStep}
      />
    </main>
  );
}
