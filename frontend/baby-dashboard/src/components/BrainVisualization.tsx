'use client'

import { useRef, useState, useMemo, Suspense, useEffect, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Text, Html } from '@react-three/drei'
import * as THREE from 'three'
import { useBrainData } from '@/hooks/useBrainData'
import type { NeuronNode, Synapse, Astrocyte } from '@/lib/database.types'
import type { DiscoveredConnection } from '@/hooks/useImaginationSessions'
import { Brain, Loader2, RefreshCw, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

// Category colors — imported from useBrainData for single source of truth
// (used in legend display; actual neuron colors come from useBrainData.CATEGORY_COLORS)
import { CATEGORY_COLORS } from '@/hooks/useBrainData'

// Single neuron node component
function Neuron({
  node,
  isSelected,
  isHighlighted,
  onSelect,
}: {
  node: NeuronNode
  isSelected: boolean
  isHighlighted: boolean
  onSelect: (node: NeuronNode | null) => void
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  const color = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.default
  const baseSize = 0.08 + node.strength * 0.12
  const size = isSelected ? baseSize * 1.5 : hovered ? baseSize * 1.2 : baseSize

  useFrame((state) => {
    if (meshRef.current) {
      // Gentle pulse animation
      const pulse = Math.sin(state.clock.elapsedTime * 2 + node.position[0]) * 0.02
      meshRef.current.scale.setScalar(size + pulse)

      // Glow effect for selected/highlighted
      if (isSelected || isHighlighted) {
        meshRef.current.scale.setScalar(size + Math.abs(Math.sin(state.clock.elapsedTime * 3)) * 0.05)
      }
    }
  })

  return (
    <group position={node.position}>
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(isSelected ? null : node)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          setHovered(false)
          document.body.style.cursor = 'auto'
        }}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.8 : isHighlighted ? 0.5 : hovered ? 0.3 : 0.1}
          transparent
          opacity={isHighlighted || isSelected ? 1 : hovered ? 0.9 : 0.7}
        />
      </mesh>

      {/* Show label on hover or select */}
      {(hovered || isSelected) && (
        <Html distanceFactor={10} style={{ pointerEvents: 'none' }}>
          <div className="bg-slate-900/90 px-2 py-1 rounded text-xs text-white whitespace-nowrap border border-slate-700">
            <div className="font-medium">{node.name}</div>
            <div className="text-slate-400 text-[10px]">{node.category}</div>
          </div>
        </Html>
      )}
    </group>
  )
}

// Astrocyte meta-node component (glowing cluster sphere)
function AstrocyteSphere({
  astrocyte,
  isSelected,
  onSelect,
}: {
  astrocyte: Astrocyte
  isSelected: boolean
  onSelect: (a: Astrocyte | null) => void
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  useFrame((state) => {
    if (meshRef.current) {
      // Slow pulse animation
      const pulse = Math.sin(state.clock.elapsedTime * 0.5) * 0.1
      meshRef.current.scale.setScalar(astrocyte.size + pulse)

      // Rotation
      meshRef.current.rotation.y += 0.002
    }
  })

  return (
    <group position={astrocyte.position}>
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(isSelected ? null : astrocyte)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[1, 24, 24]} />
        <meshStandardMaterial
          color={astrocyte.color}
          emissive={astrocyte.color}
          emissiveIntensity={isSelected ? 0.6 : hovered ? 0.4 : 0.2}
          transparent
          opacity={isSelected ? 0.4 : hovered ? 0.3 : 0.15}
          wireframe={false}
        />
      </mesh>

      {/* Inner glow sphere */}
      <mesh scale={0.8}>
        <sphereGeometry args={[astrocyte.size, 16, 16]} />
        <meshBasicMaterial
          color={astrocyte.color}
          transparent
          opacity={0.1}
        />
      </mesh>

      {/* Label on hover */}
      {(hovered || isSelected) && (
        <Html distanceFactor={15} style={{ pointerEvents: 'none' }}>
          <div className="bg-slate-900/95 px-3 py-2 rounded-lg text-xs text-white whitespace-nowrap border border-slate-600 shadow-lg">
            <div className="font-bold text-sm">{astrocyte.name}</div>
            <div className="text-slate-400 mt-1">
              {astrocyte.neuronIds.length}개 뉴런 · 강도 {(astrocyte.strength * 100).toFixed(0)}%
            </div>
          </div>
        </Html>
      )}
    </group>
  )
}

// Synapse connection line
function SynapseConnection({
  synapse,
  neurons,
  isHighlighted,
  isIntraCluster,
}: {
  synapse: Synapse
  neurons: Map<string, NeuronNode>
  isHighlighted: boolean
  isIntraCluster: boolean
}) {
  const lineRef = useRef<THREE.Line>(null)

  const fromNeuron = neurons.get(synapse.fromId)
  const toNeuron = neurons.get(synapse.toId)

  // Create line object
  const lineObject = useMemo(() => {
    if (!fromNeuron || !toNeuron) return null

    const points = [
      new THREE.Vector3(...fromNeuron.position),
      new THREE.Vector3(...toNeuron.position),
    ]
    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    // Intra-cluster synapses are brighter
    const baseOpacity = isIntraCluster ? 0.3 : 0.1
    const material = new THREE.LineBasicMaterial({
      color: isHighlighted ? '#22c55e' : isIntraCluster ? '#8b5cf6' : '#475569',
      transparent: true,
      opacity: isHighlighted ? 0.8 : baseOpacity + synapse.strength * 0.2,
    })
    return new THREE.Line(geometry, material)
  }, [fromNeuron, toNeuron, isHighlighted, synapse.strength, isIntraCluster])

  useFrame((state) => {
    if (lineRef.current && isHighlighted) {
      // Animate opacity for highlighted synapses
      const material = lineRef.current.material as THREE.LineBasicMaterial
      material.opacity = 0.5 + Math.sin(state.clock.elapsedTime * 4) * 0.3
    }
  })

  if (!lineObject) return null

  return <primitive ref={lineRef} object={lineObject} />
}

// Imagination connection line (special glowing line for discovered connections)
function ImaginationConnection({
  fromNeuron,
  toNeuron,
}: {
  fromNeuron: NeuronNode
  toNeuron: NeuronNode
}) {
  const lineRef = useRef<THREE.Line>(null)

  const lineObject = useMemo(() => {
    const points = [
      new THREE.Vector3(...fromNeuron.position),
      new THREE.Vector3(...toNeuron.position),
    ]
    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const material = new THREE.LineBasicMaterial({
      color: '#f59e0b', // Amber color for imagination connections
      transparent: true,
      opacity: 0.9,
      linewidth: 2,
    })
    return new THREE.Line(geometry, material)
  }, [fromNeuron, toNeuron])

  useFrame((state) => {
    if (lineRef.current) {
      const material = lineRef.current.material as THREE.LineBasicMaterial
      material.opacity = 0.5 + Math.sin(state.clock.elapsedTime * 4) * 0.4
    }
  })

  return <primitive ref={lineRef} object={lineObject} />
}

// Main 3D scene
function BrainScene({
  neurons,
  synapses,
  astrocytes,
  neuronToAstrocyte,
  selectedNeuron,
  onSelectNeuron,
  selectedAstrocyte,
  onSelectAstrocyte,
  highlightedConnection,
}: {
  neurons: NeuronNode[]
  synapses: Synapse[]
  astrocytes: Astrocyte[]
  neuronToAstrocyte: Record<string, string>
  selectedNeuron: NeuronNode | null
  onSelectNeuron: (node: NeuronNode | null) => void
  selectedAstrocyte: Astrocyte | null
  onSelectAstrocyte: (a: Astrocyte | null) => void
  highlightedConnection?: DiscoveredConnection | null
}) {
  const neuronMap = useMemo(() => new Map(neurons.map((n) => [n.id, n])), [neurons])

  // Find connected neurons when one is selected
  const connectedNeuronIds = useMemo(() => {
    if (!selectedNeuron) return new Set<string>()
    const connected = new Set<string>()
    synapses.forEach((s) => {
      if (s.fromId === selectedNeuron.id) connected.add(s.toId)
      if (s.toId === selectedNeuron.id) connected.add(s.fromId)
    })
    return connected
  }, [selectedNeuron, synapses])

  // Determine if synapse is intra-cluster
  const isIntraCluster = useMemo(() => {
    const map = new Map<string, boolean>()
    synapses.forEach(s => {
      const fromCluster = neuronToAstrocyte[s.fromId]
      const toCluster = neuronToAstrocyte[s.toId]
      map.set(s.id, fromCluster !== undefined && fromCluster === toCluster)
    })
    return map
  }, [synapses, neuronToAstrocyte])

  // Neurons in selected astrocyte
  const selectedAstrocyteNeuronIds = useMemo(() => {
    if (!selectedAstrocyte) return new Set<string>()
    return new Set(selectedAstrocyte.neuronIds)
  }, [selectedAstrocyte])

  // Find neurons matching highlighted imagination connection
  const imaginationHighlight = useMemo(() => {
    if (!highlightedConnection) return null

    // Find neurons by name (partial match for flexibility)
    const findNeuronByName = (name: string): NeuronNode | null => {
      // Exact match first
      let found = neurons.find(n => n.name === name)
      if (found) return found

      // Partial match (contains)
      found = neurons.find(n => n.name.includes(name) || name.includes(n.name))
      if (found) return found

      return null
    }

    const fromNeuron = findNeuronByName(highlightedConnection.from)
    const toNeuron = findNeuronByName(highlightedConnection.to)

    if (!fromNeuron || !toNeuron) return null

    return {
      fromNeuron,
      toNeuron,
      fromId: fromNeuron.id,
      toId: toNeuron.id,
    }
  }, [highlightedConnection, neurons])

  // Set of imagination-highlighted neuron IDs
  const imaginationHighlightedIds = useMemo(() => {
    if (!imaginationHighlight) return new Set<string>()
    return new Set([imaginationHighlight.fromId, imaginationHighlight.toId])
  }, [imaginationHighlight])

  return (
    <>
      {/* Ambient light */}
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#8b5cf6" />

      {/* Astrocytes (render first, as background) */}
      {astrocytes.map((astrocyte) => (
        <AstrocyteSphere
          key={astrocyte.id}
          astrocyte={astrocyte}
          isSelected={selectedAstrocyte?.id === astrocyte.id}
          onSelect={onSelectAstrocyte}
        />
      ))}

      {/* Synapses (render behind neurons) */}
      {synapses.map((synapse) => (
        <SynapseConnection
          key={synapse.id}
          synapse={synapse}
          neurons={neuronMap}
          isHighlighted={
            selectedNeuron !== null &&
            (synapse.fromId === selectedNeuron.id || synapse.toId === selectedNeuron.id)
          }
          isIntraCluster={isIntraCluster.get(synapse.id) || false}
        />
      ))}

      {/* Neurons */}
      {neurons.map((neuron) => (
        <Neuron
          key={neuron.id}
          node={neuron}
          isSelected={selectedNeuron?.id === neuron.id}
          isHighlighted={
            connectedNeuronIds.has(neuron.id) ||
            selectedAstrocyteNeuronIds.has(neuron.id) ||
            imaginationHighlightedIds.has(neuron.id)
          }
          onSelect={onSelectNeuron}
        />
      ))}

      {/* Imagination connection line (when hovering over a discovered connection) */}
      {imaginationHighlight && (
        <ImaginationConnection
          fromNeuron={imaginationHighlight.fromNeuron}
          toNeuron={imaginationHighlight.toNeuron}
        />
      )}

      {/* Camera controls */}
      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        autoRotate={!selectedNeuron && !selectedAstrocyte}
        autoRotateSpeed={0.5}
        minDistance={1}
        maxDistance={80}
      />
    </>
  )
}

// Camera controller for zoom buttons
function CameraController({ zoomIn, zoomOut, reset }: { zoomIn: boolean; zoomOut: boolean; reset: boolean }) {
  const { camera } = useThree()

  useFrame(() => {
    if (zoomIn && camera.position.length() > 1.5) {
      camera.position.multiplyScalar(0.98)
    }
    if (zoomOut && camera.position.length() < 70) {
      camera.position.multiplyScalar(1.02)
    }
    if (reset) {
      camera.position.lerp(new THREE.Vector3(0, 0, 8), 0.1)
    }
  })

  return null
}

// Info panel for selected neuron
function NeuronInfoPanel({
  neuron,
  connectedCount,
  onClose,
}: {
  neuron: NeuronNode
  connectedCount: number
  onClose: () => void
}) {
  return (
    <div className="absolute bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-72 bg-slate-800/95 backdrop-blur rounded-xl p-4 border border-slate-700">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold text-white">{neuron.name}</h3>
          <span
            className="inline-block px-2 py-0.5 rounded text-xs mt-1"
            style={{ backgroundColor: CATEGORY_COLORS[neuron.category] + '30', color: CATEGORY_COLORS[neuron.category] }}
          >
            {neuron.category}
          </span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
          ✕
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-slate-900/50 rounded-lg p-2">
          <p className="text-slate-400 text-xs">강도</p>
          <p className="text-white font-medium">{(neuron.strength * 100).toFixed(0)}%</p>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2">
          <p className="text-slate-400 text-xs">연결</p>
          <p className="text-white font-medium">{connectedCount}개</p>
        </div>
      </div>

      <div className="mt-3 text-xs text-slate-400">
        클릭하여 연결된 뉴런 확인
      </div>
    </div>
  )
}

// Legend component — shows only categories present in data
function Legend({ neurons }: { neurons?: NeuronNode[] }) {
  const activeCategories = useMemo(() => {
    if (!neurons) return []
    const counts = new Map<string, number>()
    neurons.forEach(n => {
      counts.set(n.category, (counts.get(n.category) || 0) + 1)
    })
    // Sort by count descending, take top 10
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
  }, [neurons])

  return (
    <div className="absolute top-4 left-4 bg-slate-800/80 backdrop-blur rounded-lg p-3 text-xs">
      <p className="text-slate-400 mb-2 font-medium">카테고리</p>
      <div className="space-y-1.5">
        {activeCategories.map(([category, count]) => (
          <div key={category} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[category] || CATEGORY_COLORS.default }} />
            <span className="text-slate-300">{category} <span className="text-slate-500">({count})</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}

// WebGL Context Loss Recovery Handler
function WebGLRecoveryHandler({ onContextLost }: { onContextLost: () => void }) {
  const { gl } = useThree()

  useEffect(() => {
    const canvas = gl.domElement

    const handleContextLost = (event: Event) => {
      event.preventDefault()
      console.warn('[BrainVisualization] WebGL context lost, will recover...')
      onContextLost()
    }

    const handleContextRestored = () => {
      console.log('[BrainVisualization] WebGL context restored')
    }

    canvas.addEventListener('webglcontextlost', handleContextLost)
    canvas.addEventListener('webglcontextrestored', handleContextRestored)

    return () => {
      canvas.removeEventListener('webglcontextlost', handleContextLost)
      canvas.removeEventListener('webglcontextrestored', handleContextRestored)
    }
  }, [gl, onContextLost])

  return null
}

// Main export component
export function BrainVisualization({
  fullScreen = false,
  highlightedConnection,
}: {
  fullScreen?: boolean
  highlightedConnection?: DiscoveredConnection | null
}) {
  const { brainData, isLoading, error, refetch } = useBrainData()
  const [selectedNeuron, setSelectedNeuron] = useState<NeuronNode | null>(null)
  const [selectedAstrocyte, setSelectedAstrocyte] = useState<Astrocyte | null>(null)
  const [zoomIn, setZoomIn] = useState(false)
  const [zoomOut, setZoomOut] = useState(false)
  const [reset, setReset] = useState(false)
  const [mounted, setMounted] = useState(false)
  const [contextLost, setContextLost] = useState(false)
  const [canvasKey, setCanvasKey] = useState(0)

  // Hydration 에러 방지
  useEffect(() => {
    setMounted(true)
  }, [])

  // WebGL Context Recovery: remount Canvas
  const handleContextLost = useCallback(() => {
    setContextLost(true)
    // Remount canvas after short delay
    setTimeout(() => {
      setCanvasKey(k => k + 1)
      setContextLost(false)
    }, 100)
  }, [])

  // Count connections for selected neuron
  const connectedCount = useMemo(() => {
    if (!selectedNeuron || !brainData) return 0
    return brainData.synapses.filter(
      (s) => s.fromId === selectedNeuron.id || s.toId === selectedNeuron.id
    ).length
  }, [selectedNeuron, brainData])

  // 서버와 클라이언트 모두 동일한 기본 높이로 시작, mounted 후에만 fullScreen 적용
  const containerHeight = mounted && fullScreen ? 'h-[calc(100vh-140px)]' : 'h-[400px] md:h-[500px]'
  const canvasHeight = mounted && fullScreen ? 'h-[calc(100vh-140px)]' : 'h-[400px] md:h-[500px]'

  if (isLoading) {
    return (
      <div className={`bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 ${containerHeight} flex items-center justify-center`} suppressHydrationWarning>
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin mx-auto mb-3" />
          <p className="text-slate-400">뉴런 네트워크 로딩 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 ${containerHeight} flex items-center justify-center`} suppressHydrationWarning>
        <div className="text-center">
          <p className="text-red-400 mb-3">{error}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white"
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  if (!brainData || brainData.neurons.length === 0) {
    return (
      <div className={`bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50 ${containerHeight} flex items-center justify-center`} suppressHydrationWarning>
        <div className="text-center">
          <Brain className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">뉴런 데이터가 없습니다</p>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden relative ${mounted && fullScreen ? 'h-[calc(100vh-140px)]' : ''}`}
      suppressHydrationWarning
    >
      {/* Header */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <div className="bg-slate-800/80 backdrop-blur rounded-lg px-3 py-1.5 text-xs text-slate-300">
          <span className="text-violet-400 font-medium">{brainData.neurons.length}</span> 뉴런 ·{' '}
          <span className="text-emerald-400 font-medium">{brainData.synapses.length}</span> 시냅스 ·{' '}
          <span className="text-amber-400 font-medium">{brainData.astrocytes?.length || 0}</span> 클러스터
        </div>
        <button
          onClick={refetch}
          className="p-2 bg-slate-800/80 backdrop-blur rounded-lg hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-1">
        <button
          onMouseDown={() => setZoomIn(true)}
          onMouseUp={() => setZoomIn(false)}
          onMouseLeave={() => setZoomIn(false)}
          className="p-2 bg-slate-800/80 backdrop-blur rounded-lg hover:bg-slate-700 transition-colors"
        >
          <ZoomIn className="w-4 h-4 text-slate-400" />
        </button>
        <button
          onMouseDown={() => setZoomOut(true)}
          onMouseUp={() => setZoomOut(false)}
          onMouseLeave={() => setZoomOut(false)}
          className="p-2 bg-slate-800/80 backdrop-blur rounded-lg hover:bg-slate-700 transition-colors"
        >
          <ZoomOut className="w-4 h-4 text-slate-400" />
        </button>
        <button
          onMouseDown={() => setReset(true)}
          onMouseUp={() => setReset(false)}
          onMouseLeave={() => setReset(false)}
          className="p-2 bg-slate-800/80 backdrop-blur rounded-lg hover:bg-slate-700 transition-colors"
        >
          <RotateCcw className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {/* Legend */}
      <Legend neurons={brainData?.neurons} />

      {/* 3D Canvas */}
      <div className={`w-full ${canvasHeight}`}>
        {contextLost ? (
          <div className="w-full h-full flex items-center justify-center bg-slate-900/50">
            <p className="text-slate-400 text-sm">렌더러 복구 중...</p>
          </div>
        ) : (
          <Canvas
            key={canvasKey}
            camera={{ position: [0, 0, 8], fov: 60 }}
            gl={{
              antialias: true,
              powerPreference: 'high-performance',
              failIfMajorPerformanceCaveat: false,
            }}
            onCreated={({ gl }) => {
              // Enable context loss handling
              gl.getContext().canvas.addEventListener('webglcontextlost', (e) => e.preventDefault())
            }}
          >
            <Suspense fallback={null}>
              <WebGLRecoveryHandler onContextLost={handleContextLost} />
              <BrainScene
                neurons={brainData.neurons}
                synapses={brainData.synapses}
                astrocytes={brainData.astrocytes || []}
                neuronToAstrocyte={brainData.neuronToAstrocyte || {}}
                selectedNeuron={selectedNeuron}
                onSelectNeuron={setSelectedNeuron}
                selectedAstrocyte={selectedAstrocyte}
                onSelectAstrocyte={setSelectedAstrocyte}
                highlightedConnection={highlightedConnection}
              />
              <CameraController zoomIn={zoomIn} zoomOut={zoomOut} reset={reset} />
            </Suspense>
          </Canvas>
        )}
      </div>

      {/* Selected neuron info */}
      {selectedNeuron && (
        <NeuronInfoPanel
          neuron={selectedNeuron}
          connectedCount={connectedCount}
          onClose={() => setSelectedNeuron(null)}
        />
      )}
    </div>
  )
}
