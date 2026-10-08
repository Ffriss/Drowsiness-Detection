"use client";
import { useEffect, useState } from "react";
import { RotateCcw, Save, SlidersHorizontal } from "lucide-react";
import Panel from "@/components/Panel";
import { getSettings, resetSettings, saveSettings } from "@/lib/api";

const GROUPS = [
  {
    title: "ตาปิด",
    fields: [
      { key: "eye_warn", label: "เตือนเมื่อตาปิดนาน", unit: "วินาที", step: 0.1 },
      { key: "eye_danger", label: "อันตรายเมื่อตาปิดนาน", unit: "วินาที", step: 0.1 },
    ],
  },
  {
    title: "หันหน้า",
    fields: [
      { key: "yaw_limit", label: "นับว่าไม่มองถนนเมื่อหันเกิน", unit: "องศา", step: 1 },
      { key: "yaw_return", label: "กลับเป็นปกติเมื่อหันไม่เกิน", unit: "องศา", step: 1 },
      { key: "distract_warn", label: "เตือนเมื่อไม่มองถนนนาน", unit: "วินาที", step: 0.1 },
      { key: "distract_danger", label: "อันตรายเมื่อไม่มองถนนนาน", unit: "วินาที", step: 0.1 },
    ],
  },
];

function NumberField({ field, value, limits, onChange }) {
  const [lo, hi] = limits?.[field.key] || [0, 100];
  const id = `set-${field.key}`;
  return (
    <div>
      <label htmlFor={id} className="flex items-center justify-between text-sm">
        <span className="text-mute">{field.label}</span>
        <span className="tabular-nums">
          {Number(value).toFixed(field.step < 1 ? 1 : 0)} {field.unit}
        </span>
      </label>
      <input
        id={id}
        type="range"
        min={lo}
        max={hi}
        step={field.step}
        value={value}
        onChange={(e) => onChange(field.key, Number(e.target.value))}
        className="mt-1 w-full accent-[#5b8cff]"
      />
    </div>
  );
}

export default function SettingsPanel({ model, modelLabel }) {
  const [data, setData] = useState(null);
  const [form, setForm] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const apply = (d) => {
    setData(d);
    setForm({ ...d, thresholds: { ...d.thresholds } });
  };

  useEffect(() => {
    getSettings().then(apply).catch(() => setMsg("โหลดค่าตั้งไม่ได้ ตรวจว่า backend รันอยู่"));
  }, []);

  if (!form) {
    return (
      <Panel title="ตั้งค่าการแจ้งเตือน">
        <p className="text-sm text-mute">{msg || "กำลังโหลด..."}</p>
      </Panel>
    );
  }

  const fileThr = data.model_thresholds?.[model];
  const customThr = form.thresholds[model];
  const thrValue = customThr ?? fileThr ?? 0.5;
  const dirty = JSON.stringify({ ...form, defaults: 0 }) !== JSON.stringify({ ...data, defaults: 0 });

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setThr = (v) => setForm((f) => ({ ...f, thresholds: { ...f.thresholds, [model]: v } }));
  const clearThr = () =>
    setForm((f) => {
      const t = { ...f.thresholds };
      delete t[model];
      return { ...f, thresholds: t };
    });

  const save = async () => {
    setBusy(true);
    setMsg("");
    try {
      const thresholds = { ...form.thresholds };
      Object.keys(data.thresholds).forEach((k) => {
        if (!(k in thresholds)) thresholds[k] = null; // ลบค่าที่ตั้งไว้ -> กลับไปใช้ค่าจากไฟล์
      });
      const patch = { thresholds };
      GROUPS.forEach((g) => g.fields.forEach((f) => (patch[f.key] = form[f.key])));
      apply(await saveSettings(patch));
      setMsg("บันทึกแล้ว มีผลทันทีกับเฟรมถัดไป");
    } catch (e) {
      setMsg(`บันทึกไม่สำเร็จ: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    if (!confirm("คืนค่าทั้งหมดเป็นค่าเริ่มต้น?")) return;
    setBusy(true);
    try {
      apply(await resetSettings());
      setMsg("คืนค่าเริ่มต้นแล้ว");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" aria-hidden /> ตั้งค่าการแจ้งเตือน
        </span>
      }
      right={
        <div className="flex gap-2">
          <button
            onClick={reset}
            disabled={busy}
            className="flex items-center gap-1.5 rounded-lg border border-navy-600 px-3 py-1.5 text-xs text-mute hover:text-ink disabled:opacity-50"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden /> ค่าเริ่มต้น
          </button>
          <button
            onClick={save}
            disabled={busy || !dirty}
            className="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-navy-950 disabled:opacity-40"
          >
            <Save className="h-3.5 w-3.5" aria-hidden /> บันทึก
          </button>
        </div>
      }
    >
      <div className="grid gap-6 md:grid-cols-3">
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Threshold ของ {modelLabel}</h3>
          <div>
            <label htmlFor="set-thr" className="flex items-center justify-between text-sm">
              <span className="text-mute">นับว่าตาปิดเมื่อ P(closed) ตั้งแต่</span>
              <span className="tabular-nums">{thrValue.toFixed(2)}</span>
            </label>
            <input
              id="set-thr"
              type="range"
              min={0.01}
              max={0.99}
              step={0.01}
              value={thrValue}
              onChange={(e) => setThr(Number(e.target.value))}
              className="mt-1 w-full accent-[#5b8cff]"
            />
          </div>
          <p className="text-xs text-mute">
            ค่าจากไฟล์โมเดล: {fileThr ?? "-"}
            {customThr != null && (
              <button onClick={clearThr} className="ml-2 text-accent underline-offset-2 hover:underline">
                ใช้ค่าจากไฟล์
              </button>
            )}
          </p>
          <p className="text-xs text-mute">
            ค่าที่ตั้งตรงนี้ใช้ตอนตรวจจับเท่านั้น ไม่เปลี่ยนตัวเลขในหน้าเปรียบเทียบโมเดล
          </p>
        </div>
        {GROUPS.map((g) => (
          <div key={g.title} className="space-y-3">
            <h3 className="text-sm font-medium">{g.title}</h3>
            {g.fields.map((f) => (
              <NumberField key={f.key} field={f} value={form[f.key]} limits={data.limits} onChange={setField} />
            ))}
          </div>
        ))}
      </div>
      {msg && <p className="mt-4 text-sm text-mute">{msg}</p>}
    </Panel>
  );
}
