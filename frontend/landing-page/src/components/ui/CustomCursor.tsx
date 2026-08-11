"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

export default function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);
  const [dispUrl, setDispUrl] = useState<string>("");

  // Generate a spherical lens displacement texture on mount
  useEffect(() => {
    const size = 128;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const imgData = ctx.createImageData(size, size);
    const data = imgData.data;
    const cx = size / 2;
    const cy = size / 2;
    const R = size / 2 - 2; // radius of 62px inside the 128x128 canvas

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const idx = (y * size + x) * 4;
        const dx = x - cx;
        const dy = y - cy;
        const d = Math.sqrt(dx * dx + dy * dy);

        if (d >= R) {
          // Outside the lens: neutral 128 (no displacement)
          data[idx] = 128;
          data[idx + 1] = 128;
          data[idx + 2] = 128;
          data[idx + 3] = 255;
        } else {
          // Spherical convex lens displacement math
          const normDist = d / R;
          
          // Displacement magnitude following a sine wave
          // Peak displacement is in the middle of the lens radius, dropping to 0 at center and edges
          // to create a smooth, distortion-free boundary merge.
          const magnitude = Math.sin(normDist * Math.PI);
          
          // Magnify: shift lookup coordinates inward (toward the center)
          // This stretches pixels outward from the center
          const dirX = -dx / (d || 1);
          const dirY = -dy / (d || 1);

          // 0.8 is the refractive strength multiplier
          const shiftX = dirX * magnitude * 0.8;
          const shiftY = dirY * magnitude * 0.8;

          data[idx] = Math.round(128 + shiftX * 127);
          data[idx + 1] = Math.round(128 + shiftY * 127);
          data[idx + 2] = 128;
          data[idx + 3] = 255;
        }
      }
    }
    ctx.putImageData(imgData, 0, 0);
    setDispUrl(canvas.toDataURL());
  }, []);

  useGSAP(() => {
    if (!cursorRef.current || !dotRef.current) return;

    // quickTo is optimized for performance in high-frequency events like mousemove
    // 0.25s lag makes the glass lens drift behind the mouse dot with a gorgeous inertia feel
    const xToCursor = gsap.quickTo(cursorRef.current, "x", { duration: 0.25, ease: "power3.out" });
    const yToCursor = gsap.quickTo(cursorRef.current, "y", { duration: 0.25, ease: "power3.out" });
    
    const xToDot = gsap.quickTo(dotRef.current, "x", { duration: 0.06, ease: "power3.out" });
    const yToDot = gsap.quickTo(dotRef.current, "y", { duration: 0.06, ease: "power3.out" });

    const onMouseMove = (e: MouseEvent) => {
      xToCursor(e.clientX);
      yToCursor(e.clientY);
      xToDot(e.clientX);
      yToDot(e.clientY);
    };

    const onMouseEnter = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName.toLowerCase() === "a" || 
        target.tagName.toLowerCase() === "button" ||
        target.closest("a") || 
        target.closest("button") ||
        target.closest("[role='button']") ||
        target.closest("input[type='range']")
      ) {
        // Expand the lens and highlight active state
        gsap.to(cursorRef.current, { 
          scale: 1.4, 
          borderColor: "rgba(167, 139, 250, 0.45)", // Glowing purple border
          backgroundColor: "rgba(255, 255, 255, 0.08)",
          duration: 0.4, 
          ease: "power2.out" 
        });
        gsap.to(dotRef.current, {
          scale: 0.4,
          opacity: 0.6,
          backgroundColor: "#a78bfa",
          duration: 0.4,
          ease: "power2.out"
        });
      }
    };

    const onMouseLeave = () => {
      gsap.to(cursorRef.current, { 
        scale: 1, 
        borderColor: "rgba(255, 255, 255, 0.18)",
        backgroundColor: "rgba(255, 255, 255, 0.04)",
        duration: 0.4, 
        ease: "power2.out" 
      });
      gsap.to(dotRef.current, {
        scale: 1,
        opacity: 1,
        backgroundColor: "#c084fc",
        duration: 0.4,
        ease: "power2.out"
      });
    };

    window.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseover", onMouseEnter, true);
    document.addEventListener("mouseout", onMouseLeave, true);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseover", onMouseEnter, true);
      document.removeEventListener("mouseout", onMouseLeave, true);
    };
  }, []);

  return (
    <>
      <style>{`
        /* Refractive glass lens style that bends the backdrop elements */
        .refractive-lens {
          box-shadow: 
            inset 0 1.5px 2px rgba(255, 255, 255, 0.35), 
            inset 0 -1.5px 2px rgba(0, 0, 0, 0.2),
            0 12px 36px rgba(0, 0, 0, 0.4);
          backdrop-filter: blur(3px) saturate(120%) contrast(100%);
          -webkit-backdrop-filter: blur(3px) saturate(120%) contrast(100%);
        }
        
        /* Apply our highly refractive custom lens filter */
        .refractive-lens {
          backdrop-filter: url(#lens-refraction-filter) saturate(135%) contrast(102%) !important;
          -webkit-backdrop-filter: url(#lens-refraction-filter) saturate(135%) contrast(102%) !important;
        }
      `}</style>

      {/* SVG Refraction Filter injection */}
      {dispUrl && (
        <svg width="0" height="0" className="absolute" aria-hidden="true">
          <defs>
            <filter 
              id="lens-refraction-filter" 
              colorInterpolationFilters="sRGB"
              filterUnits="objectBoundingBox"
              primitiveUnits="objectBoundingBox"
              x="-0.2"
              y="-0.2"
              width="1.4"
              height="1.4"
            >
              <feImage
                href={dispUrl}
                x="0"
                y="0"
                width="1"
                height="1"
                preserveAspectRatio="none"
                result="displacementMap"
              />
              <feDisplacementMap
                in="SourceGraphic"
                in2="displacementMap"
                scale="0.55" /* Set to a high, realistic magnification factor (55% bounding box width) */
                xChannelSelector="R"
                yChannelSelector="G"
              />
            </filter>
          </defs>
        </svg>
      )}
      
      {/* Outer Floating Glass Lens Circle */}
      <div 
        ref={cursorRef} 
        className="refractive-lens fixed top-0 left-0 w-16 h-16 border border-white/18 bg-white/4 rounded-full pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block transition-all duration-300"
      />
      
      {/* Inner instant glowing pointer dot */}
      <div 
        ref={dotRef} 
        className="fixed top-0 left-0 w-2.5 h-2.5 bg-purple-400 rounded-full shadow-[0_0_8px_#c084fc] pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block"
      />
    </>
  );
}
