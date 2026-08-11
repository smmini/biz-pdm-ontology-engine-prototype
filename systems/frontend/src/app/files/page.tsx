"use client";

import { useEffect, useState } from "react";

interface FileItem {
  name: string;
  path: string;
  size_bytes: number;
  size_label: string;
  type: string;
  preview: string | null;
  note: string | null;
  oversized_warning: boolean;
}

interface GroupFiles {
  group_label: string;
  files: FileItem[];
}

interface LineageData {
  raw: GroupFiles;
  processed: {
    groups: GroupFiles[];
  };
  scanned_at: string;
}

export default function FilesLineagePage() {
  const [data, setData] = useState<LineageData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchLineageData();
  }, []);

  const fetchLineageData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/files/lineage");
      if (!res.ok) {
        throw new Error(`API response failed with status ${res.status}`);
      }
      const json: LineageData = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || "파일 목록을 불러올 수 없습니다. 백엔드 서버 상태를 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (filePath: string) => {
    setExpandedFiles((prev) => ({
      ...prev,
      [filePath]: !prev[filePath],
    }));
  };

  return (
    <div style={{ backgroundColor: "#0f172a", color: "#f8fafc", minHeight: "100vh", padding: "2rem", fontFamily: "sans-serif" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem", borderBottom: "1px solid #334155", paddingBottom: "1rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "bold", margin: 0, color: "#ffffff" }}>
            📂 원본 & 가공 파일 비교 뷰어 (File Lineage)
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "0.9rem", marginTop: "0.25rem" }}>
            실시간 파일시스템 스캔 결과를 바탕으로 원본 데이터와 가공된 아티팩트를 비교합니다.
          </p>
        </div>
        <button
          onClick={fetchLineageData}
          style={{
            backgroundColor: "#3b82f6",
            color: "#ffffff",
            border: "none",
            borderRadius: "0.375rem",
            padding: "0.5rem 1rem",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          🔄 실시간 새로고침
        </button>
      </div>

      {loading && (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8", fontSize: "1.1rem" }}>
          📡 파일시스템 스캔 진행 중...
        </div>
      )}

      {error && (
        <div style={{ padding: "1.5rem", backgroundColor: "#7f1d1d", border: "1px solid #dc2626", borderRadius: "0.5rem", color: "#fca5a5", marginBottom: "2rem" }}>
          <strong>⚠️ 오류 발생:</strong> {error}
        </div>
      )}

      {data && (
        <>
          <div style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "1.5rem" }}>
            스캔 시각: {new Date(data.scanned_at).toLocaleString("ko-KR")}
          </div>

          {/* 2-Column Grid Layout */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
            {/* Left Column: Origin / Raw (Amber Theme) */}
            <div style={{ backgroundColor: "#1e293b", borderRadius: "0.75rem", padding: "1.5rem", border: "1px solid #78350f" }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
                <span style={{ backgroundColor: "#d97706", color: "#ffffff", padding: "0.25rem 0.75rem", borderRadius: "9999px", fontSize: "0.8rem", fontWeight: "bold", marginRight: "0.75rem" }}>
                  ORIGIN
                </span>
                <h2 style={{ fontSize: "1.25rem", fontWeight: "bold", color: "#fef3c7", margin: 0 }}>
                  {data.raw.group_label}
                </h2>
              </div>

              {data.raw.files.length === 0 ? (
                <div style={{ color: "#64748b", fontSize: "0.9rem" }}>파일이 존재하지 않습니다.</div>
              ) : (
                data.raw.files.map((file) => (
                  <FileCard key={file.path} file={file} theme="amber" isExpanded={!!expandedFiles[file.path]} onToggle={() => toggleExpand(file.path)} />
                ))
              )}
            </div>

            {/* Right Column: Processed (Teal Theme) */}
            <div style={{ backgroundColor: "#1e293b", borderRadius: "0.75rem", padding: "1.5rem", border: "1px solid #134e4a" }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
                <span style={{ backgroundColor: "#0d9488", color: "#ffffff", padding: "0.25rem 0.75rem", borderRadius: "9999px", fontSize: "0.8rem", fontWeight: "bold", marginRight: "0.75rem" }}>
                  PROCESSED
                </span>
                <h2 style={{ fontSize: "1.25rem", fontWeight: "bold", color: "#ccfbf1", margin: 0 }}>
                  가공 완료 아티팩트
                </h2>
              </div>

              {data.processed.groups.map((group, idx) => (
                <div key={idx} style={{ marginBottom: "1.5rem" }}>
                  <h3 style={{ fontSize: "0.95rem", color: "#2dd4bf", margin: "0 0 0.75rem 0", fontWeight: 600 }}>
                    {group.group_label}
                  </h3>
                  {group.files.length === 0 ? (
                    <div style={{ color: "#64748b", fontSize: "0.85rem", marginBottom: "1rem" }}>해당 디렉터리에 파일이 없습니다.</div>
                  ) : (
                    group.files.map((file) => (
                      <FileCard key={file.path} file={file} theme="teal" isExpanded={!!expandedFiles[file.path]} onToggle={() => toggleExpand(file.path)} />
                    ))
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function FileCard({ file, theme, isExpanded, onToggle }: { file: FileItem; theme: "amber" | "teal"; isExpanded: boolean; onToggle: () => void }) {
  const badgeBg = theme === "amber" ? "#b45309" : "#0f766e";
  const cardBorder = isExpanded ? (theme === "amber" ? "#f59e0b" : "#14b8a6") : "#334155";

  return (
    <div style={{ backgroundColor: "#0f172a", borderRadius: "0.5rem", border: `1px solid ${cardBorder}`, marginBottom: "0.75rem", overflow: "hidden", transition: "all 0.2s" }}>
      {/* Title Bar (Accordion Toggle Header) */}
      <div
        onClick={onToggle}
        style={{
          padding: "0.75rem 1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{isExpanded ? "▼" : "▶"}</span>
          <span style={{ fontFamily: "monospace", fontSize: "0.9rem", fontWeight: "bold", color: "#f8fafc" }}>
            {file.name}
          </span>
          <span style={{ fontSize: "0.7rem", backgroundColor: badgeBg, color: "#ffffff", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", textTransform: "uppercase" }}>
            {file.type || "FILE"}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {file.oversized_warning && (
            <span style={{ backgroundColor: "#991b1b", color: "#fca5a5", fontSize: "0.75rem", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", fontWeight: "bold" }}>
              ⚠ 100MB+ 경고
            </span>
          )}
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", backgroundColor: "#1e293b", padding: "0.2rem 0.5rem", borderRadius: "0.25rem" }}>
            {file.size_label}
          </span>
        </div>
      </div>

      {/* Expanded Accordion Body */}
      {isExpanded && (
        <div style={{ borderTop: "1px solid #1e293b", padding: "0.75rem 1rem", backgroundColor: "#020617" }}>
          <div style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "monospace", marginBottom: "0.5rem" }}>
            경로: {file.path}
          </div>

          {file.note && (
            <div style={{ color: "#94a3b8", fontSize: "0.85rem", fontStyle: "italic" }}>
              💡 {file.note}
            </div>
          )}

          {file.preview && (
            <div>
              <div style={{ fontSize: "0.75rem", color: "#475569", marginBottom: "0.25rem", fontWeight: 600 }}>미리보기:</div>
              <pre
                style={{
                  fontFamily: "monospace",
                  fontSize: "0.8rem",
                  color: "#cbd5e1",
                  backgroundColor: "#0f172a",
                  padding: "0.75rem",
                  borderRadius: "0.375rem",
                  overflowX: "auto",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  border: "1px solid #1e293b",
                }}
              >
                {file.preview}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
