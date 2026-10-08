# Driver Drowsiness Detection System Using Deep Learning-Based Eye State Classification

ระบบตรวจจับการหลับในจากกล้อง webcam: จำแนก **ตาเปิด / ตาปิด** ด้วย CNN แล้วตัดสินสถานะจาก **ระยะเวลาที่ตาปิด**
(ปิด 1–2 วินาที = Warning, เกิน 2 วินาที = Danger, ตาเปิด = Normal และรีเซ็ตตัวจับเวลา)

เลือกใช้ได้ 3 โมเดลบน dataset และ split เดียวกัน: **Custom CNN / MobileNetV2 / ResNet50**
ค่า metrics ทั้งหมดในหน้า Dashboard มาจากการวัดบน test set จริงเท่านั้น (ไม่มีตัวเลขสมมติ)

## โครงสร้าง

```
ml/         เตรียมข้อมูล เทรน วัดผล (TensorFlow/Keras)
backend/    FastAPI + MediaPipe + SQLite
frontend/   Next.js + Tailwind + Recharts + Lucide
models/     ไฟล์โมเดล (.keras) และ metrics (.json) ที่ได้จากการเทรน
data/       dataset ที่เตรียมแล้ว และฐานข้อมูล SQLite
```

## ขั้นตอน

### 0) ติดตั้ง (Python 3.10 หรือ 3.11)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1) ดาวน์โหลด MRL Eye Dataset แล้วเตรียมข้อมูล
- ต้นทาง: https://mrl.cs.vsb.cz/eyedataset.html
- Kaggle: https://www.kaggle.com/datasets/imadeddinedjerarda/mrl-eye-dataset

```bash
python ml/prepare_mrl.py --root path/to/mrl-eye-dataset --out data/mrl
```
แบ่ง train/val/test = 70/15/15 **ตามตัวบุคคล** (กัน data leakage) ดูสรุปที่ `data/mrl/split_summary.json`

### 2) เทรนโมเดล
```bash
python ml/train.py --data data/mrl                        # ทั้ง 3 ตัว
python ml/train.py --data data/mrl --models custom_cnn    # ตัวเดียว
python ml/train.py --weights none                         # ไม่ดาวน์โหลด ImageNet weights
```
ได้ `models/<name>.keras` และ `models/<name>_metrics.json` (accuracy, precision, recall, F1, AUC,
confusion matrix, กราฟ loss/accuracy, เวลาต่อภาพ, จำนวนพารามิเตอร์, threshold ที่เลือกจาก validation)
แนะนำให้ใช้ GPU สำหรับ MobileNetV2/ResNet50

### 3) (แนะนำ) วัดผลกับ webcam จริง เพื่อดู domain gap
MRL เป็นภาพ IR แต่งานจริงเป็นภาพสีจาก webcam ผลบน test set ของ MRL อาจดีกว่าการใช้งานจริง
```bash
python ml/collect_webcam.py --person me     # o = บันทึกตาเปิด, c = บันทึกตาปิด, q = ออก
python ml/preview_compare.py                # ดูภาพ MRL เทียบ webcam หลัง preprocess (preview_compare.png)
python ml/evaluate_folder.py                # วัดผลทั้ง 3 โมเดลบนภาพ webcam
```
เก็บอย่างละ 100–200 ภาพ ต่อคน หลายแสง/ใส่-ไม่ใส่แว่น และ **ห้ามนำไปเทรน** ใช้เป็น test set แยกเท่านั้น
ถ้าผลต่ำกว่า MRL test มาก ให้ลองปรับ `margin` ใน `ml/eyecrop.py` หรือเพิ่ม augmentation / ผสม dataset CEW

### 4) รัน backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### 5) รัน frontend (Node.js 18+)
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev          # เปิด http://localhost:3000
```
หน้าที่มี: **Dashboard** (กล้องสด เลือกโมเดล สถานะ กราฟ P(closed)), **เปรียบเทียบโมเดล**,
**รายละเอียดแต่ละโมเดล** (confusion matrix, กราฟการเทรน), **ประวัติ** (SQLite)

## หลักการทำงาน

1. เบราว์เซอร์ส่งเฟรม ~10 FPS ไป `POST /api/predict`
2. MediaPipe Face Mesh หาตาซ้าย/ขวา -> ตัด ROI -> `ml/preprocess.py` (grayscale + CLAHE + 64x64)
3. โมเดลคืน P(closed) ของแต่ละตา -> เฉลี่ย
4. `backend/state.py`: majority vote 5 เฟรม -> กฎเวลา (Normal/Warning/Danger) | ไม่พบใบหน้า = NoFace (ไม่นับเป็นตาปิด)
5. บันทึกเหตุการณ์ Warning/Danger ลง SQLite

ฟังก์ชัน preprocess เป็นไฟล์เดียวกันทั้งตอนเทรนและตอนใช้งานจริง ห้ามแยกเขียนสองที่

## หมายเหตุ

- โปรเจกต์นี้เป็นต้นแบบเพื่อการเรียน ไม่ใช่ระบบความปลอดภัยสำหรับขับขี่จริง
- กล้อง: เบราว์เซอร์อนุญาตให้ใช้กล้องเฉพาะ `localhost` หรือ HTTPS
- CEW (ถ้าจะผสม): https://parnec.nuaa.edu.cn/_upload/tpl/02/db/731/template731/pages/xtan/ClosedEyeDatabases.html
  ใช้เพื่อการวิจัยเท่านั้น (ห้ามใช้เชิงพาณิชย์)
