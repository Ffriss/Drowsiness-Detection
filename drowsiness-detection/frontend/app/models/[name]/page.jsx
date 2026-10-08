"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer } from "recharts";
import Panel, { Notice } from "@/components/Panel";
import ConfusionMatrix from "@/components/ConfusionMatrix";
import { getModel } from "@/lib/api";
import { MODEL_COLORS, pct } from "@/lib/status";

const tip = { background: "#101b33", border: "1px solid #243763", borderRadius: 8 };

function Curve({ data, a, b, title }) {
  return (
    <Panel title={title}>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#18264a" vertical={false} />
            <XAxis dataKey="epoch" stroke="#8fa1c4" />
            <YAxis stroke="#8fa1c4" />
            <Tooltip contentStyle={tip} />
            <Legend />
            <Line type="monotone" dataKey={a[0]} name={a[1]} stroke="#5b8cff" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey={b[0]} name={b[1]} stroke="#ffb54a" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export default function ModelDetail() {
  const { name } = useParams();
  const [m, setM] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setM(null);
    getModel(name).then(setM).catch(() => setError("เชื่อมต่อ backend ไม่ได้ หรือไม่พบโมเดลนี้"));
  }, [name]);

  if (error) return <Notice tone="error">{error}</Notice>;
  if (!m) return <p className="text-sm text-mute">กำลังโหลด...</p>;

  const x = m.metrics;
  const curve = x ? x.history.loss.map((_, i) => ({
    epoch: i + 1,
    loss: x.history.loss[i], val_loss: x.history.val_loss[i],
    accuracy: x.history.accuracy[i], val_accuracy: x.history.val_accuracy[i],
  })) : [];

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header className="flex items-center gap-3">
        <span className="h-3 w-3 rounded-full" style={{ background: MODEL_COLORS[m.name] }} />
        <h1 className="text-2xl font-semibold">{m.label}</h1>
      </header>

      {!x && (
        <Notice>ยังไม่ได้เทรนโมเดลนี้ รัน <code>python ml/train.py --models {m.name}</code> แล้วรีเฟรชหน้านี้</Notice>
      )}

      {x && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[["Accuracy", x.test.accuracy], ["Precision", x.test.precision], ["Recall", x.test.recall], ["F1", x.test.f1]].map(([k, v]) => (
              <Panel key={k}>
                <div className="text-sm text-mute">{k}</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums">{pct(v)}</div>
              </Panel>
            ))}
            <Panel>
              <div className="text-sm text-mute">AUC</div>
              <div className="mt-1 text-2xl font-semibold tabular-nums">{x.test.auc == null ? "-" : x.test.auc.toFixed(4)}</div>
            </Panel>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title={`Confusion matrix บน test set (${x.test.n.toLocaleString()} ภาพ)`}>
              <ConfusionMatrix cm={x.test.confusion_matrix} />
            </Panel>
            <Panel title="รายละเอียดการเทรน">
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
                <dt className="text-mute">พารามิเตอร์</dt><dd className="tabular-nums">{x.params.toLocaleString()}</dd>
                <dt className="text-mute">ขนาดไฟล์โมเดล</dt><dd>{x.size_mb} MB</dd>
                <dt className="text-mute">เวลาต่อภาพ</dt><dd>{x.latency_ms} ms ({x.device})</dd>
                <dt className="text-mute">Threshold</dt><dd>{x.threshold} (เลือกจาก validation)</dd>
                <dt className="text-mute">จำนวน epoch</dt><dd>{x.epochs_trained}</dd>
                <dt className="text-mute">ข้อมูล</dt>
                <dd>train {x.dataset.train.toLocaleString()} / val {x.dataset.val.toLocaleString()} / test {x.dataset.test.toLocaleString()}</dd>
                {x.test_glasses && (<><dt className="text-mute">ใส่แว่น</dt><dd>acc {pct(x.test_glasses.accuracy)} (n={x.test_glasses.n.toLocaleString()})</dd></>)}
                {x.test_no_glasses && (<><dt className="text-mute">ไม่ใส่แว่น</dt><dd>acc {pct(x.test_no_glasses.accuracy)} (n={x.test_no_glasses.n.toLocaleString()})</dd></>)}
                <dt className="text-mute">webcam จริง</dt>
                <dd>{m.webcam ? `acc ${pct(m.webcam.accuracy)}, recall ${pct(m.webcam.recall)} (n=${m.webcam.n})` : "ยังไม่ได้วัด"}</dd>
              </dl>
            </Panel>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Curve data={curve} title="Loss" a={["loss", "train"]} b={["val_loss", "validation"]} />
            <Curve data={curve} title="Accuracy" a={["accuracy", "train"]} b={["val_accuracy", "validation"]} />
          </div>
        </>
      )}
    </div>
  );
}
