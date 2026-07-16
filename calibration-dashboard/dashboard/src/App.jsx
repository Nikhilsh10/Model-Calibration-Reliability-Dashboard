import React, { useState, useEffect } from 'react'
import './index.css'
import MetricCards from './components/MetricCards'
import ReliabilityDiagram from './components/ReliabilityDiagram'
import ScoreSimulator from './components/ScoreSimulator'
import { Activity } from 'lucide-react'

const API_BASE = 'http://127.0.0.1:8001'

export default function App() {
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [calibrationData, setCalibrationData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load model list on mount
  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then(r => r.json())
      .then(data => {
        setModels(data.models)
        if (data.models.length > 0) setSelectedModel(data.models[0].id)
      })
      .catch(e => setError(`Cannot reach API: ${e.message}. Is the API server running on port 8001?`))
  }, [])

  // Load calibration data when model changes
  useEffect(() => {
    if (!selectedModel) return
    setLoading(true)
    setCalibrationData(null)
    setError(null)
    fetch(`${API_BASE}/calibration/${selectedModel}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => { setCalibrationData(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [selectedModel])

  return (
    <div className="app">
      <header className="header" role="banner">
        <div className="header-inner">
          <div className="header-title">
            <Activity size={18} color="var(--color-accent)" aria-hidden="true" />
            <h1>Model Calibration &amp; Reliability Dashboard</h1>
            <span className="header-badge">StreamSentinel addendum</span>
          </div>

          {models.length > 0 && (
            <div className="model-selector">
              <label htmlFor="model-select">Model</label>
              <select
                id="model-select"
                value={selectedModel ?? ''}
                onChange={e => setSelectedModel(e.target.value)}
                aria-label="Select model to inspect"
              >
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.label} stream</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </header>

      <main id="main-content" role="main">
        {error && (
          <div className="state-container">
            <div className="error-box" role="alert">{error}</div>
          </div>
        )}

        {loading && !error && (
          <div className="state-container" aria-label="Loading calibration data">
            <div className="spinner" aria-hidden="true" />
            <span>Loading calibration data…</span>
          </div>
        )}

        {calibrationData && !loading && (
          <>
            <MetricCards data={calibrationData} />
            <ReliabilityDiagram data={calibrationData} />
            {selectedModel && <ScoreSimulator modelId={selectedModel} />}
          </>
        )}
      </main>
    </div>
  )
}
