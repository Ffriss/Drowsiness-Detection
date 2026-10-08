export default function ConfusionMatrix({ cm }) {
  // cm = [[TN, FP], [FN, TP]] ; แถว = ค่าจริง, คอลัมน์ = ที่ทำนาย ; 0 = ตาเปิด, 1 = ตาปิด
  const rows = [
    { label: "จริง: ตาเปิด", cells: cm[0], good: 0 },
    { label: "จริง: ตาปิด", cells: cm[1], good: 1 },
  ];
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-1.5 text-sm">
      <div />
      <div className="px-2 pb-1 text-center text-xs text-mute">ทำนาย: ตาเปิด</div>
      <div className="px-2 pb-1 text-center text-xs text-mute">ทำนาย: ตาปิด</div>
      {rows.map((r, ri) => {
        const total = r.cells[0] + r.cells[1] || 1;
        return [
          <div key={`l${ri}`} className="flex items-center pr-2 text-xs text-mute">{r.label}</div>,
          ...r.cells.map((v, ci) => {
            const ok = ci === r.good;
            const a = 0.15 + 0.6 * (v / total);
            return (
              <div
                key={`${ri}${ci}`}
                className="grid place-items-center rounded-lg py-5"
                style={{ background: ok ? `rgba(63,224,160,${a})` : `rgba(255,90,115,${a})` }}
              >
                <span className="text-xl font-semibold tabular-nums">{v.toLocaleString()}</span>
                <span className="text-xs text-ink/80">{((v / total) * 100).toFixed(1)}% ของแถว</span>
              </div>
            );
          }),
        ];
      })}
    </div>
  );
}
