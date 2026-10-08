"use client";
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer } from "recharts";
import Panel, { Notice } from "@/components/Panel";
import { getModels } from "@/lib/api";
import { MODEL_COLORS, pct } from "@/lib/status";

const METRICS = [
  ["accuracy", "Accuracy"],
  ["precision", "Precision"],
  ["recall", "Recall"],
  ["f1", "F1"],
];

export default function Compare() {
  const [models, setModels] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getModels().then(setModels).catch(() => setError("เชื่อมต่อ backend ไม่ได้ ตรวจว่ารัน uvicorn ที่พอร์ต 8000 แล้ว"));
  }, []);

  const trained = (models || []).filter((m) => m.metrics);
  const chartData = METRICS.map(([k, label]) => {
    const row = { metric: label };
    trained.forEach((m) => (row[m.name] = m.metrics.test[k]));
    return row;
  });
  const ds = trained[0]?.metrics.dataset;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <h1 className="text-2xl font-semibold">เปรียบเทียบโมเดล</h1>
        <p className="mt-1 text-sm text-mute">
          ทุกโมเดลใช้ dataset และ split เดียวกัน (แบ่งตามบุคคล 70/15/15) ค่าทั้งหมดมาจากการวัดบน test set จริง คลาสบวก = ตาปิด
        </p>
      </header>

      {error && <Notice tone="error">{error}</Notice>}
      {models && trained.length === 0 && (
        <Notice>ยังไม่มีผลการเทรน รัน <code>python ml/train.py --data data/mrl</code> แล้วรีเฟรชหน้านี้</Notice>
      )}

      {trained.length > 0 && (
        <>
          <Panel title="คะแนนบน test set">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#18264a" vertical={false} />
                  <XAxis dataKey="metric" stroke="#8fa1c4" />
                  <YAxis domain={[0, 1]} stroke="#8fa1c4" tickFormatter={(v) => `${v * 100}%`} />
                  <Tooltip
                    contentStyle={{ background: "#101b33", border: "1px solid #243763", borderRadius: 8 }}
                    formatter={(v, n) => [pct(v), trained.find((m) => m.name === n)?.label || n]}
                  />
                  <Legend formatter={(n) => trained.find((m) => m.name === n)?.label || n} />
                  {trained.map((m) => (
                    <Bar key={m.name} dataKey={m.name} fill={MODEL_COLORS[m.name]} radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel title="ตารางเปรียบเทียบ">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-mute">
                  <tr className="border-b border-navy-700">
                    {["โมเดล", "Accuracy", "Precision", "Recall", "F1", "AUC", "Acc (webcam จริง)", "พารามิเตอร์", "ขนาดไฟล์", "เวลา/ภาพ"].map((h) => (
                      <th key={h} className="px-3 py-2 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {trained.map((m) => (
                    <tr key={m.name} className="border-b border-navy-800">
                      <td className="px-3 py-3 font-medium">
                        <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: MODEL_COLORS[m.name] }} />
                        {m.label}
                      </td>
                      <td className="px-3 py-3">{pct(m.metrics.test.accuracy)}</td>
                      <td className="px-3 py-3">{pct(m.metrics.test.precision)}</td>
                      <td className="px-3 py-3">{pct(m.metrics.test.recall)}</td>
                      <td className="px-3 py-3">{pct(m.metrics.test.f1)}</td>
                      <td className="px-3 py-3">{m.metrics.test.auc == null ? "-" : m.metrics.test.auc.toFixed(4)}</td>
                      <td className="px-3 py-3">{m.webcam ? `${pct(m.webcam.accuracy)} (n=${m.webcam.n})` : "ยังไม่ได้วัด"}</td>
                      <td className="px-3 py-3">{(m.metrics.params / 1e6).toFixed(2)}M</td>
                      <td className="px-3 py-3">{m.metrics.size_mb} MB</td>
                      <td className="px-3 py-3">{m.metrics.latency_ms} ms ({m.metrics.device})</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-mute">
              {ds && `train ${ds.train.toLocaleString()} / val ${ds.val.toLocaleString()} / test ${ds.test.toLocaleString()} ภาพ. `}
              ช่อง Acc (webcam จริง) มาจากภาพตาที่เก็บเอง รันด้วย <code>python ml/evaluate_folder.py</code> ถ้าต่ำกว่า test set ปกติมาก แปลว่ามี domain gap
            </p>
          </Panel>
        </>
      )}
    </div>
  );
}
