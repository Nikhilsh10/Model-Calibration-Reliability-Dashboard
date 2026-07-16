import React, { useState, useCallback, useRef } from 'react'
import { Zap } from 'lucide-react'

const API_BASE = 'http://127.0.0.1:8001'

/**
 * ScoreSimulator
 *
 * Slider → POST /score → displays calibrated probability.
 * Method toggle between Platt and Isotonic.
 * Error surfaces inline near the control, not as a top-level banner.
 * 200ms CSS transition on result update (reduced-motion respected).
 */
export default function ScoreSimulator({ modelId }) {
  const [rawScore, setRawScore] = useState(0.65)
  const [method, setMethod] = useState('platt')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)

  const fetchScore = useCallback(async (score, meth) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId, raw_score: score, method: meth }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data.calibrated_probability)
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [modelId])

  const handleSlider = (e) => {
    const val = parseFloat(e.target.value)
    setRawScore(val)
    // Debounce API calls — 150ms feels responsive without hammering the API
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchScore(val, method), 150)
  }

  const handleMethod = (meth) => {
    setMethod(meth)
    fetchScore(rawScore, meth)
  }

  // Call on mount with default values
  React.useEffect(() => {
    fetchScore(rawScore, method)
  }, [modelId]) // eslint-disable-line react-hooks/exhaustive-deps

  const resultDisplay = loading
    ? '...'
    : result != null
      ? result.toFixed(4)
      : '—'

  return (
    <section className="simulator-section" aria-label="Score simulator">
      <div className="simulator-header">
        <div>
          <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Zap size={15} color="var(--color-accent)" aria-hidden="true" />
            Score Simulator
          </div>
          <div className="chart-subtitle">
            Slide a raw fusion score to see its calibrated probability via the real corrector
          </div>
        </div>
      </div>

      <div className="simulator-body">
        <div className="slider-group">
          <div className="slider-label">
            <span>Raw fusion score</span>
            <span>{rawScore.toFixed(3)}</span>
          </div>
          <input
            id="score-slider"
            type="range"
            min="0"
            max="1"
            step="0.001"
            value={rawScore}
            onChange={handleSlider}
            aria-label="Raw fusion score"
            aria-valuemin={0}
            aria-valuemax={1}
            aria-valuenow={rawScore}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-muted)' }}>
            <span>0.0 — Normal</span>
            <span>1.0 — Anomaly</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 6, lineHeight: 1.5 }}>
            Input must use <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>evaluate_models.py</code> min-max normalization,
            not <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>fusion.py</code>'s fixed-range clip —
            these produce different score distributions. The corrector was fit on the former.
          </div>

          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 6 }}>Corrector method</div>
            <div className="method-selector" role="group" aria-label="Calibration method">
              <button
                className={`method-btn${method === 'platt' ? ' active-platt' : ''}`}
                onClick={() => handleMethod('platt')}
                aria-pressed={method === 'platt'}
              >
                Platt
              </button>
              <button
                className={`method-btn${method === 'isotonic' ? ' active-isotonic' : ''}`}
                onClick={() => handleMethod('isotonic')}
                aria-pressed={method === 'isotonic'}
              >
                Isotonic
              </button>
            </div>
          </div>

          {error && (
            <div className="score-error" role="alert">
              Error: {error}
            </div>
          )}
        </div>

        <div className="score-result" aria-live="polite" aria-label="Calibrated probability result">
          <div className="score-result-label">Calibrated probability</div>
          <div
            className="score-result-value"
            style={{
              color: result != null
                ? result > 0.65 ? '#ef4444' : result > 0.35 ? '#f59e0b' : '#10b981'
                : 'var(--color-text-secondary)',
            }}
          >
            {resultDisplay}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
            via {method} corrector
          </div>
          <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>
            raw: {rawScore.toFixed(3)}
          </div>
        </div>
      </div>
    </section>
  )
}
