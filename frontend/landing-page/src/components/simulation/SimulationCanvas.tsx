"use client";

import { useEffect, useRef, useState } from "react";
import { GridCell } from "@/lib/localSimulator";

interface SimulationCanvasProps {
  grid: GridCell[];
  rainIntensity: number;
  roadCongestion: number;
  isPlaying: boolean;
  timeOfDay: string;
}

interface Particle {
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  speed: number;
  type: "citizen" | "delivery";
  progress: number; // 0 to 1
  pathType: "radial" | "concentric" | "metro";
  lineIndex: number;
  direction: 1 | -1; // 1: toward center, -1: away from center
}

export function SimulationCanvas({
  grid,
  rainIntensity,
  roadCongestion,
  isPlaying,
  timeOfDay,
}: SimulationCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredCell, setHoveredCell] = useState<{ idx: number; x: number; y: number } | null>(null);
  const particlesRef = useRef<Particle[]>([]);

  // Initialize particles once
  useEffect(() => {
    const particles: Particle[] = [];
    const particleCount = 180;

    for (let i = 0; i < particleCount; i++) {
      const type = Math.random() < 0.25 ? "delivery" : "citizen";
      const pathType = Math.random() < 0.15 ? "metro" : Math.random() < 0.5 ? "radial" : "concentric";
      const lineIndex = Math.floor(Math.random() * 8);
      const direction = Math.random() < 0.55 ? 1 : -1; // mostly commuting to center

      particles.push({
        x: 0,
        y: 0,
        targetX: 0,
        targetY: 0,
        speed: type === "delivery" ? 0.015 : 0.008,
        type,
        progress: Math.random(),
        pathType,
        lineIndex,
        direction,
      });
    }

    particlesRef.current = particles;
  }, []);

  // Handle animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    const center = { x: canvas.width / 2, y: canvas.height / 2 };
    const maxRadius = Math.min(canvas.width, canvas.height) * 0.45;

    const draw = () => {
      // 1. Clear with deep rich backdrop
      ctx.fillStyle = "#0c0a09"; // Stone 950
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // 2. Draw grid cells as a faint congestion heatmap underneath
      const cellCount = grid.length;
      if (cellCount > 0) {
        const cols = 10;
        const rows = 10;
        const cellW = canvas.width / cols;
        const cellH = canvas.height / rows;

        grid.forEach((cell, idx) => {
          const r = Math.floor(idx / cols);
          const c = idx % cols;
          const x = c * cellW;
          const y = r * cellH;

          // Render congestion as a soft glowing red-orange rect
          if (cell.congestion > 0.15) {
            ctx.fillStyle = `rgba(239, 68, 68, ${cell.congestion * 0.18})`; // Red
            ctx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);
          }

          // Subtle grid line dots or border
          ctx.strokeStyle = "rgba(255, 255, 255, 0.02)";
          ctx.strokeRect(x, y, cellW, cellH);
        });
      }

      // 3. Draw Rajiv Chowk Concentric Road Ring Networks (CP Circles)
      const concentricCircles = [maxRadius * 0.3, maxRadius * 0.6, maxRadius * 0.9];
      concentricCircles.forEach((radius, i) => {
        ctx.beginPath();
        ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.08 - i * 0.02})`;
        ctx.lineWidth = i === 2 ? 2.5 : 1.5;
        ctx.stroke();
      });

      // 4. Draw Radial Spoke Roads
      const radialSpokes = 8;
      for (let i = 0; i < radialSpokes; i++) {
        const angle = (i * Math.PI * 2) / radialSpokes;
        const endX = center.x + Math.cos(angle) * maxRadius;
        const endY = center.y + Math.sin(angle) * maxRadius;

        ctx.beginPath();
        ctx.moveTo(center.x, center.y);
        ctx.lineTo(endX, endY);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      // 5. Draw DMRC Metro Transit Lines
      // Yellow Line (North-South)
      ctx.beginPath();
      ctx.moveTo(center.x, center.y - maxRadius);
      ctx.lineTo(center.x, center.y + maxRadius);
      ctx.strokeStyle = "rgba(234, 179, 8, 0.25)"; // Yellow Line DMRC
      ctx.lineWidth = 3.5;
      ctx.stroke();

      // Blue Line (East-West)
      ctx.beginPath();
      ctx.moveTo(center.x - maxRadius, center.y);
      ctx.lineTo(center.x + maxRadius, center.y);
      ctx.strokeStyle = "rgba(59, 130, 246, 0.25)"; // Blue Line DMRC
      ctx.lineWidth = 3.5;
      ctx.stroke();

      // 6. Animate & Draw Commuter Particles
      const speedModifier = Math.max(0.2, 1 - roadCongestion * 0.7); // slow down in heavy traffic

      particlesRef.current.forEach((p) => {
        // Compute current coordinates based on progress along paths
        if (p.pathType === "metro") {
          // Linear North-South or East-West DMRC paths
          const axis = p.lineIndex % 2; // 0: NS, 1: EW
          const startOffset = -maxRadius;
          const endOffset = maxRadius;
          const currentOffset = startOffset + (endOffset - startOffset) * p.progress;

          if (axis === 0) {
            p.x = center.x;
            p.y = center.y + currentOffset;
          } else {
            p.x = center.x + currentOffset;
            p.y = center.y;
          }
        } else if (p.pathType === "radial") {
          // Inward/outward along radial spoke roads
          const angle = (p.lineIndex * Math.PI * 2) / 8;
          const r = maxRadius * p.progress;
          p.x = center.x + Math.cos(angle) * r;
          p.y = center.y + Math.sin(angle) * r;
        } else {
          // Circular paths along concentric circles
          const radiusIdx = p.lineIndex % concentricCircles.length;
          const radius = concentricCircles[radiusIdx];
          const angle = p.progress * Math.PI * 2;
          p.x = center.x + Math.cos(angle) * radius;
          p.y = center.y + Math.sin(angle) * radius;
        }

        // Draw particle
        if (p.type === "delivery") {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
          ctx.fillStyle = "#f97316"; // Orange 500
          ctx.shadowBlur = 4;
          ctx.shadowColor = "#f97316";
          ctx.fill();
          ctx.shadowBlur = 0; // reset
        } else {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
          // Highlight active mode color (cyan for regular citizens)
          ctx.fillStyle = p.pathType === "metro" ? "#3b82f6" : "#22d3ee"; // Blue vs Cyan
          ctx.fill();
        }

        // Update progress
        if (isPlaying) {
          // Speed depends on agent type, congestion, and weather
          let baseSpeed = p.speed;
          if (p.pathType !== "metro") {
            baseSpeed *= speedModifier; // roads are congested
            if (p.type === "citizen" && rainIntensity > 0.3) {
              baseSpeed *= 0.8; // citizen walkers slow down in rain
            }
          }
          p.progress += baseSpeed * p.direction;

          // Wrap progress boundary
          if (p.progress > 1.0) {
            p.progress = 0;
            p.direction = Math.random() < 0.5 ? 1 : -1;
          } else if (p.progress < 0) {
            p.progress = 1.0;
            p.direction = Math.random() < 0.5 ? 1 : -1;
          }
        }
      });

      // 7. Draw Metro Station Hubs (Connaught Place Center + Outer Stations)
      const stationNodes = [
        { x: center.x, y: center.y, label: "Rajiv Chowk" },
        { x: center.x, y: center.y - maxRadius * 0.6, label: "New Delhi" },
        { x: center.x, y: center.y + maxRadius * 0.6, label: "Patel Chowk" },
        { x: center.x - maxRadius * 0.6, y: center.y, label: "R.K. Ashram" },
        { x: center.x + maxRadius * 0.6, y: center.y, label: "Barakhamba Road" },
      ];

      stationNodes.forEach((node, i) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, i === 0 ? 7 : 4.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(59, 130, 246, 0.8)"; // DMRC Blue node
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1;
        ctx.shadowBlur = 8;
        ctx.shadowColor = "#3b82f6";
        ctx.fill();
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Faint labels
        if (maxRadius > 120) {
          ctx.fillStyle = "rgba(255,255,255,0.4)";
          ctx.font = "8px monospace";
          ctx.textAlign = "center";
          ctx.fillText(node.label, node.x, node.y - 8);
        }
      });

      // 8. Draw Rain Streak Overlay
      if (rainIntensity > 0) {
        ctx.strokeStyle = "rgba(174, 207, 238, 0.15)";
        ctx.lineWidth = 1;
        const streaks = Math.floor(rainIntensity * 35);
        for (let i = 0; i < streaks; i++) {
          const rx = Math.random() * canvas.width;
          const ry = Math.random() * canvas.height;
          const length = 12 + rainIntensity * 15;
          ctx.beginPath();
          ctx.moveTo(rx, ry);
          ctx.lineTo(rx - 2, ry + length); // angled rain
          ctx.stroke();
        }
      }

      // 9. Draw HUD clock & stats in corner
      ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
      ctx.fillRect(10, 10, 140, 48);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.strokeRect(10, 10, 140, 48);

      ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
      ctx.font = "bold 11px var(--font-jetbrains-mono), monospace";
      ctx.textAlign = "left";
      ctx.fillText(`TIME: ${timeOfDay}`, 20, 28);

      ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
      ctx.font = "9px var(--font-jetbrains-mono), monospace";
      ctx.fillText(`AGENTS: ${particlesRef.current.length} particles`, 20, 44);

      // 10. Draw hovered cell highlight tooltip
      if (hoveredCell && grid.length > 0) {
        const cols = 10;
        const cellW = canvas.width / cols;
        const cellH = canvas.height / 10;
        const cell = grid[hoveredCell.idx];

        if (cell) {
          ctx.strokeStyle = "rgba(255,255,255,0.7)";
          ctx.lineWidth = 1.5;
          ctx.strokeRect(
            Math.floor(hoveredCell.idx % cols) * cellW,
            Math.floor(hoveredCell.idx / cols) * cellH,
            cellW,
            cellH
          );

          // Draw tooltip text box
          const tx = Math.min(canvas.width - 120, Math.max(10, hoveredCell.x));
          const ty = Math.min(canvas.height - 50, Math.max(60, hoveredCell.y - 45));

          ctx.fillStyle = "rgba(10, 10, 10, 0.9)";
          ctx.fillRect(tx, ty, 110, 40);
          ctx.strokeStyle = "rgba(255,255,255,0.2)";
          ctx.lineWidth = 1;
          ctx.strokeRect(tx, ty, 110, 40);

          ctx.fillStyle = "#ffffff";
          ctx.font = "9px monospace";
          ctx.textAlign = "left";
          ctx.fillText(`Density: ${cell.density}`, tx + 8, ty + 16);
          ctx.fillText(`Congestion: ${Math.round(cell.congestion * 100)}%`, tx + 8, ty + 30);
        }
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [grid, rainIntensity, roadCongestion, isPlaying, timeOfDay, hoveredCell]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || grid.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const cols = 10;
    const rows = 10;
    const cellW = canvas.width / cols;
    const cellH = canvas.height / rows;

    const c = Math.floor(x / cellW);
    const r = Math.floor(y / cellH);

    if (c >= 0 && c < cols && r >= 0 && r < rows) {
      const idx = r * cols + c;
      setHoveredCell({ idx, x, y });
    } else {
      setHoveredCell(null);
    }
  };

  const handleMouseLeave = () => {
    setHoveredCell(null);
  };

  return (
    <div className="relative w-full aspect-square md:max-w-2xl bg-stone-900/60 rounded-3xl border border-white/10 overflow-hidden shadow-2xl backdrop-blur-md">
      <canvas
        ref={canvasRef}
        width={500}
        height={500}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="w-full h-full block cursor-crosshair"
      />
    </div>
  );
}
