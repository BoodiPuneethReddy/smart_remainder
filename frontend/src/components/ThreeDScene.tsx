import React, { useRef, Component, ErrorInfo, ReactNode } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Dodecahedron } from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';

// WebGL availability check
export function isWebGLAvailable() {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch (e) {
    return false;
  }
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class CanvasErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false
  };

  public static getDerivedStateFromError(_: Error): ErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Canvas error caught by boundary:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export function CSSFallbackCore() {
  return (
    <div className="relative w-full h-full flex items-center justify-center min-h-[380px]">
      {/* Outer Rotating Dotted Ring */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
        className="absolute w-72 h-72 rounded-full border border-dashed border-[var(--info)] opacity-20 pointer-events-none"
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 35, repeat: Infinity, ease: 'linear' }}
        className="absolute w-80 h-80 rounded-full border border-dashed border-[var(--priority-high)] opacity-10 pointer-events-none"
      />

      {/* Central Organic Blob Core */}
      <motion.div
        animate={{
          scale: [1, 1.15, 0.9, 1],
          borderRadius: [
            "42% 58% 70% 30% / 45% 45% 55% 55%",
            "70% 30% 52% 48% / 60% 40% 60% 40%",
            "42% 58% 70% 30% / 45% 45% 55% 55%"
          ]
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        className="w-48 h-48 bg-gradient-to-tr from-[var(--priority-high)] to-[var(--info)] blur-md opacity-80 shadow-[0_0_60px_rgba(255,107,53,0.25)] pointer-events-auto cursor-pointer"
      />
    </div>
  );
}

interface CrystalCoreProps {
  activeStep: number;
}

function HolographicCrystalCore({ activeStep }: CrystalCoreProps) {
  const crystalRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  // Speed and colors based on workflow step
  const speedMultiplier = activeStep === 1 ? 3.5 : activeStep === 3 ? 2 : 1;
  const crystalColor = 
    activeStep === 0 ? '#5B8DEF' : // Blue (Import)
    activeStep === 1 ? '#FFC857' : // Gold (Analyze)
    activeStep === 2 ? '#2EC4B6' : // Teal (Extract)
    activeStep === 3 ? '#FF6B35' : // Orange-Red (Score)
    activeStep === 4 ? '#5B8DEF' : // Blue (Schedule)
    '#2EC4B6';                    // Teal (Remind)

  useFrame((state) => {
    const time = state.clock.getElapsedTime();

    if (crystalRef.current) {
      crystalRef.current.rotation.x = time * 0.12 * speedMultiplier;
      crystalRef.current.rotation.y = time * 0.2 * speedMultiplier;
      crystalRef.current.position.y = Math.sin(time * 1.8) * 0.08;
    }

    if (ringRef.current) {
      ringRef.current.rotation.z = -time * 0.25;
      ringRef.current.position.y = Math.sin(time * 1.8) * 0.08;
    }

    if (lightRef.current) {
      lightRef.current.position.x = Math.sin(time * 2) * 2.2;
      lightRef.current.position.z = Math.cos(time * 2) * 2.2;
    }
  });

  return (
    <group>
      {/* Crystal Core (Dodecahedron representing high-dimensional planning crystal) */}
      <Dodecahedron ref={crystalRef} args={[1.3, 0]}>
        <meshPhysicalMaterial 
          color={crystalColor}
          emissive={crystalColor}
          emissiveIntensity={activeStep === 1 ? 2.5 : 1.2}
          roughness={0.05}
          metalness={0.9}
          clearcoat={1.0}
          clearcoatRoughness={0.05}
          transmission={0.65}
          thickness={0.8}
          transparent
          opacity={0.85}
        />
      </Dodecahedron>

      {/* Orbiting Gyro Ring */}
      <mesh ref={ringRef} rotation={[1.2, 0.4, 0]}>
        <torusGeometry args={[1.9, 0.02, 8, 64]} />
        <meshBasicMaterial 
          color={crystalColor} 
          transparent 
          opacity={0.35} 
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Active dynamic light */}
      <pointLight ref={lightRef} intensity={3} distance={8} color={crystalColor} />
      
      {/* Ambient background lights */}
      <pointLight position={[4, 4, 4]} intensity={2.5} color="#FF6B35" />
      <pointLight position={[-4, -4, -4]} intensity={1.5} color="#5B8DEF" />
    </group>
  );
}

interface ThreeDSceneProps {
  activeStep: number;
}

export default function ThreeDScene({ activeStep }: ThreeDSceneProps) {
  const isAvailable = isWebGLAvailable();

  if (!isAvailable) {
    return <CSSFallbackCore />;
  }

  return (
    <div className="w-full h-full min-h-[400px] relative select-none flex items-center justify-center">
      <CanvasErrorBoundary fallback={<CSSFallbackCore />}>
        <Canvas camera={{ position: [0, 0, 4.2], fov: 60 }} gl={{ alpha: true }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 10]} intensity={1.5} />
          <HolographicCrystalCore activeStep={activeStep} />
        </Canvas>
      </CanvasErrorBoundary>
      
      {/* Dynamic backglow */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 transition-all duration-1000 blur-3xl pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${
            activeStep === 0 ? 'rgba(91,141,239,0.18)' :
            activeStep === 1 ? 'rgba(255,200,87,0.18)' :
            activeStep === 2 ? 'rgba(46,196,182,0.18)' :
            activeStep === 3 ? 'rgba(255,107,53,0.18)' :
            activeStep === 4 ? 'rgba(91,141,239,0.18)' :
            'rgba(46,196,182,0.18)'
          } 0%, transparent 70%)`
        }}
      />
    </div>
  );
}
