/**
 * 《聚场》引擎的类型。
 *
 * 刻意保留了 Python 那边的「字典感」：`State` 是 `Record<string, any>`，
 * 因为 `engine.py` 会往 `s` 里按需建键（`zhong` / `zhongs` / `heart` /
 * `shirou` 这些都是剧情线专属量，只有走到那条线才会出现）。
 * 用严格接口反而要在每处 `s.get(k, 0)` 前先断言一次，翻译时更容易抄错。
 *
 * 这里类型松、`engine.ts` 的逻辑密——对账靠逐字段 diff，不靠类型系统兜。
 */

/** 一个 OTA（台下那个人）。字段随剧情长出来，所以带索引签名。 */
export interface Ota {
  [k: string]: any;
  id: string;
  name: string;
  stick: number;
  archetype: string;
  fan_type: string;
  gender: string;
  spend: number;
  weeks_known: number;
  is_seed?: boolean;
  is_storyline?: boolean;
  met_week?: number;
  notes?: string;
  memory?: Record<string, string>;
}

/** 引擎状态。`s["flags"]` 是 Set，`s["ota"]` 是 Ota[]。 */
export interface State {
  [k: string]: any;
  ota: Ota[];
  flags: Set<string>;
  delayed: Delayed[];
  cooldown: Record<string, number>;
  seen: string[];
  log: any[];
  clues: Record<string, ClueInfo>;
  story: Record<string, { stage: number }>;
  week: number;
  weeks_total: number;
  beat: number;
  money: number;
  stamina: number;
  psyche: number;
  fame: number;
  stage: number;
  dance: number;
  sing: number;
  mc: number;
  enjou: number;
  kaibox: number;
  banzi: number;
  shiroi: number;
  shiren: number;
  relation_A: number;
  relation_B: number;
  relation_C: number;
  name: string | null;
  name_style: string | null;
  ended: string | null;
}

export interface ClueInfo {
  state: "said" | "asked" | "known" | "wrong" | "dropped";
  asked: boolean;
  said_week?: number;
  who?: string | null;
  truth?: string;
  result?: "ok" | "bad";
}

export interface Delayed {
  when: string | null;
  cond: string | null;
  effect: Record<string, any> | null;
  note?: string | null;
  slots: Record<string, string>;
  hatch_friend?: any;
  base_stick?: number;
  condition?: string | null;
}

/** 卡库里的一个选项。 */
export interface Option {
  [k: string]: any;
  id: string;
  label: string;
  desc?: string;
  note?: string;
  tone?: "truth" | "safe";
  bold?: string;
  flags?: string[];
  delayed?: any[];
  rq_lock?: any;
  rq_drop?: any;
  rq_pick?: any;
  immediate?: Record<string, any>;
  effect?: Record<string, any>;
}

/** 卡库里的一个 casting 槽。 */
export interface CastSpec {
  slot?: string;
  select?: Record<string, any>;
  allow_hatch?: boolean;
  force_hatch?: boolean;
  hatch_only?: boolean;
}

/** 一张卡。 */
export interface Card {
  [k: string]: any;
  id: string;
  type: string;
  title?: string;
  narrative?: string;
  gate?: string;
  weight?: number;
  cooldown?: number;
  casting?: CastSpec[];
  options?: Option[];
  effect?: Record<string, any>;
  _meta?: Record<string, any>;
}

/** 剧情线的一个拍。 */
export interface LineStage {
  stage: number;
  gate?: string;
  enter_heat?: number | null;
  key?: string;
  variants: LineVariant[];
}

export interface LineVariant {
  options: Option[];
  [k: string]: any;
}

/** 一条剧情线。 */
export interface StoryLine {
  _meta: { id: string; [k: string]: any };
  stages: LineStage[];
  [k: string]: any;
}

/** ota_memory.json 里的一条线索。 */
export interface MemClue {
  key: string;
  set?: string[];
  ask?: string[];
  ask_q?: string;
  react_good?: Record<string, any>;
  react_bad?: Record<string, any>;
  [k: string]: any;
}

/** 整个数据世界（load_world 的产物）。 */
export interface World {
  cards: Card[];
  lines: StoryLine[];
  intro: any;
  endings: any;
  memory: any;
  pool: any;
  names: any;
}

/** 抽卡/跑局用的策略。对应 Python 里既可以是函数也可以是带方法的对象。 */
export interface Policy {
  act?: (s: State) => string;
  tone?: (s: State) => string;
  choose?: (s: State, card: any, options: Option[]) => number | null | undefined;
}
