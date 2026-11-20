/**
 * 特典会一周一张账单：谁买了几张、谁没来。
 *
 * 一张券 **80 元**（2026-11-14 用户定，全团统一价）。
 * 钱 = 张数 × 80，不再乘人气系数：人气只决定今天谁来、来几个。
 *
 * 移植自 game/bill.py，行为逐行对齐——`weekly_income()` 在引擎里
 * 直接拿它的 `yen` 当这一周的收入，所以这里一改，整季的钱都会变。
 */

import type { Ota, State } from "./types.ts";

export const PRICE = 80; // 特典券统一 80 元一张

export type Split = "big" | "small" | "mixed";

/** 这个人是大券型、小券型，还是一半一半。 */
export function bigSplit(o: Ota): Split {
  if ((o.spend ?? 3) >= 4 || o.archetype === "重力系") return "big";
  if ((o.spend ?? 3) <= 2) return "small";
  return "mixed";
}

/**
 * 黏性每 25 一档多买一张，消费力到 4 再多一张。
 * 黏性 55→3、70→3、78→4；消费力 4 的第零排 70→4。
 *
 * 阶梯与 Python bill.tickets_of 一致：<70→1；70→2；80→4；90→7；95→10；98→14。
 */
/** 轻量舞台分：与 engine.stageScore 同口径（bill 不能反过来 import engine）。 */
function stageOf(state: State): number {
  const rel = [state.relation_A ?? 0, state.relation_B ?? 0, state.relation_C ?? 0].map((v) => Number(v) || 0);
  const relavg = rel.length ? rel.reduce((a, b) => a + b, 0) / rel.length : 0;
  return 0.32 * (Number(state.dance) || 0) + 0.28 * (Number(state.sing) || 0)
    + 0.22 * (Number(state.mc) || 0) + 0.18 * relavg;
}

export function ticketsOf(o: Ota, stage?: number | null): number {
  const stick = Math.max(0, Math.min(100, o.stick ?? 0));
  const spend = o.spend ?? 3;
  let base: number;
  if (stick >= 98) base = 14;
  else if (stick >= 95) base = 10;
  else if (stick >= 90) base = 7;
  else if (stick >= 80) base = 4;
  else if (stick >= 70) base = 2;
  else base = 1;
  const sm = spend <= 2 ? 0.6 : spend >= 4 ? 1.6 : 1.0;
  const st = stage == null ? 0 : Number(stage);
  const tm = st >= 85 ? 1.6 : st >= 70 ? 1.3 : st >= 55 ? 1.1 : 1.0;
  return Math.max(1, Math.floor(base * sm * tm + 0.5));
}

export interface BillRow {
  id: string;
  name: string;
  spend: number;
  tickets: number;
  yen: number;
}

/** 一个人这一场的账单。 */
export function billFor(o: Ota, stage?: number | null, _cheap = false): BillRow {
  const n = ticketsOf(o, stage);
  return {
    id: o.id,
    name: o.name,
    spend: o.spend ?? 3,
    tickets: n,
    yen: n * PRICE,
  };
}

export interface Bill {
  rows: BillRow[];
  tickets: number;
  yen: number;
  absent: string[];
  price: number;
}

/** 整场的账单。who=null = 今天来了的所有人（引擎给的 warm 名单）。 */
export function weeklyBill(state: State, who?: Ota[] | null): Bill {
  const cheap = (state.week ?? 1) <= 2;
  const pool: Ota[] =
    who != null ? who : ((state.ota as Ota[]) ?? []).filter((o) => (o.stick ?? 0) >= 30);
  const stage = stageOf(state);
  let rows = pool.map((o) => billFor(o, stage, cheap)).filter((r) => r.tickets > 0);
  // Python: rows.sort(key=lambda r: (-r["yen"], r["name"]))
  // 中文名字的排序在 Python 里是按码点，JS 的 < 比较也是按 UTF-16 码元，
  // 对 BMP 内的汉字一致（本项目的名字都在 BMP 内）。
  rows = rows.slice().sort((a, b) => {
    if (a.yen !== b.yen) return b.yen - a.yen;
    return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
  });
  const totalY = rows.reduce((acc, r) => acc + r.yen, 0);
  const came = new Set(rows.map((r) => r.id));
  const absent = ((state.ota as Ota[]) ?? []).filter((o) => !came.has(o.id)).map((o) => o.name);
  return {
    rows,
    tickets: rows.reduce((acc, r) => acc + r.tickets, 0),
    yen: totalY,
    absent,
    price: PRICE,
  };
}
