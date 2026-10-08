"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Volume2, VolumeX, Timer, Gauge, Compass } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, ReferenceLine, ResponsiveContainer } from "recharts";
import Panel, { Notice } from "@/components/Panel";
import SettingsPanel from "@/components/SettingsPanel";
import { getModels, predictFrame } from "@/lib/api";
import { STATUS } from "@/lib/status";

const INTERVAL_MS = 100; // ~10 FPS

// ค่าบวก = หันซ้ายของผู้ขับ, ค่าลบ = หันขวา (ตาม backend/detector.py)
const yawText = (yaw) =>
  yaw == null ? "-" : Math.abs(yaw) < 5 ? "มองตรง" : `${yaw > 0 ? "หันซ้าย" : "หันขวา"} ${Math.abs(yaw).toFixed(0)}°`;

function statusHint(key, result, running) {
  if (running && !result) return "กำลังเชื่อมต่อ backend...";
  if (result?.reason === "distracted") {
    const side = result.yaw > 0 ? "ซ้าย" : "ขวา";
    if (key === "Danger") return `ไม่มองถนน: หัน${side}นานเกิน 4 วินาที`;
    if (key === "Warning") return `ไม่มองถนน: หัน${side}นานเกิน 2 วินาที`;
    return `กำลังหัน${side} ${Math.abs(result.yaw ?? 0).toFixed(0)}°`;
  }
  return STATUS[key].hint;
}

export default function Dashboard() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const runningRef = useRef(false);
  const sessionRef = useRef("");
  const modelRef = useRef("custom_cnn");
  const soundRef = useRef(true);
  const audioRef = useRef(null);
  const lastBeepRef = useRef(0);
  const lastStatusRef = useRef("Idle");
  const seriesRef = useRef([]);
  const counterRef = useRef(0);

  const [models, setModels] = useState([]);
  const [model, setModel] = useState("custom_cnn");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [series, setSeries] = useState([]);
  const [counts, setCounts] = useState({ frames: 0, warnings: 0, dangers: 0 });
  const [error, setError] = useState("");
  const [sound, setSound] = useState(true);

  useEffect(() => {
    getModels()
      .then((list) => {
        setModels(list);
        const first = list.find((m) => m.ready) || list[0];
        if (first) {
          setModel(first.name);
          modelRef.current = first.name;
        }
      })
      .catch(() => setError("เชื่อมต่อ backend ไม่ได้ ตรวจว่ารัน uvicorn backend.main:app ที่พอร์ต 8000 แล้ว"));
  }, []);

  const beep = () => {
    const ctx = audioRef.current;
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.value = 0.15;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.25);
  };

  const handleResult = (res) => {
    setResult(res);
    counterRef.current += 1;
    seriesRef.current = [...seriesRef.current.slice(-59), { i: counterRef.current, p: res.p_closed }];
    setSeries(seriesRef.current);
    const key = `${res.status}:${res.reason}`;
    const prev = lastStatusRef.current;
    setCounts((c) => ({
      frames: c.frames + 1,
      warnings: c.warnings + (res.status === "Warning" && prev !== key ? 1 : 0),
      dangers: c.dangers + (res.status === "Danger" && prev !== key ? 1 : 0),
    }));
    if (res.status === "Danger" && soundRef.current) {
      const now = Date.now();
      if (now - lastBeepRef.current > 1200) {
        lastBeepRef.current = now;
        beep();
      }
    }
    lastStatusRef.current = key;
  };

  const stop = useCallback(() => {
    runningRef.current = false;
    clearTimeout(timerRef.current);
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    lastStatusRef.current = "Idle";
    setRunning(false);
    setResult(null);
  }, []);

  const tick = useCallback(async () => {
    if (!runningRef.current) return;
    const t0 = performance.now();
    let failed = false;
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && video.readyState >= 2 && video.videoWidth) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.85));
        const res = await predictFrame(blob, modelRef.current, sessionRef.current);
        if (runningRef.current) {
          setError("");
          handleResult(res);
        }
      }
    } catch (e) {
      failed = true;
      setError(e.message);
      if (e.message.includes("ยังไม่ได้เทรน")) {
        stop();
        return;
      }
    }
    if (!runningRef.current) return;
    const wait = failed ? 1000 : Math.max(0, INTERVAL_MS - (performance.now() - t0));
    timerRef.current = setTimeout(tick, wait);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stop]);

  const start = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      audioRef.current = audioRef.current || new (window.AudioContext || window.webkitAudioContext)();
      sessionRef.current = crypto.randomUUID();
      seriesRef.current = [];
      counterRef.current = 0;
      setSeries([]);
      setCounts({ frames: 0, warnings: 0, dangers: 0 });
      lastStatusRef.current = "Normal:null";
      runningRef.current = true;
      setRunning(true);
      tick();
    } catch (e) {
      setError(
        e.name === "NotAllowedError"
          ? "เบราว์เซอร์ไม่ได้รับอนุญาตให้ใช้กล้อง อนุญาตกล้องที่ไอคอนล็อกข้างช่องที่อยู่ แล้วลองใหม่"
          : e.message
      );
    }
  };

  useEffect(() => stop, [stop]);

  const pickModel = (name) => {
    setModel(name);
    modelRef.current = name;
  };
  const toggleSound = () => {
    soundRef.current = !soundRef.current;
    setSound(soundRef.current);
  };

  const key = running && result ? result.status : "Idle";
  const st = STATUS[key];
  const hint = statusHint(key, result, running);
  const distracted = result?.reason === "distracted";
  const seconds = distracted ? result?.distract_seconds ?? 0 : result?.closed_seconds ?? 0;
  const p = result?.p_closed;
  const thr = result?.threshold ?? 0.5;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">ตรวจจับการหลับในและการละสายตา</h1>
          <p className="mt-1 text-sm text-mute">จำแนกตาเปิด/ปิดจากกล้องแบบเรียลไทม์ ตรวจการหันหน้า แล้วตัดสินจากระยะเวลา</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={toggleSound}
            aria-pressed={sound}
            className="flex items-center gap-2 rounded-lg border border-navy-600 px-3 py-2 text-sm text-mute hover:text-ink"
          >
            {sound ? <Volume2 className="h-4 w-4" aria-hidden /> : <VolumeX className="h-4 w-4" aria-hidden />}
            {sound ? "เสียงเตือนเปิด" : "เสียงเตือนปิด"}
          </button>
          {running ? (
            <button onClick={stop} className="flex items-center gap-2 rounded-lg bg-danger px-4 py-2 text-sm font-medium text-navy-950">
              <CameraOff className="h-4 w-4" aria-hidden /> ปิดกล้อง
            </button>
          ) : (
            <button onClick={start} className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-navy-950">
              <Camera className="h-4 w-4" aria-hidden /> เปิดกล้องและเริ่มตรวจจับ
            </button>
          )}
        </div>
      </header>

      {error && <Notice tone="error">{error}</Notice>}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div
          className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-navy-900"
          style={{ boxShadow: `0 0 0 3px ${st.color}, 0 0 48px ${st.color}40` }}
        >
          <video ref={videoRef} playsInline muted className="h-full w-full -scale-x-100 object-cover" />
          <canvas ref={canvasRef} className="hidden" />
          {result?.eye_boxes?.map(([x, y, w, h], i) => (
            <div
              key={i}
              className="absolute rounded-sm border-2"
              style={{
                left: `${(1 - (x + w)) * 100}%`,
                top: `${y * 100}%`,
                width: `${w * 100}%`,
                height: `${h * 100}%`,
                borderColor: st.color,
              }}
            />
          ))}
          {!running && (
            <div className="absolute inset-0 grid place-items-center text-sm text-mute">กล้องยังไม่เปิด</div>
          )}
          {running && result?.yaw != null && (
            <div className="absolute right-4 top-4 flex items-center gap-1.5 rounded-full bg-navy-950/70 px-3 py-1 text-sm">
              <Compass className="h-4 w-4" aria-hidden />
              {yawText(result.yaw)}
            </div>
          )}
          <div className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-navy-950/90 to-transparent p-5">
            <div>
              <div className="text-4xl font-bold leading-none" style={{ color: st.color }}>{st.label}</div>
              <div className="mt-1 text-sm text-ink/80">{hint}</div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-semibold tabular-nums">{seconds.toFixed(1)}</div>
              <div className="text-sm text-ink/80">{distracted ? "วินาทีที่ไม่มองถนน" : "วินาทีที่ตาปิด"}</div>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <Panel title="โมเดล">
            <div role="radiogroup" aria-label="เลือกโมเดล" className="flex flex-col gap-2">
              {(models.length ? models : [{ name: "custom_cnn", label: "CNN", ready: true }]).map((m) => (
                <button
                  key={m.name}
                  role="radio"
                  aria-checked={model === m.name}
                  disabled={!m.ready}
                  onClick={() => pickModel(m.name)}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    model === m.name ? "border-accent bg-navy-700" : "border-navy-600 hover:bg-navy-800"
                  }`}
                >
                  <span>{m.label}</span>
                  <span className="text-xs text-mute">
                    {!m.ready ? "ยังไม่ได้เทรน" : m.metrics ? `F1 ${(m.metrics.test.f1 * 100).toFixed(1)}%` : ""}
                  </span>
                </button>
              ))}
            </div>
          </Panel>

          <Panel
            title="โอกาสที่ตาปิด P(closed)"
            right={<span className="text-sm tabular-nums">{p == null ? "-" : `${(p * 100).toFixed(1)}%`}</span>}
          >
            <div className="relative h-3 overflow-hidden rounded-full bg-navy-700">
              <div className="h-full rounded-full transition-[width] duration-100" style={{ width: `${(p ?? 0) * 100}%`, background: st.color }} />
              <div className="absolute inset-y-0 w-0.5 bg-ink" style={{ left: `${thr * 100}%` }} title={`threshold ${thr}`} />
            </div>
            <div className="mt-1 text-xs text-mute">เส้นขาว = threshold {thr.toFixed(2)}{result && result.threshold_default != null && result.threshold !== result.threshold_default ? " (ตั้งจากหน้าเว็บ)" : ""}</div>
            <div className="mt-3 h-24">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                  <XAxis dataKey="i" hide />
                  <YAxis domain={[0, 1]} hide />
                  <ReferenceLine y={thr} stroke="#8fa1c4" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="p" stroke={st.color} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel title="ภาพที่โมเดลเห็นจริง">
            <div className="grid grid-cols-2 gap-3">
              {["ตาขวา", "ตาซ้าย"].map((label, i) => {
                const src = result?.eye_images?.[i];
                const prob = result?.eye_probs?.[i];
                return (
                  <figure key={label} className="text-center">
                    <div className="mx-auto grid aspect-square w-full max-w-[128px] place-items-center overflow-hidden rounded-lg bg-navy-800">
                      {src ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={src} alt={`ภาพ${label}หลัง preprocess`} className="h-full w-full" style={{ imageRendering: "pixelated" }} />
                      ) : (
                        <span className="text-xs text-mute">-</span>
                      )}
                    </div>
                    <figcaption className="mt-1 text-xs text-mute">
                      {label} {prob == null ? "" : `· ${(prob * 100).toFixed(0)}%`}
                    </figcaption>
                  </figure>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-mute">ขาวดำ + CLAHE ขนาด 64×64 · % = โอกาสที่ตาข้างนั้นปิด</p>
          </Panel>

          <Panel title="เซสชันนี้">
            <dl className="grid grid-cols-3 gap-3 text-center">
              <div>
                <dt className="flex items-center justify-center gap-1 text-xs text-mute"><Gauge className="h-3 w-3" aria-hidden />เฟรม</dt>
                <dd className="text-xl font-semibold tabular-nums">{counts.frames}</dd>
              </div>
              <div>
                <dt className="text-xs text-warn">เตือน</dt>
                <dd className="text-xl font-semibold tabular-nums">{counts.warnings}</dd>
              </div>
              <div>
                <dt className="text-xs text-danger">อันตราย</dt>
                <dd className="text-xl font-semibold tabular-nums">{counts.dangers}</dd>
              </div>
            </dl>
            <div className="mt-3 flex items-center justify-between text-xs text-mute">
              <span className="flex items-center gap-1">
                <Timer className="h-3 w-3" aria-hidden />
                ประมวลผล {result ? `${result.latency_ms} ms/เฟรม` : "-"}
              </span>
              <span className="flex items-center gap-1">
                <Compass className="h-3 w-3" aria-hidden />
                {yawText(result?.yaw)}
              </span>
            </div>
          </Panel>
        </div>
      </div>

      <SettingsPanel model={model} modelLabel={models.find((m) => m.name === model)?.label || model} />
    </div>
  );
}
