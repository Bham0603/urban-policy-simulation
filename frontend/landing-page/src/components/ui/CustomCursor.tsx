"use client";

import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

export default function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);
  const dotRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!cursorRef.current || !dotRef.current) return;

    // Reduced duration for a highly responsive, snappy tracking feel
    const xToCursor = gsap.quickTo(cursorRef.current, "x", { duration: 0.06, ease: "power2.out" });
    const yToCursor = gsap.quickTo(cursorRef.current, "y", { duration: 0.06, ease: "power2.out" });
    
    const xToDot = gsap.quickTo(dotRef.current, "x", { duration: 0.01, ease: "power2.out" });
    const yToDot = gsap.quickTo(dotRef.current, "y", { duration: 0.01, ease: "power2.out" });

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
        // Expand and fade the outer ring, scale down the inner dot on interactive elements
        gsap.to(cursorRef.current, { 
          scale: 1.6, 
          borderColor: "rgba(255, 255, 255, 0.8)",
          backgroundColor: "rgba(255, 255, 255, 0.08)",
          duration: 0.3, 
          ease: "power2.out" 
        });
        gsap.to(dotRef.current, {
          scale: 0.4,
          opacity: 0.5,
          duration: 0.3,
          ease: "power2.out"
        });
      }
    };

    const onMouseLeave = () => {
      gsap.to(cursorRef.current, { 
        scale: 1, 
        borderColor: "rgba(255, 255, 255, 0.4)",
        backgroundColor: "transparent",
        duration: 0.3, 
        ease: "power2.out" 
      });
      gsap.to(dotRef.current, {
        scale: 1,
        opacity: 1,
        duration: 0.3,
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
      {/* Outer Floating Circle Ring */}
      <div 
        ref={cursorRef} 
        className="fixed top-0 left-0 w-8 h-8 border border-white/40 rounded-full pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block transition-all duration-200"
      />
      
      {/* Inner solid white dot with drop shadow for contrast against white screens */}
      <div 
        ref={dotRef} 
        className="fixed top-0 left-0 w-2 h-2 bg-white rounded-full shadow-[0_1px_3px_rgba(0,0,0,0.5)] pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block"
      />
    </>
  );
}
