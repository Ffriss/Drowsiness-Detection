"use client";
import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Trash2 } from "lucide-react";
import Panel, { Notice } from "@/components/Panel";
import { clearHistory, getHistory, getStats } from "@/lib/api";
import { STATUS } from "@/lib/status";

const LABELS = { custom_cnn: "CNN", mobilenetv2: "MobileNetV2", resnet50: "ResNet50", mobilenetv2_scratch: "MobileNetV2 (scratch)" };
const REASONS = { eyes: "ตาปิด", distracted: "ไม่มองถนน" };

export default function HistoryPage() {
  const [events, setEvents] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    Promise.all([getHistory(200), getStats()])
      .then(([e, s]) => { setEvents(e); setStats(s); })
      .catch(() => setError("เชื่อมต่อ backend ไม่ได้ ตรวจว่ารัน uvicorn ที่พอร์ต 8000 แล้ว"));
  }, []);

  useEffect(load, [load]);

  const onClear = async () => {
    if (!confirm("ลบประวัติทั้งหมด? การลบนี้ย้อนกลับไม่ได้")) return;
    await clearHistory();
    load();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">ประวัติการแจ้งเตือน</h1>
          <p className="mt-1 text-sm text-mute">บันทึกทุกครั้งที่สถานะเปลี่ยนเป็นเตือนหรืออันตราย</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-2 rounded-lg border border-navy-600 px-3 py-2 text-sm text-mute hover:text-ink">
            <RefreshCw className="h-4 w-4" aria-hidden /> รีเฟรช
          </button>
          <button onClick={onClear} className="flex items-center gap-2 rounded-lg border border-danger/50 px-3 py-2 text-sm text-danger hover:bg-danger/10">
            <Trash2 className="h-4 w-4" aria-hidden /> ลบประวัติ
          </button>
        </div>
      </header>

      {error && <Notice tone="error">{error}</Notice>}

      {stats && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {[["เหตุการณ์ทั้งหมด", stats.total, ""], ["เตือน", stats.warnings, "text-warn"], ["อันตราย", stats.dangers, "text-danger"], ["ไม่มองถนน", stats.distracted ?? 0, ""], ["เซสชัน", stats.sessions, ""]].map(([k, v, c]) => (
            <Panel key={k}>
              <div className={`text-sm ${c || "text-mute"}`}>{k}</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums">{v}</div>
            </Panel>
          ))}
        </div>
      )}

      {stats?.by_model?.length > 0 && (
        <Panel title="แยกตามโมเดล">
          <ul className="grid gap-2 text-sm sm:grid-cols-3">
            {stats.by_model.map((m) => (
              <li key={m.model} className="rounded-lg bg-navy-800 px-3 py-2">
                <span className="font-medium">{LABELS[m.model] || m.model}</span>
                <span className="ml-2 text-warn">เตือน {m.warnings}</span>
                <span className="ml-2 text-danger">อันตราย {m.dangers}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel title="เหตุการณ์ล่าสุด (สูงสุด 200 รายการ)">
        {events && events.length === 0 ? (
          <p className="text-sm text-mute">ยังไม่มีเหตุการณ์ เปิดกล้องที่หน้า Dashboard แล้วลองหลับตาหรือหันหน้านาน ๆ ดู</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-mute">
                <tr className="border-b border-navy-700">
                  {["เวลา", "โมเดล", "สถานะ", "สาเหตุ", "นาน (วินาที)", "P(closed)", "มุมหัน", "เซสชัน"].map((h) => (
                    <th key={h} className="px-3 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {(events || []).map((e) => (
                  <tr key={e.id} className="border-b border-navy-800">
                    <td className="px-3 py-2">{new Date(e.ts).toLocaleString("th-TH")}</td>
                    <td className="px-3 py-2">{LABELS[e.model] || e.model}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: `${STATUS[e.status]?.color}26`, color: STATUS[e.status]?.color }}>
                        {STATUS[e.status]?.label || e.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">{REASONS[e.reason] || "ตาปิด"}</td>
                    <td className="px-3 py-2">{e.closed_seconds.toFixed(1)}</td>
                    <td className="px-3 py-2">{e.p_closed == null ? "-" : e.p_closed.toFixed(3)}</td>
                    <td className="px-3 py-2">{e.yaw == null ? "-" : `${e.yaw > 0 ? "ซ้าย" : "ขวา"} ${Math.abs(e.yaw).toFixed(0)}°`}</td>
                    <td className="px-3 py-2 text-mute">{e.session_id.slice(0, 8)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
