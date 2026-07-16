import React, { useState, useMemo } from 'react'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer
} from 'recharts'
import { BarChart2 } from 'lucide-react'

/**
 * ReliabilityDiagram
 *
 * Shows predicted probability vs. observed frequency for:
 *   - Raw (uncalibrated) scores — gray-blue dashed
 *   - Platt scaling — teal solid
 *   - Isotonic regression — amber solid
 *   - Perfect calibration diagonal — gray dotted reference
 *
 * Bin count bar underlay is toggled via the overlay button.
 * Color is NOT the only distinguishing signal — line styles differ too.
 */

const CURVE_CONFIG = [
  {
    key: 'raw',
    label: 'Raw (uncalibrated)',
    color: 'var(--color-raw)',
    stroke: '#6b7280',
    strokeDasharray: '5 3',
    strokeWidth: 2,
    dot: false,
  },
  {
    key: 'platt',
    label: 'Platt scaling',
    color: 'var(--color-platt)',
    stroke: '#0d9488',
    strokeDasharray: undefined,
    strokeWidth: 2.5,
    dot: { r: 3, fill: '#0d9488', strokeWidth: 0 },
  },
  {
    key: 'isotonic',
    label: 'Isotonic regression',
    color: 'var(--color-isotonic)',
    stroke: '#d97706',
    strokeDasharray: '2 2',
    strokeWidth: 2.5,
    dot: { r: 3, fill: '#d97706', strokeWidth: 0 },
  },
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--color-surface-2)',
      border: '1px solid var(--color-border-light)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--color-text-muted)', marginBottom: 6 }}>
        Predicted: {label}
      </div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.stroke || p.fill, marginBottom: 3 }}>
          {p.name}: <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
            {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function ReliabilityDiagram({ data }) {
  const [showBinCount, setShowBinCount] = useState(false)

  // Build chart data: one point per bin, merging raw/platt/isotonic
  const chartData = useMemo(() => {
    const rawBins = data.raw.bins
    return rawBins.map((bin, i) => {
      const plattBin = data.platt.bins[i]
      const isoBin = data.isotonic.bins[i]
      const midpoint = ((bin.bin_lower + bin.bin_upper) / 2).toFixed(2)
      return {
        midpoint,
        // Predicted bin center as reference x
        raw_observed: bin.observed_freq,
        platt_observed: plattBin?.observed_freq,
        iso_observed: isoBin?.observed_freq,
        count: bin.count,
        bin_label: `[${bin.bin_lower.toFixed(2)}, ${bin.bin_upper.toFixed(2)})`,
      }
    })
  }, [data])

  const maxCount = Math.max(...chartData.map(d => d.count))

  // Sparse bin warning — any bin with < 30 samples
  const sparseBins = chartData.filter(d => d.count < 30 && d.count > 0)

  return (
    <section className="chart-section">
      <div className="chart-header">
        <div>
          <div className="chart-title" id="diagram-title">Reliability Diagram</div>
          <div className="chart-subtitle">
            Predicted probability vs. observed anomaly frequency per bin
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Legend */}
          <div className="legend" role="list" aria-label="Chart legend">
            {CURVE_CONFIG.map(c => (
              <div key={c.key} className="legend-item" role="listitem">
                <div
                  className={c.strokeDasharray && c.key === 'raw' ? 'legend-line-dashed' : 'legend-line'}
                  style={{
                    background: c.strokeDasharray && c.key !== 'raw' ? undefined : c.stroke,
                    borderTopColor: c.stroke,
                    borderTopStyle: c.strokeDasharray ? 'dashed' : 'solid',
                    height: c.strokeDasharray && c.key !== 'raw' ? 0 : 2,
                    borderTopWidth: 2,
                    width: 20,
                  }}
                  aria-hidden="true"
                />
                {c.label}
              </div>
            ))}
            <div className="legend-item">
              <div style={{
                width: 20, height: 0,
                borderTop: '2px dotted #374151',
              }} aria-hidden="true" />
              Perfect calibration
            </div>
          </div>

          {/* Bin count toggle */}
          <button
            className={`toggle-btn${showBinCount ? ' active' : ''}`}
            onClick={() => setShowBinCount(v => !v)}
            aria-pressed={showBinCount}
            aria-label="Toggle bin sample count overlay"
          >
            <BarChart2 size={13} aria-hidden="true" />
            Bin counts
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart
          data={chartData}
          margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
          aria-label="Reliability diagram showing predicted probability vs observed frequency"
          aria-describedby="diagram-title"
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#222535" vertical={false} />
          <XAxis
            dataKey="midpoint"
            tick={{ fill: '#5c6180', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: '#2e3347' }}
            tickLine={false}
            label={{ value: 'Predicted probability', position: 'insideBottom', offset: -2, fill: '#5c6180', fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: '#5c6180', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: '#2e3347' }}
            tickLine={false}
            label={{ value: 'Observed frequency', angle: -90, position: 'insideLeft', fill: '#5c6180', fontSize: 11 }}
            yAxisId="left"
          />
          {showBinCount && (
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: '#3d4260', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'Count', angle: 90, position: 'insideRight', fill: '#3d4260', fontSize: 10 }}
            />
          )}
          <Tooltip content={<CustomTooltip />} />

          {/* Perfect calibration diagonal */}
          <ReferenceLine
            yAxisId="left"
            segment={[{ x: '0.05', y: 0.05 }, { x: '0.95', y: 0.95 }]}
            stroke="#374151"
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />

          {/* Bin count bar underlay */}
          {showBinCount && (
            <Bar
              yAxisId="right"
              dataKey="count"
              name="Bin count"
              fill="var(--color-bin-bar)"
              opacity={0.45}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
          )}

          {/* Calibration curves */}
          <Line
            yAxisId="left"
            dataKey="raw_observed"
            name="Raw"
            stroke="#6b7280"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="left"
            dataKey="platt_observed"
            name="Platt"
            stroke="#0d9488"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#0d9488', strokeWidth: 0 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            yAxisId="left"
            dataKey="iso_observed"
            name="Isotonic"
            stroke="#d97706"
            strokeWidth={2.5}
            strokeDasharray="2 2"
            dot={{ r: 3, fill: '#d97706', strokeWidth: 0 }}
            connectNulls
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {sparseBins.length > 0 && (
        <div className="sparse-notice" role="note">
          Note: {sparseBins.length} bin(s) have fewer than 30 samples.
          Enable "Bin counts" to see which. Treat those curve segments with caution.
        </div>
      )}

      {data.isotonic_overfit_note && (
        <div className="sparse-notice" role="note" style={{ marginTop: 6 }}>
          Isotonic: {data.isotonic_overfit_note}
        </div>
      )}
    </section>
  )
}
