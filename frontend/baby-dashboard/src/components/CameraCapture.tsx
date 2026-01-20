'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCamera } from '@/hooks'
import {
  Camera,
  CameraOff,
  SwitchCamera,
  Upload,
  X,
  Check,
  RefreshCw,
  AlertCircle,
  Image as ImageIcon,
} from 'lucide-react'

export interface CameraCaptureProps {
  onCapture: (imageData: Blob) => void
  onClose?: () => void
  className?: string
}

export function CameraCapture({ onCapture, onClose, className = '' }: CameraCaptureProps) {
  const {
    stream,
    isPermissionGranted,
    isLoading,
    error,
    videoRef,
    startCamera,
    stopCamera,
    capturePhoto,
    switchCamera,
    currentFacing,
    hasMultipleCameras,
  } = useCamera()

  // Captured image preview
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null)

  // Handle capture
  const handleCapture = useCallback(async () => {
    const blob = await capturePhoto()
    if (blob) {
      setCapturedBlob(blob)
      setCapturedImage(URL.createObjectURL(blob))
    }
  }, [capturePhoto])

  // Confirm captured image
  const handleConfirm = useCallback(() => {
    if (capturedBlob) {
      onCapture(capturedBlob)
      setCapturedImage(null)
      setCapturedBlob(null)
      stopCamera()
    }
  }, [capturedBlob, onCapture, stopCamera])

  // Retake photo
  const handleRetake = useCallback(() => {
    if (capturedImage) {
      URL.revokeObjectURL(capturedImage)
    }
    setCapturedImage(null)
    setCapturedBlob(null)
  }, [capturedImage])

  // Handle file upload
  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      onCapture(file)
    }
  }, [onCapture])

  return (
    <div className={`bg-gradient-to-br from-slate-800/90 to-slate-900/90 rounded-2xl border border-slate-700/50 backdrop-blur-sm overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Camera className="w-5 h-5 text-cyan-400" />
          카메라
        </h3>
        <div className="flex items-center gap-2">
          {/* File upload button */}
          <label className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors cursor-pointer">
            <Upload className="w-5 h-5 text-slate-300" />
            <input
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
            />
          </label>

          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              <X className="w-5 h-5 text-slate-300" />
            </button>
          )}
        </div>
      </div>

      {/* Camera View */}
      <div className="relative aspect-video bg-slate-900">
        <AnimatePresence mode="wait">
          {/* Error state */}
          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center p-4"
            >
              <AlertCircle className="w-12 h-12 text-rose-400 mb-4" />
              <p className="text-slate-400 text-center mb-4">{error}</p>
              <button
                onClick={startCamera}
                className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors"
              >
                다시 시도
              </button>
            </motion.div>
          )}

          {/* Loading state */}
          {isLoading && !error && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
            </motion.div>
          )}

          {/* Not started state */}
          {!stream && !isLoading && !error && (
            <motion.div
              key="start"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center p-4"
            >
              <CameraOff className="w-12 h-12 text-slate-500 mb-4" />
              <p className="text-slate-400 text-center mb-4">
                카메라가 활성화되지 않았습니다
              </p>
              <button
                onClick={startCamera}
                className="px-6 py-3 bg-cyan-500 text-white rounded-xl hover:bg-cyan-600 transition-colors flex items-center gap-2"
              >
                <Camera className="w-5 h-5" />
                카메라 시작
              </button>
            </motion.div>
          )}

          {/* Captured image preview */}
          {capturedImage && (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="absolute inset-0"
            >
              <img
                src={capturedImage}
                alt="Captured"
                className="w-full h-full object-contain"
              />
            </motion.div>
          )}

          {/* Video stream - always visible, use opacity for hiding */}
          {/* NOTE: visibility:hidden causes black screen on some mobile browsers */}
          <div
            className="absolute inset-0"
            style={{
              opacity: stream && !capturedImage ? 1 : 0,
              pointerEvents: stream && !capturedImage ? 'auto' : 'none',
              zIndex: stream && !capturedImage ? 1 : -1,
            }}
          >
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              webkit-playsinline="true"
              className="w-full h-full object-cover"
              style={{
                transform: currentFacing === 'user' ? 'scaleX(-1)' : 'none',
              }}
            />
          </div>
        </AnimatePresence>

        {/* Camera facing indicator */}
        {stream && !capturedImage && (
          <div className="absolute top-4 left-4 px-2 py-1 bg-slate-900/70 rounded-full text-xs text-slate-300">
            {currentFacing === 'user' ? '전면' : '후면'}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-4 flex items-center justify-center gap-4">
        {/* Captured image controls */}
        {capturedImage ? (
          <>
            <button
              onClick={handleRetake}
              className="p-4 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="w-6 h-6 text-slate-300" />
            </button>
            <button
              onClick={handleConfirm}
              className="p-5 rounded-full bg-emerald-500 hover:bg-emerald-600 transition-colors"
            >
              <Check className="w-8 h-8 text-white" />
            </button>
          </>
        ) : stream ? (
          <>
            {/* Switch camera */}
            {hasMultipleCameras && (
              <button
                onClick={switchCamera}
                className="p-3 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
              >
                <SwitchCamera className="w-6 h-6 text-slate-300" />
              </button>
            )}

            {/* Capture button */}
            <button
              onClick={handleCapture}
              className="p-5 rounded-full bg-cyan-500 hover:bg-cyan-600 transition-colors shadow-lg shadow-cyan-500/30"
            >
              <Camera className="w-8 h-8 text-white" />
            </button>

            {/* Stop camera */}
            <button
              onClick={stopCamera}
              className="p-3 rounded-full bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              <CameraOff className="w-6 h-6 text-slate-300" />
            </button>
          </>
        ) : null}
      </div>

      {/* Permission info */}
      {isPermissionGranted && stream && (
        <div className="px-4 pb-4">
          <div className="text-xs text-slate-500 text-center">
            카메라 권한이 허용되었습니다. 사진을 찍어 Baby AI에게 보여주세요.
          </div>
        </div>
      )}
    </div>
  )
}

// Compact version for embedding
export function CameraCaptureCompact({ onCapture, className = '' }: Omit<CameraCaptureProps, 'onClose'>) {
  const { stream, videoRef, startCamera, capturePhoto, currentFacing } = useCamera()
  const [isCapturing, setIsCapturing] = useState(false)

  const handleCapture = useCallback(async () => {
    if (!stream) {
      await startCamera()
      return
    }

    setIsCapturing(true)
    const blob = await capturePhoto()
    if (blob) {
      onCapture(blob)
    }
    setIsCapturing(false)
  }, [stream, startCamera, capturePhoto, onCapture])

  return (
    <div className={`relative rounded-xl overflow-hidden bg-slate-800 ${className}`}>
      {stream ? (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            style={{
              transform: currentFacing === 'user' ? 'scaleX(-1)' : 'none',
            }}
          />
          <button
            onClick={handleCapture}
            disabled={isCapturing}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 p-3 rounded-full bg-cyan-500 hover:bg-cyan-600 disabled:opacity-50 transition-colors shadow-lg"
          >
            {isCapturing ? (
              <RefreshCw className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Camera className="w-5 h-5 text-white" />
            )}
          </button>
        </>
      ) : (
        <button
          onClick={handleCapture}
          className="w-full h-full flex flex-col items-center justify-center p-4 hover:bg-slate-700/50 transition-colors"
        >
          <ImageIcon className="w-8 h-8 text-slate-500 mb-2" />
          <span className="text-sm text-slate-400">사진 찍기</span>
        </button>
      )}
    </div>
  )
}
