// planB/frontUI.ts
// Firebase RTDB 실시간 모니터링 + 원격 제어 UI
//
// 의존성:
//   npm install firebase
//
// 사용 전 교체 필요:
//   firebaseConfig 객체 — Firebase 콘솔 > 프로젝트 설정 > 앱 추가 > 웹

import { initializeApp } from "firebase/app";
import { getDatabase, ref, onValue, set, get } from "firebase/database";

// ── Firebase 설정 (TODO: 실제 값으로 교체) ────────────────────────
const firebaseConfig = {
  apiKey:            "TODO_API_KEY",
  authDomain:        "TODO_PROJECT_ID.firebaseapp.com",
  databaseURL:       "https://TODO_PROJECT_ID-default-rtdb.firebaseio.com",
  projectId:         "TODO_PROJECT_ID",
  storageBucket:     "TODO_PROJECT_ID.appspot.com",
  messagingSenderId: "TODO_SENDER_ID",
  appId:             "TODO_APP_ID",
};

// ── RTDB 경로 ─────────────────────────────────────────────────────
const PATH_STATUS   = "acha/status";
const PATH_COMMANDS = "acha/commands";

// ── 타입 정의 ─────────────────────────────────────────────────────
interface BlockData {
  block:   string;
  voltage: number;
  raw:     number;
  level:   0 | 1 | 2;
}

interface StatusData {
  blocks:     Record<string, BlockData>;
  updated_at: number;
}

interface Commands {
  brightness:    number;
  led_override:  number | null;
  alert_enabled: boolean;
}

// ── 상수 ──────────────────────────────────────────────────────────
const LEVEL_LABEL: Record<number, string>  = { 0: "건조", 1: "수막", 2: "고임" };
const LEVEL_COLOR: Record<number, string>  = {
  0: "#e0e0e0",   // 회색 — 건조
  1: "#ffa500",   // 주황 — 수막
  2: "#e53935",   // 적색 — 고임
};
const BLOCK_ORDER = ["0", "1", "2", "3"];   // 2×2 그리드 순서

// ── Firebase 초기화 ───────────────────────────────────────────────
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

// ── 센서 상태 구독 ────────────────────────────────────────────────
export function subscribeStatus(
  callback: (data: StatusData) => void
): () => void {
  const statusRef = ref(database, PATH_STATUS);
  const unsubscribe = onValue(statusRef, (snapshot) => {
    const data = snapshot.val() as StatusData | null;
    if (data) callback(data);
  });
  return unsubscribe;
}

// ── 원격 명령 전송 ────────────────────────────────────────────────
export async function sendBrightness(value: number): Promise<void> {
  const cmd = await _getCommands();
  await set(ref(database, PATH_COMMANDS), { ...cmd, brightness: value });
}

export async function sendLedOverride(level: number | null): Promise<void> {
  const cmd = await _getCommands();
  await set(ref(database, PATH_COMMANDS), { ...cmd, led_override: level });
}

export async function sendAlertEnabled(enabled: boolean): Promise<void> {
  const cmd = await _getCommands();
  await set(ref(database, PATH_COMMANDS), { ...cmd, alert_enabled: enabled });
}

async function _getCommands(): Promise<Commands> {
  const snap = await get(ref(database, PATH_COMMANDS));
  return (snap.val() as Commands) ?? {
    brightness: 128, led_override: null, alert_enabled: true,
  };
}

// ── DOM レンダリング (vanilla TS, 프레임워크 없음) ─────────────────
export function renderDashboard(mountId: string): void {
  const root = document.getElementById(mountId);
  if (!root) return;

  root.innerHTML = _buildHTML();
  _bindControls();

  // 실시간 구독
  subscribeStatus((data) => {
    const ts = new Date(data.updated_at * 1000).toLocaleTimeString("ko-KR");
    const tsEl = document.getElementById("ts-label");
    if (tsEl) tsEl.textContent = `마지막 업데이트: ${ts}`;

    BLOCK_ORDER.forEach((ch) => {
      const block = data.blocks?.[ch];
      if (!block) return;

      const card = document.getElementById(`block-${ch}`);
      if (!card) return;

      card.style.backgroundColor = LEVEL_COLOR[block.level];
      const voltEl  = card.querySelector(".voltage");
      const rawEl   = card.querySelector(".raw");
      const labelEl = card.querySelector(".level-label");
      if (voltEl)  voltEl.textContent  = `${block.voltage.toFixed(4)} V`;
      if (rawEl)   rawEl.textContent   = `raw: ${block.raw}`;
      if (labelEl) labelEl.textContent = LEVEL_LABEL[block.level];
    });
  });
}

function _buildHTML(): string {
  const cards = BLOCK_ORDER.map((ch) => `
    <div id="block-${ch}" class="block-card" style="background:${LEVEL_COLOR[0]}">
      <h3>블록${Number(ch) + 1} (A${ch})</h3>
      <div class="level-label">--</div>
      <div class="voltage">-- V</div>
      <div class="raw">raw: --</div>
    </div>
  `).join("");

  return `
    <div class="dashboard">
      <h2>CPD 타일 낙상방지 — 원격 모니터링</h2>
      <p id="ts-label" style="color:#888">연결 대기 중...</p>

      <div class="grid-2x2">${cards}</div>

      <div class="controls">
        <label>
          밝기
          <input id="brightness-slider" type="range" min="0" max="255" value="128">
          <span id="brightness-val">128</span>
        </label>

        <fieldset>
          <legend>LED 강제 단계</legend>
          <button data-override="null">자동</button>
          <button data-override="0">건조(백색)</button>
          <button data-override="1">수막(황색)</button>
          <button data-override="2">고임(적색)</button>
        </fieldset>

        <label>
          <input id="alert-toggle" type="checkbox" checked>
          원격 알림 활성화
        </label>
      </div>
    </div>
  `;
}

function _bindControls(): void {
  const slider = document.getElementById("brightness-slider") as HTMLInputElement | null;
  const valSpan = document.getElementById("brightness-val");

  slider?.addEventListener("input", () => {
    if (valSpan) valSpan.textContent = slider.value;
  });
  slider?.addEventListener("change", () => {
    sendBrightness(Number(slider.value));
  });

  document.querySelectorAll<HTMLButtonElement>("[data-override]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const raw = btn.dataset.override;
      const level = raw === "null" ? null : Number(raw);
      sendLedOverride(level);
    });
  });

  const alertToggle = document.getElementById("alert-toggle") as HTMLInputElement | null;
  alertToggle?.addEventListener("change", () => {
    sendAlertEnabled(alertToggle.checked);
  });
}
