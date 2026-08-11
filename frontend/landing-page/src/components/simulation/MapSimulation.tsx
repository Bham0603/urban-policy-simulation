"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { GridCell } from "@/lib/localSimulator";

interface MapSimulationProps {
  grid: GridCell[];
  rainIntensity: number;
  roadCongestion: number;
  isPlaying: boolean;
  timeOfDay: string;
}

interface MapParticle {
  progress: number;
  speed: number;
  type: "citizen" | "delivery";
  pathType: "radial" | "concentric" | "metro";
  lineIndex: number;
  direction: 1 | -1;
  lat: number;
  lon: number;
}

export default function MapSimulation({
  grid,
  rainIntensity,
  roadCongestion,
  isPlaying,
  timeOfDay,
}: MapSimulationProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const rectsRef = useRef<L.Rectangle[]>([]);
  const particlesRef = useRef<MapParticle[]>([]);

  const centerLat = 28.6328;
  const centerLon = 77.2197;
  const maxSpan = 0.018; // Degrees span for radial nodes

  // DMRC Metro Stations Coords
  const stations = [
    { coords: [28.6328, 77.2197], name: "Rajiv Chowk" },
    { coords: [28.6431, 77.2214], name: "New Delhi Station" },
    { coords: [28.6231, 77.2150], name: "Patel Chowk" },
    { coords: [28.6395, 77.2085], name: "R.K. Ashram Marg" },
    { coords: [28.6300, 77.2295], name: "Barakhamba Road" },
  ];

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // 1. Create Leaflet Map instance
    const map = L.map(mapContainerRef.current, {
      center: [centerLat, centerLon],
      zoom: 14,
      zoomControl: false,
      attributionControl: false,
      maxBounds: [
        [28.60, 77.18],
        [28.67, 77.26],
      ],
      minZoom: 13,
      maxZoom: 16,
    });
    mapRef.current = map;

    // 2. Add CartoDB Dark Matter tile layer
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
    }).addTo(map);

    // 3. Draw Metro Tracks
    // Yellow Line (North-South)
    L.polyline(
      [
        [28.6580, 77.2160],
        [28.6431, 77.2214],
        [28.6328, 77.2197],
        [28.6231, 77.2150],
        [28.6080, 77.2090],
      ] as L.LatLngExpression[],
      {
        color: "rgba(234, 179, 8, 0.45)", // DMRC Yellow Line
        weight: 3.5,
      }
    ).addTo(map);

    // Blue Line (East-West)
    L.polyline(
      [
        [28.6360, 77.1950],
        [28.6395, 77.2085],
        [28.6328, 77.2197],
        [28.6300, 77.2295],
        [28.6260, 77.2480],
      ] as L.LatLngExpression[],
      {
        color: "rgba(59, 130, 246, 0.45)", // DMRC Blue Line
        weight: 3.5,
      }
    ).addTo(map);

    // 4. Draw Station Nodes
    stations.forEach((st) => {
      L.circleMarker(st.coords as L.LatLngExpression, {
        radius: st.name === "Rajiv Chowk" ? 6 : 4.5,
        fillColor: "#3b82f6",
        fillOpacity: 0.8,
        color: "#ffffff",
        weight: 1,
      })
        .addTo(map)
        .bindTooltip(st.name, { permanent: false, direction: "top", opacity: 0.85 });
    });

    // 5. Draw 100 Congestion Grid Cells
    const rects: L.Rectangle[] = [];
    const rows = 10;
    const cols = 10;
    // Map bounds spans approx 0.05 degrees total
    const cellW = 0.005;
    const cellH = 0.005;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellLat = centerLat + (r - rows / 2) * cellH;
        const cellLon = centerLon + (c - cols / 2) * cellW;

        const bounds: L.LatLngBoundsExpression = [
          [cellLat - cellH / 2, cellLon - cellW / 2],
          [cellLat + cellH / 2, cellLon + cellW / 2],
        ];

        const rect = L.rectangle(bounds, {
          color: "rgba(255, 255, 255, 0.015)",
          weight: 0.5,
          fillColor: "rgb(239, 68, 68)",
          fillOpacity: 0.0,
        }).addTo(map);

        rects.push(rect);
      }
    }
    rectsRef.current = rects;

    // 6. Initialize geolocated particles
    const particles: MapParticle[] = [];
    const count = 160;

    for (let i = 0; i < count; i++) {
      const type = Math.random() < 0.25 ? "delivery" : "citizen";
      const pathType = Math.random() < 0.15 ? "metro" : Math.random() < 0.45 ? "radial" : "concentric";
      const lineIndex = Math.floor(Math.random() * 8);
      const direction = Math.random() < 0.6 ? 1 : -1;

      particles.push({
        progress: Math.random(),
        speed: type === "delivery" ? 0.012 : 0.007,
        type,
        pathType,
        lineIndex,
        direction,
        lat: centerLat,
        lon: centerLon,
      });
    }
    particlesRef.current = particles;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Grid Overlay styling when grid data changes
  useEffect(() => {
    if (rectsRef.current.length === 0 || grid.length === 0) return;

    rectsRef.current.forEach((rect, idx) => {
      const cell = grid[idx];
      if (cell) {
        // Higher congestion → denser red fill overlay
        rect.setStyle({
          fillOpacity: cell.congestion > 0.15 ? cell.congestion * 0.18 : 0.0,
        });
      }
    });
  }, [grid]);

  // Sync canvas dimensions and particle calculations inside animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const map = mapRef.current;
    if (!canvas || !map) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const updateAndDrawParticles = () => {
      // 1. Resize canvas dynamically to match map container dimensions
      const width = canvasRef.current?.parentElement?.clientWidth || 500;
      const height = canvasRef.current?.parentElement?.clientHeight || 500;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const speedMod = Math.max(0.25, 1 - roadCongestion * 0.75);

      // 2. Update particle positions on map coordinates & project to pixels
      particlesRef.current.forEach((p) => {
        if (p.pathType === "metro") {
          // Travel back/forth along Yellow or Blue line track
          const isYellow = p.lineIndex % 2 === 0;
          const axisOffset = -maxSpan * 0.8 + maxSpan * 1.6 * p.progress;

          if (isYellow) {
            p.lat = centerLat + axisOffset;
            p.lon = centerLon + axisOffset * 0.1; // subtle curve
          } else {
            p.lat = centerLat + axisOffset * 0.15;
            p.lon = centerLon + axisOffset;
          }
        } else if (p.pathType === "radial") {
          // Radial commuting along roads
          const angle = (p.lineIndex * Math.PI * 2) / 8;
          const r = maxSpan * p.progress;
          p.lat = centerLat + Math.cos(angle) * r;
          p.lon = centerLon + Math.sin(angle) * r;
        } else {
          // Circular concentric route around CP
          const radii = [maxSpan * 0.35, maxSpan * 0.7, maxSpan * 1.15];
          const radius = radii[p.lineIndex % radii.length];
          const angle = p.progress * Math.PI * 2;
          p.lat = centerLat + Math.cos(angle) * radius;
          p.lon = centerLon + Math.sin(angle) * radius * 1.1; // skew to simulate oval road
        }

        // Map geocoordinates to screen pixels
        const latlng = L.latLng(p.lat, p.lon);
        const point = map.latLngToContainerPoint(latlng);

        // Draw particle
        ctx.beginPath();
        ctx.arc(point.x, point.y, p.type === "delivery" ? 3.2 : 2.0, 0, Math.PI * 2);
        
        if (p.type === "delivery") {
          ctx.fillStyle = "#f97316"; // Orange
          ctx.shadowBlur = 3;
          ctx.shadowColor = "#f97316";
          ctx.fill();
          ctx.shadowBlur = 0;
        } else {
          ctx.fillStyle = p.pathType === "metro" ? "#3b82f6" : "#22d3ee"; // DMRC Blue vs Cyan
          ctx.fill();
        }

        // Update progress
        if (isPlaying) {
          let speed = p.speed * speedMod;
          if (p.type === "citizen" && rainIntensity > 0.3) {
            speed *= 0.75; // slow down walk/bike in downpours
          }
          p.progress += speed * p.direction;

          if (p.progress > 1.0) {
            p.progress = 0;
            p.direction = Math.random() < 0.5 ? 1 : -1;
          } else if (p.progress < 0) {
            p.progress = 1.0;
            p.direction = Math.random() < 0.5 ? 1 : -1;
          }
        }
      });

      // 3. Overlay rain streaks in screen space
      if (rainIntensity > 0) {
        ctx.strokeStyle = "rgba(174, 207, 238, 0.15)";
        ctx.lineWidth = 1.2;
        const streaks = Math.floor(rainIntensity * 25);
        for (let i = 0; i < streaks; i++) {
          const rx = Math.random() * canvas.width;
          const ry = Math.random() * canvas.height;
          const length = 15 + rainIntensity * 12;
          ctx.beginPath();
          ctx.moveTo(rx, ry);
          ctx.lineTo(rx - 2, ry + length);
          ctx.stroke();
        }
      }

      // HUD Stats overlay
      ctx.fillStyle = "rgba(10, 10, 10, 0.75)";
      ctx.fillRect(10, 10, 140, 48);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
      ctx.strokeRect(10, 10, 140, 48);

      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
      ctx.font = "bold 11px var(--font-jetbrains-mono), monospace";
      ctx.fillText(`TIME: ${timeOfDay}`, 20, 28);

      ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
      ctx.font = "9px var(--font-jetbrains-mono), monospace";
      ctx.fillText(`AGENTS: ${particlesRef.current.length} particles`, 20, 44);

      animId = requestAnimationFrame(updateAndDrawParticles);
    };

    updateAndDrawParticles();

    return () => cancelAnimationFrame(animId);
  }, [isPlaying, rainIntensity, roadCongestion, timeOfDay]);

  return (
    <div className="relative w-full aspect-square md:max-w-2xl bg-[#0c0a09] rounded-3xl border border-white/10 overflow-hidden shadow-2xl backdrop-blur-md">
      {/* Leaflet map container */}
      <div ref={mapContainerRef} className="w-full h-full z-0" />
      {/* Synchronized canvas for particle rendering */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-[400] w-full h-full"
      />
    </div>
  );
}
