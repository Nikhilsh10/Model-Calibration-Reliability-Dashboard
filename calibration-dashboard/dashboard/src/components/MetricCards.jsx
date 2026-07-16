import React from 'react'

/**
 * MetricCards
 * Renders ECE, MCE, Brier score cards for raw vs Platt vs Isotonic.
 * All values come directly from the calibration JSON — no client-side computation.
 */

const METHODS = [
  { key: 'raw',      label: 'Raw',      color: 'var(--color-raw)' },
  { key: 'platt',    label: 'Platt',    color: 'var(--color-platt)' },
  { key: 'isotonic', label: 'Isotonic', color: 'var(--color-isotonic)' },
]

const METRICS = [
  { key: 'ece',   label: 'ECE',         help: 'Expected Calibration Error' },
  { key: 'mce',   label: 'MCE',         help: 'Maximum Calibration Error' },
  { key: 'brier', label: 'Brier Score', help: 'Brier Score (lower = better)' },
]

function DeltaBadge({ delta }) {
  if (delta == null) return null
  const improved = delta < 0
  const cls = improved ? 'metric-delta delta-improve' : 'metric-delta delta-regress'
  const sign = delta > 0 ? '+' : ''
  return (
    <span className={cls} title={improved ? 'Improvement' : 'Regression'}>
      {sign}{delta.toFixed(4)}
    </span>
  )
}

export default function MetricCards({ data }) {
  return (
    <section className="metric-section" aria-label="Calibration metrics">
      <div className="section-label">Calibration Metrics</div>
      <div className="metric-grid">
        {METRICS.map(metric => (
          <div key={metric.key} className="metric-card" role="group" aria-label={metric.help}>
            <div className="metric-card-name" title={metric.help}>{metric.label}</div>
            {METHODS.map(method => {
              const val = data[method.key][metric.key]
              const delta = method.key !== 'raw' ? data[method.key][`delta_${metric.key}`] : null
              return (
                <div key={method.key} className="metric-row">
                  <span className="metric-method">
                    <span
                      className="method-dot"
                      style={{ background: method.color }}
                      aria-hidden="true"
                    />
                    {method.label}
                  </span>
                  <span>
                    <span className="metric-value">{val.toFixed(4)}</span>
                    <DeltaBadge delta={delta} />
                  </span>
                </div>
              )
            })}
          </div>
        ))}

        {/* Eval set metadata card */}
        <div className="metric-card">
          <div className="metric-card-name">Eval Set</div>
          <div className="metric-row">
            <span className="metric-method">Samples</span>
            <span className="metric-value">{data.eval_set_size.toLocaleString()}</span>
          </div>
          <div className="metric-row">
            <span className="metric-method">Anomalies</span>
            <span className="metric-value">{data.eval_set_positives}</span>
          </div>
          <div className="metric-row">
            <span className="metric-method">Rate</span>
            <span className="metric-value">
              {((data.eval_set_positives / data.eval_set_size) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-method">Bins</span>
            <span className="metric-value">{data.n_bins}</span>
          </div>
        </div>
      </div>
    </section>
  )
}
