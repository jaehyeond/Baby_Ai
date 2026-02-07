'use client'

import { useRef, useState, useMemo, Suspense, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Html } from '@react-three/drei'
import * as THREE from 'three'
import { useBrainRegions, type BrainRegion } from '@/hooks/useBrainRegions'
import { useNeuronActivations } from '@/hooks/useNeuronActivations'
import { useBrainData } from '@/hooks/useBrainData'
import { Brain, Loader2, ZoomIn, ZoomOut, RotateCcw, Eye } from 'lucide-react'

// ── Helpers ────────────────────────────────────────────────

/** Convert spherical coords (theta, phi, r) to cartesian (x, y, z) for ellipsoid */
function sphericalToCartesian(
  theta: number, phi: number, r: number,
  scaleX = 1.2, scaleY = 1.0, scaleZ = 1.1
): [number, number, number] {
  return [
    r * Math.sin(theta) * Math.cos(phi) * scaleX,
    r * Math.cos(theta) * scaleY,
    r * Math.sin(theta) * Math.sin(phi) * scaleZ,
  ]
}

/** Generate random positions within a region's bounds */
function getRegionCenter(region: BrainRegion): [number, number, number] {
  const thetaMid = (region.theta_min + region.theta_max) / 2
  const phiMid = (region.phi_min + region.phi_max) / 2
  const rMid = (region.radius_min + region.radius_max) / 2
  return sphericalToCartesian(thetaMid, phiMid, rMid * 4) // Scale to scene
}

function getRandomPositionInRegion(region: BrainRegion, jitter = 0.3): [number, number, number] {
  const theta = region.theta_min + Math.random() * (region.theta_max - region.theta_min)
  const phi = region.phi_min + Math.random() * (region.phi_max - region.phi_min)
  const r = region.radius_min + Math.random() * (region.radius_max - region.radius_min)
  const pos = sphericalToCartesian(theta, phi, r * 4)
  // Add small jitter for organic look
  return [
    pos[0] + (Math.random() - 0.5) * jitter,
    pos[1] + (Math.random() - 0.5) * jitter,
    pos[2] + (Math.random() - 0.5) * jitter,
  ]
}

// ── Brain Shell (outer cortex shape) ──────────────────────

function BrainShell({ opacity = 0.06, scale = 1 }: { opacity?: number; scale?: number }) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (meshRef.current) {
      // Very subtle breathing animation
      const breath = Math.sin(state.clock.elapsedTime * 0.5) * 0.01
      meshRef.current.scale.set(
        (1.2 + breath) * scale,
        (1.0 + breath) * scale,
        (1.1 + breath) * scale
      )
    }
  })

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[4, 32, 32]} />
      <meshStandardMaterial
        color="#8b5cf6"
        transparent
        opacity={opacity}
        wireframe={false}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}

// ── Brain Region Mesh ─────────────────────────────────────

function BrainRegionMesh({
  region,
  isActive,
  isAvailable,
  activeIntensity,
  neuronCount,
  isSelected,
  onSelect,
}: {
  region: BrainRegion
  isActive: boolean
  isAvailable: boolean
  activeIntensity: number
  neuronCount: number
  isSelected: boolean
  onSelect: (region: BrainRegion | null) => void
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)
  const center = useMemo(() => getRegionCenter(region), [region])

  // Region size based on neuron count
  const baseSize = useMemo(() => {
    return Math.max(0.3, Math.min(1.2, 0.3 + neuronCount * 0.003))
  }, [neuronCount])

  useFrame((state) => {
    if (!meshRef.current) return

    if (isAvailable) {
      // Pulse when active
      if (isActive) {
        const pulse = Math.sin(state.clock.elapsedTime * 4) * 0.15
        meshRef.current.scale.setScalar(baseSize + pulse * activeIntensity)
      } else {
        meshRef.current.scale.setScalar(baseSize)
      }
    } else {
      // Ghost state for undeveloped regions
      meshRef.current.scale.setScalar(baseSize * 0.4)
    }

    // Glow effect
    if (glowRef.current) {
      if (isActive) {
        const glow = Math.sin(state.clock.elapsedTime * 3) * 0.3 + 0.7
        ;(glowRef.current.material as THREE.MeshBasicMaterial).opacity = glow * activeIntensity * 0.4
        glowRef.current.scale.setScalar(baseSize * 2.0)
      } else {
        ;(glowRef.current.material as THREE.MeshBasicMaterial).opacity = 0
      }
    }
  })

  const regionOpacity = isAvailable ? (hovered ? 0.7 : 0.45) : 0.08

  return (
    <group position={center}>
      {/* Glow sphere (behind the main mesh) */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial
          color={region.color}
          transparent
          opacity={0}
          depthWrite={false}
        />
      </mesh>

      {/* Main region sphere */}
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(isSelected ? null : region)
        }}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <sphereGeometry args={[1, 24, 24]} />
        <meshStandardMaterial
          color={region.color}
          transparent
          opacity={regionOpacity}
          emissive={region.color}
          emissiveIntensity={isActive ? activeIntensity * 0.8 : isAvailable ? 0.1 : 0}
          roughness={0.6}
          metalness={0.2}
        />
      </mesh>

      {/* Label */}
      {(hovered || isSelected) && isAvailable && (
        <Html position={[0, baseSize + 0.5, 0]} center distanceFactor={12}>
          <div className="bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-700/50 whitespace-nowrap pointer-events-none">
            <p className="text-xs font-medium text-white">{region.display_name}</p>
            <p className="text-[10px] text-slate-400">{region.display_name_en}</p>
            {neuronCount > 0 && (
              <p className="text-[10px] text-slate-500">{neuronCount} concepts</p>
            )}
          </div>
        </Html>
      )}
    </group>
  )
}

// ── Neuron Particles in Regions ───────────────────────────

function RegionNeurons({
  region,
  count,
  isAvailable,
  activeNeuronIds,
}: {
  region: BrainRegion
  count: number
  isAvailable: boolean
  activeNeuronIds: Set<string>
}) {
  const positions = useMemo(() => {
    const maxDisplay = Math.min(count, 50) // Cap at 50 per region
    return Array.from({ length: maxDisplay }, () => getRandomPositionInRegion(region, 0.2))
  }, [region, count])

  if (!isAvailable || count === 0) return null

  return (
    <>
      {positions.map((pos, i) => (
        <mesh key={`${region.name}-n-${i}`} position={pos}>
          <sphereGeometry args={[0.04, 8, 8]} />
          <meshStandardMaterial
            color={region.color}
            emissive={region.color}
            emissiveIntensity={0.3}
            transparent
            opacity={0.6}
          />
        </mesh>
      ))}
    </>
  )
}

// ── Connection Lines Between Active Regions ───────────────

function RegionConnections({
  regions,
  activeRegions,
}: {
  regions: BrainRegion[]
  activeRegions: Map<string, number>
}) {
  const lines = useMemo(() => {
    const activeIds = Array.from(activeRegions.keys())
    if (activeIds.length < 2) return []

    const result: { from: [number, number, number]; to: [number, number, number]; intensity: number }[] = []
    const regionMap = new Map(regions.map(r => [r.id, r]))

    for (let i = 0; i < activeIds.length; i++) {
      for (let j = i + 1; j < activeIds.length; j++) {
        const rA = regionMap.get(activeIds[i])
        const rB = regionMap.get(activeIds[j])
        if (rA && rB) {
          const intensity = Math.min(
            activeRegions.get(activeIds[i]) || 0,
            activeRegions.get(activeIds[j]) || 0
          )
          result.push({
            from: getRegionCenter(rA),
            to: getRegionCenter(rB),
            intensity,
          })
        }
      }
    }
    return result
  }, [regions, activeRegions])

  return (
    <>
      {lines.map((line, i) => {
        const points = [new THREE.Vector3(...line.from), new THREE.Vector3(...line.to)]
        const geometry = new THREE.BufferGeometry().setFromPoints(points)
        return (
          <line key={`conn-${i}`}>
            <bufferGeometry attach="geometry" {...geometry} />
            <lineBasicMaterial
              color="#a78bfa"
              transparent
              opacity={line.intensity * 0.6}
              linewidth={2}
            />
          </line>
        )
      })}
    </>
  )
}

// ── Brain Scene (inside Canvas) ───────────────────────────

function BrainScene({
  developmentStage,
  selectedRegion,
  onSelectRegion,
  showCrossSection,
}: {
  developmentStage: number
  selectedRegion: BrainRegion | null
  onSelectRegion: (region: BrainRegion | null) => void
  showCrossSection: boolean
}) {
  const { regions, stageParams } = useBrainRegions(developmentStage)
  const { activeRegions, activeNeurons } = useNeuronActivations()
  const { brainData } = useBrainData()

  // Count neurons per region (using brainData.neurons count distributed by region)
  const neuronCountByRegion = useMemo(() => {
    const counts = new Map<string, number>()
    const totalNeurons = brainData?.neurons?.length ?? 0
    // Distribute proportionally across available regions
    const available = regions.filter(r => developmentStage >= r.development_stage_min)
    available.forEach(r => counts.set(r.id, Math.max(5, Math.floor(totalNeurons / Math.max(1, available.length)))))
    regions.filter(r => developmentStage < r.development_stage_min).forEach(r => counts.set(r.id, 0))
    return counts
  }, [regions, brainData, developmentStage])

  // Get active neuron IDs as set
  const activeNeuronIdSet = useMemo(() => {
    return new Set(activeNeurons.keys())
  }, [activeNeurons])

  return (
    <>
      <ambientLight intensity={0.25} />
      <pointLight position={[10, 10, 10]} intensity={0.8} color="#c4b5fd" />
      <pointLight position={[-10, -5, -10]} intensity={0.3} color="#818cf8" />
      <pointLight position={[0, -10, 5]} intensity={0.2} color="#a78bfa" />

      {/* Brain shell */}
      <BrainShell opacity={showCrossSection ? 0.03 : 0.06} scale={stageParams.scale} />

      {/* Scale group by development stage */}
      <group scale={stageParams.scale}>
        {/* Brain regions */}
        {regions.map(region => {
          const isAvailable = developmentStage >= region.development_stage_min
          const isInternal = region.is_internal
          // Hide internal regions unless cross-section is on
          if (isInternal && !showCrossSection) return null

          return (
            <BrainRegionMesh
              key={region.id}
              region={region}
              isActive={activeRegions.has(region.id)}
              isAvailable={isAvailable}
              activeIntensity={activeRegions.get(region.id) || 0}
              neuronCount={neuronCountByRegion.get(region.id) || 0}
              isSelected={selectedRegion?.id === region.id}
              onSelect={onSelectRegion}
            />
          )
        })}

        {/* Neuron particles */}
        {regions.map(region => (
          <RegionNeurons
            key={`neurons-${region.name}`}
            region={region}
            count={neuronCountByRegion.get(region.id) || 10}
            isAvailable={developmentStage >= region.development_stage_min}
            activeNeuronIds={activeNeuronIdSet}
          />
        ))}

        {/* Connection lines between active regions */}
        <RegionConnections regions={regions} activeRegions={activeRegions} />
      </group>

      <OrbitControls
        autoRotate
        autoRotateSpeed={0.3}
        enablePan={false}
        minDistance={6}
        maxDistance={20}
      />
    </>
  )
}

// ── Main Component ────────────────────────────────────────

interface RealisticBrainProps {
  developmentStage?: number
  fullScreen?: boolean
  className?: string
}

export function RealisticBrain({
  developmentStage = 2,
  fullScreen = false,
  className = '',
}: RealisticBrainProps) {
  const [selectedRegion, setSelectedRegion] = useState<BrainRegion | null>(null)
  const [showCrossSection, setShowCrossSection] = useState(false)
  const { regions, stageParams, loading } = useBrainRegions(developmentStage)
  const { activeRegions } = useNeuronActivations()

  const handleSelectRegion = useCallback((region: BrainRegion | null) => {
    setSelectedRegion(region)
  }, [])

  if (loading) {
    return (
      <div className={`flex items-center justify-center ${fullScreen ? 'h-full' : 'h-[500px]'} ${className}`}>
        <div className="text-center">
          <Brain className="w-12 h-12 text-violet-400 animate-pulse mx-auto mb-3" />
          <p className="text-slate-400 text-sm">해부학적 뇌 로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${fullScreen ? 'h-full' : 'h-[500px]'} ${className}`}>
      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 2, 12], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
        className="rounded-2xl"
      >
        <Suspense fallback={null}>
          <BrainScene
            developmentStage={developmentStage}
            selectedRegion={selectedRegion}
            onSelectRegion={handleSelectRegion}
            showCrossSection={showCrossSection}
          />
        </Suspense>
      </Canvas>

      {/* Controls Overlay */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button
          onClick={() => setShowCrossSection(!showCrossSection)}
          className={`p-2 rounded-lg transition-colors ${
            showCrossSection
              ? 'bg-violet-500/30 text-violet-300'
              : 'bg-slate-800/70 text-slate-400 hover:text-slate-300'
          }`}
          title={showCrossSection ? '외부 뷰' : '단면 보기'}
        >
          <Eye className="w-4 h-4" />
        </button>
      </div>

      {/* Stage Info */}
      <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur rounded-lg px-3 py-2 border border-slate-700/50">
        <p className="text-xs text-slate-400">
          발달 단계: <span className="text-violet-400 font-medium">{stageParams.label}</span>
        </p>
        <p className="text-[10px] text-slate-500">
          뇌 크기 {Math.round(stageParams.scale * 100)}% · 시냅스 밀도 {Math.round(stageParams.synapseDensity * 100)}%
        </p>
      </div>

      {/* Active Regions Legend */}
      {activeRegions.size > 0 && (
        <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur rounded-lg px-3 py-2 border border-slate-700/50">
          <p className="text-[10px] text-slate-400 mb-1">활성 영역</p>
          <div className="flex flex-wrap gap-1">
            {regions
              .filter(r => activeRegions.has(r.id))
              .map(r => (
                <span
                  key={r.id}
                  className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{ backgroundColor: r.color + '33', color: r.color }}
                >
                  {r.display_name}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Selected Region Info */}
      {selectedRegion && (
        <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur rounded-lg px-4 py-3 border border-slate-700/50 max-w-xs">
          <div className="flex items-center gap-2 mb-1">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: selectedRegion.color }}
            />
            <p className="text-sm font-medium text-white">{selectedRegion.display_name}</p>
            <p className="text-xs text-slate-400">{selectedRegion.display_name_en}</p>
          </div>
          {selectedRegion.description && (
            <p className="text-xs text-slate-400 mt-1">{selectedRegion.description}</p>
          )}
          <p className="text-[10px] text-slate-500 mt-1">
            활성화 단계: {selectedRegion.development_stage_min}+
            {selectedRegion.is_internal && ' · 내부 구조'}
          </p>
        </div>
      )}
    </div>
  )
}
