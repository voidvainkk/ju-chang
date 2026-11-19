/**
 * 《聚场》可玩流程 —— `game/loop.py` 的 TypeScript 移植。
 *
 * 分工和 Python 版一样：
 * - `engine.ts` 算账（动作、抽卡、结算、结局），本文件只管
 *   「什么时候停下来、停在哪、给哪几个按钮」。
 * - 所有跨步状态在 `Game` 里；界面每次请求只拿一个 step，不自己算任何数。
 *
 * step 的 type：
 *   text     一段文字 + 继续
 *   choice   文字 + 若干按钮
 *   card     一张卡（标题 / 正文 / 选项）
 *   chat     版聊（聊天记录 + 选项）
 *   receipt  回执（对白 + 数值增减）
 *   live     演出结果
 *   bill     券账
 *   panel    周结算 / 季结算
 *   name     取名（选风格 → 候选 → 自己写）
 *   end      结局
 *
 * 移植要点（与 `engine.ts` 同一套）：
 * * `round()` 是银行家舍入，`round(x, n)` 也是 → 本文件的 `pyRound`。
 * * `int()` → `Math.trunc`。
 * * `s.get(k, d)` 只在键**不存在**时给 d → `gv()`。
 * * 字符串模板里的减号是 U+2212「−」、分隔符是 U+00B7「·」，不是 ASCII。
 */

import { PyRandom } from "./rng.ts";
import * as E from "./engine.ts";
import * as B from "./bill.ts";
import type { Card, Ota, Option, State, World } from "./types.ts";

// ------------------------------------------------------------------ 常量

export const WEEKS = 8;

/**
 * Python `round(x)` / `round(x, n)`。
 * 直接借用引擎里那份精确实现——两边各写一份迟早会分叉，
 * 而且 `0.1949999999999999` 这种值用「乘 10^n 再 Math.round」会舍错。
 */
const pyRound = (x: number, nd = 0): number => E.pyRound(x, nd);

const hasOwn = (o: any, k: string): boolean =>
  o != null && Object.prototype.hasOwnProperty.call(o, k);

/** Python `d.get(k, dflt)`：键不存在才给默认值。 */
function gv<T = any>(o: any, k: string, dflt?: T): any {
  if (o == null) return dflt;
  return hasOwn(o, k) ? o[k] : dflt;
}

const n0 = (v: any): number => (v ? Number(v) : 0);

/**
 * Python 的 falsy 判据：None 和空 dict 都算「没拿到」。
 * cast() 在卡没声明 casting 时返回 {}，JS 里 {} 是真值，直接写 `if (!slots)` 会漏掉这个分支。
 */
const emptySlots = (slots: Record<string, any> | null | undefined): boolean =>
  slots == null || Object.keys(slots).length === 0;

function cmpCodepoint(a: string, b: string): number {
  const ac = Array.from(a);
  const bc = Array.from(b);
  const n = Math.min(ac.length, bc.length);
  for (let i = 0; i < n; i++) {
    const x = ac[i].codePointAt(0)!;
    const y = bc[i].codePointAt(0)!;
    if (x !== y) return x - y;
  }
  return ac.length - bc.length;
}

/** 界面要报的数值。练舞练唱练话术也得动，否则一整周都是白练。 */
const TRACKED = ["money", "stamina", "psyche", "fame"] as const;
const SHOWN = [...TRACKED, "dance", "sing", "mc", "enjou", "banzi", "kaibox"];

type Step = Record<string, any>;

/** 一个 step 里只有这些字段是给界面看的（下划线开头的是内部对象）。 */
export function cleanStep(step: Step): Step {
  const out: Step = {};
  for (const k of Object.keys(step)) {
    if (k.startsWith("_")) continue;
    out[k] = step[k];
  }
  return out;
}

// ------------------------------------------------------------------ 小工具

function delta(before: Record<string, any>, s: State): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of SHOWN) {
    const d = pyRound(n0(gv(s, k, 0)) - n0(gv(before, k, 0)));
    if (d) out[k] = d;
  }
  return out;
}

/** 三个队友的关系涨跌：团内那张卡到底换来了什么，得当场看见。 */
function matesChanged(before: Record<string, any>, s: State): Record<string, number> {
  const out: Record<string, number> = {};
  const names: Record<string, string> = {
    relation_A: "阿棠",
    relation_B: "露露",
    relation_C: "小满",
  };
  for (const [k, nm] of Object.entries(names)) {
    const d = pyRound(n0(gv(s, k, 0)) - n0(gv(before, k, 0)));
    if (d) out[nm] = d;
  }
  return out;
}

const MATE_TEXT: Record<string, string> = {
  "{{A}}阿棠": "阿棠",
  "{{B}}露露": "露露",
  "{{C}}小满": "小满",
};

const MATE_NAME: Record<string, string> = {
  relation_A: "阿棠",
  relation_B: "露露",
  relation_C: "小满",
};

/**
 * 这张卡的这一选项，主要冲谁去的：看谁的负值最狠，再看正值最多。
 *
 * 排练室那些事正文里只有一个开场，谁在里面本来就该由选项决定——
 * 「跟她说清楚规矩」和「这次算我的」面对的是同一个人。
 */
function whoHit(_card: Card, option: Option | undefined): string {
  const eff: Record<string, any> = (option && option.immediate) || {};
  const rel: [string, number][] = [];
  for (const k of ["relation_A", "relation_B", "relation_C"]) {
    if (hasOwn(eff, k)) rel.push([k, Number(eff[k])]);
  }
  if (!rel.length) return "";
  const neg = rel.filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1] || cmpCodepoint(a[0], b[0]));
  if (neg.length) return MATE_NAME[neg[0][0]];
  const pos = rel.filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1] || cmpCodepoint(b[0], a[0]));
  if (pos.length) return MATE_NAME[pos[0][0]];
  return "";
}

/** OTA 黏性的快照。`snap()` 只拍四大数值，拿它去算 OTA 涨跌会永远得 0。 */
function osnap(s: State | null): { ota: { id: string; name: string; stick: number }[] } {
  return {
    ota: ((s || {}).ota || []).map((o: Ota) => ({
      id: o.id,
      name: o.name,
      stick: pyRound(o.stick),
    })),
  };
}

/** 每条 OTA 的黏性涨跌：键是名字。交互之后玩家要看得见「她离我更近了一点」。 */
function sticks(before: any, s: State | null): Record<string, number> {
  const out: Record<string, number> = {};
  const old: Record<string, number> = {};
  for (const o of (before || {}).ota || []) old[o.id] = o.stick;
  for (const o of (s || ({} as State)).ota || []) {
    if (!hasOwn(old, o.id)) continue; // 新人不是「涨跌」
    const d = pyRound(o.stick) - old[o.id];
    if (d) out[o.name] = d;
  }
  return out;
}

function snap(s: State): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of SHOWN) out[k] = n0(gv(s, k, 0));
  return out;
}

/**
 * 三个队友的关系快照。`snap()` 里没有 relation_A/B/C，
 * 拿它去算队友涨跌会每次都算成「0 → 当前值」。
 */
function rsnap(s: State): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of ["relation_A", "relation_B", "relation_C"]) out[k] = n0(gv(s, k, 0));
  return out;
}

// ------------------------------------------------------------------ 数据

/** `Game` 需要的那几份 JSON（其余由 `engine.loadWorld` 自己从 files 里取）。 */
export interface GameAssets {
  intro: any;
  endings: any;
  names: any;
  stances: any[];
  outside: any;
  endingMd: string;
}

function assetsFrom(files: Record<string, any>): GameAssets {
  if (!hasOwn(files, "stances.json")) throw new Error("缺数据：stances.json");
  if (!hasOwn(files, "outside.json")) throw new Error("缺数据：outside.json");
  return {
    intro: files["intro.json"],
    endings: files["endings.json"],
    names: files["idol_names.json"],
    stances: (files["stances.json"].stances || []) as any[],
    outside: files["outside.json"],
    endingMd: typeof files["结局.md"] === "string" ? files["结局.md"] : "",
  };
}

// ------------------------------------------------------------------ Game

export class Game {
  static ACT_LEFT = 6; // 一周六个晚上可排
  static ACT_SAT = 7; // 周六那一格：排完之后 acts_done 就是 7
  static WEEK_EVENTS = 3; // 一周几张「路上遇上的事」，卷在周末两场之后
  static LINE_CHANCE = 0.85; // 能推的周，大概率就推（八周里每条线大约走两拍）

  /**
   * 一周 6 个事件位。团里的戏只在第 3 位出现一次（一周最多一张，
   * 见 `_drawWeekEvents`）。
   */
  static EVENT_SPOTS: string[][] = [
    ["外部", "external", "外部舆论"],
    ["OTA互动", "OTA相处的瞬间"],
    ["团内", "团内关系"],
    ["同行"],
    ["日常", "ambient", "daily"],
    ["外部", "external", "positive", "舞台事故"],
    ["OTA互动", "daily", "ambient"],
  ];

  /** 某个位置抽空了（池子为空 / 全在冷却），按这个顺序接着往下试。 */
  static EV_FALLBACK: string[] = [
    "团内", "团内关系", "外部", "external", "外部舆论",
    "OTA互动", "OTA相处的瞬间", "positive", "日常", "ambient",
    "同行", "舞台事故", "私生", "私生跟踪", "私联恋爱",
  ];

  /** 卡面上那行「谁在跟我打交道」：有具体人就写人，没有就写场所。 */
  static SCENE: Record<string, string> = {
    ambient: "这个城市",
    日常: "家里",
    daily: "家里",
    外部: "网上",
    external: "网上",
    外部舆论: "网上",
    positive: "这一季的运气",
    同行: "别人的场",
    舞台事故: "台上",
    团内: "排练室",
    团内关系: "排练室",
    团内冲突: "排练室",
    私生: "散场以后",
    私生跟踪: "门外",
    私联恋爱: "后台",
    OTA记忆: "",
    OTA互动: "",
    OTA相处的瞬间: "",
  };

  static ACT_TEXT: Record<string, string | string[]> = {
    dance: "练到快十点，最后一节才算顺下来。",
    sing: "嗓子一开始是哑的，唱到后面反而开了。",
    mc: "对着镜子说了一个小时的话，说到自己都想笑。",
    content: "拍了一组，挑了半天配了句话发出去。",
    work: "架好手机播到凌晨，在线人数一直没过两位数。",
    // 休息没有「事件」，回复轮着来，别天天煮面
    rest: [
      "什么都没做，睡到下午，起来煮了碗面。",
      "闹钟定了五个也没用，一觉睡到天黑，屋里暗得分不清几点。",
      "在地板上躺了一下午，听完一整张专辑，手机都懒得看。",
      "去楼下泡了个热水澡，出来的时候觉得骨头轻了二两。",
      "给家里打了个电话，没提这行的事，光听我妈讲菜市场就听了半个钟头。",
      "翻了一遍这一季的返图，挑出最喜欢的一张设成了锁屏。",
    ],
  };

  static TEAM_TYPES = ["团内", "团内关系", "团内冲突"];

  /** 运营递来那条路：季中之后才出现。 */
  static OFFER_FROM_WEEK = 4;

  static OFFER_TEXT: Record<string, [string, string]> = {
    炒CP: [
      "运营把一份策划摊在桌上：和露露捆一个『双人线』，每周发两条互动，超话会自己吵起来。",
      "这条能火，做不做？",
    ],
    讲以前那个团: [
      "运营说，台上那段『从散了的团里出来』，讲一遍上热搜，讲两遍就是人设。",
      "这条能火，做不做？",
    ],
    接一条擦边商务: [
      "运营推过来一张报价单，是一个擦边饮料的商单。钱不少，发出来会有人骂，也一定会有人转。",
      "这条能火，做不做？",
    ],
  };

  world: World;
  rng: PyRandom;
  intro: any;
  endings: any;
  names: any;
  stances: any[];
  outside: any;
  endingMd: string;

  state: State | null = null;
  queue: Step[] = [];
  name: string | null = null;
  acts_done = 0;
  name_style: string | null = null;
  name_options: string[] = [];
  allow_stance = false; // 二周目：图鉴里有结局时才开
  prev_season: any = null; // 上一季的结局/回响，显示在姿态屏
  pending: any = null; // ["card", card, slots] / ["act", …]
  private _bill: any = null;
  // `_week_cards` / `_pending_week_settle` 在 Python 侧也只赋值不读（loop.py:174-175，
  // 唯一读它的是死代码 auto_play），不移植，免得留一堆没人用的字段。

  /** 这一周排到哪一步了：`stepWeek()` 只按它决定下一屏放什么。 */
  wk: Record<string, any> = {
    act: 0, mid: 0, fri: 0, sat_act: 0, sat: 0,
    bill: 0, sun: 0, bill2: 0, sun_talk: 0,
    events: [], extra: [], talk: null,
  };

  over = false;

  constructor(files: Record<string, any>, seed: number) {
    this.world = E.loadWorld(files);
    const a = assetsFrom(files);
    this.rng = new PyRandom(seed);
    this.intro = a.intro;
    this.endings = a.endings;
    this.names = a.names;
    this.stances = a.stances;
    this.outside = a.outside;
    this.endingMd = a.endingMd;
    this._buildIntro();
  }

  // ---------------- 队列 ----------------

  push(step: Step): void {
    this.queue.push(step);
  }

  pushFront(step: Step): void {
    this.queue.unshift(step);
  }

  /**
   * 屏幕上现在这一屏。队列是排好的，这里只负责把 pending 对到这一屏上。
   */
  current(): Step | null {
    let n = 0;
    while (this.queue.length && n < 40) {
      n += 1;
      const head = this.queue[0];
      const t = head.type;
      if ((t === "choice" || t === "card" || t === "chat") && !head.options) {
        this.queue.shift();
        continue;
      }
      break;
    }
    const head = this.queue.length ? this.queue[0] : null;
    if (head !== null) {
      if ((head.type === "card" || head.type === "chat") && head._card) {
        this.pending = ["card", head._card, head._slots || {}];
      } else if (head.line && head._line) {
        this.pending = head._line;
      } else if (head.rtalk && head._rtalk) {
        this.pending = head._rtalk;
      } else if (head.talk && head._talk) {
        this.pending = head._talk;
      } else if (
        head.type === "choice" &&
        ["offer", "empty", "leave"].includes(head.kind)
      ) {
        this.pending = [head.kind, null, null];
      }
    }
    return head;
  }

  /** 按「继续」。弹掉这一屏，然后让 `afterStep()` 决定下一屏。 */
  advance(): Step | null {
    if (!this.queue.length) return null;
    const cur = this.queue[0];
    if (["choice", "card", "name", "end"].includes(cur.type)) return cur;
    this.queue.shift();
    if (!this.queue.length) this.afterStep();
    return cur;
  }

  // ---------------- 下一屏由谁决定：只有这里 ----------------

  /** 走到这一步了：把这一周还欠的格子一格一格补齐，直到有东西可看。 */
  afterStep(): void {
    const s = this.state;
    if (s === null || this.over) return;
    for (let i = 0; i < 40; i++) {
      if (this.queue.length) return;
      if (this.over) return;
      if (n0(s.week) > WEEKS) {
        this._finish();
        return;
      }
      // 这一周是否已经开过头（`_startWeek` 会重置 wk，不能用 wk 判断）
      if (gv(s, "_week_started", null) !== s.week) {
        s._week_started = s.week;
        this._startWeek();
        continue;
      }
      // 私联收场排到一半：先把那几屏走完，再回去过日子
      if (gv(s, "_finale", null) && this._afterFinale()) continue;
      if (this.stepWeek()) continue;
      this._finish();
      return;
    }
  }

  /** 上一周结算完了：回到「第 N 周」开头（或收尾）。 */
  startWeekNext(): void {
    const s = this.state!;
    if (n0(s.week) > WEEKS) {
      this._finish();
      return;
    }
    this._startWeek();
  }

  /**
   * 排这一周还没排的那一格。顺序写死在这里，别处不许再插队。
   *
   * 一周的格：六个晚上 → 路线/版聊那张（第 3 晚后面）→ 周五场 →
   * 周六那一格晚上 → 周六场 → 券账 → 特典会 → 本周的卡 → 结算。
   */
  stepWeek(): boolean {
    const wk = this.wk;
    if (!wk.act) {
      wk.act = 1;
      this.push(this._wkChoice());
      return true;
    }
    if (wk.act < Game.ACT_LEFT) {
      wk.act += 1;
      if (wk.act === 4 && !wk.mid) {
        wk.mid = 1;
        this.pushMidweek();
      } else {
        this.push(this._wkChoice());
      }
      return true;
    }
    if (!wk.sat_act) {
      wk.sat_act = 1;
      this.push(this._wkChoice());
      return true;
    }
    if (!wk.sat) {
      wk.sat = 1;
      this.pushLive(true);
      return true;
    }
    if (!wk.bill) {
      wk.bill = 1;
      this.push(this._billStep(false));
      // 周六场下来先开特典会（人就在桌子那头），再把剩下的卡接在后面，
      // 最后结算。以前是「3 张卡 → 特典」，看着像特典会没开就散场了。
      if (wk.talk) {
        this.push(wk.talk);
      } else {
        this.push({
          type: "text",
          title: "特典",
          body: ["今天收得快，几张券换完，后面就没人排了。"],
        });
      }
      return true;
    }
    if (!wk.sun) {
      wk.sun = 1;
      this.pushLive(true, true);
      return true;
    }
    if (!wk.bill2) {
      wk.bill2 = 1;
      this.push(this._billStep(true));
      return true;
    }
    if (!wk.sun_talk) {
      wk.sun_talk = 1;
      // 周日的「还是这几个人」过场已删（用户 2026-11-19 拍板）：周日券账之后
      // 直接接一次性提问和三张周卡，选完最后一张卡就结算。
      // 一次性提问排在前，三张周卡收尾：选完最后一张卡紧接着就是周结算
      for (const st of [...wk.extra, ...wk.events]) this.push(st);
      return true;
    }
    this.settleWeek();
    return true;
  }

  snapshot(): Step | null {
    const s = this.state;
    if (!s) return null;
    return {
      name: this.name,
      week: n0(gv(s, "week", 1)),
      money: pyRound(s.money),
      stamina: pyRound(s.stamina),
      psyche: pyRound(s.psyche),
      fame: pyRound(s.fame),
      dance: pyRound(n0(gv(s, "dance", 0))),
      sing: pyRound(n0(gv(s, "sing", 0))),
      mc: pyRound(n0(gv(s, "mc", 0))),
      template: pyRound(n0(gv(s, "template", 0)), 2),
      enjou: pyRound(n0(gv(s, "enjou", 0))),
      banzi: pyRound(n0(gv(s, "banzi", 0))),
      kaibox: pyRound(n0(gv(s, "kaibox", 0))),
      // 身份标签（女友粉/重力系那些）不进界面：玩家看到的只是「这个人」
      ota: (s.ota || []).map((o: Ota) => ({
        id: o.id,
        name: o.name,
        stick: pyRound(o.stick),
        weeks: Math.trunc(n0(gv(o, "weeks_known", 0))),
        spend: Math.trunc(n0(gv(o, "spend", 3))),
      })),
      teammates: hasOwn(s, "relation_A")
        ? [
            { name: "阿棠", relation: pyRound(n0(gv(s, "relation_A", 0))) },
            { name: "露露", relation: pyRound(n0(gv(s, "relation_B", 0))) },
            { name: "小满", relation: pyRound(n0(gv(s, "relation_C", 0))) },
          ]
        : [],
      // 「这一季你都做过什么」的计数：说真话、记住她说过的事、硬撑、租子断过几次
      stats: {
        true_talk: Math.trunc(n0(gv(s, "true_talk", 0))),
        clues: Object.values(s.clues || {}).filter((i: any) => i && i.state === "known").length,
        clues_wrong: Object.values(s.clues || {}).filter((i: any) => i && i.state === "wrong").length,
        pushed: Math.trunc(n0(gv(s, "pushed_while_spent", 0))),
        spent_weeks: Math.trunc(n0(gv(s, "spent_weeks", 0))),
        rent_missed: Boolean(gv(s, "rent_missed", false)),
        tiers: {
          dance: E.tierName(pyRound(n0(gv(s, "dance", 0)))),
          sing: E.tierName(pyRound(n0(gv(s, "sing", 0)))),
          mc: E.tierName(pyRound(n0(gv(s, "mc", 0)))),
        },
        left: {
          dance: E.nextTier(pyRound(n0(gv(s, "dance", 0)))),
          sing: E.nextTier(pyRound(n0(gv(s, "sing", 0)))),
          mc: E.nextTier(pyRound(n0(gv(s, "mc", 0)))),
        },
      },
    };
  }

  // ---------------- 序章 ----------------

  private _buildIntro(): void {
    const g = this.intro.group;
    this.push({ type: "text", title: g.name, body: this.intro.text });
    this.push({ type: "text", title: "", body: [this.intro.before_quote] });
    // 2026-11-15：序章的「上台之前三选一」删了。现在读完 before_quote，
    // 下一屏按「继续」就落定开局，直接取名。
    const c = (this.intro.choices || [{}])[0];
    const base = { ...this.intro.base_state };
    this.state = E.newState(this.world, c.id ?? null, null, this.rng);
    for (const [k, v] of Object.entries(base)) {
      if (typeof v === "number") (this.state as any)[k] = v;
    }
    // after_quote 本身就是一个数组（两句），不能再套一层方括号——
    // 套了会渲染成「一个段落里塞着两句话的数组」。
    this.push({ type: "text", title: "", body: this.intro.after_quote });
    this._buildName();
  }

  // ---------------- 取名 ----------------

  private _buildName(): void {
    const styles = (this.names.styles || []).map((st: any) => ({
      id: st.id,
      label: st.name,
      desc: gv(st, "desc", ""),
    }));
    this.push({
      type: "name",
      title: "海报上要印个名字",
      body: ["这个团的 C 位总得有个名字。想要哪一种？"],
      stage: "style",
      styles,
    });
  }

  pickStyle(sid: string): void {
    const st = (this.names.styles || []).find((x: any) => x.id === sid);
    const pool = [...(st.names || [])];
    this.name_style = sid;
    this.name_options = this.rng.sample(pool, Math.min(3, pool.length));
    this.queue.shift();
    this.push({
      type: "name",
      title: "挑一个",
      body: [gv(st, "desc", "")],
      stage: "pick",
      style: st.name,
      candidates: this.name_options,
    });
  }

  setName(nameIn: string | null | undefined): void {
    let name = String(nameIn ?? "").trim().slice(0, 8);
    if (!name) name = this.name_options.length ? this.name_options[0] : "小夏";
    this.name = name;
    this.state!.name = name;
    this.queue.shift();
    this.push({ type: "text", title: "", body: [`海报上印的是「${name}」。`] });
    if (this.allow_stance) {
      this._buildStance();
    } else {
      this._startWeek();
    }
  }

  // ---------------- 二周目：姿态 ----------------

  private _buildStance(): void {
    const sts = this.stances.map((st: any) => ({
      id: st.id,
      label: st.name,
      desc: gv(st, "desc", ""),
      line: gv(st, "line", ""),
    }));
    const body: string[] = [];
    const p = this.prev_season || {};
    if (p.name) {
      const bits = [`上一季，你走到了「${p.name}」`];
      const meta: string[] = [];
      if (p.week) meta.push(`第 ${Math.trunc(p.week)} 周`);
      if (p.stage !== undefined && p.stage !== null) meta.push(`舞台 ${p.stage}`);
      if (p.psyche !== undefined && p.psyche !== null) meta.push(`心理 ${p.psyche}`);
      if (meta.length) bits.push(meta.join("，"));
      body.push(bits.join("，") + "。");
    }
    body.push(
      "这一次，先想清楚你要什么。姿态不替你选线，也不替你交房租——" +
        "它只是让这一季往那个方向偏一点。",
    );
    this.push({
      type: "stance",
      title: "这一季，你想成为怎样的偶像",
      body,
      stances: sts,
    });
  }

  chooseStance(sid: string): void {
    let st = this.stances.find((x: any) => x.id === sid);
    if (st === undefined) st = { id: "none", name: "不选，照旧", bonus: {} };
    E.applyStance(this.state!, st);
    this.queue.shift();
    if (st.id === "none") {
      this.push({ type: "text", title: "", body: ["这一季，先不给自己定什么。"] });
    } else {
      this.push({
        type: "text",
        title: "",
        body: [`这一季，我给自己定的是「${st.name}」。`],
      });
    }
    this._startWeek();
  }

  // ---------------- 一周 ----------------

  /** 「周几晚上做点什么」这一屏（只返回 step，不往队列里塞）。 */
  private _wkChoice(): Step {
    const left = Game.ACT_SAT - n0(this.wk.act);
    const s = this.state!;
    const day = left > 0 ? 7 - left : 6;
    const DAY_CN = ["", "一", "二", "三", "四", "五", "六", "日"];
    const st = pyRound(s.stamina);
    let body: string[];
    if (left > 0) {
      body = [`周六之前还有 ${left - 1} 个晚上。`];
    } else {
      body = ["周五那一场刚下来，周六还有一场。"];
    }
    if (st < 15) body.push("身体一直是空的，脑子里像隔着一层。");
    return {
      type: "choice",
      title: `周${DAY_CN[day] || day}，晚上做点什么`,
      body,
      kind: "act",
      options: [
        {
          id: "dance",
          label: "练舞",
          desc: `体力 −18 · 钱 −40 · 舞 +${E.actGain(s, "dance")}${this._repeatNote(s, "dance")}`,
        },
        {
          id: "sing",
          label: "练唱",
          desc: `体力 −18 · 钱 −40 · 唱 +${E.actGain(s, "sing")}${this._repeatNote(s, "sing")}`,
        },
        {
          id: "mc",
          label: "练营业话术",
          desc: `体力 −10 · 钱 −20 · 营业 +${E.actGain(s, "mc")}${this._repeatNote(s, "mc")}`,
        },
        { id: "content", label: "拍内容发微博", desc: "体力 −8 · 人气 +1" },
        { id: "work", label: "开直播", desc: "体力 −22 · 钱 +380 · 人气 +2" },
        { id: "rest", label: "躺一整天", desc: "体力 +28 · 心理 +2" },
      ],
    };
  }

  /** 这一屏是谁在对面：优先实际角色名，其次场所。 */
  private _face(card: Card, slots: Record<string, Ota> | null, who?: Ota | null): string {
    const names: string[] = [];
    if (who && who.name) names.push(who.name);
    for (const [k, o] of Object.entries(slots || {})) {
      if (k === "speaker" && o === who) continue;
      const nm = (o || ({} as Ota)).name;
      if (nm && !names.includes(nm)) names.push(nm);
    }
    if (names.length) {
      if (names.length === 1) return names[0];
      return names.slice(0, 2).join("、") + (names.length > 2 ? "等" : "");
    }
    if (card.scene) return card.scene;
    return Game.SCENE[card.type ?? ""] ?? "";
  }

  /** 连着两晚做同一件事：第二天只涨一半，这句提示要写出来。 */
  private _repeatNote(s: State, act: string): string {
    // 只在真的减半（0.5）的动作上显示；拍内容 ×0.8、躺/开播不减，不能说瞎话
    if (gv(s, "_last_act", null) === act && (E.ACT_REPEAT[act] ?? 1.0) === 0.5) return "（连着做，减半）";
    return "";
  }

  /**
   * 第六周，还剩两个晚上：这一季跳完就不跳了吧？这是「现生快乐」那一类的入口。
   */
  private _maybeAskStay(): Step | null {
    const s = this.state!;
    if (s.week !== WEEKS || s.leave_asked) return null;
    if (this.acts_done < Game.ACT_LEFT - 2) return null;
    s.leave_asked = true;
    return {
      type: "choice",
      kind: "leave",
      title: "这个月还剩两个晚上",
      body: ["排班表贴在排练室门后面。这个月的最后两个晚上，我盯着看了很久。"],
      options: [
        { id: "stay", label: "再撑一周，把这一季跳完", desc: "都到这儿了，停下来反而空" },
        { id: "leave", label: "算了，这季跳完就不跳了", desc: "钱还是会紧，但晚上是自己的了" },
      ],
    };
  }

  chooseLeave(oid: string): boolean {
    const s = this.state!;
    s.chose_leave = oid === "leave";
    this.pending = null;
    this.queue.shift();
    let body: string[];
    let d: Record<string, number>;
    if (oid === "leave") {
      body = ["这两个晚上，我去了一趟便利店，买了两瓶酒，坐在桥边喝到很晚。"];
      d = { psyche: 4, stamina: 8 };
      s.psyche += 4;
      s.stamina += 8;
    } else {
      body = ["我把排班表折起来放进包里，第二天照常去排练了。"];
      d = { psyche: -2, stamina: -4 };
      s.psyche -= 2;
      s.stamina -= 4;
    }
    E.clamp(s);
    this.push({ type: "receipt", title: "这个月还剩两个晚上", body, delta: d });
    this.afterStep();
    return true;
  }

  chooseAct(aid: string): void {
    const s = this.state!;
    const before = snap(s);
    const ob = osnap(s);
    const rb = rsnap(s);
    E.doAct(s, aid, this.rng);
    this.acts_done += 1;
    this.queue.shift();
    const extra: string[] = [];
    if (s._last_act_spent) {
      extra.push("身体是空的，手上在动，人不在。");
      delete s._last_act_spent;
    }
    // 练功类：把「从几档到几档、离下一档还差多少」说清楚，
    // 否则玩家只看到体力掉，不知道自己练出了什么
    const key = ({ dance: "dance", sing: "sing", mc: "mc" } as Record<string, string>)[aid];
    if (key) {
      const v = pyRound((s as any)[key]);
      const left = E.nextTier(v);
      const now = `现在 ${v}，${E.tierName(v)}`;
      if (left) extra.push(now + `；再练 ${left} 点到下一档。`);
      else extra.push(now + "；已经压得住整场了。");
    }
    let actText = Game.ACT_TEXT[aid] ?? "";
    if (Array.isArray(actText)) actText = this.rng.choice(actText as string[]);
    this.push({
      type: "receipt",
      title: actText,
      body: extra,
      delta: delta(before, s),
      sticks: sticks(ob, s),
      mates: matesChanged(rb, s),
      skill: key ?? null,
      skill_now: key ? pyRound((s as any)[key]) : null,
      skill_tier: key ? E.tierName(pyRound((s as any)[key])) : null,
      skill_left: key ? E.nextTier(pyRound((s as any)[key])) : null,
    });
    this.afterStep();
  }

  // ---------------- 版聊 + 一张卡 ----------------

  /** 六个晚上排完之后的版聊：一句白天的碎话 + 路上遇上的一张卡。 */
  pushMidweek(): void {
    const s = this.state!;
    this.pending = null;
    if (s.stamina < 25) s.nights_stamina_low = n0(gv(s, "nights_stamina_low", 0)) + 1;
    if (s.stamina < 15) {
      s.psyche -= 5;
      s.spent_weeks = n0(gv(s, "spent_weeks", 0)) + 1;
      E.clamp(s);
      this.push({
        type: "receipt",
        title: "身体一直是空的",
        body: ["这周没睡够，礼拜三开始就在飘，对着人笑的时候知道自己在笑。"],
        delta: { psyche: -5 },
      });
    }
    let card = E.draw(s, this.world, this.rng, null, null, ["版聊"]);
    if (!card || !card.options) {
      this.push({ type: "text", title: "", body: ["今晚没人说话，我看了两眼就睡了。"] });
      return;
    }
    let slots = E.cast(s, card, this.rng, this.world);
    // 抽到新人卡但新人名额满了：换一张，别把老粉当「第一次来的人」演。
    let tries = 0;
    while (slots === null && E.wantsNewFace(card) && tries < 4) {
      tries += 1;
      card = E.draw(s, this.world, this.rng, null, null, ["版聊"]);
      if (!card || !card.options) break;
      slots = E.cast(s, card, this.rng, this.world);
    }
    if (slots === null || !card) {
      // 卡上要的人不在场、新生也没名额：这张卡根本演不起来。
      this.push({ type: "text", title: "", body: ["今晚没人说话，我看了两眼就睡了。"] });
      return;
    }
    const step = this._renderChat(card, slots);
    step._card = card;
    step._slots = slots;
    this.push(step);
  }

  /** 版聊上屏：把 messages 铺成聊天记录，引用的那条显示成小引用块。 */
  private _renderChat(card: Card, slots: Record<string, Ota>): Step {
    const cid = card.id;
    if (this.state !== null && cid) {
      if (!this.state.seen) this.state.seen = [];
      this.state.seen.push(cid);
    }
    const msgs: any[] = [];
    for (const m of card.messages || []) {
      const who = m.from || "speaker";
      const name =
        who === "you" ? "你" : ((slots || {})[who] || ({} as Ota)).name || "对方";
      let quoted = "";
      const qi = m.quote;
      if (typeof qi === "number" && qi >= 0 && qi < msgs.length) quoted = msgs[qi].text;
      msgs.push({
        who: name,
        me: who === "you",
        text: this._fill(gv(m, "text", ""), slots),
        time: gv(m, "time", ""),
        quote: quoted,
      });
    }
    return {
      type: "chat",
      title: gv(card, "title", "版聊"),
      label: "版聊",
      time: gv(card, "time", ""),
      no: card.no, // 全池序号（卡角标）
      messages: msgs,
      options: (card.options || []).map((o: Option) => ({
        id: o.id,
        label: this._fill(gv(o, "label", ""), slots),
        desc: this._fill(gv(o, "desc", ""), slots),
      })),
    };
  }

  /**
   * 占位符填充。这是全局最热的函数：4606 个汉字文案全靠它落到玩家眼前。
   *
   * 顺序不能变——她自己的细节（猫叫什么、常点哪杯、老家在哪、最爱哪首）
   * 必须在最后那道「兜成对方」之前换掉，否则「猫叫『对方』」。
   */
  private _fill(t: string | null | undefined, slots: Record<string, Ota> | null): string {
    if (!t) return t || "";
    let out = t;
    for (const [k, o] of Object.entries(slots || {})) {
      if (!o) continue;
      out = out.split(`{{${k}.ta}}`).join("TA");
      out = out.split(`{{${k}}}`).join(o.name);
    }
    const mem = E.protaMemory(this.state!);
    for (const [k, v] of Object.entries(mem)) {
      if (!v) continue;
      const token = `{{${k}}}`;
      if (out.includes(token)) {
        out = out.split(token).join(String(v));
        // 她当着玩家的面说过这个细节了：登记进「已揭示」，收场拷问优先出这些
        const rec = (this.state!._prota_revealed as string[] | undefined) ?? [];
        if (!rec.includes(k)) rec.push(k);
        this.state!._prota_revealed = rec;
      }
    }
    // 还有没填上的占位符（选角没落地、或者卡要的槽跟 casting 声明的不一致）：
    // 绝不能把 {{xxx}} 原样端到玩家眼前。这里兜成「对方」，至少读得通。
    if (out.includes("{{")) {
      out = out.replace(/\{\{[a-zA-Z_]+\}\}/g, "对方");
      out = out.split("{{").join("").split("}}").join("");
    }
    return out;
  }

  /**
   * 卡面正文。回考卡里的 `{truth}` 必须在「上屏这一刻」就换掉——
   * 她第一次说这个细节时真值就得掷死，不能等玩家点了选项才定。
   *
   * 但两张卡的写法不一样：她说（say）要把真话讲出来，她问（ask）不能——
   * 问句原样带真值就等于把答案印在题干上。所以 ask 一律抹成「那个」，
   * 靠三个选项交代范围。
   */
  private _cardBody(card: Card, slots: Record<string, Ota>): string[] {
    let body = [this._fill(gv(card, "narrative", ""), slots)];
    const meta = card._meta || {};
    const cid = meta.clue;
    const stage = meta.rq_stage;
    if (cid && (stage === "say" || stage === "ask")) {
      const word = stage === "say" ? E.ensureTruth(this.state!, cid, this.rng) : "那个";
      body = body.map((b) => b.split("{truth}").join(word || "那个"));
    }
    return body;
  }

  /** 回考「她问的是哪一样」：选项顺序按本局掷的排，别让玩家背「第一个」。 */
  private _cardOpts(card: Card): Option[] {
    let opts = [...(card.options || [])];
    const meta = card._meta || {};
    if (meta.rq_stage === "ask") opts = this._askOptions(card, opts);
    return opts;
  }

  private _renderCard(card: Card, slots: Record<string, Ota>): Step {
    // 上屏即登记：draw() 会拿这份名单给「这一季见过的卡」降权（不硬禁）。
    const cid = card.id;
    if (this.state !== null && cid) {
      if (!this.state.seen) this.state.seen = [];
      this.state.seen.push(cid);
    }
    const meta = card._meta || {};
    const rq = meta.rq_stage;
    const body = this._cardBody(card, slots);
    if (rq === "ask") body.push("（她问的是哪一样。）");
    // 排练室那些事：谁在场就说谁。卡上写了 {{A}} 就是认准了阿棠，
    // 没写的话，由第一个选项的得失推一个出来（同一个人）
    let castName = "";
    for (const [plain, nm] of Object.entries(MATE_TEXT)) {
      if ((card.narrative || "").includes(plain)) {
        castName = nm;
        break;
      }
    }
    if (!castName) {
      for (const o of card.options || []) {
        castName = whoHit(card, o);
        if (castName) break;
      }
    }
    // 选完才给数值：选项本身只写「我打算怎么做」
    const opts = this._cardOpts(card);
    let face = this._face(card, slots);
    if (castName && (face === "" || face === "排练室")) face = "排练室 · " + castName;
    return {
      type: "card",
      title: card.title,
      face,
      recall: rq === "ask",
      compact: !["OTA记忆"].includes(card.type),
      body,
      no: card.no, // 全池序号（卡角标）
      options: opts.map((o: Option) => ({
        id: o.id,
        label: this._fill(gv(o, "label", ""), slots),
        desc: rq === "ask" ? "" : this._fill(gv(o, "desc", ""), slots),
      })),
    };
  }

  /**
   * 回考三选一的上屏顺序：按这一局锁定的真值重新排。
   *
   * 卡数据里三道题的正确答案都写在 pick_0（生成脚本为了让 diff 稳定），
   * 真值一随机就必须重排，否则玩家背「第一个」就永远答对。
   */
  private _askOptions(card: Card, opts: Option[]): Option[] {
    const meta = card._meta || {};
    const cid = meta.clue;
    if (!cid || opts.length < 2) return opts;
    const order = E.askOrder(this.state!, cid, opts.length, this.rng);
    if (order.length !== opts.length) return opts;
    return order.map((i: number) => opts[i]);
  }

  /** 回考答完，按原型取她那一句。 */
  private _rqReply(card: Card, o: Option, slots: Record<string, Ota>): string {
    const pick = o.rq_pick;
    if (!pick) return "";
    const meta = card._meta || {};
    const who = (slots || {})[pick.slot || "speaker"] || ({} as Ota);
    const arch = who.archetype || "gravity";
    const cid = pick.clue;
    // 真值从「本局锁定表」里取——她随口说那一屏定下的那个词。
    const truth = cid ? E.ensureTruth(this.state!, cid, this.rng) : "";
    const correct = Boolean(truth) && String(o.label || "").trim() === truth;
    const tab = meta[correct ? "react_good" : "react_bad"] || {};
    let txt = tab[arch] || tab.gravity || "";
    if (!txt) return "";
    const wrong = o.label || "";
    return String(txt).split("{truth}").join(truth).split("{wrong}").join(wrong);
  }

  chooseCard(oid: string): any {
    if (!this.pending) {
      // 已经结算过（比如双击 / 回包重复）：把这一屏当成「继续」
      return this.advance();
    }
    if (this.pending[0] === "line") {
      // 剧情线的卡被当成普通卡点了（line 标记丢了）：转给 chooseStory
      return this.chooseStory(oid);
    }
    if (this.pending[0] === "rtalk") {
      // 「谈一谈」那张卡被当成普通卡点了：转给 chooseRomanceTalk
      return this.chooseRomanceTalk(oid);
    }
    if (this.pending[0] === "talk") {
      // 特典那张卡被当成普通卡点了：屏幕上是特典卡才转过去，
      // 否则就是被别的卡抢了 pending
      if (this.queue.length && this.queue[0].talk) return this.chooseTalk(oid);
      if (this.queue.length && this.queue[0]._card) {
        this.pending = ["card", this.queue[0]._card, this.queue[0]._slots || {}];
        return this.chooseCard(oid);
      }
    }
    const cur: Step = this.queue.length ? this.queue[0] : {};
    if (this.pending[0] === "card" && cur._card) {
      // 屏幕上的卡自己带一份（周末连排时 pending 可能已经被下一张换掉）
      let card = this.pending[1];
      if (cur._card !== card) {
        card = cur._card;
        this.pending = ["card", card, cur._slots || this.pending[2]];
      }
    }
    let card: Card = this.pending[1];
    let slots: Record<string, Ota> = this.pending[2];
    // 这一屏显示的是不是 pending 那张卡？周末连排几张时 pending 会被后一张换掉，
    // 点开的是前一张，就得按队列里那一张重新取。
    const shownT = this.queue.length ? this.queue[0].title || "" : "";
    if (shownT && shownT !== (card.title || "")) {
      for (const x of this.queue) {
        if (x.type === "card" && (x.title || "") === shownT) {
          if (x.talk) return this.chooseTalk(oid);
          if (x._card) {
            card = x._card;
            slots = x._slots || slots;
          }
          break;
        }
      }
    }
    const o = (card.options || []).find((x: Option) => x.id === oid)!;
    const before = snap(this.state!);
    const ob = osnap(this.state!);
    const rb = rsnap(this.state!);
    const meta = card._meta || {};
    E.applyOption(this.state!, o, this.rng, slots, card);
    // ---- 私联收场：这一题对没对，往前挪一格
    if (meta.finale) {
      const fin: any = this.state!._finale || {};
      const truth = E.ensureTruth(
        this.state!,
        (o.rq_pick || {}).clue,
        this.rng,
      );
      if (truth && String(o.label || "").trim() === truth) {
        fin.ok = Math.trunc(n0(fin.ok)) + 1;
      }
      fin.idx = Math.trunc(n0(fin.idx)) + 1;
      this.state!._finale = fin;
    }
    // ---- 收场那两条路：沉沦去「唯一」，断联去失控
    if (meta.finale_choice) {
      const fin: any = this.state!._finale || {};
      if (oid === "cut_clean") {
        // 说了别来，事情却没停。这一段玩家点不了，只有数字在走。
        fin.phase = "collapse";
        fin.cidx = 0;
        fin.script = this._collapseScript();
        this.state!._collapse = true;
        this.state!._collapse_who =
          ((slots || {}).ta || ({} as Ota)).name;
        this.state!.flags.add("final_collapse");
      } else {
        // 沉沦：不公开也不断，就这么一直下去。这就是「唯一」。
        fin.phase = "done";
        this.state!.flags.add("truly_seen");
      }
      this.state!._finale = fin;
    }
    if (!this.state!.cooldown) this.state!.cooldown = {};
    this.state!.cooldown[card.id] = Math.trunc(n0(gv(card, "cooldown", 3)));
    this.state!._extra_cards = n0(gv(this.state!, "_extra_cards", 0));
    this.pending = null;
    this.queue.shift();
    // 这一屏上的那张卡点完就真没了：把队列里其余同一张卡的副本也拿掉。
    // 队列里排着好几张卡时（这周几件事 + 剧情线 + 特典），同一张会在队列里留副本，
    // 等轮到副本时玩家已经在别的一周了。
    this.queue = this.queue.filter(
      (x) => !((x.type === "card" || x.type === "chat") && x._card === card),
    );
    // 回执不能只剩一个标题。选项没写 note 时退到 desc（那是「这么做的后果」），
    // 再没有就退一句中性的收束——总之不能给玩家一屏空白。
    let body: string[] = [];
    for (const x of [o.note, o.desc, "就这样吧。"]) {
      if (x && String(x).trim()) {
        body = [this._fill(x as string, slots)];
        break;
      }
    }
    // 回考：她问的那件事，我答对/答错了，她当场怎么接——这一句才是玩家想看的反馈
    const reply = this._rqReply(card, o, slots);
    if (reply) body.unshift(reply);
    for (const d of (o.delayed || []).slice(0, 1)) {
      if (d && d.note) {
        body.push(`（${gv(d, "when", "")}·${this._fill(d.note, slots)}）`);
      }
    }
    // 回复插队首：选了哪张卡，那条回复立刻跟在后面
    this.queue.unshift({
      type: "receipt",
      title: this._fill(gv(o, "label", ""), slots),
      body,
      delta: delta(before, this.state!),
      sticks: sticks(ob, this.state!),
      mates: matesChanged(rb, this.state!),
      face: this._face(card, slots),
    });
    this.afterStep();
  }

  /**
   * 周末那一场：只算演出、只把这一屏排出去；
   * 券账/特典/结算由 `stepWeek` 接着排。
   */
  pushLive(last = false, sunday = false): void {
    const s = this.state!;
    const rng = this.rng;
    const fatigue = ((s.stamina - 50) / 50) * 5.0;
    let sc = E.stageScore(s) + fatigue + rng.uniform(-5, 5);
    if (sunday) sc -= 3.5; // 周日加场：人少一点，嗓子也哑了
    let tier: string;
    let lines: string[];
    if (sc >= 64) {
      tier = "神场";
      lines = ["有一瞬间我忘了自己在哪，台下的声音是压过去的那种。"];
      E.addFame(s, 8);
      s.psyche += 3;
      s.gorshou = n0(gv(s, "gorshou", 0)) + 1;
      for (const o of s.ota) o.stick += 3;
    } else if (sc >= 54) {
      tier = "好场";
      lines = ["下来的时候 staff 说我今天眼睛是亮的。"];
      E.addFame(s, 5);
      s.psyche += 1;
      for (const o of s.ota) o.stick += 2;
    } else if (sc >= 44) {
      tier = "平场";
      lines = ["跳完了，不出错，也就跳完了。"];
      E.addFame(s, 2);
    } else if (sc >= 34) {
      tier = "冷场";
      lines = ["台下没坐满，掌声落下来的时候散得很快。"];
      s.psyche -= 4;
      for (const o of s.ota) o.stick -= 1.5;
    } else {
      tier = "翻车";
      lines = ["第二段走位踩空了半步，我笑了一下，把下一个动作接过去。"];
      s.psyche -= 8;
      s.enjou += 3;
      for (const o of s.ota) o.stick -= 2.5;
    }
    s.max_single = Math.max(n0(s.max_single), sc);
    if (tier === "冷场" || tier === "翻车") {
      s.blew_it = Math.trunc(n0(gv(s, "blew_it", 0))) + 1;
    }
    if (s.psyche < 20) s.played_while_collapsing = true;
    E.clamp(s);
    const warm = E.warmOta(s);
    // 每场各算各的账（人气决定今天谁来、来几个），state 里累加这一周的券数与
    // 收入，结算把所有场次加总——券账屏展示的钱就是会进钱包的钱。
    this._bill = B.weeklyBill(s, warm);
    s._week_tickets = n0(gv(s, "_week_tickets", 0)) + this._bill.tickets;
    s._week_income = n0(gv(s, "_week_income", 0)) + this._bill.yen;
    this._collectWeekExtras(warm);
    this.push({
      type: "live",
      title: sunday ? `周日·${tier}` : last ? `周六·${tier}` : `周五·${tier}`,
      body: lines,
      tier,
      score: pyRound(sc, 1),
      delta: { fame: pyRound(s.fame), psyche: pyRound(s.psyche) },
    });
  }

  private _billStep(sunday = false): Step {
    return {
      type: "bill",
      title: sunday ? "周日这一场的券" : "这一场的券",
      body: [`券 ${this._bill.price} 块一张。买了券的人，才能排到桌子前面坐一会儿。`],
      bill: this._bill,
    };
  }

  /**
   * 这一周的事：三张卡、她的话、运营那条路、特典那张卡，全部先算好放着。
   *
   * `pushLive()` 一周会跑三次（周五、周六、周日）。「累不累、接不接运营、
   * 这季跳不跳完」都是一次性提问，各自只生成一次：生成时就把 asked 标志
   * 立起来了。所以这里得把它们攒进 `wk.extra`，不能每场拿新结果整体覆盖。
   *
   * 同理，`otaPick` 也有副作用（抽到 ask 卡就把线索标成已问、上冷却），
   * 所以一周只能抽一次。
   */
  private _collectWeekExtras(warm: Ota[]): void {
    const wk = this.wk;
    if (wk._prep) return;
    wk._prep = 1;
    wk.events = this._drawWeekEvents();
    const have = new Set((wk.extra as Step[]).map((x) => x.kind));
    for (const st of [this._maybeAskTired(warm), this._maybeAskOffer(), this._maybeAskStay()]) {
      if (st && !have.has(st.kind)) {
        wk.extra.push(st);
        have.add(st.kind);
      }
    }
    wk.talk = this._makeTalk(warm);
  }

  private _makeTalk(warm: Ota[]): Step | null {
    if (!warm.length) return null;
    const s = this.state!;
    const names = warm
      .map(
        (o) =>
          o.name +
          (!gv(o, "is_seed", true) && gv(o, "met_week", null) === s.week
            ? "（第一次来）"
            : ""),
      )
      .join("、");
    let [card, who] = E.otaPick(s, this.world, this.rng, warm);
    if (!(card && who)) {
      return { type: "text", title: "特典", body: [`留在后面等着的是${names}。`] };
    }
    let slots = E.cast(s, card, this.rng, this.world);
    // 新人卡（hatch_only）生不出人时，卡就作废——不能拿今天留下来的老粉顶上去，
    // 否则「第一次来的人」演出来的是第零排那张熟了的脸。
    // 注意：Python 的空 dict 是 falsy，JS 的 {} 是真值。cast() 在卡没声明 casting 时
    // 返回的就是 {}，所以这里必须判「没有键」，不能只判 null。
    let tries = 0;
    while (emptySlots(slots) && E.wantsNewFace(card) && tries < 4) {
      tries += 1;
      [card, who] = E.otaPick(s, this.world, this.rng, warm);
      if (!(card && who)) {
        return { type: "text", title: "特典", body: [`留在后面等着的是${names}。`] };
      }
      slots = E.cast(s, card, this.rng, this.world);
    }
    if (emptySlots(slots) && E.wantsNewFace(card)) {
      return { type: "text", title: "特典", body: [`留在后面等着的是${names}。`] };
    }
    if (emptySlots(slots)) {
      // 选角没落地：把这张卡自己声明的每个槽都指给「今天留下来的人」。
      // 以前这里只塞 speaker，卡要的槽叫 nightowl/devotee 时就填不上，
      // 正文会顶着裸占位符上场（「特典突然一张残卡」就是这么来的）。
      slots = {};
      for (const cs of card.casting || []) {
        if (cs.slot) slots[cs.slot] = who!;
      }
      if (!slots.speaker) slots.speaker = who!;
    }
    // 走到这里 slots 一定非空（空的和 null 都在上面被拦掉了），但 TS 看不穿
    // `emptySlots()`，所以这里收一个局部变量明确收口。
    const finalSlots: Record<string, Ota> = slots ?? {};
    const step = this._renderTalk(card, finalSlots, who!);
    step.talk = true;
    step._talk = ["talk", card, finalSlots];
    return step;
  }

  private _drawWeekEvents(): Step[] {
    const out: Step[] = [];
    const used = new Set<string>();
    let teamN = 0;
    const s = this.state!;
    const spots = Game.EVENT_SPOTS;
    let tries = 0;
    // 兑现卡优先：上周埋下的那件事这周回来找你，先占事件位。
    // 只给一次机会——这周排不进去（要的人不在场、位子已经满了），
    // 就当场作废，不再拖到下周；埋下的账不该越滚越久。
    const dueIds: string[] = Array.isArray(s._due_cards) ? s._due_cards : [];
    s._due_cards = [];
    if (dueIds.length) {
      const byId = new Map<string, Card>();
      for (const c of this.world.cards) byId.set(c.id, c);
      for (const cid of dueIds) {
        if (out.length >= Game.WEEK_EVENTS) break;
        const card = byId.get(cid);
        if (!card || !card.options || used.has(card.id)) continue;
        const slots = E.cast(s, card, this.rng, this.world);
        if (slots === null) continue;
        used.add(card.id);
        if (Game.TEAM_TYPES.includes(card.type)) teamN += 1;
        const step = this._renderCard(card, slots);
        step._card = card;
        step._slots = slots;
        step.origin = "week";
        out.push(step);
      }
    }
    while (out.length < Game.WEEK_EVENTS && tries < spots.length + Game.WEEK_EVENTS) {
      const idx = Math.trunc(n0(gv(s, "_ev_idx", 0)));
      const kinds = spots[idx % spots.length];
      tries += 1;
      s._ev_idx = idx + 1;
      let card = E.draw(s, this.world, this.rng, null, null, kinds);
      if (!card || !card.options || used.has(card.id)) {
        card = E.draw(s, this.world, this.rng, null, null, Game.EV_FALLBACK);
      }
      if (!card || !card.options || used.has(card.id)) {
        card = E.draw(
          s,
          this.world,
          this.rng,
          null,
          null,
          Game.EV_FALLBACK.filter((k) => k !== "ambient"),
        );
      }
      // 团里的戏一周最多一场：多了会让人觉得整季都在跟队友吵架
      if (card && Game.TEAM_TYPES.includes(card.type)) {
        if (teamN >= 1 || !kinds.some((k) => Game.TEAM_TYPES.includes(k))) {
          card = E.draw(s, this.world, this.rng, null, null, [
            "外部", "external", "日常", "daily",
            "OTA互动", "OTA相处的瞬间", "ambient", "positive",
            "同行",
          ]);
        }
      }
      if (card && Game.TEAM_TYPES.includes(card.type)) teamN += 1;
      if (!card || !card.options || used.has(card.id)) continue;
      used.add(card.id);
      const slots = E.cast(s, card, this.rng, this.world);
      if (slots === null) {
        // 演不起来（要的人不在场）：这张算没抽到，继续补，别塞一张残卡进队列
        continue;
      }
      const step = this._renderCard(card, slots);
      step._card = card;
      step._slots = slots;
      step.origin = "week";
      out.push(step);
    }
    return out;
  }

  /**
   * 季中之后、我这一季一次真话都没说过、嘴上已经全是现成话的时候，
   * 她会当面问一句「你是不是有点累」。回什么，决定这一季会不会变成空心。
   */
  private _maybeAskTired(warm: Ota[]): Step | null {
    const s = this.state!;
    if (s.empty_asked || s.week < 3) return null;
    const t = Math.trunc(n0(gv(s, "truth_pick", 0)));
    const f = Math.trunc(n0(gv(s, "safe_pick", 0)));
    if (t + f < 2 || t / (t + f) > 0.25) return null;
    let who: Ota | null = null;
    for (const o of warm || []) {
      if (n0(gv(o, "stick", 0)) >= 45) {
        who = o;
        break;
      }
    }
    if (who === null) return null;
    s.empty_asked = true;
    s.empty_asked_who = who.name;
    this.pending = ["empty", null, null];
    return {
      type: "choice",
      kind: "empty",
      title: "她问了一句",
      body: [
        `收桌子的时候，${who.name} 还没走。她把券放在桌角，没递过来，` +
          "看了一会儿才说：『你是不是有点累。』",
      ],
      options: [
        {
          id: "reply",
          label: "笑一下：『没有啊，挺好的。』",
          desc: "这句我今天已经说过好几遍了",
        },
        {
          id: "truth",
          label: "停一下，说：『有点。』",
          desc: "说出来的时候，声音自己先软了",
        },
      ],
    };
  }

  chooseEmpty(oid: string): void {
    const s = this.state!;
    s.empty_choice = oid === "reply" ? "reply" : "truth";
    this.pending = null;
    this.queue.shift();
    let body: string[];
    let d: Record<string, number>;
    if (oid === "reply") {
      s.safe_pick = Math.trunc(n0(gv(s, "safe_pick", 0))) + 1;
      s.template = Math.min(1.0, s.template + 0.05);
      body = ["她说『那就好』，把券推过来，笑了一下。", "那两秒钟里我没说话，她也没再问。"];
      d = { psyche: -4 };
    } else {
      s.truth_pick = Math.trunc(n0(gv(s, "truth_pick", 0))) + 1;
      s.true_talk = Math.trunc(n0(gv(s, "true_talk", 0))) + 1;
      s.template = Math.max(0.0, s.template - 0.05);
      body = ["她愣了一下，说『嗯』。", "后来她什么都没再问，我也没再多说。"];
      d = { psyche: 3, fame: -1 };
    }
    E.clamp(s);
    this.push({ type: "receipt", title: "她问了一句", body, delta: d });
    this.afterStep();
  }

  // ---------------- 运营递来的那条路（守住本心的入口） ----------------

  /**
   * 季中之后，运营来递那条「会火的路」。这是我这一季唯一一次当面说不的机会，
   * 结局「守住本心」就靠它。引擎里早就设了 offer_seen / offer_choice，
   * 可界面从来没把这件事问出来——那条路一直是被默默拒绝的。
   */
  private _maybeAskOffer(): Step | null {
    const s = this.state!;
    if (s.week < Game.OFFER_FROM_WEEK || s.offer_choice || s.offer_asked) return null;
    s.offer_asked = true;
    if (!s.offer_kind) {
      const offers = ["炒 CP", "讲以前那个团", "接一条擦边商务"];
      s.offer_kind = offers[(s.week - 3) % 3];
    }
    const kind = s.offer_kind;
    const [head] = Game.OFFER_TEXT[kind] ?? ["运营递过来一个能火的路子。", "这条能火，做不做？"];
    return {
      type: "choice",
      kind: "offer",
      title: "运营找我谈话",
      face: "后台走廊",
      body: [head],
      options: [
        { id: "refuse", label: "摇了摇头：『这个我不做。』", desc: "话一出口，走廊里安静了一拍" },
        { id: "take", label: "点头：『行，就按这个来。』", desc: "那条路是真的会火，也真的会烧" },
      ],
    };
  }

  chooseOffer(oid: string): void {
    const s = this.state!;
    s.offer_choice = oid === "refuse" ? "refuse" : "take";
    this.pending = null;
    this.queue.shift();
    let body: string[];
    let d: Record<string, number>;
    if (s.offer_choice === "refuse") {
      s.psyche -= 3;
      body = [
        "我说这个我不做。运营看了我一眼，把那份东西收回去，说『行，那就再想想』。",
        "那天晚上我睡得很沉，这件事没再提过。",
      ];
      d = { psyche: -3 };
    } else {
      s.enjou = n0(gv(s, "enjou", 0)) + 30;
      const gained = E.addFame(s, 12);
      body = [
        "我点头了。第二周超话就炸了，票是真的卖得比以前快。",
        "也有人在板子上把我的名字和那件事一起挂了出来。",
      ];
      d = { fame: gained === Math.trunc(gained) ? Math.trunc(gained) : pyRound(gained, 1) };
    }
    E.clamp(s);
    this.push({ type: "receipt", title: "运营找我谈话", body, delta: d });
    this.afterStep();
  }

  private _renderTalk(card: Card, slots: Record<string, Ota>, who: Ota): Step {
    // 特典也走回考卡（「她随口说的一件事」就在特典池里）：
    // 走这条路以前直接塞 narrative，{truth} 就顶着一串花括号上场了。
    const meta = card._meta || {};
    const rq = meta.rq_stage;
    const body = this._cardBody(card, slots);
    if (rq === "ask") body.push("（她问的是哪一样。）");
    const opts = this._cardOpts(card);
    return {
      type: "card",
      talk: true,
      title: card.title,
      face: this._face(card, slots, who),
      speaker: who.name,
      recall: rq === "ask",
      compact: !["OTA记忆"].includes(card.type),
      body,
      no: card.no, // 全池序号（卡角标）
      options: opts.map((o: Option) => ({
        id: o.id,
        label: this._fill(o.label, slots),
        desc: rq === "ask" ? "" : this._fill(gv(o, "desc", ""), slots),
      })),
      _card: card,
      _slots: slots,
    };
  }

  chooseTalk(oid: string): any {
    if (!this.pending) return this.advance();
    const [, card, slots] = this.pending as [string, Card, Record<string, Ota>];
    const o = (card.options || []).find((x: Option) => x.id === oid)!;
    const before = snap(this.state!);
    const ob = osnap(this.state!);
    const rb = rsnap(this.state!);
    E.applyOption(this.state!, o, this.rng, slots, card);
    if (!this.state!.cooldown) this.state!.cooldown = {};
    this.state!.cooldown[card.id] = Math.trunc(n0(gv(card, "cooldown", 3)));
    this.pending = null;
    this.queue.shift();
    let body: string[] = [this._fill(gv(o, "note", ""), slots)].filter((x) => x);
    if (!body.length) {
      // 选项没写 note：退到 desc，别给一屏只有标题的回执
      body = [this._fill(gv(o, "desc", ""), slots)].filter((x) => x);
    }
    const reply = this._rqReply(card, o, slots);
    if (reply) body.unshift(reply);
    // 同 chooseCard：回复插队首，选完立刻看到
    this.queue.unshift({
      type: "receipt",
      title: this._fill(gv(o, "label", ""), slots),
      body,
      delta: delta(before, this.state!),
      sticks: sticks(ob, this.state!),
      mates: matesChanged(rb, this.state!),
      face: this._face(card, slots),
    });
    this.afterStep();
  }

  /** 「谈一谈」那张卡的落子：收下表态或只攒一点 risk。 */
  chooseRomanceTalk(oid: string): any {
    if (!this.pending) return this.advance();
    const [, talk, slots] = this.pending as [string, any, Record<string, Ota>];
    const o = (talk.options || []).find((x: Option) => x.id === oid)!;
    const s = this.state!;
    const before = snap(s);
    E.applyOption(s, o, this.rng, slots, talk as Card);
    // 关键：applyOption 只把 flag 塞进 s.flags，risk 的数值累积在 applyStoryFlags 里
    E.applyStoryFlags(s, o);
    s._rtalk_week = s.week;
    E.clamp(s);
    this.pending = null;
    this.queue.shift();
    let body: string[] = [this._fill(gv(o, "note", ""), slots)].filter((x) => x);
    if (!body.length) body = [this._fill(gv(o, "desc", ""), slots)].filter((x) => x);
    this.push({
      type: "receipt",
      title: this._fill(gv(o, "label", ""), slots),
      body,
      delta: delta(before, s),
      face: (slots.ta as Ota)?.name || "阿棠",
    });
    this.afterStep();
  }

  /** 每周末记一行「历史大事」的底账；只记真发生过的值。 */
  private _journalWeek(week: number): void {
    const s = this.state!;
    const line = E.mainline(s) || "";
    const st = (s.story || {})[line] || ({} as any);
    const row = {
      week: Math.trunc(week),
      stage: pyRound(s.stage),
      tier: E.tierName(s.stage),
      psyche: pyRound(s.psyche),
      money: pyRound(s.money),
      enjou: pyRound(s.enjou),
      banzi: pyRound(s.banzi),
      kaibox: pyRound(s.kaibox),
      template: pyRound(s.template, 2),
      truth_rate: pyRound(E.truthRate(s), 2),
      relavg: pyRound(E.relavg(s)),
      line,
      line_stage: Math.trunc(n0(gv(st, "stage", -1))),
      shiren_stage: Math.trunc(n0(gv((s.story || {}).shiren || {}, "stage", -1))),
      rent_missed: Boolean(gv(s, "rent_missed", false)),
      chose_leave: Boolean(gv(s, "chose_leave", false)),
      offer_refused: s.offer_choice === "refuse",
    };
    if (!s.log) s.log = [];
    const log = s.log;
    if (log.length && log[log.length - 1].week === week) log[log.length - 1] = row;
    else log.push(row);
  }

  settleWeek(): void {
    const s = this.state!;
    if (gv(s, "_settled_week", null) === s.week) {
      // 这一周已经结算过了（特典卡被打断或多点了一次），别再推一次
      return;
    }
    s._settled_week = s.week;
    const before = snap(s);
    // 一周的券全部加总（每场各自记账，state 里累加；旧档没有累计时退回单场账）
    let income = n0(gv(s, "_week_income", 0));
    let tickets = n0(gv(s, "_week_tickets", 0));
    if (income === 0 && tickets === 0) {
      const bill = this._bill || B.weeklyBill(s, E.warmOta(s));
      income = bill.yen;
      tickets = bill.tickets;
    }
    const fee = s.week === 1 ? 160 : 620;
    s.money += income - fee;
    if (s.money < 0) {
      s.psyche -= 10;
      s.stamina -= 5;
      s.money = 0;
    }
    s._income_last = income;
    if (income >= 560) s.psyche += 2;
    if (income < 240) {
      s.low_income_weeks = n0(gv(s, "low_income_weeks", 0)) + 1;
      s.psyche -= 6;
    }
    E.clamp(s);
    // 延迟后果：卡面上写「下周 / 下个月」的，到了就结
    // （这条原来只在引擎跑局里生效，界面上写了「下周」却什么都不会发生）
    const born = E.settleDelayed(s, this.world, this.rng);
    E.coolDown(s);
    E.clamp(s);
    this._journalWeek(s.week);
    const doneWeek = s.week;
    const body = [`一共卖出 ${tickets} 张券，进账 ${pyRound(income)} 块；场租和分成 ${fee} 块。`];
    if (born && born.length) body.push(`她把朋友带来了：${born.join("、")}。`);
    const panel: Step = {
      type: "panel",
      title: `第 ${doneWeek} 周结算`,
      body,
      delta: delta(before, s),
      kind: "week",
    };
    this._bill = null;
    // 先把周号推上去，再 push 结算屏：afterStep 靠
    // `_settled_week == week` 判断「这一周收完了」，顺序反了会连着结算到季末。
    s.week = doneWeek + 1;
    s._settled_week = doneWeek;
    for (const o of s.ota) o.weeks_known = n0(o.weeks_known) + 1;
    // 结算屏放在最前面；它后面接哪一格，等玩家按「继续」时 afterStep 再决定
    this.push(panel);
  }

  /**
   * 新的一周：周初那几屏 + 房租 + 这一周的剧情线那一拍。
   *
   * 不在这里调 `afterStep`——周流程是 `afterStep` 自己循环推的，这里排完就返回。
   */
  private _startWeek(): void {
    const s = this.state!;
    // 「这一周已经开过头」的标记在这里落库：setName / startWeekNext 会直接调
    // _startWeek，不走 afterStep 的守卫——以前每个新档第 1 周都开两次周，
    // 房租真扣款之后，第二次开局还会拿扣完的钱误判「房租没交上」。
    s._week_started = s.week;
    s._week_tickets = 0;
    s._week_income = 0;
    this.acts_done = 0;
    this.wk = {
      act: 0, mid: 0, fri: 0, sat_act: 0, sat: 0,
      bill: 0, sun: 0, bill2: 0, sun_talk: 0,
      events: [], extra: [], talk: null,
    };
    s._extra_cards = 0;
    s._gap_done = -1;
    s._mid_done = false;
    // 推线周期号要跟着周走：`_thisWeek` 比的是「本周有没有推过这条线」，
    // 而 tick 以前只在抽到线之后才更新，于是上周推过的那条线这周开头就被误判成
    // 「本周已推」，`lineStage` 直接返回 null——私联从此再也轮不到，8 周只走一拍。
    s._line_tick = s.week;
    // 房租：交得起就真扣；交不上才是下面那套惩罚
    let rentPaid = false;
    if (s.week % 2 === 1 && s.money >= E.RENT) {
      s.money -= E.RENT;
      rentPaid = true;
    }
    const rent = s.week % 2 === 1 ? (rentPaid ? "，房租已经交了" : `，这周还要交 ${E.RENT} 块房租`) : "";
    const body = [`六天晚上，周五、周六各一场 live。手里还剩 ${pyRound(s.money)} 块${rent}。`];
    this.push({ type: "text", title: `第 ${s.week} 周`, body });
    if (s.week % 2 === 1 && !rentPaid) {
      s.psyche -= 18;
      s.stamina -= 10;
      s.rent_missed = true;
      E.clamp(s);
      this.push({
        type: "receipt",
        title: "房租没交上",
        body: ["房东在门口站了一会儿，没说话。这天晚上我在排练室的沙发上睡的。"],
        delta: { psyche: -18, stamina: -10 },
      });
    }
    // 末周开头：「收场」就是那一晚。越了线就必到，不等 stage4 走完。
    if (E.shirenFinaleReady(s, this.world)) {
      this._beginFinale();
      return;
    }
    // 末周开头：恋爱线还没到收场，就把「那一晚」排上（不再等 stage4 走完）。
    const force =
      E.mainline(s) === "romance" &&
      Math.trunc(n0(gv((s.story || {}).romance || {}, "stage", -1))) < 4 &&
      s.week >= Math.trunc(n0(gv(s, "weeks_total", 8)));
    const st = this._maybeStory(force);
    if (st) this.push(st);
  }

  // ---------------- 私联终局：收场 ----------------

  /** 末周开头把「收场」排上：先一句前夜的话，然后是三问。 */
  private _beginFinale(): void {
    const s = this.state!;
    // 方案A：拷问走私联独立通道，只从她自己随口说过的小事出题。
    // 真值在 protagonist() 里已预锁（她说的=拷问问的=判对的同一个值），
    // 不再需要「收场前临时补三条线索」那一段——那正是线索突兀的根源。
    const quiz = E.shirenFinaleQuizCards(s, this.world, this.rng, 3);
    s._finale = { phase: "intro", quiz, idx: 0, ok: 0, total: quiz.length };
    const ln = E.shirenLine(this.world) || ({} as any);
    const fin = ln.finale || {};
    const { slots } = this._finaleSlots();
    const intro = this._fill(gv(fin, "intro", ""), slots);
    const body = intro ? [intro] : ["场馆空着，灯只开了一半。"];
    this.push({ type: "text", title: "收场", body });
  }

  /** 终局进行到哪一步了。返回 true 表示这一步已经排了新屏。 */
  private _afterFinale(): boolean {
    const s = this.state!;
    const fin = s._finale;
    if (!fin || this.queue.length) return false;
    const phase = fin.phase;
    if (phase === "intro" || phase === "quiz") return this._pushFinaleQuiz();
    if (phase === "outcome") return this._pushFinaleChoices();
    if (phase === "collapse") return this._pushCollapse();
    if (phase === "done") {
      delete s._finale;
      // 收场走完，这一季就到这里。13「用完」/14「唯一」的正文写的是
      // 「你在第 X 周走到了这里 / 剩下的周没有发生」，所以这里必须真的提前结束。
      this._finish();
      return true;
    }
    return false;
  }

  // ---------------- 断联之后的失控 ----------------

  /**
   * 断联之后那几分钟。
   *
   * 她要的是「我控制不了」，所以这里不写选项、不给按钮：`auto` 标记让前端
   * 自己往下翻，玩家只能看着。炎上和板子一路涨到 999，最后进「控制不了」结局。
   *
   * 这一段不是「我没能让她停」，而是「原来我不止她一个」——
   * 前面一整季玩家只看见一个人，崩溃的时候才发现自己攒了一本账。
   * 数字不是一口气跳上去的——一屏一屏涨，玩家才会觉得事情在滑走。
   */
  private _collapseScript(): Step[] {
    const s = this.state!;
    const who = s._collapse_who || "她";
    return [
      {
        title: "",
        auto: true,
        body: ["我说完那句话就回家了。那天晚上睡得很沉，心想这件事总算处理干净了。"],
      },
      {
        title: "",
        auto: true,
        body: [
          "第四天晚上，板子上出现了一条帖子，标题只有三个字：想聊聊。",
          `我以为是${who}。点进去，第一行写着：「周三那次，你也是这么跟我说的。」`,
        ],
        bump: { enjou: 60, banzi: 40 },
      },
      {
        title: "",
        auto: true,
        body: [
          "周三。我在心里过了一遍周三，是空的。",
          "第二条帖子是周六发的：「你说，只有我听得懂。」我也想不起自己说过。",
        ],
      },
      {
        title: "",
        auto: true,
        body: [
          "她们开始对句子。同一句「你是特别的」，出现了三次，落款是三个人。",
          "有人把截图按日期排开，三行字一模一样，连标点都没差。",
        ],
        bump: { enjou: 130, banzi: 110 },
      },
      {
        title: "",
        auto: true,
        body: [
          "我翻自己的聊天记录。有几段话完全没有印象，语气却确实是我的。",
          "同一个晚上，同一个地址，我发给了三个人。间隔十七分钟。",
        ],
      },
      {
        title: "",
        auto: true,
        body: [
          "她们开始对照片。同一张拍切，裁掉不同的人，发给不同的人。",
          "有人问：这张到底拍的是谁。没有人回答。",
        ],
        bump: { enjou: 180, banzi: 190 },
      },
      {
        title: "",
        auto: true,
        body: [
          "运营的电话是晚上打来的。他没有问是不是真的。",
          "他问：到底几个。",
        ],
      },
      {
        title: "",
        auto: true,
        body: [
          "我张了一下嘴，发现说不出准确的数。",
          "那一刻我才意识到，我连自己都骗过去了。",
        ],
        bump: { enjou: 220, banzi: 240 },
      },
      {
        title: "",
        auto: true,
        body: [
          "第二天早上，热搜第三，第二，第一。",
          "标题里那句是她们中一个人写的：她好像对每个人都这样。",
        ],
      },
      {
        title: "",
        auto: true,
        body: ["群里没有人问我。小满发了一句「我们先别说话」。露露退群了。"],
        bump: { enjou: 250, banzi: 300 },
      },
      {
        title: "",
        auto: true,
        body: [
          "傍晚，场地退了，票全退。我坐在空的列里，把版聊往上翻。",
          "翻到最早那条，她说：你是第一个记住我名字的人。我盯着这句话，想不起来是哪一个。",
        ],
      },
      {
        title: "",
        auto: true,
        body: [
          "她们还在对日子。第四十七个。落款一栏排得很整齐。",
          "我数到第四十七个，停住了。第四十八个是谁，我到现在也没想起来。",
        ],
        bump: { enjou: 999, banzi: 999 },
      },
    ];
  }

  /** 排失控演出的下一屏。演完就把这一季收掉。 */
  private _pushCollapse(): boolean {
    const s = this.state!;
    const fin = s._finale || {};
    const idx = Math.trunc(n0(gv(fin, "cidx", 0)));
    const script: Step[] = fin.script || [];
    if (idx >= script.length) {
      // 演完了：这里必须直接收场。若只把 phase 改成 done 就返回，
      // afterStep 会接着 stepWeek() 把这一周过下去，失控就成了插曲。
      delete s._finale;
      this._finish();
      return true;
    }
    const row = script[idx];
    fin.cidx = idx + 1;
    s._finale = fin;
    const step: Step = {
      type: "text",
      title: row.title || "",
      body: [...(row.body || [])],
      auto: true,
      cidx: idx,
    };
    if (idx === 0) step.collapse_start = true;
    const bump = row.bump || {};
    if (Object.keys(bump).length) {
      // 这里不能走 applyEffect：它末尾会 clamp，而 clamp 本来会把
      // 炎上/板子削回 100。断联之后这两个数不归那套规矩管。
      // 顶端仍是 999——一路涨上去，涨到顶就停在那儿。
      const d: Record<string, number> = {};
      for (const [k, v] of Object.entries(bump)) {
        const old = n0(gv(s, k, 0));
        const nw = Math.min(999, old + Number(v));
        (s as any)[k] = nw;
        d[k] = nw - old;
      }
      step.delta = d;
    }
    this.push(step);
    return true;
  }

  private _finaleSlots(): { slots: Record<string, Ota>; ta: Ota | null } {
    const ta = (this._lineSlots("shiren", {}) as any).ta ?? null;
    return { slots: ta ? { ta, speaker: ta } : {}, ta };
  }

  private _pushFinaleQuiz(): boolean {
    const s = this.state!;
    const fin = s._finale || {};
    const quiz: Card[] = fin.quiz || [];
    const idx = Math.trunc(n0(gv(fin, "idx", 0)));
    const { slots, ta } = this._finaleSlots();
    if (idx < quiz.length) {
      fin.phase = "quiz";
      s._finale = fin;
      const card = quiz[idx];
      const step = this._renderCard(card, slots);
      step.face = (ta && ta.name) || "特典会";
      step._card = card;
      step._slots = slots;
      step.finale_quiz = true;
      this.push(step);
      return true;
    }
    // 答完了：判成绩，写成一句能看懂的话
    const nOk = Math.trunc(n0(gv(fin, "ok", 0)));
    const nAll = quiz.length;
    const [key, ok] = E.applyFinaleOutcome(s, nOk, nAll);
    fin.phase = "outcome";
    fin.key = key;
    fin.ok_quiz = Boolean(ok); // 答上了才有得选，答错直接收场
    s._finale = fin;
    const ln = E.shirenLine(this.world) || ({} as any);
    let note = "";
    for (const oc of (ln.finale || {}).outcomes || []) {
      if (oc.id === key) {
        note = oc.note || "";
        break;
      }
    }
    const head = nAll
      ? `她一共问了我 ${nAll} 件小事，我答上了 ${nOk} 件。`
      : "她问的那些，我一件都说不上来。";
    const body = [head];
    if (note) body.push(note);
    this.push({ type: "text", title: "她问完了", body });
    return true;
  }

  /**
   * 答对了才问这一句：接下来，你想怎么办。
   *
   * 以前这里直接把 storyline 里那四条抄出来（公开/断联/沉沦/划边界），
   * 四条都只改资源，不改结局——玩家选完，结局早在答题那一刻定死了。
   * 现在只剩两条，而且它们真的通向不同的地方。
   */
  private _finaleChoicesCard(): Card {
    return {
      id: "finale_choice",
      type: "私联恋爱",
      title: "收场",
      _meta: { finale_choice: true },
      narrative: "台上那一晚还没到。最后一场之前，我得决定这件事往哪放。",
      options: [
        {
          id: "sink",
          label: "就这么下去",
          desc: "不公开，也不断。当它没有尽头",
          note: "我没有回那条消息，也没有不回。第二天她照常坐在列里等我。",
          immediate: { psyche: 4, kaibox: 10, enjou: 6 },
        },
        {
          id: "cut_clean",
          label: "跟她说清楚，以后别来了",
          desc: "把线剪干净，各自回到岸上",
          note: "我打了一大段，删了，又打了一段。最后发出去的是最短的那句。",
          immediate: { psyche: -8, kaibox: -14, shiroi: -10 },
        },
      ],
    };
  }

  private _pushFinaleChoices(): boolean {
    const s = this.state!;
    const fin = s._finale || {};
    // 答错了就没有这一屏：直接往「用完」走，别给一个选不了任何事的选项。
    if (!fin.ok_quiz) {
      fin.phase = "done";
      s._finale = fin;
      return false;
    }
    const card = this._finaleChoicesCard();
    fin.phase = "choices";
    s._finale = fin;
    const { slots, ta } = this._finaleSlots();
    const step = this._renderCard(card, slots);
    step.face = (ta && ta.name) || "特典会";
    step._card = card;
    step._slots = slots;
    step.finale_choice = true;
    this.push(step);
    return true;
  }

  /**
   * 越了线之后，私联就一周推一拍，不再等骰子。
   *
   * 以前这里只在「按剩余周数算，再不推就来不及」时才插队，其余周仍走
   * 正常抽卡（2.6 倍权重）。结果越线早的档，中间几周可能一次都抽不到，
   * 玩家看到的是「刚加微信，下一屏就是决赛前夜」。这条线一旦开始就是我
   * 过的另一种日子，拍数又固定 5 拍，所以只要主线已经落在私联，就每周强推。
   */
  private _shirenIfCrossed(): [any, any] | null {
    const s = this.state!;
    if (!(s.flags || new Set()).has("crossed_line")) return null;
    const main = E.mainline(s);
    if (main && main !== "shiren") return null; // 这一季走的是别的线
    const ln = E.shirenLine(this.world);
    if (ln === null || E.lineLocked(s, ln)) return null;
    const st = E.lineStage(s, ln);
    if (st === null) return null;
    return [ln, st];
  }

  /**
   * 恋爱线一旦成了这一季的主线，就一周推一拍，不再等骰子。
   *
   * 以前只靠 drawLine 的 45% 落率，八周里经常只轮到两三拍，
   * 玩家还没走到「确认」就季末了。
   */
  private _romanceIfMain(): [any, any] | null {
    const s = this.state!;
    if (E.mainline(s) !== "romance") return null;
    const ln = E.romanceLine(this.world);
    if (ln === null || E.lineLocked(s, ln)) return null;
    const st = E.lineStage(s, ln);
    return st ? [ln, st] : null;
  }

  /**
   * 「谈一谈」独立幕：确认关系后、还没做过一次性表态时，每周开头来问一次。
   * 选「再等等/逃避」只攒 risk，下周照问（越拖越勤）；选「公开/只看当下」收下表态，不再问。
   * 不占抽线骰子、不写 story 进度；末周 forceFinale 时跳过它，直接推收场。
   */
  private _maybeRomanceTalk(): Step | null {
    const s = this.state!;
    if (E.mainline(s) !== "romance") return null;
    const fl: Set<string> = s.flags || new Set<string>();
    if (!fl.has("romance_confirmed")) return null;
    // 表过态就不再问（公开 / 只看当下，都是一次性收下）
    if (fl.has("romance_public_intent") || fl.has("romance_now_intent")) return null;
    // 每周最多问一次
    if (n0(gv(s, "_rtalk_week", -1)) === n0(s.week)) return null;
    const ln = E.romanceLine(this.world);
    if (ln === null || E.lineLocked(s, ln)) return null;
    const talks: any[] = (ln as any).talks || [];
    if (!talks.length) return null;
    // 三变体轮换：尽量不接着问同一张
    const last = gv(s, "_last_rtalk", "");
    const pool = talks.filter((t) => t.id !== last);
    const talk = this.rng.choice(pool.length ? pool : talks);
    s._last_rtalk = talk.id;
    const slots: Record<string, Ota> = { ta: { name: "阿棠" } as Ota };
    const pending: any[] = ["rtalk", talk, slots];
    const body = [this._fill(gv(talk, "narrative", ""), slots)];
    return {
      type: "card",
      rtalk: true,
      title: this._fill(gv(talk, "title", ""), slots),
      face: (slots.ta as Ota).name,
      speaker: (slots.ta as Ota).name,
      compact: true,
      body,
      options: (talk.options || []).map((o: Option) => ({
        id: o.id,
        label: this._fill(o.label, slots),
        desc: this._fill(gv(o, "desc", ""), slots),
      })),
      _rtalk: pending,
    };
  }

  /**
   * 每周开头先问一句：这一周有没有哪条线在走。
   *
   * 以前这里的 `_story_try` 两周共用一次拦截，结果排完动作那一周就再也推不动线
   * ——一周也推进不了。现在只由每周开头那一次调用决定，本函数不自锁。
   */
  private _maybeStory(forceFinale = false): Step | null {
    const s = this.state!;
    // 「谈一谈」是独立通道：不占每周抽线的骰子，也不写 story 进度。
    if (!forceFinale) {
      const rtalkStep = this._maybeRomanceTalk();
      if (rtalkStep !== null) return rtalkStep;
    }
    let line: [any, any] | null = null;
    let forced = false;
    if (forceFinale) {
      // 末周兜底：恋爱线还没走到收场，也把「那一晚」排上。
      const ln = E.romanceLine(this.world);
      if (ln !== null) {
        const st = (ln.stages || []).find((x: any) => Math.trunc(x.stage) === 4);
        if (st !== undefined) {
          line = [ln, st];
          forced = true;
        }
      }
    } else {
      line = this._shirenIfCrossed();
      forced = line !== null; // 私联进度落后：不等骰子
      if (line === null) {
        line = this._romanceIfMain();
        forced = line !== null;
      }
    }
    if (line === null) line = E.drawLine(s, this.world, this.rng);
    if (line === null) return null;
    if (!forced && this.rng.random() > Game.LINE_CHANCE) return null;
    const [lid, st] = line;
    const lidId = lid._meta.id;
    let v: any = null;
    if (lidId === "romance" && st.stage === 4) {
      // 收场这一晚会不会被人撞破：不再一票否决，按「意图 + 攒下的 risk」掷一次骰。
      // 公开意图 = 本来就打算摊开，几乎不怕被看见（risk 攒够才有一点风声）；
      // 只想顾当下 / 一直没表态 = 越拖越悬，risk 越高越容易被推开门。
      const fl = s.flags || new Set();
      const risk = Math.max(0, Math.trunc(n0(gv(s, "romance_risk", 0))));
      let caughtPct: number;
      if (fl.has("romance_public_intent")) {
        caughtPct = risk >= 3 ? 20 : 0;
      } else if (fl.has("romance_now_intent")) {
        caughtPct = Math.min(90, 60 + 10 * risk);
      } else {
        caughtPct = Math.min(90, 50 + 15 * risk);
      }
      if (this.rng.random() * 100 < caughtPct) {
        v = (st.variants || []).find((x: any) => x.id === "finale_caught");
      }
    }
    if (v === null || v === undefined) {
      // 同一拍隔两周再回来时，尽量换一张没演过的：
      // 玩家推开的那个选项不该让同一张卡原地重播（「又遇到第一拍」）。
      if (!s._line_seen) s._line_seen = {};
      const seen: string[] = s._line_seen[lidId] || [];
      const pool = (st.variants || []).filter((x: any) => !seen.includes(x.id));
      v = this.rng.choice(pool.length ? pool : st.variants);
      s._line_seen[lidId] = seen.concat([v.id]).slice(-8);
    }
    s._line_tick = s.week;
    s._story_try = s.week;
    if (!s._line_week) s._line_week = {};
    E._rememberChaser(s, lid, v, this.rng);
    const slots = this._lineSlots(lidId, v);
    const pending: any[] = ["line", lidId, st, v, slots];
    this.pending = pending;
    return {
      type: "card",
      line: true,
      line_name: Game.lineName(lidId),
      _line: pending,
      face:
        Object.values(slots)
          .filter((o: any) => o && o.name)
          .map((o: any) => o.name)
          .join("、") ||
        ({ shiren: "特典会", zhong: "散场以后", romance: "排练室" } as Record<string, string>)[lidId] ||
        "",
      title: this._fill(gv(v, "title", ""), slots),
      body: [this._fill(gv(v, "narrative", ""), slots)],
      options: (v.options || []).map((o: Option) => ({
        id: o.id,
        label: this._fill(gv(o, "label", ""), slots),
        desc: this._fill(gv(o, "desc", ""), slots),
      })),
    };
  }

  static lineName(lid: string): string {
    return ({ shiren: "私联", zhong: "重线", romance: "恋爱" } as Record<string, string>)[lid] ?? "";
  }

  /** 私联踩空后她又发来的私信表白卡：三张轮换，带选项，回/冷/推开各有代价。 */
  private _confessStep(slots: Record<string, Ota>): any {
    const s = this.state!;
    const cards = (this.world.cards || []).filter((c: any) => c.type === "私联表白");
    if (!cards.length) return null;
    const last = s._last_confess;
    const pool = cards.filter((c: any) => c.id !== last);
    const card = this.rng.choice(pool.length ? pool : cards);
    s._last_confess = card.id;
    const step = this._renderCard(card, slots);
    step._card = card;
    step._slots = slots;
    step.face = (slots?.ta || {}).name || "版聊";
    return step;
  }

  /** 剧情线里 `{{ta}}` 是谁：重线跟着「一直来的那个人」，私联/恋爱各有自己的对象。 */
  private _lineSlots(lid: string, v: any): Record<string, Ota> {
    const s = this.state!;
    let ta: Ota | null = null;
    if (lid === "zhong") {
      let cid = s._chaser;
      if (!cid && s.ota && s.ota.length) {
        // 高黏性里随机挑，不再固定 max(stick)——否则永远同一个人。
        const pool = s.ota
          .filter((o) => !o.is_storyline)
          .slice()
          .sort((a, b) => n0(b.stick) - n0(a.stick))
          .slice(0, 3);
        if (pool.length) {
          cid = this.rng.choice(pool).id;
          s._chaser = cid;
        }
      }
      ta = (s.ota || []).find((o) => o.id === cid) ?? null;
    } else if (lid === "romance") {
      ta = { name: gv(v, "partner", null) || "阿棠" } as Ota;
    } else if (lid === "shiren") {
      // 私联对象从现有高黏性 OTA 里挑一个「不会走的」，整季固定。
      ta = E.protagonist(s, this.world, this.rng);
    }
    if (ta === null && s.ota && s.ota.length) {
      const pool = s.ota
        .filter((o) => !o.is_storyline)
        .slice()
        .sort((a, b) => n0(b.stick) - n0(a.stick))
        .slice(0, 3);
      if (pool.length) ta = this.rng.choice(pool);
    }
    return ta ? { ta } : {};
  }

  chooseStory(oid: string): any {
    const s = this.state!;
    if (!this.pending || this.pending[0] !== "line") return this.advance();
    const lidId = this.pending[1];
    const st = this.pending[2];
    const v = this.pending[3];
    const slots = this.pending[4];
    const o = (v.options || []).find((x: Option) => x.id === oid)!;
    const before = snap(s);
    const snapv: Record<string, number> = {};
    for (const k of ["zhong", "zhongs", "heat", "heart"]) snapv[k] = n0(gv(s, k, 0));
    s._line_tick = s.week;
    E.applyOption(s, o, this.rng, slots, null);
    // 她讲出来的事：这一拍 `learns` 里写的东西，从此算「你知道」。
    // 以前引擎根本不读 learns，所以 {{cat_name}}/{{home}} 这类全是空的。
    E.learnMemory(s, o.learns, o.note || "");
    // 那些「选了就真的有事发生」的旗标：断线、被记住家在哪、官方辟谣反而坐实…
    E.applyStoryFlags(s, o);
    // 推进量在引擎这一层补：选项一般只写「她攒下的」，不写「重线进度」
    if ((snapv.zhong || 0) >= n0(gv(s, "zhong", 0))) {
      s.zhong = (snapv.zhong || 0) + 1;
    }
    // 私联看选项的 advance：答应了、去了、回了，才算往前走一步。
    // 以前这里是 `0 >= 0` 恒真，连「当晚就跟她说以后别来了」也照样 +1，
    // 与 design_note 的「冷淡则卡住甚至断线」正好相反。
    if (lidId === "shiren" && o.advance && (snapv.heat || 0) >= n0(gv(s, "heat", 0))) {
      s.heat = (snapv.heat || 0) + 1;
    }
    if (lidId === "romance" && o.advance && (snapv.heart || 0) >= n0(gv(s, "heart", 0))) {
      s.heart = (snapv.heart || 0) + 1;
    }
    if (lidId === "zhong") {
      s.shiroi = n0(gv(s, "shiroi", 0)) + (st.stage >= 3 ? 12 : 8);
    }
    if (lidId === "shiren") {
      s.kaibox = n0(gv(s, "kaibox", 0)) + 4;
    }
    // 只有真的往前走了一拍才记进度：重线的选项没有 advance（怎么答都压过来），
    // 另外两条要看选项。没推进就别写 story——否则私联「半开一扇门」也会
    // 留下一条 stage 0 的记录，可能被兜底选成主线，而它永远迈不出下一步。
    let confessed = false;
    if (lidId === "zhong" || o.advance || st.stage >= 4) {
      // 收场拍（stage 4）的选项都不带 advance（它不再「往前走」），
      // 但这一拍本身必须记下来，否则末周会反复排「决赛前夜」。
      if (!s.story) s.story = {};
      s.story[lidId] = { stage: st.stage };
    } else if (lidId === "shiren") {
      // 私联踩空：不写进度、也不加冷却。她会再发一条私信表白过来。
      confessed = true;
    }
    if (!s._line_week) s._line_week = {};
    s._line_week[lidId] = s.week;
    E.clamp(s);
    this.pending = null;
    this.queue.shift();
    let body: string[] = [this._fill(gv(o, "note", ""), slots)].filter((x) => x);
    if (!body.length) body = [this._fill(gv(o, "desc", ""), slots)].filter((x) => x);
    this.push({
      type: "receipt",
      title: this._fill(gv(o, "label", ""), slots),
      body,
      delta: delta(before, s),
    });
    // 被撞破 / 当场公开 / 重线那句「全都告诉她」：这一季到此为止，不拖到季末。
    // final_intimate 以前只写 flag、要等 judge，结果第 5 周就能触发的
    // 「我只是太爱你了」被硬拖到第 8 周——和恋爱线撞破是同一个问题。
    const flags = new Set(o.flags || []);
    if (flags.has("romance_caught") || flags.has("romance_public") || flags.has("final_intimate")) {
      this._finish();
      return;
    }
    // 这一拍踩空了（拒绝、把线关了）：这条线安静两周
    const closed = flags.has("line_closed") || flags.has("romance_giveup");
    if (closed) {
      E.lineCool(s, lidId, 2);
    }
    // 私联踩空且没有明确断线：她又发来一条私信表白。插到队首，立刻成为下一屏。
    // 一直不往前就一直表白（三张轮换），而不是同一拍换卡重播。
    if (confessed && !closed) {
      const step = this._confessStep(slots);
      if (step) this.pushFront(step);
    }
    this.afterStep();
  }

  _resumeLive(): void {
    this.afterStep();
  }

  private _finish(): void {
    const s = this.state!;
    this._journalWeek(n0(gv(s, "week", 1)));
    // 「再跳一场」：没选离开、一路演到季末 = last_live（彗星第三条件）。
    // 以前只有离线 doWeek 会置位，线上永远拿不到彗星。
    if (!s.chose_leave) s.last_live_choice = true;
    const [name, isEarly] = E.judge(s, this.world, null);
    s.ending = name;
    this.over = true;
    const text = Game.endingText(this.endingMd, name);
    this.push({
      type: "end",
      title: name,
      ending: name,
      early: Boolean(isEarly),
      echo: this._echo(),
      outside: this.outside,
      body: text ? [text] : ["（这个结局的正文还没写进来。）"],
    });
  }

  /** 结局那一屏底下「这一季的回响」：只报这一局真发生过的数，不写攻略。 */
  private _echo(): Step {
    const s = this.state!;
    const sn = this.snapshot() || {};
    const stats: any = sn.stats || {};
    const tp = Math.trunc(n0(gv(s, "truth_pick", 0)));
    const sp = Math.trunc(n0(gv(s, "safe_pick", 0)));
    const picked = tp + sp;
    const stageScore = E.stageScore(s);
    return {
      week: Math.trunc(n0(gv(s, "week", 0))),
      stage: pyRound(stageScore, 1),
      tier: E.tierName(pyRound(E.stageScore(s))),
      psyche: pyRound(n0(gv(s, "psyche", 0))),
      money: pyRound(n0(gv(s, "money", 0))),
      enjou: pyRound(n0(gv(s, "enjou", 0))),
      kaibox: pyRound(n0(gv(s, "kaibox", 0))),
      line: s._mainline || "",
      truth_pick: tp,
      safe_pick: sp,
      truth_rate: picked ? pyRound(tp / picked, 2) : null,
      clues: Math.trunc(n0(stats.clues)),
      clues_wrong: Math.trunc(n0(stats.clues_wrong)),
      pushed: Math.trunc(n0(stats.pushed)),
      rent_missed: Boolean(gv(s, "rent_missed", false)),
      chose_leave: Boolean(gv(s, "chose_leave", false)),
      offer_refused: Boolean(gv(s, "offer_refused", false)),
      shiren_stage: Math.trunc(
        n0(gv((s.story || {}).shiren || {}, "stage", -1)),
      ),
      stance: gv(s, "stance", "") || "",
      stance_name: gv(s, "stance_name", "") || "",
    };
  }

  /**
   * 从 `结局.md` 里抠出某一段正文。找不到就返回空，界面只显示结局名。
   */
  static endingText(src: string, name: string | null | undefined): string {
    if (!src) return "";
    // 章节：## N · 名字 … 直到下一个 ## 或文末
    const blocks = src.split(/\n(?=##\s)/);
    for (const b of blocks) {
      const head = b.split("\n", 1)[0];
      if (name && head.includes(name)) {
        let m = /\*\*正文\*\*\s*\n([\s\S]*?)(?=\n\*\*|$)/.exec(b);
        if (m) {
          const t = m[1].trim();
          return t.replace(/\n{3,}/g, "\n\n");
        }
        // 有的结局（如散场）把正文直接写在 **内核** 后面，没有 **正文** 标题
        m = /\*\*内核\*\*[:：][\s\S]*?\n\s*\n([\s\S]*?)(?=\n\*\*|$)/.exec(b);
        if (m) {
          const t = m[1].trim();
          return t.replace(/\n{3,}/g, "\n\n");
        }
      }
    }
    return "";
  }
}
