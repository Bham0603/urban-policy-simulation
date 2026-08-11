"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

export default function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!cursorRef.current || !dotRef.current) return;

    // quickTo is optimized for performance in high-frequency events like mousemove
    // Increased duration slightly to 0.3s for the glass lens to give it a more fluid, elastic drag behind the cursor
    const xToCursor = gsap.quickTo(cursorRef.current, "x", { duration: 0.3, ease: "power3.out" });
    const yToCursor = gsap.quickTo(cursorRef.current, "y", { duration: 0.3, ease: "power3.out" });
    
    const xToDot = gsap.quickTo(dotRef.current, "x", { duration: 0.08, ease: "power3.out" });
    const yToDot = gsap.quickTo(dotRef.current, "y", { duration: 0.08, ease: "power3.out" });

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
        // Expand the lens and increase its brightness when hovering over interactive elements
        gsap.to(cursorRef.current, { 
          scale: 1.5, 
          borderColor: "rgba(167, 139, 250, 0.4)", // Purple-400
          backgroundColor: "rgba(255, 255, 255, 0.08)",
          duration: 0.4, 
          ease: "power2.out" 
        });
        gsap.to(dotRef.current, {
          scale: 0.5,
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
        borderColor: "rgba(255, 255, 255, 0.15)",
        backgroundColor: "rgba(255, 255, 255, 0.03)",
        duration: 0.4, 
        ease: "power2.out" 
      });
      gsap.to(dotRef.current, {
        scale: 1,
        opacity: 1,
        backgroundColor: "#c084fc", // Purple-400
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
            inset 0 1px 1px rgba(255, 255, 255, 0.25), 
            inset 0 -1px 1px rgba(0, 0, 0, 0.15),
            0 8px 32px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(8px) saturate(120%) contrast(100%);
          -webkit-backdrop-filter: blur(8px) saturate(120%) contrast(100%);
        }
        
        /* If browser supports SVG filters, apply our custom liquid-glass lite filter */
        html[data-liquid-glass-supported="true"] .refractive-lens {
          backdrop-filter: url(#lg-liquid-glass-filter-lite) saturate(130%) contrast(100%) !important;
          -webkit-backdrop-filter: url(#lg-liquid-glass-filter-lite) saturate(130%) contrast(100%) !important;
        }
      `}</style>
      
      {/* Outer Floating Glass Lens Circle */}
      <div 
        ref={cursorRef} 
        className="refractive-lens fixed top-0 left-0 w-16 h-16 border border-white/15 bg-white/3 rounded-full pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block transition-colors duration-300"
      />
      
      {/* Inner instant glowing pointer dot */}
      <div 
        ref={dotRef} 
        className="fixed top-0 left-0 w-2.5 h-2.5 bg-purple-400 rounded-full shadow-[0_0_8px_#c084fc] pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block"
      />
    </>
  );
}
