// 《聚场》界面：只负责把引擎给的 step 画出来，不自己算任何数。
// 原来这里打 /api/*，现在是本地 TS 引擎（见 app/src/boot.ts），接口形状一样。
import { call } from "./boot.ts";

const $ = (id) => document.getElementById(id);
const api = async (path, body) => {
  const d = await call(path, body);
  if (d && d.error) toast("出了点问题：" + d.error);
  return d;
};

const DETAIL_KEY = "chengchang.detail";

// 数值一律不超过一位小数：失控那一段的炎上/板子是从浮点加上去的，
// 直接拼出来会变成「+90.10000000000001」。
function fmtNum(v) {
  if (typeof v !== "number" || !isFinite(v)) return String(v);
  const n = Math.round(v * 10) / 10;
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/* ---------- 数值 ---------- */
function setNum(el, v) {
  if (!el) return;
  const old = parseInt(el.dataset.v || "NaN", 10);
  el.dataset.v = String(v);
  el.textContent = fmtNum(v);
  if (!isNaN(old) && old !== v) {
    const box = el.closest(".kv");
    if (!box) return;
    box.classList.remove("up", "down");
    void box.offsetWidth;
    box.classList.add(v > old ? "up" : "down");
  }
}

/* ---------- 像素小人 ----------
   玩家自己的形象。立绘是四张 64×80 的六帧精灵图（王道/和风/地雷/摇滚），
   按存档里的 name_style 选一张，按体力/心理/人气挑帧。
   帧序：1 平静微笑 2 闭眼笑 3 张嘴大笑 4 哭 5 累·无语 6 生气·害臊 */
const IDOL_STYLES = ["sweet", "night", "odd", "cool"];
// 剧情线角标配色：私联=红（危险）、重线=紫（压过来）、恋爱=粉
const LINE_TAG_CLASS = { 私联: "line-shiren", 重线: "line-zhong", 恋爱: "line-romance" };
const IDOL_FRAMES = {
  calm: 0,     // 平静微笑
  smile: 1,    // 闭眼笑
  laugh: 2,    // 张嘴大笑
  cry: 3,      // 哭
  tired: 4,    // 累 / 无语
  shy: 5,      // 生气 / 害臊
};
let idolStyle = "";
// 数值算出来的「底帧」和临时插进来的「反应帧」。反应帧过一会儿自己退回底帧。
let idolBaseFrame = 0;
let idolFlash = -1;
let idolFlashTimer = null;

// 帧序号 -> 选哪个表情。体力/心理优先，人气只在不累的时候加分。
function pickFrame(s) {
  const stamina = Number(s.stamina) || 0;
  const psyche = Number(s.psyche) || 0;
  const fame = Number(s.fame) || 0;
  if (stamina < 25) return IDOL_FRAMES.tired;
  if (psyche < 25) return IDOL_FRAMES.cry;
  if (stamina < 40 || psyche < 40) return IDOL_FRAMES.tired;
  if (fame >= 50) return IDOL_FRAMES.smile;
  return IDOL_FRAMES.calm;
}

function applyIdolFrame() {
  const sprite = $("idol-sprite"), box = $("idol");
  if (!sprite) return;
  const frame = idolFlash >= 0 ? idolFlash : idolBaseFrame;
  sprite.style.setProperty("--frame", String(frame));
  if (box) {
    box.dataset.frame = String(frame);
    box.classList.toggle("reacting", idolFlash >= 0);
  }
}

// 这一屏有情绪就临时换一张脸，ms 之后退回数值态。
// 同一屏连着来的几种反应只取第一条，别互相盖掉。
function flashFrame(frame, ms) {
  clearTimeout(idolFlashTimer);
  idolFlash = frame;
  applyIdolFrame();
  idolFlashTimer = setTimeout(() => {
    idolFlash = -1;
    applyIdolFrame();
  }, ms || 2400);
}

// 看这一屏发生了什么，决定要不要插一张脸。优先级从上到下。
// 每屏进来先把上一屏没退完的反应帧清掉：换屏了，那张脸就不属于这一屏了。
function reactToStep(step) {
  if (!step) return;
  if (idolFlash >= 0) {
    clearTimeout(idolFlashTimer);
    idolFlash = -1;
    applyIdolFrame();
  }
  const d = step.delta || {};
  const drop = (k) => Number(d[k] || 0);
  if (step.type === "live") return flashFrame(IDOL_FRAMES.laugh, 2800);
  if (step.type === "end") {
    if (step.ending === "控制不了") return flashFrame(IDOL_FRAMES.cry, 6000);
    return flashFrame(IDOL_FRAMES.smile, 6000);
  }
  if (step.type === "card" && step.recall) return flashFrame(IDOL_FRAMES.shy, 2200);
  if (drop("psyche") <= -8) return flashFrame(IDOL_FRAMES.cry, 2800);
  if (drop("stamina") <= -12) return flashFrame(IDOL_FRAMES.tired, 2600);
  if (drop("fame") >= 5) return flashFrame(IDOL_FRAMES.laugh, 2600);
  if (drop("psyche") >= 8) return flashFrame(IDOL_FRAMES.smile, 2400);
  if (step.type === "chat") return flashFrame(IDOL_FRAMES.smile, 2000);
}

function renderIdol(s) {
  const box = $("idol");
  if (!box) return;
  const name = String((s && s.name) || "").trim();
  if (!name) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  $("idol-name").textContent = name;

  // 旧存档可能没有 name_style（老版本没记这一项），退回王道系
  const style = IDOL_STYLES.includes(s.name_style) ? s.name_style : "sweet";
  const sprite = $("idol-sprite");
  if (style !== idolStyle) {
    sprite.style.backgroundImage = `url(idol_${style}.png)`;
    idolStyle = style;
  }
  const frame = pickFrame(s);
  idolBaseFrame = frame;
  applyIdolFrame();

  const tired = Number(s.stamina) < 35, low = Number(s.psyche) < 35;
  box.classList.toggle("tired", tired);
  box.classList.toggle("low", low);
  box.classList.toggle("shine", Number(s.fame) >= 50);
  $("idol-mood").textContent = tired && low ? "站都站不太稳"
    : low ? "笑不太出来"
    : tired ? "有点撑不住"
    : Number(s.fame) >= 50 ? "台下有人举牌了"
    : "还撑得住";
}

function renderHud(s) {
  if (!s) return;
  renderIdol(s);
  setNum($("v-money"), s.money);
  setNum($("v-stamina"), s.stamina);
  setNum($("v-psyche"), s.psyche);
  setNum($("v-fame"), s.fame);
  $("v-dance").textContent = s.dance;
  $("v-sing").textContent = s.sing;
  $("v-mc").textContent = s.mc;
  $("v-template").textContent = Math.round(s.template * 100) + "%";
  $("v-enjou").textContent = s.enjou;
  $("v-banzi").textContent = s.banzi;
  // 失控时 HUD 顶上会多出这两个数，玩家眼看着它们往 999 走
  if ($("v-enjou2")) setNum($("v-enjou2"), s.enjou);
  if ($("v-banzi2")) setNum($("v-banzi2"), s.banzi);
  $("v-kaibox").textContent = s.kaibox;
  $("v-week").textContent = "第" + s.week + "周";

  const st = s.stats || {};
  const tiers = st.tiers || {}, left = st.left || {};
  for (const k of ["dance", "sing", "mc"]) {
    const el = $("t-" + k);
    if (!el) continue;
    const l = left[k] || 0;
    el.textContent = (tiers[k] || "") + (l ? `　再练 ${l} 点进下一档` : "");
  }
  if ($("d-stats")) {
    const bits = [`说过 ${st.true_talk || 0} 次真话`,
                  `记住她说过的事 ${st.clues || 0} 件`,
                  st.clues_wrong ? `记错 ${st.clues_wrong} 次` : "",
                  st.pushed ? `硬上 ${st.pushed} 次` : "",
                  st.spent_weeks ? `排到身体见底 ${st.spent_weeks} 周` : "",
                  st.rent_missed ? "租子断过" : ""].filter(Boolean);
    $("d-stats").textContent = bits.join("　·　");
  }

  renderOtaTable(s.ota || []);
  $("mate-list").innerHTML = (s.teammates || []).map((m) => `
    <li><span class="nm">${m.name}</span>
    <span class="bar"><i style="width:${Math.max(0, Math.min(100, m.relation))}%"></i></span>
    <span class="st">${m.relation}</span></li>`).join("");
}

/* ---------- 她们：单独一张表 ----------
   只放能看见的东西：认识了几周、有多熟（黏性）、出手有多大方（消费力）。
   不显示「女友粉」「重力系」这种归类——玩家看到的应该是一个人，不是一个标签。 */
const SPEND_WORD = { 0: "只买一张", 1: "很少买", 2: "买得不多", 3: "偶尔多买几张", 4: "出手大方", 5: "出手很大" };

function spendWord(v) {
  const n = Math.max(0, Math.min(5, Math.round(v || 0)));
  return SPEND_WORD[n] || "";
}

function renderOtaTable(list) {
  const box = $("ota-table");
  if (!box) return;
  if (!list.length) {
    box.innerHTML = `<p class="none">还没有人来看过。</p>`;
    return;
  }
  const rows = list.slice().sort((a, b) => (b.stick || 0) - (a.stick || 0)).map((o) => `
    <tr>
      <td class="nm">${o.name}</td>
      <td class="n">${o.weeks > 0 ? o.weeks : "—"}</td>
      <td class="stick"><span class="bar"><i style="width:${Math.max(0, Math.min(100, o.stick))}%"></i></span><b>${o.stick}</b></td>
      <td class="sp">${spendWord(o.spend)}</td>
    </tr>`).join("");
  box.innerHTML = `<table>
    <thead><tr><th>名字</th><th class="n">认识</th><th>黏性</th><th class="sp">出手</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// OTA 面板默认收起（HUD 右边一个小方块）。只记住「玩家主动展开过」这一种状态，
// 没存过就是收起——所以新玩家第一眼不会被一张表挡住正文。
const OTA_FOLD_KEY = "ju-chang.otafold";
function applyOtaFold(folded) {
  const panel = $("ota-panel");
  if (!panel) return;
  panel.classList.toggle("fold", folded);
  const btn = $("ota-fold");
  if (btn) {
    btn.textContent = folded ? "OTA" : "OTA ✕";
    btn.setAttribute("aria-expanded", folded ? "false" : "true");
    btn.title = folded ? "她们（点开）" : "收起";
  }
  localStorage.setItem(OTA_FOLD_KEY, folded ? "1" : "0");
}
if ($("ota-fold")) $("ota-fold").onclick = () => applyOtaFold(!$("ota-panel").classList.contains("fold"));
applyOtaFold(localStorage.getItem(OTA_FOLD_KEY) !== "0");

/* ---------- BGM：随剧情推进换歌（选歌面板在游戏外的 music.html） ---------- */
const BGM_TRACKS = [
  { key: "base",    src: "bgm_1.mp3",     name: "Offline Sedation",       tag: "日常" },
  { key: "god",     src: "bgm_2.mp3",     name: "Digital Coma (1)",       tag: "神场 专属" },
  { key: "romance", src: "bgm_5.mp3",     name: "Digital Rot Lullaby",    tag: "恋爱 专属" },
  { key: "shiren",  src: "bgm_6.mp3",     name: "Sweet Overdose Lullaby", tag: "私联 专属" },
  { key: "noway",   src: "bgm_noway.mp3", name: "无路可退的视线",         tag: "失控 专属" },
  { key: "guanmu",  src: "bgm_guanmu.mp3", name: "棺木生花",              tag: "太爱你 专属" },
];
let bgmAudio = null;
let bgmLastKey = null;
let storyNoway = false;   // 无路可退的视线已起播（失控演出）：之后不再被剧情换歌打断
let storyGuanmu = false;  // 棺木生花已起播（我只是太爱你了结局）：最高优先，不再被打断

function bgmEnsureAudio() {
  if (bgmAudio) return;
  bgmAudio = new Audio();
  bgmAudio.loop = true;
  bgmAudio.volume = 0.7;
}
function bgmPlayTrack(t) {
  if (!t) return;
  bgmEnsureAudio();
  if (bgmAudio.src.endsWith(t.src)) return;
  bgmAudio.src = t.src;
  bgmAudio.play().catch(() => {});
}
function bgmDesired(snap) {
  if (storyGuanmu) return "guanmu";
  if (storyNoway) return "noway";
  const st = (snap && snap.story) || {};
  const flags = (snap && snap.flags) || [];
  if ((st.shiren || {}).stage >= 0) return "shiren";
  if (flags.includes("romance_confirmed")) return "romance";
  if ((snap && (snap.gorshou || 0)) >= 1) return "god";
  return "base";
}
function bgmSyncStory(snap) {
  const key = bgmDesired(snap);
  if (key === bgmLastKey) return;
  const prev = bgmLastKey;
  bgmLastKey = key;
  bgmPlayTrack(BGM_TRACKS.find((x) => x.key === key));
  // 解禁横幅只在「第一次换上某条专属曲」的时候飘：开局上日常曲不打扰
  if (prev !== null && key !== "base" && key !== prev) bgmUnlockBanner(BGM_TRACKS.find((x) => x.key === key));
}
function bgmUnlockBanner(t) {
  // 游戏小人说话：气泡挂在 #idol 上（她的立绘按存档换过装，直接复用）
  const idol = $("idol");
  if (!idol) return;
  const old = idol.querySelector(".idol-bubble");
  if (old) old.remove();
  const b = document.createElement("div");
  b.className = "idol-bubble";
  b.innerHTML = `<b>♪ ${t.tag} BGM 解禁 ♪</b><span>好像发生了什么变化。</span>`;
  idol.appendChild(b);
  setTimeout(() => b.remove(), 5600);
}

// 唱片只做一件事：音乐开 / 关（选歌面板在游戏外的 music.html）
function bgmSetPlaying(on) {
  const box = $("bgm-box"), disc = $("bgm-disc");
  if (box) box.classList.toggle("playing", on);
  if (disc) disc.title = on ? "音乐：开着（点一下停）" : "音乐：停了（点一下放）";
}
if ($("bgm-disc")) $("bgm-disc").onclick = () => {
  bgmEnsureAudio();
  if (bgmAudio.paused) bgmAudio.play().then(() => bgmSetPlaying(true)).catch(() => {});
  else { bgmAudio.pause(); bgmSetPlaying(false); }
};

/* ---------- 重线演出：走到「我只是太爱你了」，愛してる落下来 ---------- */
let zhongRainShown = false;
function zhongRainSync(step) {
  if (zhongRainShown) return;
  if (!(step && step.type === "end" && step.ending === "我只是太爱你了")) return;
  zhongRainShown = true;
  zhongRainShow();
}
function zhongRainShow() {
  if (document.getElementById("zhong-rain")) return;
  const root = document.createElement("div");
  root.id = "zhong-rain";
  root.innerHTML = `<div class="zr-dialog">这几天，安静得让人心慌。<br>像她终于决定，要做点什么了。</div>`
    + `<div class="zr-cols"></div>`
    + `<div class="zr-core"><div class="zr-type"><span class="zr-text"></span><i class="zr-caret"></i></div></div>`
    + `<div class="zr-red"></div>`;
  document.body.appendChild(root);
  // 第一幕：黑场弹窗（安静得让人心慌）；打字等弹窗结束才开始
  const POPUP_OUT = 3800;
  setTimeout(() => root.querySelector(".zr-dialog").classList.add("on"), 900);
  setTimeout(() => root.querySelector(".zr-dialog").classList.add("off"), POPUP_OUT);
  setTimeout(() => startLine1(root), POPUP_OUT + 800);
}
function startLine1(root) {
  // 第二幕：她的话打出来，问号停一会才出来，停稳再一个字一个字删掉
  const el = root.querySelector(".zr-text");
  const line1 = "为什么你就不肯回头看看我呢";
  const full = line1 + "？";
  let i = 0;
  const t1 = setInterval(() => {
    i += 1;
    el.textContent = full.slice(0, i);
    if (i < line1.length) return;
    clearInterval(t1);
    setTimeout(() => { el.textContent = full; }, 1600);        // 问号迟一步
    setTimeout(() => {                                          // 问号停稳后开始删
      const t2 = setInterval(() => {
        i -= 1;
        el.textContent = full.slice(0, Math.max(i, 0));
        if (i > 0) return;
        clearInterval(t2);
        setTimeout(() => zhongRainPhase(root), 900);
      }, 60);
    }, 2800);
  }, 450);
}
function zhongRainPhase(root) {
  // 第三幕：雨。每列一个「愛してる」，全部从天上落，批次越下越大，铺屏前 400+ 列
  const colsBox = root.querySelector(".zr-cols");
  const addCol = () => {
    const s = document.createElement("span");
    s.className = "zr-col";
    s.style.cssText = `left:${(Math.random() * 97).toFixed(1)}%;`
      + `font-size:${(9 + Math.random() * 14).toFixed(0)}px;`
      + `opacity:${(0.4 + Math.random() * 0.6).toFixed(2)};`
      + `animation-duration:${(4.5 + Math.random() * 4.5).toFixed(2)}s;`
      + `animation-delay:${(Math.random() * 0.45).toFixed(2)}s`;
    s.textContent = "愛してる";
    colsBox.appendChild(s);
  };
  for (let i = 0; i < 8; i++) addCol();
  // 全部从天上落：正延迟只在屏外上方待命（fill both 钉在起点），落点永不在半空。
  // 铺天盖地：300ms 一波、单波一路加到 50，铺屏前累计 700+ 列
  const PLAN = [[300, 4], [600, 6], [900, 8], [1200, 10], [1500, 12], [1800, 14],
    [2100, 16], [2400, 18], [2700, 20], [3000, 22], [3300, 24], [3600, 26],
    [3900, 28], [4200, 30], [4500, 32], [4800, 34], [5100, 36], [5400, 38],
    [5700, 40], [6000, 42], [6300, 44], [6600, 46], [6900, 48], [7200, 50],
    [7500, 40], [7800, 30], [8100, 20]];
  PLAN.forEach(([t, k]) => setTimeout(() => { for (let j = 0; j < k; j++) addCol(); }, t));
  const glow = document.createElement("div");
  glow.className = "zr-glow";
  root.insertBefore(glow, root.querySelector(".zr-core"));
  const TXT = "我会一直一直看着你";
  const el = root.querySelector(".zr-text");
  let i = 0;
  const t1 = setInterval(() => {
    i += 1;
    el.textContent = TXT.slice(0, i);
    if (i < TXT.length) return;
    clearInterval(t1);
    setTimeout(() => { el.textContent = TXT + " ^^"; }, 2200);
    setTimeout(() => root.querySelector(".zr-red").classList.add("on"), 3800);
    setTimeout(() => root.classList.add("zr-out"), 6200);  // 渐亮出结局界面
    setTimeout(() => root.remove(), 8000);
  }, 450);
}
window.__zhongRainShow = zhongRainShow; // 预览/验收用
window.__renderStep = renderStep;       // 预览/验收用

/* ---------- 舞台 ---------- */
function para(text, cls) {
  if (!text) return "";
  return `<p class="${cls || ""}">${String(text).replace(/\n/g, "<br>")}</p>`;
}

function chatLog(step) {
  const msgs = (step.messages || []).map((m) => {
    const q = m.quote ? `<div class="quote">${m.quote}</div>` : "";
    return `<div class="msg${m.me ? " me" : ""}">
      <div class="bubble">${q}
        <div class="who">${m.who}${m.time ? `<span class="tm">${m.time}</span>` : ""}</div>
        <div class="txt">${String(m.text || "").replace(/\n/g, "<br>")}</div>
      </div>
    </div>`;
  }).join("");
  return `<div class="chat-log">${step.time ? `<div class="chat-day">${step.time}</div>` : ""}${msgs}</div>`;
}

function addOption(label, desc, onclick, id) {
  const b = document.createElement("button");
  b.className = "opt-in";
  b.style.setProperty("--i", $("options").children.length);
  if (id) b.dataset.act = id;
  b.innerHTML = `${label}${desc ? `<small>${desc}</small>` : ""}`;
  b.onclick = onclick;
  $("options").appendChild(b);
  return b;
}

const NUM_NAME = { money: "钱", stamina: "体力", psyche: "心理", fame: "人气",
  dance: "舞", sing: "唱", mc: "营业", enjou: "炎上", banzi: "板子", kaibox: "开盒" };

function popup(delta, snap, sticks, mates) {
  const box = $("pop");
  const rows = Object.entries(delta || {}).filter(([, v]) => v);
  const sticks2 = Object.entries(sticks || {}).filter(([, v]) => v);
  const mates2 = Object.entries(mates || {}).filter(([, v]) => v);
  if (!rows.length && !sticks2.length && !mates2.length) {
    box.classList.add("hidden");
    return;
  }
  const nowOf = (name) => {
    const o = ((snap && snap.ota) || []).find((x) => x.name === name);
    return o ? `<em>${o.stick}</em>` : "";
  };
  const main = rows.map(([k, v]) => {
    const now = snap && typeof snap[k] === "number" ? `<em>${fmtNum(snap[k])}</em>` : "";
    return `<div class="prow"><span>${NUM_NAME[k] || k}</span>
      <b class="${v > 0 ? "up" : "dn"}">${v > 0 ? "+" : ""}${fmtNum(v)}</b>${now}</div>`;
  }).join("");
  // OTA 黏性：单独一段，前面写名字，涨了绿、掉了红
  const ota = sticks2.length
    ? `<div class="pota">${sticks2.map(([name, v]) =>
        `<div class="prow"><span>${name}</span>
         <b class="${v > 0 ? "up" : "dn"}">${v > 0 ? "+" : ""}${v}</b>${nowOf(name)}</div>`).join("")}</div>`
    : "";
  // 队友关系：排练室里那件事到底换来了什么
  const nowMate = (name) => {
    const m = ((snap && snap.teammates) || []).find((x) => x.name === name);
    return m ? `<em>${m.relation}</em>` : "";
  };
  const mate = mates2.length
    ? `<div class="pmate">${mates2.map(([name, v]) =>
        `<div class="prow"><span>${name}</span>
         <b class="${v > 0 ? "up" : "dn"}">${v > 0 ? "+" : ""}${v}</b>${nowMate(name)}</div>`).join("")}</div>`
    : "";
  // 右下角只露主数值；黏性/关系两条以内直接摊开（得带上名字，裸 +N 看不出是谁），
  // 再多才收进「更多」，点一下展开
  const extra = ota + mate;
  const extraN = sticks2.length + mates2.length;
  const collapsed = extraN > 2;
  box.innerHTML = `<div class="pmain">${main}</div>`
    + (extra
      ? (collapsed
        ? `<button type="button" class="pmore" aria-expanded="false">+${extraN}</button>
         <div class="pextra">${extra}</div>`
        : `<div class="pextra">${extra}</div>`)
      : "");
  box.classList.remove("hidden", "open");
  if (extra && !collapsed) box.classList.add("open");
  box.classList.remove("in");
  void box.offsetWidth;
  box.classList.add("in");
  const more = box.querySelector(".pmore");
  if (more) {
    more.onclick = () => {
      const open = box.classList.toggle("open");
      more.setAttribute("aria-expanded", open ? "true" : "false");
      more.textContent = open ? "收起" : `+${extraN}`;
    };
  }
}

// 失控演出：灯一盏盏灭 + 最后两屏裁字
const KILL_STEPS = { 5: "v-money", 7: "v-stamina", 9: "v-psyche", 10: "v-fame" };
function collapseFx(step) {
  const ci = Number(step.cidx);
  if (!Number.isFinite(ci)) return;
  const id = KILL_STEPS[ci];
  if (id) {
    const kv = $(id) && $(id).closest(".kv");
    if (kv) kv.classList.add("dying");
  }
  $("body").classList.toggle("cut", ci >= 10);
}
function clearCollapseFx() {
  document.querySelectorAll("#hud .kv.dying").forEach((kv) => kv.classList.remove("dying"));
  $("body").classList.remove("cut");
}

/* ---------- 结局屏：这一季的回响 ---------- */
const LINE_TEXT = { zhong: "重线", shiren: "私联", romance: "恋爱线" };
function echoPanel(e, early) {
  const cells = [];
  const add = (k, v) => cells.push(`<div class="ekv"><span>${k}</span><b>${v}</b></div>`);
  add("收场", (early ? "提前结束 · 第 " : "季末 · 第 ") + e.week + " 周");
  if (e.stance_name) add("开季姿态", e.stance_name);
  add("舞台", `${e.stage}（${e.tier}）`);
  add("心理", String(e.psyche));
  add("手头", "¥" + Number(e.money).toLocaleString("zh-CN"));
  add("炎上 / 开盒", `${e.enjou} / ${e.kaibox}`);
  if (e.truth_rate === null || e.truth_rate === undefined) {
    add("真话", "这一季没被问过");
  } else {
    add("真话", `${e.truth_pick} 次说真的 · ${e.safe_pick} 次场面话（${Math.round(e.truth_rate * 100)}%）`);
  }
  add("线索", `${e.clues} 条记住 · ${e.clues_wrong} 条记错`);
  add("硬撑", `${e.pushed} 次`);
  if (e.line || e.shiren_stage >= 0) {
    const bits = [];
    if (e.line) bits.push(LINE_TEXT[e.line] || e.line);
    if (e.shiren_stage >= 0) bits.push(`私联第 ${e.shiren_stage + 1} 拍`);
    add("线", bits.join(" · "));
  }
  const flags = [];
  flags.push(e.rent_missed ? "欠过租" : "没欠租");
  flags.push(e.chose_leave ? "选了离开" : "没离开");
  flags.push(e.offer_refused ? "当面拒过运营" : "没拒过运营");
  add("做过的事", flags.join(" · "));
  return `<div class="echo-card">
    <h4>这一季的回响</h4>
    <div class="echo-grid">${cells.join("")}</div>
    <p class="echo-note">这些只是这一局发生过的，不是攻略。</p>
  </div>`;
}

/* ---------- 结局屏：游戏之外（作者话 / 链接） ---------- */
function outsidePanel(d) {
  if (!d) return "";
  const paras = (d.body || []).map((p) => `<p>${p}</p>`).join("");
  const links = (d.links || []).map((l) => {
    const label = l.url
      ? `<a href="${l.url}" target="_blank" rel="noopener noreferrer">${l.label}</a>`
      : `<b>${l.label}</b>`;
    return `<p>${l.prefix || ""}${label}${l.suffix || ""}</p>`;
  }).join("");
  return `<section class="outside"><h4>${d.title || "游戏之外"}</h4>${paras}${links}</section>`;
}

/* ---------- 结局图鉴：跨周目保留 ---------- */
function galRow(r) {
  const n = String(r.n || 0).padStart(2, "0");
  if (r.locked) {
    return `<div class="gal-row locked">
      <div class="gal-line"><span class="gal-n">${n}</span><span class="gal-name">？？？</span><span class="gal-lock">未解锁</span></div>
      <p class="gal-hint">${r.hint || ""}</p>
    </div>`;
  }
  const echo = r.last_echo || {};
  const meta = [`达成 ${r.count} 次`];
  if (r.last_at) meta.push(`最后 ${r.last_at}`);
  if (echo.week) meta.push(`第 ${echo.week} 周 · 舞台 ${echo.stage}`);
  return `<div class="gal-row unlocked">
    <div class="gal-line"><span class="gal-n">${n}</span><span class="gal-name">${r.name}</span><span class="gal-lock">✓</span></div>
    <p class="gal-core">${r.core || ""}</p>
    <p class="gal-style">${r.style || ""}</p>
    <p class="gal-meta">${meta.join(" · ")}</p>
  </div>`;
}

let galBusy = false;
async function openGallery() {
  if (galBusy) return;
  galBusy = true;
  $("gallery-modal").classList.remove("hidden");
  $("gal-count").textContent = "正在翻……";
  $("gal-list").innerHTML = "";
  try {
    const d = await api("/api/gallery");
    if (!d || d.error) {
      $("gal-count").textContent = "没翻出来";
      return;
    }
    $("gal-count").textContent = `解锁 ${d.unlocked} / ${d.total}`;
    $("gal-list").innerHTML = (d.endings || []).map(galRow).join("");
  } finally {
    galBusy = false;
  }
}
function closeGallery() {
  $("gallery-modal").classList.add("hidden");
}

const LINE_NAMES = { zhong: "重线", shiren: "私联", romance: "恋爱" };
function journalEvents(log) {
  const ev = [];
  let p = null;
  for (const r of log) {
    const line = r.line ? (LINE_NAMES[r.line] || r.line) : "";
    if (!p) {
      ev.push(`第 ${r.week} 周：开季。舞台 ${r.stage}，心理 ${r.psyche}，手里 ${r.money}。`);
      if (r.rent_missed) ev.push("这一季欠过房租。");
    } else {
      if (r.line && r.line !== p.line) ev.push(`第 ${r.week} 周：走上了${line}。`);
      if (r.shiren_stage > p.shiren_stage && r.shiren_stage >= 0)
        ev.push(`第 ${r.week} 周：私联线走到第 ${r.shiren_stage + 1} 拍。`);
      if (r.stage >= 70 && p.stage < 70) ev.push(`第 ${r.week} 周：舞台压得住整场了（${r.stage}）。`);
      if (r.stage >= 60 && p.stage < 60) ev.push(`第 ${r.week} 周：舞台站得住了（${r.stage}）。`);
      if (r.psyche < 20 && p.psyche >= 20) ev.push(`第 ${r.week} 周：心理掉到 ${r.psyche}。`);
      if (r.enjou >= 70 && p.enjou < 70) ev.push(`第 ${r.week} 周：炎上 ${r.enjou}，开始有人骂。`);
      if (r.kaibox >= 80 && p.kaibox < 80) ev.push(`第 ${r.week} 周：开盒 ${r.kaibox}，那扇门快被敲穿了。`);
      if (r.relavg < 30 && p.relavg >= 30) ev.push(`第 ${r.week} 周：队友关系均值掉到 ${r.relavg}。`);
      if (r.rent_missed && !p.rent_missed) ev.push(`第 ${r.week} 周：欠了房租。`);
      if (r.truth_rate >= 0.5 && p.truth_rate < 0.5) ev.push(`第 ${r.week} 周：真话率过半（${Math.round(r.truth_rate * 100)}%）。`);
    }
    if (r.chose_leave && !(p && p.chose_leave)) ev.push(`第 ${r.week} 周：最后那晚，选了离开。`);
    if (r.offer_refused && !(p && p.offer_refused)) ev.push(`第 ${r.week} 周：当面拒绝了运营那条路。`);
    p = r;
  }
  return ev;
}

function journalHtml(d) {
  const log = (d && d.log) || [];
  const ev = journalEvents(log);
  const evHtml = ev.length
    ? ev.map((e) => `<li>${e}</li>`).join("")
    : `<li class="muted">这一季还没走完第一周。</li>`;
  const rows = log.map((r) => {
    const line = r.line ? `${LINE_NAMES[r.line] || r.line}${r.line_stage >= 0 ? ` · 第${r.line_stage + 1}拍` : ""}` : "—";
    return `<li class="set-row">
      <b>第 ${r.week} 周</b>
      <span>舞台 ${r.stage}</span><span>心理 ${r.psyche}</span><span>钱 ${r.money}</span>
      <span>炎上 ${r.enjou}</span><span>板子 ${r.banzi}</span><span>开盒 ${r.kaibox}</span>
      <span>真话 ${Math.round((r.truth_rate || 0) * 100)}%</span>
      <span>${line}</span>
    </li>`;
  }).join("");
  return `
    <div class="set-sec">
      <div class="set-h">影响结局的事</div>
      <ul class="set-ev">${evHtml}</ul>
    </div>
    <div class="set-sec">
      <div class="set-h">每周底账</div>
      <ul class="set-log">${rows || `<li class="muted">跑完一周后这里会记一行。</li>`}</ul>
    </div>
    <div class="set-sec">
      <div class="set-h">这一季</div>
      <button id="quick-restart" class="ghost set-danger">重开这一季</button>
      <div class="set-note">会删掉当前进度；结局图鉴保留。</div>
    </div>`;
}

let journalBusy = false, quickArmed = false;
async function openJournal() {
  if (journalBusy) return;
  journalBusy = true;
  $("settings-modal").classList.remove("hidden");
  $("set-count").textContent = "这一季的记事本";
  $("set-body").innerHTML = `<div class="muted">正在翻……</div>`;
  try {
    const d = await api("/api/journal");
    $("set-body").innerHTML = journalHtml(d);
    const q = $("quick-restart");
    if (q) {
      q.onclick = async () => {
        if (!quickArmed) {
          quickArmed = true;
          q.textContent = "再点一次就删档重开";
          q.classList.add("armed");
          setTimeout(() => {
            quickArmed = false;
            q.textContent = "重开这一季";
            q.classList.remove("armed");
          }, 4000);
          return;
        }
        q.disabled = true;
        q.textContent = "正在重开……";
        const r = await api("/api/new", {});
        if (r && !r.error) {
          closeJournal();
          renderStep(r.step, r.snapshot);
          $("restart").classList.add("hidden");
        } else {
          q.disabled = false;
          q.textContent = "重开失败";
        }
      };
    }
  } catch (e) {
    $("set-body").innerHTML = `<div class="muted">没翻出来。</div>`;
  } finally {
    journalBusy = false;
  }
}
function closeJournal() {
  $("settings-modal").classList.add("hidden");
}

function renderStep(step, snap) {
  const titleEl = $("title");
  titleEl.textContent = step ? step.title || "" : "";
  titleEl.classList.remove("title-in");
  const actGrid = !!step && step.type === "choice" && step.kind === "act";
  $("options").classList.toggle("act-grid", actGrid);
  const body = $("body");
  $("options").innerHTML = "";
  $("next").classList.add("hidden");
  $("pop").classList.add("hidden");
  body.innerHTML = "";
  if (snap) renderHud(snap);
  // 这一屏的情绪反应要压在数值态之上，所以放在 renderHud 之后
  if (step) reactToStep(step);
  if (!step) return;

  $("stage").classList.toggle("compact", !!step.compact);
  const onEnd = step.type === "end";
  // 剧情歌钩子：失控演出 = 无路可退的视线；「我只是太爱你了」结局 = 棺木生花。均 latch 不再被打断
  if (step.collapse_start || (onEnd && step.ending === "我只是太爱你了")) {
    if (onEnd && step.ending === "我只是太爱你了") {
      storyGuanmu = true;
      bgmLastKey = "guanmu";
      bgmPlayTrack(BGM_TRACKS.find((x) => x.key === "guanmu"));
    } else {
      storyNoway = true;
      bgmLastKey = "noway";
      bgmPlayTrack(BGM_TRACKS.find((x) => x.key === "noway"));
    }
  }
  bgmSyncStory(snap);
  zhongRainSync(step);
  // C+A：live 屏和结局屏切到「午夜场」的深色追光；失控的纯黑另走 collapse-end
  document.body.classList.toggle("live-stage", step.type === "live");
  document.body.classList.toggle("ending-stage", onEnd && step.ending !== "控制不了");
  document.body.classList.toggle("ending-red", onEnd && step.ending === "我只是太爱你了");
  if (titleEl.textContent) {
    void titleEl.offsetWidth;
    titleEl.classList.add("title-in");
  }
  // 事件卡角标：全池序号（对话/回考/剧情线等非卡池屏不带 no）
  if (step.no) titleEl.insertAdjacentHTML("beforeend", ` <span class="card-no">No.${step.no}</span>`);
  // 右上角的小标签：版聊 / 回考 / 剧情线
  $("stage").querySelectorAll(".corner-tag").forEach((n) => n.remove());
  const lineTag = step.line && step.line_name ? step.line_name : "";
  const hasTag = step.type === "chat" || !!step.recall || !!lineTag;
  $("stage").classList.toggle("has-tag", hasTag);
  if (step.type === "chat") {
    $("stage").insertAdjacentHTML("afterbegin", `<div class="corner-tag chat">版聊</div>`);
  } else if (step.recall) {
    $("stage").insertAdjacentHTML("afterbegin", `<div class="corner-tag recall">回考</div>`);
  } else if (lineTag) {
    // 三条剧情线各自的专属卡：颜色区分，避免分不清自己在哪条线上。
    const cls = LINE_TAG_CLASS[lineTag] || "line";
    $("stage").insertAdjacentHTML("afterbegin", `<div class="corner-tag ${cls}">${lineTag}</div>`);
  }
  body.innerHTML = "";
  // 谁在跟我打交道：每屏都先清掉上一条，再按这一屏重挂
  // （以前是插在标题后面、只插不删，一条条往上堆）
  if (step.face && (step.type === "card" || step.type === "choice" || step.type === "receipt")) {
    body.insertAdjacentHTML("afterbegin", `<div class="face">${step.face}</div>`);
  }
  if (step.type === "chat") {
    body.insertAdjacentHTML("beforeend", chatLog(step));
  } else {
    body.insertAdjacentHTML("beforeend", (step.body || []).map((p) => para(p, onEnd ? "quote" : "")).join(""));
  }
  if (step.skill && step.skill_now !== null && step.skill_now !== undefined) {
    body.insertAdjacentHTML("beforeend", `<p class="grow">${
      { dance: "舞", sing: "唱", mc: "营业" }[step.skill] || step.skill
    } 现在是 ${step.skill_now}（${step.skill_tier}）${
      step.skill_left ? "，再练 " + step.skill_left + " 点进下一档" : "，已经压得住整场"}</p>`);
  }
  body.classList.remove("fade");
  void body.offsetWidth;
  body.classList.add("fade");
  popup(step.delta, snap, step.sticks, step.mates);

  if (step.type === "bill" && step.bill) body.insertAdjacentHTML("beforeend", billTable(step.bill));

  if (onEnd) {
    $("title").textContent = step.ending;
    $("title").classList.remove("title-in");
    void $("title").offsetWidth;
    $("title").classList.add("title-in");
    $("foot").classList.add("ended");
    // 失控结局要留着黑红那一层，别在最后关头把灯重新打开
    if (step.ending === "控制不了") {
      document.body.classList.remove("collapsing");
      document.body.classList.add("collapse-end");
    } else {
      document.body.classList.remove("collapsing", "collapse-end");
    }
    clearTimeout(autoTimer);
    $("restart").classList.remove("hidden");
    clearCollapseFx();
    if (step.echo) body.insertAdjacentHTML("beforeend", echoPanel(step.echo, step.early));
    if (step.outside) body.insertAdjacentHTML("beforeend", outsidePanel(step.outside));
    return;
  }
  if (["text", "receipt", "live", "panel", "bill"].includes(step.type)) {
    const n = $("next");
    n.classList.remove("hidden");
    n.textContent = step.type === "panel" ? (step.kind === "week" ? "下一周" : "继续") : "继续";
  }

  if (step.type === "choice" || step.type === "card" || step.type === "chat"
      || step.type === "stance") {
    (step.options || step.stances || []).forEach((o) => {
      // 旧存档的队列里可能还留着改版前的长标签，日常行动格只显示短名
      const label = actGrid && o.id === "mc" ? "练营业话术" : o.label;
      addOption(label, o.desc, () => send({ id: o.id }), o.id);
    });
  }

  if (step.type === "name") {
    if (step.stage === "style") {
      (step.styles || []).forEach((st) => addOption(st.label, st.desc, () => send({ id: st.id })));
    } else {
      const wrap = document.createElement("div");
      wrap.className = "cands";
      (step.candidates || []).forEach((n) => {
        const b = document.createElement("button");
        b.textContent = n;
        b.onclick = () => send({ id: n });
        wrap.appendChild(b);
      });
      const nb = document.createElement("div");
      nb.className = "namebox";
      nb.innerHTML = `<input id="myname" maxlength="8" placeholder="自己写一个（8 字以内）">
        <button class="ghost" id="okname">就用这个</button>`;
      $("options").appendChild(wrap);
      $("options").appendChild(nb);
      $("okname").onclick = () => {
        const v = ($("myname").value || "").trim();
        if (!v) return toast("先写一个名字");
        send({ id: v });
      };
      $("myname").addEventListener("keydown", (e) => { if (e.key === "Enter") $("okname").click(); });
    }
  }

  // ---- 失控段：按钮全没了，屏幕自己往下走
  if (step.auto) {
    document.body.classList.add("collapsing");
    $("next").classList.add("hidden");
    $("restart").classList.add("hidden");
    collapseFx(step);
    if (step.collapse_start) showOverlay();
    clearTimeout(autoTimer);
    autoTimer = setTimeout(() => { autoTick(); }, step.auto_after || (step.collapse_start ? 2600 : 1900));
  } else {
    document.body.classList.remove("collapsing", "collapse-end");
    clearCollapseFx();
    $("restart").classList.add("hidden");
  }

  window.scrollTo({ top: 0, behavior: "auto" });   // 结果要立刻出现在眼前：平滑滚动会让新屏迟到半秒
}

/* ---------- 失控：你不点，它也会走 ---------- */
let autoTimer = null;
let autoBusy = false;
let ovHold = null;
let ovHide = null;
async function autoTick() {
  if (autoBusy) return;
  autoBusy = true;
  try {
    const d = await api("/api/advance", {});
    if (d && !d.error) renderStep(d.step, d.snapshot);
  } finally {
    autoBusy = false;
  }
}

function showOverlay() {
  const el = $("overlay");
  if (!el) return;
  // 连着弹两次时，上一轮的收起定时器会把这一轮刚亮的弹窗又摁灭。
  // 先把旧的两个定时器都清掉，再开始新的一轮。
  clearTimeout(ovHold);
  clearTimeout(ovHide);
  el.classList.remove("hidden");
  el.innerHTML = `<div class="ovbox">
      <p class="ovline">你似乎已经控制不了这一切了</p>
    </div>`;
  void el.offsetWidth;
  el.classList.add("in");
  ovHold = setTimeout(() => {
    el.classList.remove("in");
    ovHide = setTimeout(() => el.classList.add("hidden"), 700);
  }, 2100);
}

/* 这一场的券：谁买了几张 */
function billTable(b) {
  if (!b.rows || !b.rows.length) {
    return `<div class="bill"><p class="empty">今天没有人买券。</p></div>`;
  }
  const rows = b.rows.map((r) => `<tr>
      <td class="nm">${r.name}</td>
      <td class="n">${r.tickets}</td>
      <td class="m">${r.yen}</td>
    </tr>`).join("");
  const absent = (b.absent || []).length
    ? `<p class="absent">今天没露面的：${b.absent.join("、")}</p>` : "";
  return `<div class="bill">
    <table>
      <thead><tr>
        <th>名字</th><th class="n">买了</th><th class="m">钱</th>
      </tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr>
        <td>一共卖出</td>
        <td class="n">${b.tickets} 张</td>
        <td class="m">${b.yen}</td>
      </tr></tfoot>
    </table>
    ${absent}
  </div>`;
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

/* ---------- 请求 ---------- */
let busy = false;   // 点一下只走一次：慢的时候连点会把队列打乱
async function refresh(data) {
  const d = data || (await api("/api/state"));
  if (!d || d.error) return;
  renderStep(d.step, d.snapshot);
}

async function send(payload) {
  if (busy) return;
  busy = true;
  try {
    const d = await api("/api/choose", payload);
    if (d && !d.error) await refresh(d);
  } finally {
    busy = false;
  }
}

$("next").onclick = async () => {
  if (busy) return;
  busy = true;
  try {
    const d = await api("/api/advance", {});
    if (d && !d.error) await refresh(d);
  } finally {
    busy = false;
  }
};

/* 重开：不用 confirm（有窗口不弹这种框，会像点了没反应）——改成点一次变「再点一次」，防误触又不卡住 */
let restartArmed = false;
$("restart").onclick = async () => {
  if (!restartArmed) {
    restartArmed = true;
    $("restart").textContent = "再点一次就重开";
    $("restart").classList.add("armed");
    setTimeout(() => {
      restartArmed = false;
      $("restart").textContent = "重开";
      $("restart").classList.remove("armed");
    }, 2600);
    return;
  }
  restartArmed = false;
  $("restart").textContent = "重开";
  $("restart").classList.remove("armed");
  $("foot").classList.remove("ended");
  const d = await api("/api/new", {});
  if (d && !d.error) await refresh(d);
};

/* ---------- 详细面板：记住展开状态 ---------- */
function applyDetail(on) {
  $("detail").classList.toggle("hidden", !on);
  $("toggle").classList.toggle("on", on);
  localStorage.setItem(DETAIL_KEY, on ? "1" : "0");
}
$("toggle").onclick = () => applyDetail($("detail").classList.contains("hidden"));
/* 手机默认收起：首屏不该先看到一整块数值面板 */
const _savedDetail = localStorage.getItem(DETAIL_KEY);
const _narrow = window.matchMedia("(max-width:640px)").matches;
applyDetail(_savedDetail === null ? !_narrow : _savedDetail === "1");

/* ---------- 结局图鉴 ---------- */
$("gallery").onclick = openGallery;
$("gal-close").onclick = closeGallery;
$("gallery-modal").onclick = (e) => { if (e.target === $("gallery-modal")) closeGallery(); };
$("settings").onclick = openJournal;
$("set-close").onclick = closeJournal;
$("settings-modal").onclick = (e) => { if (e.target === $("settings-modal")) closeJournal(); };
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!$("gallery-modal").classList.contains("hidden")) closeGallery();
  else if (!$("settings-modal").classList.contains("hidden")) closeJournal();
  else if (typeof bgmOpenMenu === "function" && bgmMenuOpen) bgmOpenMenu(false);
});

refresh();
