export const STATUS = {
  Normal: { label: "ปกติ", color: "#3fe0a0", hint: "ตาเปิด หรือปิดไม่เกิน 1 วินาที" },
  Warning: { label: "เตือน", color: "#ffb54a", hint: "ตาปิดต่อเนื่องตั้งแต่ 1 วินาที" },
  Danger: { label: "อันตราย", color: "#ff5a73", hint: "ตาปิดต่อเนื่องเกิน 2 วินาที" },
  NoFace: { label: "ไม่พบใบหน้า", color: "#8fa1c4", hint: "หันหน้าเข้าหากล้อง" },
  Idle: { label: "ยังไม่เริ่ม", color: "#243763", hint: "กดเปิดกล้องเพื่อเริ่มตรวจจับ" },
};

export const MODEL_COLORS = { custom_cnn: "#5b8cff", mobilenetv2: "#3fe0a0", resnet50: "#ffb54a" };

export const pct = (v) => (v == null ? "-" : `${(v * 100).toFixed(2)}%`);
