import { useEffect, useState } from "react";

type StatusData = {
  status: string;
  training_data: string;
  train_samples: number;
  val_samples: number;
  test_samples: number;
  epochs_trained?: number;
  note: string;
};

export default function Screen6Performance({ isDark: _isDark }: { isDark: boolean }) {
  const [status, setStatus] = useState<StatusData | null>(null);

  useEffect(() => {
    // Check for docs/verification.json first, then fallback to docs/status.json
    fetch("/docs/verification.json")
      .then((res) => (res.ok ? res.json() : fetch("/docs/status.json").then((r) => r.json())))
      .then((data) => setStatus(data))
      .catch(() => {
        setStatus({
          status: "Evaluation pending",
          training_data: "1 day (2026-08-19)",
          train_samples: 25,
          val_samples: 20,
          test_samples: 0,
          epochs_trained: 92,
          note: "Model is a pipeline prototype. Outputs are uncalibrated and not validated for real alerts.",
        });
      });
  }, []);

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>SCREEN 6</div>
        <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>
          Forecast Performance
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          Validation Mode · Prototype Status · Lead steps (+15, +30, +60, +120, +180 min)
        </div>
      </div>

      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-dim)",
          borderRadius: 6,
          padding: "24px",
          maxWidth: "800px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              padding: "4px 10px",
              borderRadius: 3,
              background: "color-mix(in srgb, var(--accent) 15%, transparent)",
              color: "var(--accent)",
              border: "1px solid color-mix(in srgb, var(--accent) 30%, transparent)",
              letterSpacing: 0.8,
            }}
          >
            {status?.status ?? "Evaluation Pending"}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Pipeline Proof-of-Concept</span>
        </div>

        <div style={{ fontSize: 13, color: "var(--text-primary)", marginBottom: 20, lineHeight: 1.6 }}>
          {status?.note ??
            "The model is a pipeline proof-of-concept trained on a single-day dataset. Formal metric evaluation on an independent multi-day test set is currently pending."}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "14px" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>TRAINING DATASET</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              {status?.training_data ?? "1 day (2026-08-19)"}
            </div>
          </div>

          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "14px" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>SAMPLE BREAKDOWN</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              {status?.train_samples ?? 25} train / {status?.val_samples ?? 20} val / {status?.test_samples ?? 0} test
            </div>
          </div>

          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "14px" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>CHECKPOINT HISTORY</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              Trained {status?.epochs_trained ?? 92} epochs
            </div>
          </div>

          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "14px" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>HELD-OUT TEST EVALUATION</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 600, color: "var(--wx-mod)" }}>
              Pending (0 test samples)
            </div>
          </div>
        </div>

        <div
          style={{
            padding: "12px 14px",
            background: "color-mix(in srgb, var(--accent) 8%, transparent)",
            border: "1px solid color-mix(in srgb, var(--accent) 20%, transparent)",
            borderRadius: 4,
            fontSize: 11,
            color: "var(--text-secondary)",
            lineHeight: 1.5,
          }}
        >
          <strong>Notice:</strong> Output probabilities are uncalibrated pipeline demonstrations and are not validated for operational forecasting or real alert dispatch.
        </div>
      </div>
    </div>
  );
}
