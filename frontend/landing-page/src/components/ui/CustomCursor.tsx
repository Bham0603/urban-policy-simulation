"use client";

import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

export default function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    if (!cursorRef.current) return;

    // quickTo is optimized for performance in high-frequency events like mousemove
    // 0.02s duration makes the single circle follow the pointer almost instantaneously
    const xToCursor = gsap.quickTo(cursorRef.current, "x", { duration: 0.02, ease: "power2.out" });
    const yToCursor = gsap.quickTo(cursorRef.current, "y", { duration: 0.02, ease: "power2.out" });

    const onMouseMove = (e: MouseEvent) => {
      xToCursor(e.clientX);
      yToCursor(e.clientY);
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
        // Expand the circle and make it slightly brighter on interactive hover
        gsap.to(cursorRef.current, { 
          scale: 1.5, 
          borderColor: "rgba(255, 255, 255, 0.9)",
          backgroundColor: "rgba(255, 255, 255, 0.1)",
          duration: 0.25, 
          ease: "power2.out" 
        });
      }
    };

    const onMouseLeave = () => {
      gsap.to(cursorRef.current, { 
        scale: 1, 
        borderColor: "rgba(255, 255, 255, 0.5)",
        backgroundColor: "transparent",
        duration: 0.25, 
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
    <div 
      ref={cursorRef} 
      className="fixed top-0 left-0 w-5 h-5 border border-white/50 rounded-full pointer-events-none z-[9999] -translate-x-1/2 -translate-y-1/2 hidden sm:block transition-all duration-150 shadow-[0_0_4px_rgba(0,0,0,0.3)]"
    />
  );
}
