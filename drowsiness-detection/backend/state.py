"""state.py - กฎเวลาตัดสินสถานะ (ไม่ขึ้นกับ TensorFlow ทดสอบแยกได้)

ตาปิด:   ปิดต่อเนื่อง >= EYE_WARN วินาที = Warning, > EYE_DANGER = Danger, ตาเปิด = Normal และรีเซ็ต
         majority vote ใน VOTE_WINDOW เฟรม เพื่อกันการกะพริบตาปกติ
หันหน้า: |yaw| > YAW_LIMIT_DEG เริ่มนับว่าไม่มองถนน, ต้องกลับมา <= YAW_RETURN_DEG ถึงจะปกติ (hysteresis)
         ไม่มองถนนต่อเนื่อง >= DISTRACT_WARN = Warning, > DISTRACT_DANGER = Danger
         ระหว่างหันหน้า ไม่นับเวลาตาปิด (เห็นตาไม่เต็ม ผลไม่แม่น)
ไม่พบใบหน้า: สถานะ NoFace (ไม่นับเป็นตาปิด) รอ NOFACE_GRACE วินาทีก่อนรีเซ็ต
"""
from collections import deque

EYE_WARN = 1.0
EYE_DANGER = 2.0
VOTE_WINDOW = 5
NOFACE_GRACE = 0.5

YAW_LIMIT_DEG = 30      # หันเกินเท่านี้ = เริ่มนับว่าไม่มองถนน
YAW_RETURN_DEG = 20     # ต้องหันกลับมาไม่เกินเท่านี้ถึงจะนับว่ามองถนนแล้ว
DISTRACT_WARN = 2.0     # วินาที
DISTRACT_DANGER = 4.0


def _level(elapsed, warn, danger):
    return "Danger" if elapsed > danger else "Warning" if elapsed >= warn else "Normal"


class DrowsyStateMachine:
    def __init__(self):
        self.votes = deque(maxlen=VOTE_WINDOW)
        self.closed_start = None
        self.distracted = False
        self.distract_start = None
        self.last_face_t = None
        self.last = self._result("NoFace")

    @staticmethod
    def _result(status, reason=None, closed=0.0, distract=0.0, yaw=None, is_closed=False):
        return {"status": status, "reason": reason, "closed_seconds": round(closed, 2),
                "distract_seconds": round(distract, 2), "yaw": yaw, "is_closed": is_closed}

    def _reset_eyes(self):
        self.votes.clear()
        self.closed_start = None

    def update(self, now, p_closed, threshold=0.5, yaw=None, cfg=None):
        """now: วินาที | p_closed: None = ไม่พบใบหน้า | yaw: องศา (None = ไม่ทราบ)
        cfg: dict ค่าที่ตั้งจากหน้าเว็บ (eye_warn, eye_danger, yaw_limit, yaw_return, distract_warn, distract_danger)"""
        c = cfg or {}
        eye_warn, eye_danger = c.get("eye_warn", EYE_WARN), c.get("eye_danger", EYE_DANGER)
        yaw_limit, yaw_return = c.get("yaw_limit", YAW_LIMIT_DEG), c.get("yaw_return", YAW_RETURN_DEG)
        d_warn, d_danger = c.get("distract_warn", DISTRACT_WARN), c.get("distract_danger", DISTRACT_DANGER)
        if p_closed is None:
            if self.last_face_t is not None and now - self.last_face_t <= NOFACE_GRACE:
                return self.last
            self._reset_eyes()
            self.distracted, self.distract_start = False, None
            self.last = self._result("NoFace")
            return self.last

        self.last_face_t = now
        yaw_r = None if yaw is None else round(float(yaw), 1)

        # --- หันหน้า (hysteresis) ---
        if yaw is not None:
            if not self.distracted and abs(yaw) > yaw_limit:
                self.distracted, self.distract_start = True, now
            elif self.distracted and abs(yaw) <= yaw_return:
                self.distracted, self.distract_start = False, None

        if self.distracted:
            self._reset_eyes()  # ไม่นับตาปิดระหว่างหันหน้า
            elapsed = now - self.distract_start
            self.last = self._result(_level(elapsed, d_warn, d_danger), "distracted",
                                     distract=elapsed, yaw=yaw_r)
            return self.last

        # --- ตาปิด ---
        self.votes.append(p_closed >= threshold)
        is_closed = sum(self.votes) * 2 > len(self.votes)
        if not is_closed:
            self.closed_start = None
            self.last = self._result("Normal", yaw=yaw_r)
            return self.last
        if self.closed_start is None:
            self.closed_start = now
        elapsed = now - self.closed_start
        self.last = self._result(_level(elapsed, eye_warn, eye_danger), "eyes",
                                 closed=elapsed, yaw=yaw_r, is_closed=True)
        return self.last
