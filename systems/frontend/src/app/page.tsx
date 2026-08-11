"use client";

import React, { useState } from "react";

interface Prediction {
  failure_probability: number;
  failure_type: string;
  confidence: number;
  prediction_timestamp: string;
  shap?: Record<string, number>;
}

interface TrainResult {
  mappings: Record<string, any>;
  capabilities: Record<string, boolean>;
  registry: {
    trained_at: string;
    models: Record<string, { path: string, train_positive_rate: number }>;
  };
}

export default function Dashboard() {
  const [loading, setLoading] = useState(false);
  const [forceReanalyze, setForceReanalyze] = useState(false);
  const [trainData, setTrainData] = useState<TrainResult | null>(null);
  const [predictions, setPredictions] = useState<Record<string, Prediction> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runTrain = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data_dir: "data", force_reanalyze: forceReanalyze }),
      });
      if (!res.ok) throw new Error("학습(Train) API 호출 실패");
      const data = await res.json();
      setTrainData(data);
      setPredictions(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runPredict = async () => {
    setLoading(true);
    setError(null);
    try {
      // 샘플 텔레메트리 데이터 20건 로드
      const sampleRes = await fetch("http://localhost:8000/api/sample-telemetry?n=20");
      if (!sampleRes.ok) throw new Error("샘플 데이터 로드 실패");
      const { rows } = await sampleRes.json();

      const res = await fetch("http://localhost:8000/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows }),
      });
      if (!res.ok) throw new Error("예측(Predict) API 호출 실패");
      const data = await res.json();
      setPredictions(data.predictions);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <header style={{ marginBottom: "40px", textAlign: "center" }}>
        <h1 style={{ fontSize: "2.5rem", background: "linear-gradient(90deg, #58a6ff, #9b59b6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Environment Adaptive Manufacturing Ontology Platform (v3)
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", marginTop: "12px" }}>
          Extraction Agent(구조 판단 + 컬럼 선택)와 Model Registry가 결합된 예지보전 플랫폼입니다.
        </p>
      </header>

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", marginBottom: "48px" }}>
        <div style={{ display: "flex", gap: "24px", justifyContent: "center" }}>
          <button className="btn-primary" onClick={runTrain} disabled={loading}>
            {loading ? <div className="spinner" /> : "🚀 1. Extraction & 전체 모델 학습 (Train All)"}
          </button>
          <button 
            className="btn-primary" 
            style={{ background: trainData ? "linear-gradient(135deg, #2ea043 0%, #3fb950 100%)" : "rgba(48,54,61,0.5)", cursor: trainData ? "pointer" : "not-allowed" }}
            onClick={runPredict} 
            disabled={loading || !trainData}
          >
            {loading ? <div className="spinner" /> : "⚡ 2. 실시간 3개 모델 예측 (Predict)"}
          </button>
        </div>

        <label style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.95rem" }}>
          <input 
            type="checkbox" 
            checked={forceReanalyze} 
            onChange={(e) => setForceReanalyze(e.target.checked)}
            style={{ accentColor: "var(--accent-color)", width: "16px", height: "16px" }}
          />
          🔄 파싱 캐시 무시 및 강제 재분석 (Force Reanalyze)
        </label>
      </div>

      {error && <div style={{ color: "var(--danger-color)", textAlign: "center", marginBottom: "24px" }}>{error}</div>}

      {/* 예측 결과 (모델 3종 나란히 배치) */}
      {predictions && (
        <section style={{ marginBottom: "48px" }}>
          <h2 style={{ fontSize: "1.5rem", textAlign: "center", marginBottom: "24px" }}>Real-time Prediction Results</h2>
          <div className="grid">
            {Object.entries(predictions).map(([modelName, pred]) => {
              const isDanger = pred.failure_probability > 0.5;
              return (
                <div key={modelName} className="glass-panel" style={{ textAlign: "center", border: isDanger ? "1px solid rgba(248, 81, 73, 0.5)" : "" }}>
                  <h3 style={{ textTransform: "uppercase", color: "var(--accent-color)", fontSize: "1.1rem" }}>{modelName}</h3>
                  <div className="metric-label">고장 확률</div>
                  <div className="metric-value" style={{ color: isDanger ? "var(--danger-color)" : "inherit" }}>
                    {(pred.failure_probability * 100).toFixed(1)}%
                  </div>
                  <div style={{ marginTop: "16px", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                    신뢰도: {(pred.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 학습 결과 메타데이터 */}
      {trainData && (
        <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
          
          <section className="glass-panel">
            <h2>Model Registry (Trained Models)</h2>
            <p style={{ color: "var(--text-muted)", marginBottom: "16px" }}>학습 시간: {new Date(trainData.registry.trained_at).toLocaleString()}</p>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {Object.keys(trainData.registry.models).map((m) => (
                <span key={m} className="badge success">{m} v1.0</span>
              ))}
            </div>
          </section>

          <section className="glass-panel">
            <h2>Ontology Mapping Status (Cache Applied)</h2>
            <div style={{ overflowX: "auto" }}>
              <table className="glass-table">
                <thead>
                  <tr>
                    <th>원본 필드</th>
                    <th>매핑된 노드</th>
                    <th>출처 (Cache/LLM)</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.values(trainData.mappings).map((mapping, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{mapping.source_field}</td>
                      <td style={{ color: "var(--accent-color)" }}>{mapping.target_ontology}</td>
                      <td>{mapping.source}</td>
                      <td>
                        <span className={`badge ${mapping.status === "confirmed" ? "success" : "pending"}`}>
                          {mapping.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="glass-panel">
            <h2>Capability Detection</h2>
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {Object.entries(trainData.capabilities).map(([cap, isActive]) => (
                <div
                  key={cap}
                  style={{
                    padding: "12px 20px",
                    borderRadius: "12px",
                    background: isActive ? "rgba(46, 160, 67, 0.15)" : "rgba(48, 54, 61, 0.4)",
                    border: `1px solid ${isActive ? "rgba(46, 160, 67, 0.3)" : "var(--card-border)"}`,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span style={{ color: isActive ? "var(--success-color)" : "var(--text-muted)" }}>
                    {isActive ? "✓" : "✗"}
                  </span>
                  <span style={{ color: isActive ? "#fff" : "var(--text-muted)", fontWeight: 500 }}>
                    {cap}
                  </span>
                </div>
              ))}
            </div>
          </section>
          
        </div>
      )}
    </main>
  );
}
