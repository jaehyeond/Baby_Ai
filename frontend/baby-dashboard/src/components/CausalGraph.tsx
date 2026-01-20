'use client'

import { useMemo, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import type { CausalGraphData, CausalNode, CausalEdge } from '@/lib/database.types'

interface NodePosition {
  x: number
  y: number
}

interface CausalGraphProps {
  data: CausalGraphData
  width?: number
  height?: number
  className?: string
}

export function CausalGraph({ data, width = 600, height = 400, className = '' }: CausalGraphProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null)

  // Calculate node positions using force-directed layout simulation
  const nodePositions = useMemo(() => {
    if (data.nodes.length === 0) return new Map<string, NodePosition>()

    const positions = new Map<string, NodePosition>()
    const padding = 60
    const effectiveWidth = width - padding * 2
    const effectiveHeight = height - padding * 2

    // Group nodes by type
    const causeNodes = data.nodes.filter(n => n.type === 'cause')
    const effectNodes = data.nodes.filter(n => n.type === 'effect')
    const bothNodes = data.nodes.filter(n => n.type === 'both')

    // Position cause nodes on left
    causeNodes.forEach((node, i) => {
      const y = padding + (i + 1) * effectiveHeight / (causeNodes.length + 1)
      positions.set(node.id, { x: padding, y })
    })

    // Position effect nodes on right
    effectNodes.forEach((node, i) => {
      const y = padding + (i + 1) * effectiveHeight / (effectNodes.length + 1)
      positions.set(node.id, { x: width - padding, y })
    })

    // Position 'both' nodes in center
    bothNodes.forEach((node, i) => {
      const y = padding + (i + 1) * effectiveHeight / (bothNodes.length + 1)
      positions.set(node.id, { x: width / 2, y })
    })

    return positions
  }, [data.nodes, width, height])

  // Get connections for selected node
  const getConnections = useCallback((nodeId: string) => {
    const outgoing = data.edges.filter(e => e.from === nodeId)
    const incoming = data.edges.filter(e => e.to === nodeId)
    return { outgoing, incoming }
  }, [data.edges])

  // Node color based on type
  const getNodeColor = (node: CausalNode) => {
    if (selectedNode === node.id) return 'from-yellow-400 to-orange-500'
    switch (node.type) {
      case 'cause': return 'from-blue-500 to-cyan-500'
      case 'effect': return 'from-green-500 to-emerald-500'
      case 'both': return 'from-purple-500 to-pink-500'
      default: return 'from-slate-500 to-slate-600'
    }
  }

  // Edge color based on relationship type
  const getEdgeColor = (edge: CausalEdge, isHighlighted: boolean) => {
    if (isHighlighted) return 'stroke-yellow-400'
    switch (edge.relationshipType) {
      case 'causes': return 'stroke-green-400/60'
      case 'enables': return 'stroke-blue-400/60'
      case 'prevents': return 'stroke-red-400/60'
      case 'modulates': return 'stroke-purple-400/60'
      default: return 'stroke-slate-500/60'
    }
  }

  // Calculate edge path
  const getEdgePath = (edge: CausalEdge) => {
    const from = nodePositions.get(edge.from)
    const to = nodePositions.get(edge.to)
    if (!from || !to) return ''

    // Create curved path
    const midX = (from.x + to.x) / 2
    const midY = (from.y + to.y) / 2
    const dx = to.x - from.x
    const dy = to.y - from.y
    const curve = Math.min(Math.abs(dx), Math.abs(dy)) * 0.3

    // Add curve perpendicular to the line
    const curveX = midX - (dy * curve) / Math.sqrt(dx * dx + dy * dy) * 0.5
    const curveY = midY + (dx * curve) / Math.sqrt(dx * dx + dy * dy) * 0.5

    return `M ${from.x} ${from.y} Q ${curveX} ${curveY} ${to.x} ${to.y}`
  }

  if (data.nodes.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center h-full text-slate-500 ${className}`}>
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-4xl mb-4"
        >
          ...
        </motion.div>
        <p className="text-sm">No causal relationships discovered yet</p>
        <p className="text-xs mt-1">Baby AI is learning cause and effect...</p>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <svg
        width={width}
        height={height}
        className="overflow-visible"
      >
        {/* Definitions for markers */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              className="fill-slate-400"
            />
          </marker>
          <marker
            id="arrowhead-highlight"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              className="fill-yellow-400"
            />
          </marker>
        </defs>

        {/* Edges */}
        {data.edges.map((edge) => {
          const isHighlighted = selectedNode === edge.from || selectedNode === edge.to || hoveredEdge === edge.id

          return (
            <motion.path
              key={edge.id}
              d={getEdgePath(edge)}
              className={`fill-none ${getEdgeColor(edge, isHighlighted)} transition-all duration-300`}
              strokeWidth={isHighlighted ? 3 : Math.max(1, edge.strength * 3)}
              strokeOpacity={isHighlighted ? 1 : 0.6}
              markerEnd={isHighlighted ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5 }}
              onMouseEnter={() => setHoveredEdge(edge.id)}
              onMouseLeave={() => setHoveredEdge(null)}
              style={{ cursor: 'pointer' }}
            />
          )
        })}

        {/* Nodes */}
        {data.nodes.map((node) => {
          const pos = nodePositions.get(node.id)
          if (!pos) return null

          const isSelected = selectedNode === node.id
          const isConnected = selectedNode && (
            data.edges.some(e => (e.from === selectedNode && e.to === node.id) || (e.to === selectedNode && e.from === node.id))
          )

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => setSelectedNode(isSelected ? null : node.id)}
              style={{ cursor: 'pointer' }}
            >
              <motion.circle
                r={isSelected ? 20 : 15}
                className={`fill-gradient bg-gradient-to-br ${getNodeColor(node)}`}
                style={{
                  fill: `url(#grad-${node.type})`,
                  filter: isSelected || isConnected ? 'drop-shadow(0 0 8px rgba(168, 85, 247, 0.5))' : 'none'
                }}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: 1.2 }}
                transition={{ type: 'spring', stiffness: 300 }}
              />
              {/* Fallback circle with gradient simulation */}
              <circle
                r={isSelected ? 20 : 15}
                className={`${
                  node.type === 'cause' ? 'fill-blue-500' :
                  node.type === 'effect' ? 'fill-green-500' :
                  'fill-purple-500'
                } ${isSelected ? 'opacity-100' : 'opacity-80'}`}
              />
              <text
                textAnchor="middle"
                dy=".35em"
                className="fill-white text-[10px] font-medium pointer-events-none"
              >
                {node.name.length > 8 ? node.name.slice(0, 6) + '..' : node.name}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 flex flex-wrap gap-3 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-slate-400">Cause</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-slate-400">Effect</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-purple-500" />
          <span className="text-slate-400">Both</span>
        </div>
      </div>

      {/* Selected node info */}
      {selectedNode && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-2 right-2 bg-slate-800/90 rounded-lg p-3 max-w-[200px]"
        >
          <p className="text-sm font-medium text-white mb-1">
            {data.nodes.find(n => n.id === selectedNode)?.name}
          </p>
          <p className="text-xs text-slate-400 mb-2">
            Category: {data.nodes.find(n => n.id === selectedNode)?.category || 'Unknown'}
          </p>
          {(() => {
            const connections = getConnections(selectedNode)
            return (
              <div className="space-y-1 text-xs">
                {connections.outgoing.length > 0 && (
                  <p className="text-green-400">
                    {connections.outgoing.length} outgoing
                  </p>
                )}
                {connections.incoming.length > 0 && (
                  <p className="text-blue-400">
                    {connections.incoming.length} incoming
                  </p>
                )}
              </div>
            )
          })()}
        </motion.div>
      )}
    </div>
  )
}
