"use client";

import { Canvas } from "@react-three/fiber";
import { EffectComposer, DepthOfField } from "@react-three/postprocessing";
import { GPGPUParticles } from "./particles/GPGPUParticles";

export function ParticleBackground() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none">
      <Canvas camera={{ position: [0, 0, 5], fov: 60 }} gl={{ antialias: false, alpha: true }}>
        <color attach="background" args={["#000000"]} />
        <GPGPUParticles />
        
        {/* Postprocessing for Depth of Field effect */}
        <EffectComposer multisampling={0}>
          <DepthOfField 
            focusDistance={0.0} 
            focalLength={0.02} 
            bokehScale={2.5} 
            height={480} 
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
