# 《聚场》交接文件（HANDOFF）

> 地下偶像模拟器·网页游戏。这份文件是**给下一个对话的入口**：读完它 + `DESIGN.md`，就能直接接着干，不用重新摸一遍。
> 最后更新：**2026-11-17 凌晨**（…；**§6.20 TS 移植对账全通过（85115 项）**；**§6.21 前端接 TS 引擎完成，变纯静态站**；**§6.22 已上线 ju-chang.pages.dev + 自定义域名，并修了三个界面问题：立绘随风格变、版聊补对方回音、OTA 表移到右上角默认收起**；**§6.23 四项：线索卡「今天的舞台」、弹窗收成右下角小方块可展开、星期几改汉字、指向 OTA 的「他/她」全改「ta」**；**§6.24 剧情线三修：同拍重播加冷却、chaser 排除剧情主角防串台、三条线卡右上角打 tag**；**§6.25 私联踩空改「她一直发私信表白」（撤销冷却）+ 主角/chaser 从高黏性 OTA 里随机挑，见下方——注意 §6.24 的冷却方案已被 §6.25 推翻**）

---

## 0. 一句话现状

**已经能从头到尾玩完一季八周并判出结局，而且已经上线了。**

- **线上（玩家走这条）**：<https://ju-chang.pages.dev/> / <https://diocosplay.dpdns.org/>。纯静态网页，`game/*.py` 的引擎与流程已翻成 TypeScript（`app/src/core/`），`vite build` 出 486KB 的 `dist/`。存档和图鉴在 localStorage。**推 `main` 就自动部署**。见 §6.20 / §6.21 / §6.22 / `DEPLOY.md`。
- **旧（留着当参照和标准答案）**：`game/server.py`（纯 Python，无第三方库）起本地服务 + `web/index.html` + `web/style.css`，两者用 `/api/*` 通信。`web/app.js` 已删，前端逻辑现在的家是 `app/src/ui.js`。Python 侧的真正价值是 `tools/trace_dump.py` / `tools/loop_trace.py` 那套**对账标准答案**——改 TS 引擎后必须复跑，别让两侧悄悄分叉。

- 数据层已封版：**139 张事件卡**（136 张常规 + §6.25 新增的 3 张「私联表白」卡；常规卡里含 §6.19.3 重写的 15 张版聊卡「观众发消息 → 偶像回」）、3 条在用剧情线、5 个种子 OTA、21 条记忆线索 + 42 张两拍回考卡、序章、**16 结局**判决表。
- **结局现在真的都能打到**（现 16 个；§6.10 把私联终局「收场」接进运行时后，`truly_seen` / `used_as_tool` 会真的被写入；§6.13 加了「控制不了」，§6.18 删了结构不可达的「交易孤立」）。
- **私联收场是三条路**（§6.13）：答错 → 「用完」；答对 → 沉沦「唯一」/ 断联「控制不了」。后者是整段自动演出：按钮全消失、屏幕自己翻、炎上与板子一路涨到 999。演出写的是「原来我不止她一个」——机制还是一个人，浮出来的是她一个人的账本。
- **一季只走一条剧情线**（§6.11）：私联 / 队友恋爱 / 重线不再抢同一个每周推线口，第一条被玩家主动推进的线锁定为这一季主线，另外两条不再出现。
- **私联线现在是「一个人」而不是「一阵风」**（§6.12）：她的名字、原型、猫叫什么、常点哪杯、老家在哪都整局固定；拒绝不再算推进；选「以后别来了」真的会断线。
- **规则只读代码为准**：新跑法看 `app/src/core/*.ts`，旧跑法看 `game/*.py`（两套必须一致，靠三个对账测试守住）。`DESIGN.md` 是设计意图，部分数值已被后续改动覆盖，见 §4 / §5。
- 校验：`tools/validate_all.py` 八组全 0；三个对账测试全绿（rng 84 / trace 9290 / loop 77880）——项数因 §6.25 随机选角改了 rng 序列而变，属预期。
- 旧服务地址 **http://127.0.0.1:8765**；新构建本地预览 **http://127.0.0.1:8780**（`python -m http.server 8780 --directory dist`）。

---

## 1. 快速上手（下一个对话先照这个跑）

**两条路，先想清楚要哪条。**

### 1a. 纯静态版（现在的主线，要上云的就是它）

```powershell
$node="C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
$pnpm="C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\pnpm\bin\pnpm.mjs"
$py="C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
cd 聚场

& $node $pnpm exec vite build                             # 出 dist/（486KB，gzip 158KB）
& $py -m http.server 8780 --directory dist                # 后台跑请传 run_in_background
```
然后开 `http://127.0.0.1:8780/`。`vite dev` 也行（`& $node $pnpm dev`），改 `.ts` 会热更。

**存档在 `localStorage`**（键 `ju-chang.save.v1` / `ju-chang.gallery.v1`）——换浏览器/清缓存就没了。调试时看到开局状态不对，先在 DevTools 里 `localStorage.clear()`。

**三个对账测试必须全绿再往下走**（改任何 `app/src/core/*.ts` 都要复跑）：
```powershell
& $node --experimental-strip-types app\test\rng.test.ts    # ✓ 84 项
& $node --experimental-strip-types app\test\trace.test.ts  # ✓ 9290 项（§6.25 后）
& $node --experimental-strip-types app\test\loop.test.ts   # ✓ 77880 项（§6.25 后）
& $node "$PWD\node_modules\typescript\bin\tsc" --noEmit     # exit 0
```

### 1b. 旧的 Python 服务版（改引擎逻辑时当标准答案）

```powershell
$env:PYTHONIOENCODING="utf-8"
& "C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" -X utf8 game\server.py
```
后台跑请传 `run_in_background: true`。改完 `.py` 源码**必须重启服务**才生效；重启前先杀干净旧进程，否则 `SO_REUSEADDR` 会让两个实例并存、端口还是旧的：
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'server\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

**接口**：`GET /api/state`（拉当前屏+面板）、`POST /api/advance`（按「继续」）、`POST /api/choose {id}`（选一项/取名）、`POST /api/new {seed?}`（重开一局）。`web/index.html` + `web/style.css` 还能被它提供——但**旧的 `web/app.js` 已删**，前端逻辑现在只在 `app/src/ui.js`，那一层已经不是「浏览器直连 HTTP」了。**所以 1b 现在只用来跑标准答案**（`tools/trace_dump.py` / `tools/loop_trace.py`），已经不是玩家路径。

**存档（旧路径）**：`game/_save.json`，单进程单局。**要干净周目就删掉它**。

**验证**：`dsh_browser_open` 现在**能连本地端口**（§1 旧文里说不能是错的）——`http://127.0.0.1:8765/` 与 `http://127.0.0.1:8780/` 都实测可开。

---

## 2. 项目是什么 + 技术栈

- 你是一个地下偶像团体成员，**8 周一季**（2026-11-14 从 6 周拉长），靠练舞 / 练唱 / 练话术 / 拍内容 / 打工 / 躺、版聊、周末 Live + 特典会活下来。每个「为了钱、为了被爱」的选择在收场时回来找你。主题不是「谁活得久」，是「体验当偶像到底什么感觉」。
- 三拍节奏：平日行动 → 版聊 → 周末两场 Live + 特典会；约 40 分钟打完一个结局。
- **技术栈已经是 Vite + TypeScript 了**（§6.20/§6.21）：引擎和流程全在 `app/src/core/*.ts`，`vite build` 出纯静态 `dist/`，**能直接上 Cloudflare Pages**。没上 React——界面还是原生 DOM，靠 `app/src/ui.js` 那 800 行（从旧的 `web/app.js` 原样搬过来，只换了数据来源）。**故意不引 React**：这套界面就是一屏一屏换 DOM，重写成 React 只会多一层状态同步的坑，不如把工时花在卡面和结局上。
- `web/` 现在只剩 `index.html`（vite 的模板）、`style.css`（790 行样式）和 `sprites/`（四张立绘）。**`web/app.js` 已删**。

---

## 3. 文件地图（都在 `C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\`）

### 前端工程 `app/`（§6.21 起是主线，改任何东西都看这里）
- `app/src/core/rng.ts`（278 行）——CPython `random.Random` 的 MT19937 精确移植。**别改逻辑**，改了就过不了 `rng.test.ts` 的 84 项。
- `app/src/core/engine.ts`（约 2170 行）——`game/engine.py` 全量移植，函数 camelCase。数据层是 `loadFiles(files)` / `loadWorld(files?)`，`RawFiles` = `相对路径 -> JSON`。
- `app/src/core/loop.ts`（约 2320 行）——`game/loop.py` 的 `Game` 类全量移植（70 个方法、4600 字文案）。**改这里的任何一屏文案，都必须让 `loop.test.ts` 继续绿**（它有 77880 项逐屏对账，§6.25 后）。
- `app/src/core/bill.ts`（78 行）/ `types.ts`（176 行）。
- `app/src/boot.ts`（317 行）——替代 `game/server.py`。`loadDataFiles()` 用 `import.meta.glob` 把 `data/**` 和 `结局.md` 打进 bundle；导出唯一的 `call(path, body)`。
- `app/src/ui.js`（约 810 行）——界面层，从旧 `web/app.js` 原样搬来，只改了 `api()` 的实现。**要改 UI 就改这个文件**，不是 `web/app.js`（已删）。
- `app/src/main.ts`——一行 `import "./ui.js";`。
- `app/test/`——三个对账测试 + 三份 Python 侧生成的标准答案（`rng_expected.json` / `trace_expected.json` / `loop_expected.json`，最后一份 1.2MB，**别手改，重生成**）。
- `vite.config.ts` / `tsconfig.json` / `package.json` / `pnpm-workspace.yaml`。

### 文档
- `DESIGN.md`（~316 行）——设计封版，先读。§6.5 剧情线系统、§7 结局系统、§9 数值表是核心。**注意 §2/§6/§9 里部分数值已被代码覆盖**（见 §4）。
- `结局.md` / `结局条件图.md`——17 结局正文与判定图。`data/endings.json` 从这里生成。
- `data/卡库总览.md` / `卡库审核.md`——所有卡 + 剧情线的人话版，给用户审核，`tools/gen_overview.py` / `export_cards_for_review.py` 生成。
- `CODE_PLAN.md`——早期代码规划，留档。

### 数据 `data/`
- `data/cards/*.json`——**119 张卡**，10 个文件：`ambient`10 / `daily`6 / `external`14 / `ota`9 / `ota_recall`42 / `positive`8 / `private`1 / `shiroi`8 / `team`15 / `team_bond`6。按 `type` 分：OTA记忆42、团内14、外部12、外部舆论2、OTA互动8、OTA相处的瞬间1、ambient10、日常6、positive7、私生7、私生跟踪1、私联恋爱1、舞台事故1、团内关系7。
  - schema：`{id,type,title,gate,weight,cooldown,narrative,options[,casting][,effect]}`；option=`{id,label,desc,immediate,delayed,flag?}`；ambient 卡无 options，用 `effect`+`note`。
  - **选角槽 casting**（写卡必用，别写死真人名）：`[{slot,select:{gender?/fan_type?/archetype?/min_stickiness?/private_contact?},allow_hatch?,force_hatch?}]`；文案用 `{{slot}}`（名字）、`{{slot.ta}}`（他/她）；effect 键 `"@<slot>"` 打到该 OTA 黏性。
  - effect 键全集：fame, money, ota_all, psyche, relation_A/B/C, relation_all, stage, stamina, enjou, kaibox, shiroi, banzi, shiren, `@slot`。
- `data/storylines/*.json`——**3 条在用**：
  - `storyline_shiren.json`（私联线）**`stages` 5 拍（越线/深夜/见面/上头/裂痕）+ 顶层 `finale`（stage:5「收场」，唯一有终局拷问，12 个 `memory_key` 记忆点供出题）**。`finale` **不在 `stages` 数组里**，是单独顶层 key（含 `quiz` 抽 3 道、答对≥2→`truly_seen`、≤1→`used_as_tool`、4 个 `final_choices`）。⚠️ 见 §7.7：它疑似没接进运行时引擎。
  - `storyline_zhong.json`（重线，取代原私生线）**4 拍**，由不可见内部量 `zhongs`「她攒下的」驱动，无拷问只写 flag，收口 `final_intimate`→我只是太爱你了 / `final_cautioned`→交季末判定。
  - `storyline_romance.json`（队友恋爱线）**5 拍**（心动/靠近/越界/确认/收场），对象固定阿棠，heart 驱动，无拷问。
  - `data/storylines/_retired/`：`storyline_shiroi.json`（原私生线）、`storyline_ota_jelly.json`（盐渍水母个人线）。**个人线已整体取消**（2026-11-14 用户定：功能与记忆回考重复、只对一个人不公平），不再做。
  - **剧情线 option schema**：`{id,label,desc,immediate{res:delta},advance:int,learns:'记忆点key'|list|None,flags:[],delayed:[{when,condition?,effect,note}],rq?:{clue,reason},note?}`。
  - **四条写作铁律**（用户反复拍板，别推翻）：① 重线的「她攒下的」玩家看不见，只能靠信越来越长、提到的事越来越具体来读；② 拍与拍之间必有「好孩子时刻」；③ 第三拍起她开始「模仿」我用过的关心；④ 第四拍不写她出现，写她走了留下没写名字的塑料袋。⑤ OTA 个人线（已取消，但写同类内容仍遵守）**不写私联情节**：加微信/私下见面/楼下等/定位/kaibox/shiroi 全归私联线；OTA 与 XOX 的交流只发生在特典会现场 + 微博 + 场馆内散场前后，禁止一起走到地铁口/送回家/深夜电话/换联系方式。⑥ 私生 ≠ 开盒：私生能收场，开盒收不回来，项目里开盒靠散落 `kaibox` 累积、没有自己的线。
- `data/cards/ota_recall.json`——**记忆回考两拍卡组**（42 = 21 线索 × 2），`tools/build_ota_recall.py` 生成，是当前回考主入口。
  - 第一拍「她说」`ota_say_<clue>`：三选一细节，真值当场锁进本局；三个反应都算记住、都会被考，无安全选项；差别只在第二拍期望高低。「岔开话题」带 `rq_drop:true`，延迟再掉 `@speaker -4`，运行时把这条线索**从本局回考池删掉**（唯一让线索彻底消失的路径）。cooldown 6。
  - 全场闸门 `_meta.max_clues_per_run = 6`：一局最多开 6 条线索，由抽卡器读 `_meta` 统一管（不能挂单卡）。
  - 第二拍「她问」`ota_ask_<clue>`：隔 ≥2 场再提，三选一，对 +2/+4/+6、错 −3/−5/−8（轻/中/重），cooldown 8。**绝不出现「你还记得吗」**，用「你说得出来吗」「我考考你」。
  - 重型 5 条硬闸门「任一 OTA 黏性 ≥70 且 认识周数 ≥3」weight 0.6；其余「黏性 ≥45」weight 1.0。重型走 `say_full`（三种情况各一整句）与 `_ota_memory_askheavy.py`。
- `data/ota_memory.json`——**21 条线索池**，`tools/build_ota_memory.py` 生成。`_meta.memory_key` 是自带登记表，`validate_all.py` 靠它认线索，**别把登记挪回个人线**。占位符只有 `{truth}` `{wrong}`。`say` 必含 `{truth}`、三条 `ask` 各含 `{truth}`、`react_bad.gravity` 必含 `{wrong}`。七原型键：`gravity/bold/mom/angler/shy/nerd/joker`。**同一局取值锁定、重开重新随机；同一条线索第二次被提及时才考；答错没有任何补救，直接掉好感**（用户 m00420/m00422 拍板）。修正层 `_ota_memory_fix.py / _ota_memory_react.py / _ota_memory_say.py / _ota_memory_sayfull.py / _ota_memory_askheavy.py` 都别删，改线索池后依次覆盖。
  - 轻 9（fruit_craving/food_hate/daily_drink/pet_dream/weather_hate/loop_song/commute/snack/phone_app）、中 7（work_file/off_work/pet_type/dream_place/family_pressure/money_habit/commuter_route）、重 5（first_visit/spare_thing/alone_reason/what_keeps/prev_group）。
  - 剧情线 option 挂 `rq={clue,reason}`（`build_ota_lines.py` 有 `def rq(...)` helper），语义「选了这项她才顺口说出该线索」，未刷出则静默跳过；其余线索由「每场约 30% 概率回考」覆盖。
- `data/ota_pool.json`——种子 5 人 + 6 原型（重力系/社恐温柔/自来熟/DD/长发男文青/整活型）+ 网名池 + 孵化规则。**改表**：钓师→DD、考据文青→长发男文青、妈妈粉删除（「今天也不困」改挂事业粉）。种子用 `stickiness`/`spend` 两字段，`engine.new_state()` 两个都搬。
- `data/intro.json`——序章。团名「二十二点三十分」，`text` 6 段 → `before_quote` → `choices`(3) → `after_quote`。`base_state` 已是「选完之后」的开局值，`choice.effect` 只用来核对三条路线，**别往 `base_state` 上再叠一次**（叠了心理顶到 100，执念成魔/空心全失效）。`weeks_total = 8`。
  - **⚠️ 界面已删掉三选一**（2026-11-15 用户「第一个上台之前事件意义不大」）：`loop._build_intro` 只 push（团名正文 → before_quote → after_quote → `_build_name()`），静默用 `intro["choices"][0]["id"]` 落定开局。但 `data/intro.json` 里 `choices` 三段数据仍在（供 `check_intro_econ.py` 核对用）。`server.py:146` 还留着 `if kind == "intro": g.choose_intro(oid)` 死分支（`choose_intro` 已删），因为界面不再发 intro choice 所以不会触发——**别以为三选一还在**。
- `data/endings.json`——判决表，**16 = 季末 10 + 提前 6**。`flow[]` 季末顺序、`early[]` 提前结束（flag 直接触发、不进瀑布）。`build_endings.py` 生成，条件是文档驱动的：先在 `结局条件图.md` §一改，再改脚本重跑。
- `data/idol_names.json`——取名池。

### 游戏代码 `game/`（纯 Python，随机全走传入的 `random.Random`，可复现）
- `game/engine.py`——规则引擎：`load_world()` 读全部数据 / `new_state(world)` / `do_week(...)` 跑一周 / `judge(s,world)` 判结局 / `weekly_income(s)` / `warm_ota(s)` / `hatch` / `cast` / `settle_delayed`。
  - 常量：`RENT=900`、`FEE=620`、`FEE_FIRST=160`；`income>=560` +2 心理、`<240` 记低收周 −6 心理；`SKILL_CAP=82`。
  - `_EventMult.MULT`：卡面数值→真实资源的倍率（enjou×6 / banzi×8 / kaibox×3 / psyche×1.4×0.6 / fame×1.5）——卡库原始量级只有 1~6 点，撑不起 20~90 的结局门槛，**这一层必需**。
  - `TYPE_WEIGHT`：42 张回考卡压到 0.15，避免挤掉其它卡。
  - **force_hatch（见 §6.6）**：`cast(s,card,rng,world=None)` 里只有 `force_hatch` 才现场生人，`allow_hatch` 只是「找不到人返回 None」；`hatch(...,ignore_cap=False,base_stick=None)`；`settle_delayed(s,world,rng)` 统一处理延迟（含 `hatch_friend`/`base_stick`）。
- `game/bill.py`——特典券账。**`PRICE=80`**（全团统一价，没有大小券品类；「出手大」＝买得多）。`tickets_of(o) = 1 + int(stick//25) + (1 if spend>=4 else 0)`（黏性每 25 一档、消费力到 4 再多一张：55→3、70→3、78→4、第零排 70/消费4→4）；`钱 = 张数 × 80`，**不乘人气系数**，人气只决定今天谁来、来几个（`warm_ota`）。⚠️ 文件顶部 docstring 还留着旧公式 `round((1+stick/50)*(1+spend/5)/2)`，**以 `tickets_of` 实现为准**。
- `game/loop.py`——**界面流程引擎（核心，见 §4）**。`Game` 类持有 `state/queue/pending/wk/...`，`current()` 取队首，`advance()` 弹屏，`after_step()` 唯一推进器，`step_week()` 唯一排序器。
- `game/policy.py`——测试打法：Random/Greedy/Reckless/Flirty/Hollow。**别写「钱不够就打工」这类保底动作**（券账制下基本不缺钱，写了稀释打法）。
- `game/server.py`——HTTP 服务 + **自动存档**（见 §1、§6.1）。
- `web/index.html` / `app.js` / `style.css`——原生前端（**仍是旧版，打 `/api/*` 跟 Python 服务说话**；TS 版引擎在 `app/src/core/`，前端还没接上，见 §6.20）。
- `app/src/core/`——**TS 版引擎**（`engine.ts` / `loop.ts` / `bill.ts` / `rng.ts` / `types.ts`），与 Python 侧逐屏对账全对，准备上 Cloudflare Pages。`app/test/` 是三个对账测试，`tools/trace_dump.py` / `tools/loop_trace.py` 是 Python 侧录标准答案的脚本。

### 工具 `tools/`（内容构建/校验/诊断脚本，非游戏代码，全部保留以便复现）
- **`validate_all.py`——改完任何数据必跑**。八组全 0：JSON 合法 / 第一人称 POV 无「你」（剥离 `『』「」""''“”` 后查 narrative + 变体标题 + 选项 label/desc）/ 纯赚（带 `rq_pick` 的正确项豁免）/ 写死种子名 / literal key / `learns` key 必须在任一剧情线 `memory_key` 池 / ota_memory 线索池九项 / 回考卡组结构（`RECALL PROBLEMS`：`rq_stage` 合法、每张「她说」全选项带 `rq_lock` 且恰好一个 `rq_drop` 且有延迟惩罚、每张「她问」恰好 3 个 `rq_pick` 且只有一个 `choice=="true"`、`max_clues_per_run` 整数）。`KNOWN_MEM` 同时读顶层与 `_meta.memory_key`；`UNKNOWN_LEARN` 按所有剧情线 key 并集识别。
- **`gen_overview.py`**——改完数据必跑，重生成 `data/卡库总览.md`。已修：`choice_pools`/`mk_label` 同时读顶层与 `_meta.memory_key`，`mk_label` 先 `label` 再 `q`，剧情线标题下加「本线记忆点」一行。
- 构建器：`build_shiren.py` / `build_zhong.py` / `build_romance.py` / `build_ota_memory.py` / `build_ota_recall.py` / `build_intro.py` / `build_endings.py` / `build_team_cards.py` / `build_idol_names.py`。**改数据改脚本再跑，别手改 json**；改线索池必须重跑 `build_ota_recall.py`（下游）。
- 已退役/一次性：`build_shiroi.py`、`build_ota_lines.py`（个人线，留档）、`build_round1.py`、`migrate_casting.py`、`clean_private.py`、`_fix_pov.py`、`_fix_pure.py`。
- 沙盒/诊断：`economy_sandbox.py`（`judge()` 是判定顺序代码版 + 11 打法 × 30 种子覆盖 11/11；⚠️ 它仍在用旧收入公式，只当历史沙盒看）、`check_intro_econ.py`（用 `intro.json` `base_state` 重跑 12 打法 + ±30% 事件强度带宽）、`run_policies.py` / `sweep_profiles.py` / `probe_endings.py` / `test_engine.py` / `run_seasons.py` / `audit_flow.py`、`tune_report.py` / `check_income_curve.py`、`gate_report*.py` / `line_report.py` / `wind_report.py` / `money_report.py` / `rep_report.py` / `skill_value.py` / `skill_curve.py`、各 `fix_*.py`。
- `tools/_check_order.py`——流程冒烟（开场同步：删 `choose_intro`，改 3 次 `g.advance()`），6 seed 「有问题: 0」。`tools/_smoke_loop.py`——三个 seed 走界面到底。

---

## 4. 当前架构：一周怎么排（**最重要，改动前先读这段**）

这一轮把「抢卡位」的一堆 `push_front` / 事后纠正机制**全部推倒**，改成单一队列。`game/loop.py`：

- **`Game.wk`** 是唯一进度表：
  ```
  {"act":0,"mid":0,"fri":0,"sat_act":0,"sat":0,"bill":0,
   "sun":0,"bill2":0,"sun_talk":0,"events":[],"extra":[],"talk":None}
  ```
  类常量：`ACT_LEFT=6`、`ACT_SAT=7`、`WEEK_EVENTS=3`、`LINE_CHANCE=0.85`、`EVENT_SPOTS`（6 组）、`TEAM_TYPES`、`EV_FALLBACK`、`SCENE`（卡面场所）。
- **`after_step()` 是唯一推进器**：队列空时 `for _ in range(40)`，`week > WEEKS`→`_finish()`；`s.get("_week_started") != s["week"]`→置位并 `_start_week()`；否则 `step_week()`；`step_week()` 返回 False 才 `_finish()`。**判断「本周是否开过头」用 `s["_week_started"]`，绝不能用 `wk` 全零**（`_start_week` 每次重置 wk，用 wk 判会无限重开）。
- **`step_week()` 是唯一排序器，顺序写死在这里，别处不许插队**（见 `loop.py:253–310`）。一周格子顺序：
  1. 平日 6 格：`act` 第 1 格 → 逐格 `act += 1`；**第 4 格（`wk["act"]==4`）推 `push_midweek()`（版聊/剧情线那张），其余格推 `_wk_choice()`（晚上选一件事）**，直到 `act == ACT_LEFT(6)`。
  2. `fri` → `push_live(last=False)`「周五·X 场」。
  3. `sat_act` → 周六那一格 `_wk_choice()`。
  4. `sat` → `push_live(last=True)`「周六·X 场」。
  5. `bill` → `_bill_step()` 券账屏，**紧接着 push 特典 talk**（`wk["talk"]`，没有则一句「今天收得快…」）。⚠️ 特典已从「3 张卡之后」提到券账之后（用户「周六的活后面不开特典会」）。
  6. `sun` → `push_live(last=True, sunday=True)`「周日·X 场」，`sunday` 时演出分 `sc -= 3.5`。
  7. `bill2` → `_bill_step(sunday=True)`「周日这一场的券」。
  8. `sun_talk` → `_sun_talk_step()`（只一句「还是这几个人：…话都说过一遍了，剩下的就是坐着」，**不带选项、不讲新剧情**），随后 `for st in wk["events"] + wk["extra"]: push(st)`（本周 3 张周卡 + 特例卡）。
  9. `settle_week()`：算钱/清延迟/`week += 1`/push 结算屏；它把 `_done_week` 存进 `s["_settled_week"]`。
- **`_collect_week_extras(warm)`**（在 `push_live` 末尾）算 `wk["events"]`（`_draw_week_events()`，最多 3 张）、`wk["extra"]`（`_maybe_ask_tired` / `_maybe_ask_offer`，返回 step 不自己 insert）、`wk["talk"]`（`_make_talk(warm)`）。`_start_week()` 重置 wk + push「第 N 周」+ 房租 + 那一拍剧情线（`_maybe_story()` **返回 step，不自己 insert**）。
- **教训（别重蹈覆辙）**：旧代码里有 `choose_act` 漏 return、`_build_weekday`↔`_build_live` 递归、`push_front` 把券账/事件卡排乱、同名方法覆盖、字符串切片删方法粘行、连删类常量等一连串坑。已删除 `_build_week_start/_build_weekday*/_new_week/_build_midweek/_build_live/_queue_week_events/_flush_*/_push_talk/_maybe_insert_card/_others_waiting/_reopen_week/_fix_week_queue/_rebuild_rest_of_week/_maybe_settle_or_wait/_kind_of/WEEK_ORDER`。**要改顺序就改 `step_week()`，不要再加事后纠正或 `push_front`。**

---

## 5. 已定案、别推翻的设计与数值

- **16 结局 = 季末 10 + 提前 6**（§6.18 删「交易孤立」后）。季末判定顺序（高→低，见 `endings.json flow[]`）：如影随形 → 你第一天知道我的恶劣吗 → 执念成魔 → 空心 → 残局 → 现生快乐 → 彗星来临的那一夜 → 守住本心 → 台上那十分钟 → 散场（保底）。提前 6：我只是太爱你了 / 用完 / 唯一 / 毕业日 / 后来 / 控制不了（flag 直接触发、不进瀑布）。
  - 关键改名/条件（§6.18.2 现行）：原「被吞噬」→如影随形（开盒≥80 **且私联线≥第2拍**）；「熄灯」删（与黑红共用炎上≥70 且板子≥60，且收入一季从不掉，永远打不出）；黑红→你第一天知道我的恶劣吗（炎上≥70 且板子≥60 且 `money_kept`）；高光一瞬→彗星来临的那一夜；幸存→守住本心（心理≥45、关系均值≥30、≥2 个 OTA 黏性≥40、真话率≥50%、当面拒过运营那条路 `offer_choice==refuse`）；被留下+平凡退场+旧散场→三合一「散场」；主动下车→现生快乐；连累→残局（关系均值<30 且炎上≥80）；台上那十分钟（舞台 55–61、心理<20、崩着上台）。空心=真话率<40%（至少做过两次真话/场面话选择）且 `empty_choice==reply` 的瞬间判定（week≥3、有黏性≥45 的人在场）；回考答对记 `recall_ok`，不再算真话。
  - `economy_sandbox.py` 的 `judge()` 已同步 16 结局，10 打法 × 30 种子覆盖 10/10；改结局条件时它与 `build_endings.py` 要一起改。
- **数值**：初始钱 1700 / 体力 100 / 心理 66 / 人气 12 / 舞唱话 45·40·35 / 队友各 50 / 常连 50（以 `intro.json base_state` 为准）。房租 900（隔周交，欠租→`rent_missed` 心理−10 钱清零体力−5），周费 `FEE=620`（首周 `FEE_FIRST=160`）。
- **舞台分** `= 0.32舞 + 0.28唱 + 0.22话术 + 0.18关系均值`（**不含体力**）+ 单场疲劳 `±5` 抖动。档位 神场≥64/好场≥54/平场≥44/冷场≥34。8 周实用上限 ~65~75，**别设门槛>80**。练功 A 案：舞/唱 +6.0/晚、话术 +5.0/晚、`SKILL_CAP=82`。**季末体力必为 0 → 任何结局条件不能再写 `stamina>=N`**。
- **§9.5 每周自然衰减**：OTA 黏性/团内关系/心理 各 −1.2/周；`cool_down()` 另加 板子 −6、炎上 −4 的每周回落（别让板子一周爆表）。
- **§6.5 剧情线系统**：触发靠条件不靠日历（gate 满足当周必出、压随机卡；heat/heart/dread 驱动快慢，冷淡则卡住断线）。共存「一主一辅」：每季最多 1 条深主线（私联 或 队友恋爱）+ 最多 1 条私生后果线；**三条线都可不开**；只有私联线有拷问。
- **真话 `true_talk` 只认 `option["tone"]=="truth"`**（别按 flag 名/关键词猜，会误把「拒绝加联系方式」算进去，与空心判据打架）。`shiren` 只由剧情线 `met_alone` 记账，卡面里不许直接写 `immediate.shiren`。
- **软上限**：`soft_cap_psyche`（>85 每点算 1/4）、人气软上限 `FAME_SOFT=40` + `FAME_CAP=80`（2026-11-15 改：统一走 `add_fame(s, delta)`，**只对本帧新增那一截**打 1/3 折、绝不回缩存量；旧版 `soft_cap_fame` 压的是累计值且非幂等，每张无关卡都把 fame 往 40 拽，玩家会看到人气「莫名掉」）；所有 fame 增减来源（卡面/apply_effect、平日动作、版聊、Live 舞台加分、接运营、离线 do_week/run_season）一律走 `add_fame`，不许再直接 `s["fame"] +=`。卡面正增益系数：relation ×0.4、stage/enjou/banzi/kaibox/shiren ×0.6、fame ×0.6（事件位翻倍后不收口就会被「多刷一张卡」堆到顶）。
- **孵化新人**：`hatch_rules` 一季最多 3 个（`s["hatch_n"]`/`hatch_max`），按原型从 `name_pools[性别]` 抽没用过的网名，黏性取 `min(require.min_stickiness, 原型 base_stickiness)`，`is_seed=False`、`met_week=当前周`；界面特典名单标「（第一次来）」。网名池男女各 40 个。
- **§9.6 OTA 升格**：反复被抽到 + 持续投入 → 升格核心人物 → 才解锁个人线（个人线已取消，此机制留作占位）；一季上限 1~2 个。

---

## 6. 这一轮（2026-11-15 凌晨）改了什么 / 为什么 / 实测

### 6.1 自动存档（修「莫名其妙重开」）
`game/server.py`：`SAVE = game/_save.json`；`_rng_state`/`_rng_load` 做 `random.getstate()` 的 tuple↔list；`_dump_game(g)` 存 `{state,queue,pending,wk,acts_done,over,rng,name,name_style,name_options}`（state 为 None 的序章阶段也存）；`_load_game(doc)` 用 `loop.Game(seed=0)` 建世界再覆盖状态，把 `flags`/`_fired`/`_met_people`/`_weeks_seen` 的 set↔list 还原。`Session.new/advance/choose` 末尾都 `save()`（写 `SAVE+".tmp"` 再 `os.replace`），`__init__` 优先读档、失败才新开。
- 实测「跑 120 步 → 存档 → 读档继续 → 结局与钱一分不差」；**不存 rng 状态会分叉**（`散场` vs `残局`），补 `_rng_state` 后才一致。
- 代价：只有点「重开」才真重开，干净周目要删 `_save.json`（见 §1）。

### 6.2 队友恋爱线可达性（阿棠）
原三个真 bug：① `engine._gate_ok` 把「阿棠关系≥60」当 `enter_heat=relation_A−60` 比，关系 79 都开不了；② `heart` 只在 `advance=1` 选项 +1，8 周不够走五拍；③ `draw_line` 未开线不吃「已进入 +1.2」被压死。改：`_gate_ok` 拍 0 特判 `if lid=="romance" and st["stage"]==0: return relation_A>=50 and week>=2`；`apply_option` 拍 0 进入时 `heart=1`；`draw_line` 里 `relation_A>=50 → base *= 2.4`（原 1.8）。另修 `apply_option` 的 `"slots": {k: v["id"]}` → `v.get("id")`（恋爱线 `ta={"name":"阿棠"}` 无 id，否则 `KeyError: 'id'`）。
- 实测 10 seed：拍 4（确认）2、拍 3（越界）2、拍 2（靠近）5、没进 1（那局阿棠 34）。**完整走完五拍仍紧**。

### 6.3 序章删三选一 + 特典提前
用户「第一个上台之前事件意义不大」→ 删 `kind:"intro"` choice 屏与 `choose_intro`。**踩坑**：`_build_intro` 里残留 `self.queue.pop(0)` 会吃掉名字屏导致「海报上要印个名字」无限重复；正确做法是只 push 不 pop。`_check_order.py` 开场同步改成 3 次 `g.advance()`。特典从「3 张卡之后」提到券账之后（`step_week` 的 bill 格）。

### 6.4 周日也开特典会
`wk` 加 `sun/bill2/sun_talk`；`step_week` 在周六券账后接周日场→周日券→周日特典→3 张周卡→结算。`push_live(sunday=True)` 演出分 −3.5、标题「周日·X」；`_bill_step(sunday=True)` 标题「周日这一场的券」；`_sun_talk_step()` 只出一句、不重复讲剧情。
- 顺序实测：周五场→周六场→周六券→周六特典→周日场→周日券→周日特典→3 张周卡→结算。
- **⚠️ 未处理的副作用**：一季收入约多五成（多卖一天券），钱会更宽；**是否压周日券价/分成待用户定**（open objective）。

### 6.5 团内卡降频
`EVENT_SPOTS` 6 格里团内只在第 3 位出现一次；新增 `TEAM_TYPES = ("团内","团内关系","团内冲突")`；`_draw_week_events` 加「一周最多一张团内卡，非团内位抽到团内卡就重抽」。实测每周 1.4 张（最高 3）→ 0.9 张，整季 87 → 约 54。

### 6.6 force_hatch（修「说新 OTA 来的却是老粉」）
`engine.cast` 重写：以前任何 `allow_hatch` 卡凑不出人就现场生一个，于是老剧情卡也会凭空冒新名字。现在**只有 `force_hatch` 才生人**，`allow_hatch` 只表示「找不到人返回 None」。`data/cards/ambient.json` 的 `amb_fan_brings_friend` 加 `force_hatch: True`；`ota.json` 的 `ota_newbie` 也是（`force_hatch` + `invest` 的 delayed `hatch_friend:true`/`base_stick:45`——「她真的又来了，还拉了一个人来」，由 `settle_delayed` 生人，结算屏写「她把朋友带来了：X。」）。实测 8 局非新人卡冒出新人 0 次。

### 6.7 UI 回执修正（更早一轮）
`_snap(s)` 原来只快照资源、不含 OTA 与队友关系 → 好感不显示 / 每轮 +50 队友。新增 `_osnap(s)`（OTA 列表）/ `_rsnap(s)`（`relation_A/B/C`），`_sticks()` 跳过 before 里没有的 id，`_mates_changed()` 只报 `d!=0` 的变化；三处回执各带 before 快照。`_render_card` 删掉选项 label 上的数值后缀（「（黏性+3）」）。全项目「串场」→「营业」（数值字段名 `mc` 保留）。

### 6.8 季末结局入口 + 人气「莫名掉」（2026-11-15 追加）
- **三个季末结局打不出**（空心 / 现生快乐 / 守住本心）：`loop.py` 的 `_collect_week_extras()` 每周被 `push_live` 调 3 次（fri/sat/sun），每次整体覆盖 `wk["extra"]`；一次性提问（`_maybe_ask_tired`/`_maybe_ask_offer`）生成时即立 `asked` 标志，fri 生成的那张被 sat/sun 覆盖冲掉，等 sun_talk 格消费时 `wk["extra"]` 已是 `[]`。另 `_maybe_ask_stay()` 全项目无调用点 → `chose_leave` 恒 False。改法只动 `_collect_week_extras` 一处：覆盖改成按 `kind` 累加去重，并把 `_maybe_ask_stay()` 纳入生成元组；**不动 `step_week`**（合 §4）。实测 12 seed：offer/leave 生成=上屏=12（改前生成 12/上屏 0），选 refuse/leave 后 `offer_choice=refuse`、`chose_leave=True` 均落库，隔离 `judge()` 三结局均可判。「空心」另需 `template>=0.45`：`work` 打法（每晚 `template+=0.018`）W3 会触发「累不累」并实跑命中，练舞/练唱把 template 压到 0 则不触发——**设计意图，不是 bug，不动**。
- **人气莫名掉**：`engine.py` 旧 `apply_effect` 末尾 `s["fame"] = min(FAME_CAP, soft_cap_fame(s.get("fame",0)))`，而 `soft_cap_fame(v)=cap+(v-cap)/3` 压的是**累计值**且非幂等（60→46.67→42.22→…→40），于是任何一张只加舞蹈、与人气无关的卡都把 fame 往 40 拽。用户选「忠实修法」：删 `soft_cap_fame`，新增 `add_fame(s, delta)` —— 只对本帧新增那一截打 1/3 折（40 以下全额、跨 40 分段算、40 以上每点算 1/3）、绝不回缩存量，收口 `FAME_SOFT=40`/`FAME_CAP=80`，返回真实增量；**所有** fame 增减来源（卡面 `apply_effect`、平日 `do_act`、版聊 `_pick_talk`、Live `push_live`/`do_week`、接运营 `choose_offer`/`run_season`）统一走 `add_fame`，不许再直接 `s["fame"] +=`；`choose_offer` 回执改用返回的真实增量（fame>40 时 +12 实际只 +4，别让回执骗人）。
- 实测（8 seed 全界面）：改前「effect 无负 fame 却让 fame 下降」**219 次 / 累计 191.28 点**、每周末 fame 钉死在 40 上下；改后 **0 次 / 0.00**，fame 正常爬到 40~62。`fame=60` 反复 apply 无关卡轨迹 `60→60→…→60`（幂等）。`validate_all` 八组全 0、`_check_order` 6 seed「有问题 0」、`_smoke_loop` 3/3 到结局（285/285/279 步）。**副作用（如实记，未擅自回调）**：人气不再被压会牵动 `warm_ota`/收入/结局判定，8 seed 结局分布 `残局4·台上那十分钟4 → 残局3·台上那十分钟5`；「台上那十分钟」偏多见 §7 待办第 3 条，等玩家真玩一轮再动。
- 另：`loop.py` `choose_empty` 的 truth 回执仍写 `delta={"psyche":3,"fame":-1}` 但没真的扣 `s["fame"]`（旧存的小不一致，本次未动）。

### 6.9 残卡 / 空回执 / 「第一次来的人」演成老粉（2026-11-15 下午）
用户报的两个 bug：「有时候莫名其妙出『手机亮了一下』这张卡但什么也没有」「新 OTA 第一次来这张卡时，强制用新生成的 OTA，不然不合理」。

**根因（三条，都不是表面上那条）**：
1. **残卡**：`E.cast()` 返回 `None`（卡要的人不在场）时，调用处写成 `or {}` 吞成空 dict，`_fill()` 就填不上槽，正文顶着裸 `{{slot}}` 上场。另外 `_make_talk()` 调 `E.cast()` **没传 world**，生人分支走不通，只能用 `{"speaker": who}` 顶，卡要的槽叫 `nightowl`/`devotee` 时就空着——**用户看到的残卡基本都出自特典卡这条**。
2. **空回执**：`choose_card` / `choose_talk` / `choose_story` 三处都只看 `o["note"]`。全库 321 个 option 里只有 **65 个写了 note**（258 个只有 desc），于是「什么都没有」的回执有 130+ 屏——这比「手机亮了一下」普遍得多。
3. **「第一次来的人」演成老粉**：`ota_newbie` 的 casting 是空 `select:{}`，`pick_ota` 空条件恒能命中老粉，`force_hatch` 的分支一辈子走不到；且 `_match_archetype` 在 select 无 archetype/fan_type 时直接 `return None`，就算强行走 hatch 也生不出来。

**改法（只动这三处，没碰 `step_week` / 数值表 / 卡库内容）**：
- `engine.py` 新增 `wants_new_face(card)`；`cast()` 支持 `hatch_only`（先不找老粉、直接生人），生不出来就整张卡作废（`return None`），并把「只指定 gender」补进 `_match_archetype`（「一个女生第一次来」按 `女友粉` 找对口原型，不再一律落 `archs[0]`）。
- `data/cards/ota.json` 的 `ota_newbie` casting → `{"slot":"speaker","select":{"gender":"女"},"allow_hatch":true,"force_hatch":true,"hatch_only":true}`。
- `loop.py`：`push_midweek()` / `_draw_week_events()` / `_make_talk()` 三处不再 `or {}`；抽到新人卡但名额满（`hatch_max=3`）时**换卡重抽**，不拿老粉顶；`_make_talk` 补传 `world`，并在 cast 失败时把卡自己声明的**所有槽**都指给当天留下来的人（不只 `speaker`）。
- `_fill()` 末尾兜底：还有没填上的 `{{xxx}}` 一律替换成「对方」，绝不让占位符裸奔到玩家眼前。
- 回执正文 fallback 链改成 `note → desc → 「就这样吧。」`（`choose_card` / `choose_talk` / `choose_story` 三处同改）。

**实测**（10 seed 全界面走到底，平均 276 步）：
- 残卡（正文含 `{{`）**0 屏**（改前 `_p_v5` 抓到 5 处）。
- 空正文回执从 **255 → 193**，剩下 193 屏**全部**是 `choose_act` 的行动回执（标题本身就是结果句，如「拍了一组…」，正文本来就不该有）——属于设计。
- 「第一次来的人」共出现 10 次，**speaker 100% 是 `hatch_*`（`is_seed=False`）**，改前有 `ota_row0`（第零排，种子老粉）混进去。
- `validate_all` 八组全 0；服务已重启并过一遍界面（`/api/state` 200）。

### 6.10 回考真值 / 私联收场 / 记忆点太少（2026-11-15 下午，三块一起改完）

用户拍板：「锁随机真值 + 渲染时重排选项」「finale 复用回考系统当拷问」「一次全做完再给我看」。

**(1) 回考卡把 `{truth}` 原样端上屏（比 §7.7 更严重，正片在露字）**
- 根因三条：① `engine.py` 的 `rq_lock` 只存 `{state, asked, said_week, who}`，**没有 truth 字段**，`loop._rq_reply` 取到的恒为空串；② `_fill()` 只清双花括号，`{truth}` 这种单花括号照原样上屏；③ 42 张回考卡的正确项恒为 `pick_0`（生成脚本为稳定 diff 写死的），真值一随机就变成「记得对也判错」。
- 改法：`engine._pick_truth` + `ensure_truth(s, cid, rng)`（`s["_truth"]` 里掷一次就死，同一局反复考同一件事）；`ask_order(s, cid, n, rng)`（`s["_ask_order"]` 存本局固定的三选一顺序）；`rq_pick` 判定改成 `(option["label"] == truth)`，不再看 `choice`；`loop._ask_options` 按 `ask_order` 重排选项。
- **渲染路径有两条**（`_render_card` 与特典的 `_render_talk`），只修一条仍会露字——抽了 `_card_body` / `_card_opts` 两个共用方法，两边都走它。

**(2) 收场：题干把答案印在问句上**
- `ota_memory.json` 的 63 条 `ask[]` 全是「陈述句挖空」，例 `『我上次跟你说过我想吃{truth}来着？』`。真值一填进去，答案就在题干里；抹成「那个」又读成「今天又拖到那个，午饭都省了」。
- 改法：给 21 条线索各加一个 `ask_q` 字段（一句天然问法，如 `『我平时靠什么撑着，你还记得吗？』`），`finale_quiz_cards` 优先用 `ask_q`，没有才退回 `ask[]`。

**(3) 私联线走不到收场（实测 0/20 到 stage4）**
- 根因是 `_line_tick` 只在抽到线之后才更新，`engine._this_week` 拿它跟 `_line_week[lid]` 比「本周是否已推」→ 上周推过的线这周开头就被判成已推，`line_stage` 返回 None，私联此后永远轮不到。
- 改法：`_start_week()` 里 `s["_line_tick"] = s["week"]` 跟着周走；`draw_line` 给越线后的私联 `base *= 2.6`；新增 `_shiren_if_crossed()`——只在「再不推就来不及」时插队（`left_stages > left_weeks`），不周周霸占那唯一一次推线机会。

**(4) 记忆点太少 → 收场只有一道题**
- 根因：`_collect_week_extras` 挂在 `push_live` 上，一周跑三次（周五/周六/周日），每次都重新 `ota_pick`，**只留最后一次、前两次白抽**；而 `ota_pick` 有副作用（抽到 ask 卡就把线索标成 `asked=True` 上冷却），被覆盖掉的那两次照样把线索吃掉了。
- 改法：`wk["_prep"]` 标记，一周只 prep 一次；`ota_pick` 的 `say` 份额从固定 12% 改成按缺口涨（`min(0.58, 0.14 + 0.09 * need)`，`need = 5 - 已解锁数`）。
- `finale_pass_n` 一并收紧：两题要全对才算「被看见」（三题仍是 2/3），以前两题只要求对一题，题越少门槛反而越松。

**实测**（20 seed 全界面走到底）：
- 正文露 `{truth}` / `{wrong}`：**17 → 45 → 0 屏**。
- 进线 7~8 seed；走到 stage4 的 3~5 seed；跑到终局 6~8 seed（`truly_seen` 2 / `used_as_tool` 4~6）。
- `finale_clue_pool` 分布从 `{0:1, 1:5, 2:10, 3:1, 4:3}` → `{2:1, 3:4, 4:8, 5:7}`，多数局能出满 3 题。
- 结局分布散开到 8 种：`执念成魔 8 / 用完 4 / 唯一 2 / 毕业日 2 / 台上那十分钟 1 / 残局 1 / 我只是太爱你了 1 / 后来 1`。
- `validate_all` 八组全 0；`_check_order` 6 seed「有问题: 0」。
- 存档往返已实测：`_truth` / `_ask_order` / `clues[*].truth` / `_finale` 都能 `json.dump` 后原样读回。
- 顺手修了 `rq_lock` 里再掷一次真值的问题（以前 `_pick_truth` 又调一遍，和 `_truth` 里的不是同一个，会出现屏幕上说「苏打饼」、存档锁「肉干」），统一到 `ensure_truth`。

界面实点确认：`http://127.0.0.1:8765/` 收场那屏显示为「我跟你说过，我做菜的时候不能放哪一样？」+ 三个选项，无花括号、无泄答案。

---

## 6.11 一季只走一条线（主线锁定）+ 收场走完就结束（2026-11-15 傍晚）

**用户的三条判断**（原话）：「拒绝一次直接封锁是没有问题的 / 私联走到头直接结局是不是没有做好 / 因为这些线都会提前结局，理想情况就是一次只会走一条线」。

**结构根因**：一季 8 周，每周只有**一次**推剧情线机会（`loop._start_week()` 唯一调用 `_maybe_story()`），三条线抢这一个口。私联 5 拍 + 重线 4 拍 + 恋爱 5 拍 = **14 拍需求 / 8 次机会**，物理上装不下。任何「加权 / 插队 / 专用时段」的调法都是在同一个口上重新分配，只会把某一条线饿死（实测：把 stage0 提前到第 1 周，私联到 stage4 从 5/30 涨到 9/30，代价是重线「一拍都没走上」从 1 个涨到 **15 个**）。所以改成**一季只走一条线**，不是调参问题。

**三条线各自「往前走一拍」是什么意思**（这是定主线的依据）：
- **恋爱 `romance`**：选项上有 `advance` 字段，`advance=1` 才 `heart += 1`（`loop.choose_story` 里 `if lid_id == "romance" and o.get("advance") and ...`）。玩家有明确的「推进 / 不推进」动作 → **主动型**。
- **私联 `shiren`**：进线只看 flag（选项写 `crossed_line`），拒一次就 `line_closed` 永久封锁，之后靠 `heat` 自动 +1 走。玩家只在那一次伸手时做选择 → **主动型**。
- **重线 `zhong`**：stage0 九条选项 immediate 全是 `zhong: 1`，引擎还另有一层补量，**怎么答都 +1** —— 玩家没有「不推进」这个动作，她一直压过来 → **不是玩家选的**，不能算主动型。

**据此实现的主线规则（方案一：主动型锁定，重线兜底）**
- `engine.MAINLINE_FALLBACK_WEEK(s)` = `max(3, weeks_total - 3)`（8 周季 = 第 5 周）。
- `engine._mainline_pick(s)`：`crossed_line` 在 flags → `shiren`；`heart >= 1` → `romance`；还没到兜底周 → `None`（三条线都还能出现，玩家在挑）；到了兜底周就取 `story` 里 stage 最大的、**且没被关掉**的线，一条都没有就 `zhong`。
- `engine._line_shut(s, lid)`：`shiren → line_closed`、`romance → kept_wall`。**被关掉的线不能当主线**——否则它只是「拒之前进过那一拍」进度最高，主线会锁死在一条死线上，这一季从此一条线都不出现。
- `engine.mainline(s)`：把结果**落盘**到 `s["_mainline"]` / `s["_mainline_week"]`，定了就不再改。现算的话会出现「第 5 周重线兜底接了主线，第 6 周玩家又越线，当场换成私联」——两条线同时活着。
- `engine.draw_line_all()`：先取 `mainline()`，`if main and lid != main: continue` —— 另外两条真的不再出现，不靠权重。
- `loop._shiren_if_crossed()`：开头 `if main and main != "shiren": return None`。
- `engine.shiren_finale_ready()`：加 `if mainline(s) != "shiren": return False` —— 越线发生在主线已定给别人之后，就不排收场。

**收场走完立刻结束**（用户选「走完就结束（推荐）」）：`loop._after_finale()` 的 `phase == "done"` 分支改为 `s.pop("_finale", None)` 后**直接 `self._finish()`**。理由：13「用完」/14「唯一」的正文写的是「你在第 X 周走到了这里 / 这一季剩下的 N 周，没有发生」，以前是走完继续过日子到第 8 周才结算，跟正文对不上。

**实测（120 seed，随机玩家）**

| | 结果 |
|---|---|
| 主线分布 | 重线 51 / 恋爱 36 / 私联 33 |
| 恋爱终点 stage | `{2:1, 3:5, 4:30}` |
| 私联终点 stage | `{0:1, 3:15, 4:17}` |
| 重线终点 stage | `{0:1, 1:1, 2:2, 3:47}`（重线总共 4 拍，3 是满格） |
| 一季见过的线 | 1 种 23 局 / 2 种 88 局 / 3 种 9 局 |
| 见过的组合 | 恋爱+重线 31 / 私联+重线 14 / 只有重线 7 / 三条都有 5 / 只有私联 2 / 只有恋爱 1 |
| 结局 | 执念成魔 53 / 用完 22 / 唯一 10 / 残局 9 / 散场 9 / 毕业日 8 / 后来 4 / 我只是太爱你了 4 / 台上那十分钟 1 |

**「会不会一季一条线都不走」——修过一个真 bug**：200 局里撞到 1 次（seed 41，结局「台上那十分钟」）。原因是 `_mainline_pick` 在兜底周把**没出过场**的线也当候选、stage 记成 -1 一起比大小，兜底就把主线锁给了排在最前面的私联；而私联没越过线根本不会出现，`draw_line_all` 又按主线把另外两条挡掉 → 整季一条剧情线都没有。修法：兜底只认 `story` 里真有记录的线（`if lid not in story: continue`），一条都没有才轮到重线。修完 200 随机 seed + 120「专挑冷脸」seed **全部至少走过一条线**，且「主线锁了但它从没出现」= 0。

另核实：重线兜底**不会因为黏性不够而空转** —— 重线 stage0 的 gate 是「任一 OTA 黏性 ≥ 62 且 认识周数 ≥ 2」。`weeks_known` 是**纯周数计数器**（第 2 周就是 7，不是爬升速度），黏性则每拍都会涨；120 随机 + 120 冷脸 seed 里「主线=重线但黏性始终 < 62」= 0 局。

早期线的出现周次（60 局）：重线 第 1 周 55 次 / 第 2 周 15 次；恋爱 第 2 周 28 次；私联 第 2 周 9 次。重线最早是因为它 gate 只要求「认识周数 ≥ 2」，而 `weeks_known` 第 2 周就够；私联和恋爱各自还要玩家先伸手。

**还没做的两件**
- `finale.final_choices` 的四个 flag（`final_public` / `final_cut` / `final_sink` / `final_boundary`）**依然没有任何结局消费**（grep 于 `game/` 0 命中），四选一目前只是装饰。用户说「我们等会讨论一下」，**别擅自动**。
- `结局.md` 的结算面板周数是写死的：「第 6 周跳完了最后一场」是**旧六周季遗留**，8 周季下应为第 8 周；13/14 写的是「第 X 周」占位。已试过在 `_finish()` 里统一替换，但 `ending_text()` 只抠 `**正文**` 段、根本不含结算面板行，替换是空转，已回滚。**要解决得先决定「结算面板到底由 `结局.md` 供还是由引擎算」**（前端目前也不渲染面板行，`app.js` 的 end 分支只显示正文）。

---

## 6.12 私联线「作者写了但引擎没接」的五处（2026-11-15 深夜）

用户看完私联线全文后拍板：「先把 12345 解决了，然后我们讨论选择的剧情」。这五处都是**数据里写好了、引擎里从来没读**，不是设计没想清楚，是接线没做。判断依据一律以 `data/storylines/storyline_shiren.json` 的 `_meta.design_note` / `_meta.protagonist_schema` 为准。

### (1) `memory_key` 十二个记忆点，一个都没实装

`{{cat_name}}` / `{{drink}}` / `{{food_hate}}` / `{{song}}` / `{{hometown}}` / `{{flower}}` 六个占位符没有任何来源，全落到 `loop._fill()` 末尾那道 `re.sub(r"\{\{[a-zA-Z_]+\}\}", "对方", t)` 兜底。实测 40 局走私联有 **10 屏**正文出现「对方」，例如「插到最底下那一束**对方**时，指尖碰到一点硬邦邦的东西」——语义直接坏掉。

修法（按 `protagonist_schema` 原话实现）：
- `engine._prota_preset(mem_def, rng)`：遍历 `memory_key`，`kind == "choice"` 且有 `pool` 的 `rng.choice(pool)`，得到「整局固定、复玩不同」的一组值。
- `engine.protagonist(s, world, rng)`：一局只生成一次，落 `s["_prota"]`，同时作为 `is_storyline=True` 的 OTA 挂进 `s["ota"]`。字段按 schema：`id="shiren_prota"` / `name`（从 `name_pools[gender]` 排除场上已有名字后抽）/ `archetype` / `fan_type` / `spend` / **`stick=75.0`**（越线门槛就是「某个 OTA 黏性 ≥ 75」，她得先够得着）/ `is_seed=False` / `is_storyline=True` / `met_week` / `memory=_prota_preset(...)`。
- `engine.learn_memory(s, keys, text)`：`kind=fact` 的项没有 pool，值取她那一拍的 `note` 那句。
- `loop._fill()` 在「兜成对方」**之前**把 `s["_prota"]["memory"]` 里的值全部替换掉。

### (2) 没有「私联专属对象」，每拍重算

`loop._line_slots()` 对 `shiren` 没有分支，落到最后的 `max(s["ota"], key=lambda o: o["stick"])`。实测 120 局：对象 `ota_jelly 盐渍水母 223 次 / 新生儿 32 次 / ota_row0 17 次 / ota_sleepy 13 次`，**且 22/60 局（37%）中途换人**（每拍重算），例如从「盐渍水母」→「今天也不困」→「第零排」。

修法：`_line_slots` 加 `elif lid == "shiren": ta = E.protagonist(...)`；`engine.pick_ota()` 循环开头 `if o.get("is_storyline"): continue` —— 她只在自己那条线里出现，不会作为陌生 OTA 站到特典会队列里跑龙套。

### (3) `heat` 恒定 +1，「拒绝」也推进

`loop.choose_story()` 里 `if lid_id == "shiren" and (_snapv["heat"] or 0) >= (s.get("heat") or 0): s["heat"] = ... + 1`。选项 immediate 从不写 `heat`，所以条件是 `0 >= 0` 恒真。实测 51 次私联拍，**`heat+1` 51 次，无一例外**——连 `decline` / `push_back` / `give_work`（明确「拒绝」「只给工作」）也照样 +1 并把 `story.shiren.stage` 推到 0。与 `design_note` 的「冷淡则卡住甚至断线」完全相反。

修法：条件加 `o.get("advance")`。**数据不用改**——`advance` 早就写对了（stage0 进线项 1、拒绝项 0；stage1~3 同理；stage4 的 cut 类 0）。另给进度落库加守卫：`if lid_id == "zhong" or o.get("advance")`，否则「半开一扇门」也留 stage0 记录，可能被兜底选成主线却永远迈不出下一步。

实测 40 局、84 次私联拍，**全部由 `advance=1` 的选项打出，「不推进的拍数 0 / 84」**。

### (4) 十四个旗标没人读

精确扫 `flags:[...]` 数组：22 个 flag 里只有 `crossed_line`（6 处）、`line_closed`（3 处）、`met_alone`、`work_only` 真的被读。`cut_early` / `deleted_ta` / `denied` / `dodged` / `double_life` / `manager_leverage` / `official_denial` / `team_knows` / `knows_home` / `met_at_night` / `promised_exclusive` / `promised_offduty` / `promised_remember` / `refused_promise` **14 个只进集合、没人读**。于是「选『当晚就跟她说以后别来了』之后线没断」「求运营给机会不会留下把柄」这类后果全都没实现。

修法：`engine.apply_story_flags(s, option)`，由 `loop.choose_story()` 在 `apply_option` 之后调用。关键是 `cut_early` / `deleted_ta` 要**真的断线**：

```python
if got & {"cut_early", "deleted_ta"}:
    s["flags"].add("line_closed")
```

断掉之后 `_line_shut` 会让这条线从主线候选里消失、`shiren_finale_ready` 也不再排收场。其余按「有实际代价」接：`knows_home` kaibox+8、`met_at_night` kaibox+5、`official_denial` banzi+6/enjou+5（辟谣反而坐实）、`double_life` psyche-6、`manager_leverage` fame-3/psyche-3、`team_knows` relation_C+4、`denied` psyche-4/relation_A-4、`dodged` psyche-3、`promised_exclusive` psyche+4/kaibox+6（那句话被截图存下来了）、`promised_offduty` kaibox+6、`promised_remember` psyche+3、`refused_promise` psyche-5/relation_A-3。

实测（专用探针把 stage4 变体强制到带切断项的那两个）：**12/40 局走到切断项，12/12 `line_closed=True` 且收场排程变 False**；断线后还打出「用完/唯一」= 0 局。`deleted_ta` 单独验过：对照组 `shiren_finale_ready` 从 True 变 False。

### (5) `delayed` 条件绝大多数不可达

11 条条件型 delayed 里的门槛是照着「整季末」的资源写的，但结算发生在**当周**，那时资源远低于季末。私联主线结算点的实测分位：`banzi` p90 20 / max 34；`kaibox` p25 30 / p50 51 / p90 66；`shiren` 恒 1~2。所以 `开盒 ≥ 55/60` 只有 1~4% 命中、`板子关注度 ≥ 40` **全季 0%**、`私联人数 ≥ 2` 在一季一条线下**结构上不可能**。

修法（只动 `storyline_shiren.json` 两处门槛）：`板子关注度 ≥ 40` → `≥ 15`；`私联人数 ≥ 2` → `心理 < 35`。复测命中率：`板子关注度 ≥ 15` 66.7%、`心理 < 35` 75%、`开盒 ≥ 45` 73.3% / `≥ 50` 48.8% / `≥ 55` 34% / `≥ 60` 8.3%、`炎上 ≥ 40` 30.2%、`心理 < 30` 47.1%。**门槛不再形同虚设，也保留了「到不了就别想拿到奖励」的分层**。

### 顺带修掉的一个真 bug：`板子关注度` 恒 False

`eval_clause` 先把 `板子关注度` 别名替换成 `板子`，但 `_NUM` 表里只有 `板子关注度`、没有 `板子` → 查不到 → `return False`。也就是说**所有写「板子关注度」的条件从来没成立过**。补 `"板子": "banzi"` 后 `≥ 40` 从 0.0% → 2.3%。同类补了 `"下次体力": "stamina"`（卡面写法）、`"队友关系均值": "relavg"`（并在 `eval_clause` 取值链里加了 `relavg` 分支）、`"zhongs": "zhongs"`。

另外 `settle_delayed` 的键名兼容了一下：`apply_option` 落库时把 `condition` 转成 `cond`，所以判定一直在跑（探针统计到 4131 次判定）；现在兼容两种写法，免得手塞数据时静默不触发。

**全库条件体检**：138 条 gate/condition，修完「可疑」21 条，**全部是误报**——`dread ≥ N` / `她黏性 ≤ 40` 只在 `data/storylines/_retired/` 里；`答对 ≥ 2` 是 `finale.outcomes.condition` 的说明文字；19 条 `任一 OTA 黏性 ≥ N` 走 `eval_clause` 的 `@OTA` 特判分支、不是 `_NUM` 查表；`zhongs` 由 `apply_effect` 按需建键（值存在、能算）。

### 回归

`tools/validate_all.py` 八组全 0（119 卡 / 14 stage / 21 线索）；`tools/_check_order.py` 6 seed「有问题: 0」；`py_compile` ok。服务已重启，`http://127.0.0.1:8765/api/state` 200，浏览器实点命名屏与 OTA 表正常。

**照旧没动**：`finale.final_choices` 四个 flag（`final_public` / `final_cut` / `final_sink` / `final_boundary`）还是没人消费，四选一目前仍是装饰——用户说「等会讨论」，**别擅自动**。

---

## 6.13 私联收场：答错进「用完」、答对要么「唯一」要么「控制不了」（2026-11-15 傍晚）

用户原话（m02560）：「答错了直接进错结局 然后答对了有两个抉择 一个是继续沉沦 直接到唯一结局 然后另一个选择是断联 但是私联这种事开了头就会继续 然后做一个帅气的动画效果 出来一个弹窗说 你似乎已经控制不了这一切了 然后玩家操作不了只能看着网站自己操作 然后吧炎上和板子直接渐渐加到999 放黑红结局」。

三项决策（用户全选推荐）：**① 新增第 17 个结局**（不复用「你第一天知道我的恶劣吗」，那个内核是「被骂出来的热度换成了钱」）；**② 只留两条岔路**，`go_public` / `draw_line` 不要了（数据留着不消费，不碍事）；**③ 失控演出完全自动**，按钮消失、屏幕自己翻、刷新不能救。

### (1) 收场结构

3 道回考题答完 → **答对 <20 直接走「用完」**，不出岔路屏；**答对够 2 道**才出现两条：
- `sink`「就这么下去」→ `truly_seen` → 第 14「唯一」
- `cut_clean`「跟她说清楚，以后别来了」→ `final_collapse` → 失控演出 → 第 17「控制不了」

关键改动：`apply_finale_outcome` 以前在答完那一刻**一次把 `truly_seen` 和 `used_as_tool` 两条路都写死**，于是那张四选一卡片选什么都改不了结局。现在答对只加 `psyche+10` 不写 flag，岔路屏才决定写哪个；`_push_finale_choices` 开头加 `if not fin.get("ok_quiz"): phase="done"`，答错根本不出这一屏。

### (2) 失控演出

`loop._collapse_script()` 12 屏纯文本，`_push_collapse()` 一屏一屏推，4 屏带 `bump`：enjou 60/130/180/220/250/999、banzi 40/110/190/240/300/999。三处配套：

- **`clamp` 不再一刀切 0..100**：`runaway = s["_collapse"] or "final_collapse" in flags`，runaway 时 `enjou`/`banzi` 只 `max(0, ...)` 不封顶，其余仍是 0..100。这是能涨到 999 的前提。
- **`bump` 不走 `apply_effect`**：它末尾会 `clamp` 把数削回 100，直接 `s[k] = min(999, old + v)` 自己加。
- **演完必须直接 `_finish()`**：只把 `phase` 改成 `done` 就返回的话，`after_step` 会接着 `step_week()` 把这一周过下去，失控就成了插曲。

**这段演出的内容是「一本账」，不是「一个人」（2026-11-15 晚改过一版）**。用户原话（m04441）：「游戏机制没有任何的改变 只有断联那个选项后的剧情展示 是先私联很多人再爆」。所以机制一行没动——还是一个人、还是 `sink`/`cut_clean` 两个选项；改的只是这 12 屏正文：前面一整季玩家只看见一个人，崩溃的时候几条线一起浮出来（「我也是」、「她们开始对日子，周三是谁，周六是谁」、「运营不问是不是真的，问：到底几个」），最后一句落在「原来我从来没数过，自己手上开着几条线」。`结局.md` 第 17 章同步改成了这个多线版本。

前端（`web/`）：`step.auto` 时 `body.collapsing`（黑红 + 扫描线 + 正文逐行入场）、`#next`/`#restart` 隐藏、每屏 1.9s 自动 `POST /api/advance`（绕过 `busy` 锁）。第一屏弹一次「你似乎已经控制不了这一切了」（2.1s 停留 + 0.7s 淡出）。`#hud` 里两个默认隐藏的 `炎上`/`板子` 只在失控时出现，玩家眼看着它们走到 999。结局屏保留黑红（`body.collapse-end`），「重开」恢复可点。

三处踩过的坑：
- **`showOverlay` 的收起定时器会摁灭下一次弹窗** → 现在用模块级 `ovHold`/`ovHide`，进函数先全清。
- **失控段数值是浮点加的**，直接拼会显示 `+90.10000000000001` → 加 `fmtNum(v)`（保留一位小数）用于 HUD 与右下角弹窗。
- **`validate_all.py` 里写死了 `len(_flow)==11 and len(_early)==5`** → 加第 17 个结局后报 `END_TOTAL_WRONG`。改成只核 `_meta.counts` 自洽（`END_TOTAL_MISMATCH` / `END_TABLE_EMPTY`），以后加结局不用再改校验器。

### (3) 验证

探针 60 seed × 三种策略，跑到终局的 23 局全部符合预期：
- 答错 → **23/23「用完」**（`used_as_tool` 23）
- 答对 + 沉沦 → **23/23「唯一」**（`truly_seen` 23）
- 答对 + 断联 → **23/23「控制不了」**（`final_collapse` 23，终局 `enjou/banzi = 999/999`）

浏览器实点：点继续 → 黑红起、`#next` 消失、炎上从 152 一路涨到 999、屏幕自己翻完 12 屏 → 自动进结局屏，标题「控制不了」、正文 790 字完整、`body.className = "collapse-end"`、重开可点。弹窗逐帧采样确认：`206ms` 淡入 → `806ms` 全亮 → `2210ms` 开始淡出 → `3001ms` 隐藏。

`validate_all` 八组全 0（119 卡 / 14 stage / 21 线索 / 17 结局）；`_check_order` 6 seed「有问题: 0」；`py_compile` ok。

**留给下一个对话的两个小尾巴**：`storyline_shiren.json` 的 `finale.final_choices` 仍是旧的四条（`go_public`/`cut_clean`/`sink`/`draw_line`），引擎现在只认前两条的 id，数据里那两条没删是因为不影响运行——真要清就一起清。`finale.gate` 文本仍写「周 = 6」而实际走 `weeks_total`（同 §6.12 那条）。

---

## 6.14 结局正文改龙族风 + 抽卡去重 / 死卡修复（2026-11-15）

**结局正文（上个会话收尾，本轮补记）**：用户要「学江南文风、往《龙族》那边靠，不用过于遵守去 AI 味 skill」，把 17 个结局里**除「14 唯一」外的 16 篇正文**全部重写并展示审核后批准「直接替换」。已替换进 `结局.md`，`**条件**` / `**内核**` / `**结算面板**` 与「14 唯一」原稿一字未动。`loop.py:1672` 的 `ending_text()` 靠 `**正文**` 标记抠段（「散场」特例走 `**内核**` 后的段落）；17 篇全量核验 `TOTAL=17 EMPTY=0 CONTENT_ASSERTS=PASS`。`data/endings.json` 只存判定条件、`why` 字段仍是旧文案口径，**没对齐**（用户没要求，先挂着）。

**抽卡去重 / 死卡修复（本轮，用户 m00292「1+2」）**：见 §7 第 1 条，已落地，代码在 `engine.py`（`eval_clause` 状态映射、`draw()` 的 seen 降权）与 `loop.py`（`_render_card()` 上屏登记）。文件头「已知未实现」注释已同步。

**✅ 文档口径（2026-11-16 已统一）**：`结局.md` / `结局条件图.md` / 本文 §0·§5 已按 `data/endings.json` 改成「17 = 季末 11 + 提前 6」（§6.18 之后为 16 = 季末 10 + 提前 6），`结局条件图.md` §二表也换成了现行 17 个名字（熄灯行删除、黑红改名）。遗留：`结局条件图.md` §一瀑布图与 §三/§四里仍散落「熄灯/黑红」旧名（历史图，未重画，改判定条件时记得同步）；`结局.md` 结算面板的周数写死「第 6 周」是旧六周季遗留（现为第 8 周），13/14 写「第 X 周」占位；前端 `app.js` 的 end 分支只渲染正文、不渲染面板行，所以暂时不显性。

---

## 6.15 打工 → 直播：设计定案与影响面（用户 2026-11-15 拍板；实现状态见 §6.16）

用户 m00142：「我想把打工给删了 改成直播吧」；m00292 选定**甲**方案（不是只换皮，要真改数值语义：为流量营业，不再是为活下去）；m00560 拍板「甲轻 / 两个旧卡直接删 / 小修可以加上 / 结局校验补一下」。**下面是改动前的影响面清单（历史快照，仍有效）**；实现改到一半被用户叫停，**当前半截状态见 §6.16**。
- `engine.py:1458` 原 `ACTS["work"] = {"name":"去打工","stamina":-30,"money":380,"weibo":""}`、`:1468` `ACT_REPEAT["work"]=1.6`、`:1495` 硬上列表含 `work`、`:1500` `if act=="work": template += 0.018`（注释「为了活下去连续去打工」）。
- `loop.py:453` 原选项「去打工 体力 −30 · 钱 +380」、`:488` `ACT_TEXT["work"]="在便利店站了一整天…"`（回执标题）。
- `policy.py:11/19/86/111` 的 ACT_ORDER 含 `work`、`tools/sweep_profiles.py:48` 原「打工」档案。
- 两张旧卡：`data/cards/daily.json:11` `daily_work_conflict`「排班和加练撞了」（gate「本周已选打工 或 钱 < 2200」，便利店/店长/替班语境）、`:80` `daily_rent_due` 的选项 `:119`「这周多接两个班」+500——**用户 m00560 决定直接删，不改写**。
- **建议不动**：`ota_pool.json:76` tag「打工人」、`storyline_zhong.json:174`「给我打工」、`storyline_shiren.json:156`「给工作号」、`ota_memory.json` 的 `work_file`/`off_work` 线索——都是 OTA 侧/引申义，跟「平日动作」不是一回事。
- 全局 grep「直播|配信|开播|打赏|投币|舰长」= 0 命中，无既有直播语义可复用。

---

## 6.16 ⚠️ 当前半截状态（2026-11-15 深夜，用户 m00666「先等等，你直接写交接文件吧」叫停）

> **2026-11-16 已按 §6.17 收尾，本节留作历史快照。**

**下个对话务必先读完本节再动手**：m00560 的四件事改到一半被叫停，别以为全做完了、也别以为全没做。

**已落盘（4 个文件）**：
- `game/engine.py:1458` → `{"name":"开直播","stamina":-22,"money":380,"fame":2.0,"weibo":""}`（甲轻：体力 −30→−22、加 fame +2.0；钱 +380 / id `work` / template +0.018 / ACT_REPEAT 1.6 / 硬上列表 全按提案不动）。
- `game/loop.py:453` → `{"id":"work","label":"开直播","desc":"体力 −22 · 钱 +380 · 人气 +2"}`。
- `tools/sweep_profiles.py:48` 档案名「打工」→「直播」（数值不动）。
- `tools/validate_all.py`：在 `print("== ENDINGS PROBLEMS ==")` 前新增**常驻结局正文校验**——按 `game/loop.py:1676 ending_text()` 口径，逐个核对 `endings.json` 的 17 个结局在 `结局.md` 有章节、且抠得出 ≥80 字正文（散场走 `**内核**` 特例）；新错误码 `END_NO_TEXT_FILE` / `END_NO_CHAPTER` / `END_NO_BODY` / `END_CHAPTER_COUNT`。此前 16 篇改写一直靠临时脚本核验，现固化。

**已验证**：改完这 4 处跑 `validate_all.py` → 八组 PROBLEMS 全 0（含 `ENDINGS PROBLEMS`）、`total_cards = 119`、EXITCODE=0。**其余固定流程一律没跑**（`_check_order` / `_smoke_loop` / `economy_sandbox` / `gen_overview` / `export_cards_for_review`）、**服务没重启**（本来 `SERVICE_DOWN`）。

**明确没做（从这里接）**：
1. **两张旧卡没删**：`daily_work_conflict` / `daily_rent_due` 仍在（`total_cards` 还是 119，删完应为 117）。用户原话「两个旧卡直接删吧 感觉不太合理」——是**删不是改写**。删完重跑 `gen_overview.py`（`data/卡库总览.md`）与 `export_cards_for_review.py`（`卡库审核.md`，两张卡段落在 `:341-366`）；`tools/fix_gate_round2.py:13-14` 的 FIX 表仍引用这两个 id，删后会空转（历史脚本，可不管或顺手清）。
2. **甲轻文案没改完**：`game/engine.py:1499` 注释仍写「为了活下去连续去打工」、`game/loop.py:488` `ACT_TEXT["work"]` 仍「在便利店站了一整天，收银台前排到门口。」——按提案回执应换直播语境（如「架好手机播到凌晨，在线人数一直没过两位数」）。`policy.py` 的 `ACT_ORDER` 含 `work` 是**有意保留**（id 不换，别误删）。
3. **gate 小修没做**（用户「小修可以加上」）：`game/engine.py:797-799` `eval_clause` 的「本周已选」分支仍要求 gate 内含 `『』`、并拿 `s["acted"]`（存的是 **id**，由 `do_act()` `:1492` 写入）去比；原 `daily_work_conflict` gate「本周已选打工 或 钱 < 2200」既无书名号、又写中文名「打工」，前半句永不成立。m00555 提案方向是「本周已选『开直播』 或 钱 < 2200」，但**那张卡现在要删了**——所以这条要么让 `eval_clause` 能吃「本周已选 + 中文动作名」的映射（去 `『』` 依赖 + 中文名→id），要么随卡一起作废；下个对话定。
4. **「结局校验补一下」的另一半没做：16→17 口径统一**。用户这句我按「把正文校验固化进 `validate_all`」理解并已做（见上）；但同一批文档还写 16：`结局.md:3`（「16 个结局：季末 11 + 提前 5」）、`:37`（「合计 16 个」）、目录 `:25-30` 缺 17「控制不了」；`HANDOFF.md:58` / `:138` / `:140`；`结局条件图.md:3` / `:113`（且写「季末 12 + 提前 5」与 `endings.json` 的 11+6 不符）；`data/卡库总览.md:2075`。以 `data/endings.json` 的 `_meta.counts`（season 11 / early 6 / total 17）为准。**改不改、怎么改（尤其「季末 11」vs「季末 12」）需先问用户**，别擅自动既定数值叙述。

**甲轻提案全貌（m00555，对照用）**：name 开直播 / id 保留 `work` / stamina −22 / money +380 不动 / fame +2.0（走 `add_fame` 软上限）/ template +0.018 不动 / weibo·ACT_REPEAT·硬上列表不动 / ACT_TEXT 换直播文案。风险：stamina −30→−22 动了「体力↔钱」交换比，落地后须按 §8 固定流程跑 `economy_sandbox.py` 确认 11 结局仍可达。用户另问过「要不要写新卡」，结论**现在不写**（卡库 119 张、一季只上屏约 32 屏，加卡摊薄见面率；该动的是回考配额），别擅自加卡（§7-6）。

> 另：2026-11-15 用户把「代码检索纪律」定为**永久规则**（禁 shell 递归列目录 / 项目根全量 grep；顺序 glob → 限定 path 的 grep → read+offset/limit，>200 行不整篇读；单次工具结果 ≤8000 字符；写新函数前先查有无现成实现），已写入全局记忆（critical），下个对话照办。

---

## 6.17 直播改造收尾 + 结局口径统一（2026-11-16）

§6.16 的四件收尾全部做完；结局计数按 `data/endings.json` 统一成 **17 = 季末 11 + 提前 6**。

- **删两张旧卡**：`data/cards/daily.json` 删掉 `daily_work_conflict`（排班和加练撞了）与 `daily_rent_due`（房东的消息），卡库 119 → **117**（daily 6 → 4）。`gen_overview.py` / `export_cards_for_review.py` 已重跑，`data/卡库总览.md` 与 `卡库审核.md` 里这两张卡的段落已消失。`tools/fix_gate_round2.py` 的 FIX 表仍引用这两个 id，历史脚本、空转无害，未清。
- **直播文案**：`game/engine.py:1494` 硬上注释、`:1499` 态度走样注释、`:1896` 硬上计数注释都从「打工」改成「开播」；`game/loop.py:488` 的 `ACT_TEXT["work"]` 从「在便利店站了一整天…」换成 **「架好手机播到凌晨，在线人数一直没过两位数。」**（`loop.py:519` 现生快乐正文里的便利店是剧情文本，没动）。
- **gate 小修**：`game/engine.py` `eval_clause()` 的「本周已选」分支不再依赖 `『』`，并加了中文动作名 → id 映射（练舞/练唱/练营业·练话术/拍内容/拍内容发微博/开直播·直播·打工/躺）。删卡后暂无卡使用它，纯为以后写卡；探针 6 条断言全部符合预期（`acted=work` 认「开直播/打工/直播」、不认『练舞』；`acted=dance` 认『练舞』和「练舞」）。
- **结局口径**：`结局.md` 第 3 行、正文前引文、目录（新增「17 控制不了」）；`结局条件图.md` 第 3 行与 §二表（季末 11 + 提前结束 6，删「熄灯」行、「黑红」改名「你第一天知道我的恶劣吗」、补第 17「控制不了」）；本文 §0/§3/§5/§6.14 同步。
- **验证**：`validate_all.py` 八组 PROBLEMS 全 0（117 卡 / 14 stage / 21 线索 / 17 结局）；`_check_order.py` 6 seed「有问题: 0」；`_smoke_loop.py` 3/3 到结局（274/275/256 步）；`economy_sandbox.py` 覆盖 **11/11**、未覆盖「无」；`py_compile` 三个 py 文件通过。
- **实点**：干净开局走序章 → 取名 → 第 1 周行动屏有「开直播」，选它后回执标题为直播文案，`delta` = 钱 +380 / 体力 −22 / 人气 +2，快照数值同步变化；`/api/state` 与 `/` 均 200。
- **服务状态**：已重启，`http://127.0.0.1:8765/` 是**干净第 0 步（序章「二十二点三十分」）**，`game/_save.json` 已删；上次那个 11-15 18:14 的测试存档（第 1 周、柚子）是旧调试态，一并清掉了。

**遗留（没动）**：`结局条件图.md` §一瀑布图和 §三/§四里仍散落「熄灯/黑红」旧名——那是 11-14 的判定图，重画要连 `build_endings.py` 一起对，属于下一次改判定条件时的事；`结局.md` 结算面板周数写死「第 6 周」的问题仍在（前端暂不渲染面板行）。

---

## 6.18 结局平衡第一轮：删「交易孤立」+ 两个判定 bug（2026-11-16）

用户 m00212 选定 §7.3「结局平衡」后做的一轮调查与落地；**平衡本身还没调完**（见 §7.3）。

**调查结论（真跑）**：
- 随机 30 种子（`tools/probe_endings.py`）：劣 168 / 残局 75 / 如影 18 / 执念 17 / 空心 15 / 台上 12 / 毕业 10 / 后来 9 / 太爱 5 / 散场 1；守住本心 / 现生快乐 / 彗星 0。
- 六个档案 ×40 种子（`tools/sweep_profiles.py`）：除「熬」走执念 37 外，其余档案都是劣/残局为主。
- 炎上（enjou）不是失控，是选项偏好：防御型档案能把 enjou 中位压到 7–11（`tools/_p_def.py`）。旧档案的劣 30/40 来自「永远选选项 0」。
- enjou/banzi 卡面倍率 ×3（`game/engine.py:578`）+ 每周只退 8%（`engine.py:1091`）→ 随机玩法极易冲满 92，劣的门槛（≥70 且 ≥60）因此很好过。
- 彗星需要 max_single≥64 且「不够守住本心」；防御正常练 40 种子只 3 次（`tools/_p_comet.py`）。
- 台上那十分钟的 cond 在直播档案里 19/20 命中，但被更靠前的「你第一天知道我的恶劣吗」遮住。
- 现生快乐要 `chose_leave`（UI 最后两个晚上的离开选择），沙盒 0 是构造性。

**已改**：
1. `game/engine.py` `check_cond()`：bool false 原来 `return True`，会把它后面的条件全部短路；改成 `continue`（false = 不约束，但继续检查后面的键）。
2. 新增 `money_kept`（`_extra()` 里 money_drop 取反）；`data/endings.json` 劣改成 `enjou≥70 & banzi≥60 & money_kept:true`，不再出现「钱在掉还判恶劣」。`build_endings.py` 的 FIELDS/FLOW/EARLY 已同步。
3. **删除「交易孤立」**：`beibao` flag 全项目从未写入、`max_share≥0.6` 也难达成，条件结构性不可达；用户 m00455「那删了算了 这包养太夸张了 不太可能出现」。`data/endings.json` 重排为季末 1–10 / 提前 11–16，`_meta.counts = 10/6/16`；`结局.md` 删小节并重排目录；`结局条件图.md` 总图/表/§四全按 16 重写（§四换成 2026-11-16 真跑数据）。

**下一步（§7.3 未完成）**：调 enjou 倍率/衰减或劣门槛，让台上/彗星能露头；营业线现在空出一个专属结局位（原交易孤立），要不要补由用户定。别在沙盒里过度拟合，等真玩一轮再定。

### 6.18.1 第二轮 A：炎上倍率 2.5 + 残局/台上抬门槛（同日）

低概率诊断（临时 `tools/_p_why.py`，60 局随机政策）：空心 0/60（`empty_choice` 60 次从未触发、true_talk 已破）、现生 1/60（`chose_leave` 59、psyche 59 不过）、守住 0/60、彗星条件满足 6/60 但全被前排截走、台上条件满足 55/60 实际只拿 7（48 被截）；营业档 mc/content/mc 60 局全 mc=82。结论：低概率 = 多重 AND + 高舞台/低心理反相关 + 排序截流 + UI 专属选择。
用户看过诊断后**否决了新增营业结局**（「我后悔了 不要营业结局了…我们主要讨论怎么让结局变平均吧」），在四个平衡方案里选 **A：只改三处，不放宽稀有结局**：

1. `game/engine.py:578` `_EventMult.MULT` 的 enjou/banzi **3.0 → 2.5**（卡面与 delayed 同乘）。
2. `tools/build_endings.py`：残局 `enjou ≥ 70 → 80`；台上 cond 加 `stage ≥ 55`（变成「舞台≥55 且心理<20 且本季崩着上台」）。重跑 `tools/build_endings.py` → `data/endings.json` 已更新（counts 10/6/16 不变）。
3. 文档同步：`结局.md:193` 残局≥80、`:349` 台上加舞台≥55；`结局条件图.md` §一 L37/L58、§三表残局/台上行、§四量图与 §四整节数字；`probe_endings.py` 台上目标档案动作改 dance/sing/work。

**验证（真跑）**：`validate_all.py` 八组 0（117 卡/14 stage/21 线索/16 结局）；`_check_order.py` 6 seed 0；`probe_endings.py 20` → 残局 67 / 劣 35 / 散场 30 / 空心 20 / 执念 20 / 如影 10 / 毕业 8 / 太爱 4 / 台上 3 / 后来 3；`sweep_profiles.py 40` → 熬 执念38，躺 残局13/现生10/劣8，直播 残局15/散场10/空心6/台上2，哄人 残局14/空心7/如影7/守住2，说真话 散场17/残局11/守住3，混 残局15/散场7/守住6；`economy_sandbox.py` 10/10 全 ✓；`_smoke_loop.py` 3/3（274 散场/275 残局/256 唯一）。
**观察**：残局成为新的主流收口（约三分之一），劣从改前 56% 降到约 17%，散场抬头到 15%；台上在随机探针里变稀有（3/200，门槛收紧的直接结果）；彗星仍 0；现生/守住在躺、哄人、说真话、混档案里开始少量出现。
**未做 / 待观察**：探针的十个目标档案是旧门槛时代写法，没跟着新门槛重调；「让稀有结局露头」这轮按用户选择没做；仍按上一轮教训，等玩家真玩一轮再定要不要继续调。

### 6.18.2 真话系统 + 私联抽线 + 如影/空心/守住接线（同日）

用户 m00947 提出「做真话卡、真话率高→守住、低→空心；如影是不是和重线撞了」，m01052 批准整套。

**真话系统**：
- 新增 4 张双难卡（121 卡）：`truth_before_live`（开场前 stf）、`truth_weibo_dm`（微博私信）、`truth_team_doubt`（队友）、`truth_after_live`（散场后）；每张 truth/safe 两个 tone。
- `apply_option()` 的 tone 计数移出 flag 循环（原 bug：多 flag 会重复计数）；`truth_pick`/`safe_pick` 累计；`truth_rate(s)=truth_pick/(truth_pick+safe_pick)`。
- 回考答对 `engine.py:736` 从 `true_talk+1` 改为 `recall_ok+1`——真话不再混「记得住」；空心不再被回考结构性关死。
- 空场提问触发：week≥3 且 `tone_choices≥2` 且 `truth_rate≤0.25`（去掉模板≥0.45）；`loop.py:_maybe_ask_tired` 同步，`choose_empty` 也计 tone。

**抽线**：
- `draw_line()`：zhong 权重封顶 `1.0(+0.45 if 已在 story)`，不再吃 `0.35*stage` 滚雪球；shiren 未越线 `+0.6`；越线 ×2.6 保留。

**结局条件**（`build_endings.py` → `endings.json`）：
- 空心：`empty_choice=reply` + `truth_rate≤0.4`。
- 守住本心：`no_rent_missed` & psyche≥45 & relavg≥30 & `ota_ge40≥2` & `offer_refused` & `truth_rate≥0.5`。
- 台上：`all: [stage≥55, stage≤61, psyche<20, played_while_collapsing]`。
- 如影：`all: [kaibox≥80, shiren_stage≥2]`。
- FIELDS 加 `truth_rate/truth_pick/tone_choices/shiren_stage`；`validate_all.py` 字段白名单跳过 `all`。

**验证（真跑）**：`validate_all` 八组 0（121 卡/14 stage/21 线索/16 结局）；`_check_order` 6 seed 0；`_smoke_loop` 3/3（256 散场/277 残局/256 唯一）；真话路线 40 局守住 13、truth_rate 全 1.0，场面话路线 30 局空心 17、守住 0；专攻开盒 30 局如影 4；`probe_endings.py 20`：残局 55 / 劣 40 / 散场 36 / 如影 26 / 执念 24 / 空心 7 / 毕业 6 / 后来 2 / 台上 2 / 太爱 1 / 现生 1；`sweep_profiles.py 40` 见条件图 §4.2。

**教训/未做**：`true_talk` 之前混了回考，文档却按「说真话」写，属于判定与文案不一致；本轮已拆开。台上/彗星仍稀有，用户明确不追触发率。剩：文档数字（本文/结局.md/条件图）、`gen_overview`、重启服务、删临时脚本。

### 6.18.3 失控演出重制：认领 + 灯灭 + 纯黑（同日）

用户 m01598「可以 做进去」：把 `web/collapse_preview.html` 里验过的「方案一 + 方案四」落进真实游戏。

**文案**（`game/loop.py:_collapse_script()` 12 屏整组重写，认领版）：
- 第 2 屏起：帖子第一句是「周三那次，你也是这么跟我说的」，但周三在记忆里是空的。
- 第 3 屏：同一句「你是特别的」出现三次、落款三个人、连标点都一样。
- 第 5 屏：同一个晚上、同一个地址发给三个人，间隔十七分钟。
- 第 6 屏：同一张拍切裁掉不同的人发给不同的人；有人问「这张到底拍的是谁」，没人回答。
- 末屏：她们还在对日子，第四十七个；「第四十八个是谁，我到现在也没想起来。」
- `_push_collapse` 的 step 增加 `cidx`（0-based 屏号，前端灯灭/裁字要用）；docstring 的「第 17 个结局」改为「控制不了」。

**前端**：
- `web/app.js`：`KILL_STEPS = {5: v-money, 7: v-stamina, 9: v-psyche, 10: v-fame}` → 对应 `.kv` 加 `dying`；`cidx≥10` 给 `#body` 加 `cut`；结局屏/非 auto 屏 `clearCollapseFx()` 复原。
- `web/style.css`：`.collapsing/.collapse-end` 的 HUD 数字统一 `#c0392b`；`.kv.dying` 淡到 0.14 + 灰度（炎上/板子不灭）；`#body.cut` 裁到 5.4em + 遮罩渐隐，最后一段后加闪烁光标；`body.collapse-end` 改纯黑（`--bg/--paper:#000`、关掉 pulse 与红雾 `::after`）。**坑**：纯黑覆盖规则必须写在 `body...::after` 那一组之后，同权重否则被红雾盖回去。

**验证**：`py_compile` + `node --check` 过；临时脚本伪造 `Game` 直接推 12 屏，`cidx` 0–11、末屏文案/`bump` 正确；`validate_all` 八组 0、`_smoke_loop` 3/3；重启服务（后台 job `pwsh-211e84a8a4ca48b0`），`/api/state` 200、干净序章；浏览器里注入 `collapse-end` 实测 `backgroundColor=rgb(0,0,0)`、`::after` 无红雾、数字红、`#body.cut` mask 生效。没真玩到失控（要 8 周），行为靠伪造步骤 + 样式实测确认。

临时预览页 `web/collapse_preview.html` 已按用户 m02807 删除（2026-11-16）；正式演出逻辑在 `loop.py` + `app.js`/`style.css`。

### §6.18.4 版聊改成真聊天记录（2026-11-16）
用户 m01742：「把手机亮了一下给删了 然后做版聊吧 最好右上角挂个版聊 然后回考也做tag」。原版聊是「晚上躺下，手机亮了一下」+ 一张没有上下文的特典会卡，读起来不像聊天。

- **数据**：新增 `data/cards/chat.json`，7 张 `type: 版聊` 专卡。每张有 `messages`（`{from: you|speaker, text, time, quote}`，`quote` 是前面某条的下标）和 `options`（仍是「营业地接 / 说真的 / 先不回」的三难，数值走原有 immediate/cooldown）。卡库 121 → 128。加载器 glob `data/cards/*.json` 自动收，无需改 engine。
- **loop**：`push_midweek()` 删掉「手机亮了一下」那句，只 `draw(kinds=["版聊"])`；新增 `_render_chat()` 把 messages 铺成 `{who, me, text, time, quote}`，引用的那条取前面消息原文；`current()` 把 chat 当带选项的卡挂 `pending`，`choose_card()` 照常结算；队列去重也认 chat。
- **server**：`/api/choose` 的 `elif t == "card"` 改成 `in ("card", "chat")`——这是实测点击没反应的原因：service 认不出 chat，返回原屏。
- **前端**：`web/app.js` 新增 `chatLog()`（左右气泡、引用条、名字+时间）；`chat` 屏选项照常 `addOption`；舞台右上角绝对定位 `.corner-tag.chat`「版聊」，`#stage.has-tag #title` 留 70px 防压标题。回考卡（`rq_stage == "ask"`）在 step 上带 `recall: true`，前端挂红色 `.corner-tag.recall`「回考」。
- **样式**：`style.css` 新增 `.chat-log/.msg/.bubble/.quote/.who/.tm`，me 气泡浅蓝右对齐；`.corner-tag` 像素小牌子，chat 蓝、recall 红。
- **验证**：`validate_all` 八组 0（128 卡）；`_smoke_loop` 3/3（275/276/267 步，已改脚本认 chat）；浏览器实走：自动点到第一屏版聊（23:58 的私信，2 条消息、引用条正确、右上角 tag 在 `right=1023` 舞台边），点选项出回执；继续跑到回考卡（「她问起那件事」），红「回考」tag 出现、题干后三选一不带数值暗示。
- 已知：版聊 7 张、cooldown 2–3，一季约见 5–6 张；版聊选项**不计入** `truth_rate`（真话率仍只数卡面/空场回答，避免把随口回消息算成真话）。

### §6.18.5 结局回响 + 跨周目图鉴（2026-11-16）

用户 m02807 收口结局平衡后问下一项议程，m02831 前后拍板做「回响 + 结局图鉴」，并明确**锁定条目只给一句模糊提示、不给内核**。

- **回响**：`game/loop.py:_finish()` 给 end step 加 `echo`；`_echo()` 只报这一局真发生过的数（week/stage/tier/psyche/money/enjou/kaibox/line/truth_pick/safe_pick/truth_rate/clues/clues_wrong/pushed/rent_missed/chose_leave/offer_refused/shiren_stage），不写攻略。前端 `web/app.js:echoPanel()` 在结局正文后铺「这一季的回响」两列格；CSS `.echo-card/.echo-grid/.ekv`。
- **图鉴文案**：`data/endings_lore.json`，16 个键与 `endings.json` 完全一致，每条 `{core, style, hint}`：core=内核、style=达成玩法、hint=未解锁的模糊方向。`tools/validate_all.py` 增 `MISSING_LORE/LORE_MISSING/LORE_FIELD_EMPTY/LORE_UNKNOWN`，键集合必须与结局表一致。
- **存档**：`game/_gallery.json`（跨周目，删 `_save.json`/重开都不清；想清自己删）。`game/server.py` 增 `GALLERY/_load_gallery/_save_gallery/_record_ending/_gallery_payload`；`Session.save()` 在 `over` 且结局名变化时记一次（`_recorded` 防重记），读档时若已结束只设 `_recorded`、**不重记**；`new()` 重置 `_recorded`。每局存 `count/first_at/last_at/last_echo`。
- **接口**：`GET /api/gallery` → `{endings:[...], total, unlocked, seen}`；未解锁行 `name:"？？？"` + `hint` + `locked:true`，解锁行带 core/style/count/last_echo。
- **前端**：footer 加「结局图鉴」按钮（重开按钮默认 `hidden`，结局后才出）；`#gallery-modal` 面板显示「解锁 N / 16」、序号 01–16、解锁项名字/内核/玩法/达成次数/最后时间，锁定项只给模糊句。`#gal-close`/Esc/点遮罩关闭。CSS `.gal-panel/.gal-row/.gal-hint/.gal-core/.gal-style/.gal-meta`；失控演出时隐藏按钮。
- **验证**：validate_all 八组 0（含 lore 覆盖）；node --check 通过。伪造一局结局存档（seed1 → 台上那十分钟，276 步）实看：结局屏「这一季的回响」数字正确；图鉴 1/16 解锁、其余 15 条显示模糊 hint；点重开回序章后图鉴仍 1/16（跨周目保留）。
- 注意：图鉴只在服务端 `save()` 观测到结局落盘时记录，所以**已经结束的旧存档读进来不会补记**（避免重启重复计数）；要补就手动删档重走。

### §6.18.6 移动端适配（2026-11-16）

用户 m03058：「做一下移动端适配吧 感觉主要应该是移动端游玩」。按 390–430px 手机为主场做了一轮，不改任何游戏判定。

- **断点**：`web/style.css` 末尾新增 `@media (max-width:640px)`，另加 `@media (max-width:380px)` 窄机一档；原有 480px 一档保留。桌面（>640）无变化。
- **HUD**：左右 padding 22→14，`.hud-main` gap 16→10，数值 13.5px／标签 10px；390px 下四项主数值一行约 210px，炎上/板子仍只在失控段出现。
- **首屏**：`#detail` 在窄屏默认收起（`web/app.js` 初始化按 `matchMedia("(max-width:640px)")` 决定，未存过偏好时收起；点 ⌄ 仍可展开，选择记 localStorage）。
- **正文/选项**：`#stage` 左右 14px、正文 16px/1.85、选项 min-height 48px、字号 16px；`#stage` 底部留 `calc(104px + env(safe-area-inset-bottom))`，避免 sticky 底栏压住最后一项。
- **底栏**：`#foot` 贴底 + safe-area；`继续` 按钮 flex:1、48px 高；图鉴/重开为 ghost 小按钮。
- **OTA 表**：缩字号与 cell padding，390/360 宽实测 4 列不溢出（table 327/303px，panel 无横向滚动）。
- **图鉴**：≤640 时 `#gallery-modal` 变整屏抽屉（panel 100% 宽、100dvh 高、去边框/切角），列表自身滚动，head 含 safe-area。
- **其它**：`#pop` 改左右贴边并在底栏上方；`.bill` 允许横向滑动（min-width 400）；版聊气泡 `.bubble` max-width 88%；回声面板 `.echo-grid` 单列；按钮禁 tap 高亮 + `touch-action:manipulation`。
- **顺手修 bug**：`web/app.js:397` 非 auto 分支原把「重开」按钮重新显示，导致游戏中途底栏一直有重开；改为 `add("hidden")`（结局屏仍由 onEnd 显示）。
- **验证**：`node --check web/app.js` 过；validate_all 八组 0；`_check_order` 6 seed「有问题: 0」。临时 `web/_mobile_test.html` 双 iframe（390×844、430×932，后改 360×780）实测：无横向溢出、HUD 51–53px、选项 85px、OTA 展开不溢出；伪造 seed1 结局存档（散场）看结局屏：回响单列 10 行、图鉴「解锁 0/16」整屏、footer 只剩图鉴/重开。临时预览页与测试存档均已删。

### §6.18.7 二周目姿态 + 跨周目记忆（2026-11-16）

用户 m03318：① 移动端先不改（暂时无法预览，等真机反馈）；② 先做议程 2「二周目姿态 + 跨周目记忆」；③ 游戏里要解释「一周并不是只发生这么一些事件、也不止这些版聊，它们只代表你的态度」。

- **开关**：`game/server.py _last_season()` 读 `game/_gallery.json`，取 `last_at` 最近的一条结局 + 它的 `last_echo`；`_fresh_game()` 若存在上一季就设 `g.allow_stance=True, g.prev_season=...`。**图鉴为空时一周目不弹姿态屏**（实测：删图鉴后取名完直接进第 1 周卡）。
- **数据**：`data/stances.json` 5 条——`stage` 冲神场（dance/sing/mc +3）、`money` 攒钱活下去（钱 +400）、`self` 别把自己弄丢（心理 +8）、`bond` 和谁处成朋友（三人关系 +4、五个 OTA 黏性 +4）、`none` 不选照旧（不加值）。每条含 `id/line/name/desc/bonus`。
- **引擎**：`game/engine.py apply_stance(s, stance)` 加开局增量、写 `state["stance"]/["stance_name"]`、clamp 并重算 `stage`；`stance_weight(s, c)` 扫卡面所有选项的正面增量，归 stage/money/self/bond 四类（`tone=truth` 记 self +3），最像姿态的卡 ×1.3，否则 1.0；`draw()` 权重连乘加入它。一周目无 stance 恒 1.0，分布不变。注意：**「舞台」姿态只有 5/128 张卡会被 ×1.3**（多数卡混合了关系/钱），所以姿态主要靠开局 +9 技能，抽卡偏向是弱效果。
- **流程**：`game/loop.py` 加载 stances；`set_name()` 后若 `allow_stance` → `_build_stance()`（先报上一季「走到了「散场」，第 9 周，舞台 47，心理 0」，再 5 个选项），`choose_stance()` 加值、弹一句确认（「这一季，我给自己定的是「冲神场」。」）、`_start_week()`；不选/照旧弹「这一季，先不给自己定什么。」。`_echo()` 新增 `stance/stance_name`，结局回响多一行「开季姿态」，图鉴 `last_echo` 一并保存。
- **前端**：`web/app.js` 选项分支认 `type:"stance"`（用 `step.stances` 渲染），回响面板 `echoPanel` 有 `stance_name` 时加「开季姿态」。无需新 CSS。
- **第 1 周说明**：`loop.py _start_week()` 周 1 头正文第二段：「六天不会一分钟一分钟写给你看——只有几个片段，和手机上那几条你回过的。它们不是全部，是态度。」（旧 `start_week` 同步改了同一句）。
- **验证**：py_compile / node --check 过；临时脚本直走开局（`allow_stance`+`prev_season`）确认姿态屏文案、+3 技能、确认屏、第 1 周说明；API 走真实 server（图鉴预置散场）确认 `/api/choose` 分发 stance、snapshot 里 dance/sing/mc 48/43/38；浏览器点「冲神场」出确认屏再进第 1 周；无图鉴时确认不弹姿态屏。`validate_all` 八组 0（128 卡）、`_check_order` 6 seed「有问题: 0」。临时 `tools/_p_stance.py`、`_p_stance_api.py` 已删。
- **边界**：已结束的旧存档读进来不补图鉴（见 §6.18.5），所以也不开姿态屏；要二周目得先有一局在新版里走到结局。姿态不锁线、不保结局，只是开局倾向；`none` 与一周目等价。

### §6.18.8 记事本（设置面板）+ 快速重开（2026-11-16）

用户 m03558：「要不要搞个设置面板 可以看到一些影响结局的历史大事 还可以快速重开」→ 选「完整版」。

- **入口**：footer 新增「记事本」ghost 按钮（桌面/手机同一排，390px 实测不溢出）；打开 `#settings-modal`，手机端整屏抽屉（同图鉴）。
- **底账来源**：`game/loop.py _journal_week(week)` 在 `settle_week()` 结算并 `clamp` 之后追加一行，`_finish()` 再补最后一行；字段 `week/stage/tier/psyche/money/enjou/banzi/kaibox/template/truth_rate/relavg/line/line_stage/shiren_stage/rent_missed/chose_leave/offer_refused`。一季最多 9 行，存进存档 `state["log"]`，跟档走。
- **接口**：`GET /api/journal` → `{log, over, ending}`（`Session.journal()`）。
- **面板内容**：①「影响结局的事」——前端按相邻两行差值推导，只在真发生时才写：走上哪条线、私联走到第几拍、舞台 60/70 档、心理掉破 20、炎上破 70、开盒破 80、队友关系均值破 30、欠租、真话率过半、最后选离开、当面拒运营；②「每周底账」——周/舞台/心理/钱/炎上/板子/开盒/真话率/线；③「这一季」——**重开这一季**（两段式：第一次变红「再点一次就删档重开」，4 秒内再点才 `POST /api/new`；图鉴保留），下方注明会删进度。
- **旧档**：老存档没有 `log`，面板显示「这一季还没走完第一周」，不补历史；从下一周起正常记。
- **验证**：API 走完第 1 周后 `/api/journal` 返回 1 行（舞台 54/心理 54/钱 1740/开盒 2/真话 0%）；浏览器打开记事本看到事件与底账；点重开两次回到序章「二十二点三十分」；390px iframe footer 三按钮 182/66/79px 不溢出。`validate_all` 八组 0、`_check_order` 0、`_smoke_loop` 3/3、`node --check` 过。

### §6.18.9 结局「游戏之外」（作者话 + 博客/支持链接，2026-11-16）

用户 m03728：「在最后结局写一段游戏之外…挂上支持链接和我的博客链接，博客里可能发攻略和更新」；m03732 给了正文与 blog 地址。

- **数据**：`data/outside.json`（`title` / `body[]` / `links[]`，每条 link 有 `prefix/url/label/suffix`）；`game/loop.py` 加载为 `self.outside`，`_finish()` 的 end step 加 `"outside": self.outside`。
- **前端**：`web/app.js outsidePanel(d)` 渲染 section；`renderStep` 的 onEnd 分支在 `echoPanel` 之后插入。`web/style.css` 加 `.outside` 样式（分隔线、小标题、14.5px/1.95、链接下划线），手机 640 断点降到 14px/1.9；`body.collapse-end` 下单独提亮文字/链接/小标题，保证「控制不了」纯黑结尾也能读。
- **内容**：标题「游戏之外」；正文三段（感谢 / 做这游戏的由来 + 微博留言征集 / 怕剧透）；两条链接——blog `https://vainvoidkk.dpdns.org`（`target=_blank rel=noopener noreferrer`）说「可能会发一些攻略或者往后的更新」；支持行「无偿支持一下作者🌸 补充主播逝去的token...!」，**支持 URL 暂空**，前端此时渲染成加粗文字不跳转，等爱发电/其他支持页 URL 填进 `links[1].url` 才变链接。
- **范围**：只在结局屏出现（16 个结局都出，含提前结束），序章/周中/标题页都没有常驻入口，也不记录点击。
- **验证**：seed1 造「散场」结局存档实看——body 3 段、links 2 条、桌面宽 676/高 290、390px iframe 宽 347/高 420 无横向溢出、链接 href/target/rel 正确；`body.collapse-end` 下文字色 #e6cfc9 可读；`validate_all` 八组 0、`node --check` 过。

---

## 7. 下一步 / 待办（open objectives）

1. ~~**「很多卡没看到过」**~~ —— **2026-11-15 已落地「1+2」**（用户 m00292 拍板）：① `engine.draw()` 对 `s["seen"]` 降权 ×0.25（**不硬禁**），名单由 `loop.py` 的 `_render_card()` 上屏时登记；② 修 2 张结构性死卡——`eval_clause()` 把「曾冷场或翻车 / 曾冷场 / 翻车 / 舞台翻车」接到 `blew_it`、「曾欠队友人情」接到 `owe_team`（这两个状态引擎一直在记，见 `engine.py:1749` / `loop.py:872` / `engine.py:536`），不再无条件 `return False`。实测：单季不同卡 26.9 → **29.9（+11%）**，总上屏数 31.8 不变；`validate_all` 八组全 0、`_check_order` 有问题 0、`_smoke_loop` 3/3 到结局、三个 gate 复活断言 PASS。**未做**：③ 高门槛卡随周数保底（用户没选）。原三条方案里「减每周事件位给 OTA 记忆让路」经诊断是反效果，已废弃：一季事件位满打满算约 40 个、可上屏卡 109 张，看全本就不现实也不该（毁节奏），目标应是「别老重复 + 别有永远抽不到的卡」。20 局合计见过 93/109，剩 16 张里 10 张是 OTA 记忆卡（被「一季只锁 3~5 条线索」的回考机制天然锁死，要动的是回考配额不是卡库）。
1b. ~~**私联收场「四选一」怎么收尾**~~ —— **已于 §6.13 解决**（答错→用完；答对→沉沦/断联两条，断联走失控演出到第 17 个结局）。数据里旧的 `go_public` / `draw_line` 已不再被消费。**2026-11-17（§6.27）用户 m00895 明确拍板：私联就是设计成两个结局（答对沉沦→唯一 / 答对断联→控制不了，答错→用完），不是 bug；四个 `final_choices` 里只有 `sink`/`cut_clean` 上屏，另两条是遗留死数据，不用管。旧章节（§6.11/§6.12/§6.13）里「装饰/等会讨论/别擅自动」的说法就此作废。**
2. ~~**周日券经济副作用**（§6.4）：收入多五成，是否压周日券价或分成，待用户定。~~ —— **2026-11-15 用户拍板：不用管，「钱多点挺好的」**，保持不变，以后不再提。
3. **结局平衡**（§7.3，2026-11-16 做了三轮，**整体仍未收口**）：见 §6.18——删不可达「交易孤立」、修 `check_cond` bool 短路、劣加 `money_kept`；第二轮 A 把炎上倍率降到 2.5、残局门槛抬到炎上≥80、台上加舞台≥55；第三轮（§6.18.2）做真话卡+真话率、拆 `true_talk/recall_ok`、压重线抽线、如影（开盒≥80 且私联≥第2拍）/空心（真话率<40%）/守住（真话率≥50% 且门槛放宽）接线。改后随机 20 种子：残局 55 / 劣 40 / 散场 36 / 如影 26 / 执念 24，空心上到 7、守住在档案里出现。**待定**：① 台上/彗星触发率是否继续追（用户已说不追）；② 如影随机 13% 是否偏多 —— **用户 m02807 拍板：不抬门槛，保持开盒≥80 且私联≥第2拍（2026-11-16 收口）**；③ enjou 每周 8% 衰减没动；④ 营业线专属结局位空着，用户已明确不补。教训：**先收口、别硬压触发率，等玩家真玩一轮再定**。
4. **回考两拍在界面上的展示**（§6.10 已把「说/问」打通、选项会重排）：现在一季能锁到 3~5 条线索、收场能出满 3 题。**仍未做**的是让玩家在界面上看得出来「这是回考」——目前靠 `compact` 与「（她问的是哪一样。）」这句提示。**2026-11-16（§6.18.4）已加**：`rq_stage == "ask"` 的卡在 step 带 `recall: true`，右上角挂红色「回考」tag；`say` 卡（第一次听说）不挂。
5. **长期**：~~版聊点对点引用回复模板~~（§6.18.4 已做成真聊天记录 + 引用条）、~~回响结算~~（§6.18.5 已有结局屏「这一季的回响」+ 跨周目图鉴，尚未做跨周目「姿态/记忆」）、二周目「姿态」、欠租/打工冲突的界面提示文案、~~引擎翻成 TS~~（§6.20 已完成 engine.ts + loop.ts，85115 项逐屏对账全对）、~~前端接 TS 引擎~~（**§6.21 已完成**）、~~上 Cloudflare Pages~~（**§6.22 已上线 `ju-chang.pages.dev` + 自定义域名 `diocosplay.dpdns.org`，推仓库即自动部署**）。**剩下没有硬待办了**，等玩家真玩几轮再收反馈。
6. **已明确不做**：OTA 个人线（功能与记忆回考重复）、OTA 原型卡（用户「算了吧，不写了，以后再想到新卡叫你」）——**别主动写新卡，等他点名**。
7. ~~**⚠️ 私联线终局拷问疑似没接进运行时**~~ —— **已于 §6.10 修完**（`_line_tick` 跨周误判 + `finale` 接入 loop + 复用回考系统）。剩余小尾巴：`storyline_shiren.json` 里 `finale.gate` 的文本仍写「周 = 6」，实际走的是 `engine.FINALE_WEEK(s) = weeks_total`，文本是说明性的、不影响运行，但要改文案时记得同步。

---

## 8. 工作方式 + 环境坑（务必遵守）

**用户的工作方式**：
- **一点点做，不要一次性产出很久**；时常停下来问、给更好意见。
- **结局系统、随机事件、剧情线的设计要深入讨论再落笔**；**写新卡/新内容前必须先给提案**（曾擅自加 13 张卡被要求全部回滚）。
- **写完文件要 `present`**（把 `HANDOFF.md` / `卡库总览.md` / `DESIGN.md` 当成品给用户看）。
- **临时/无用文件自己顺手删，不用告知用户**；中文回复；结局/正文要过 `humanizer-zh`。
- **默认工作区不新建文件夹**（`default-workspace` 里只做删改）；改完博客代码若 7897 代理开着可直接 commit+push。
- 成本纪律：上下文超 20 万 token 主动提醒一次并给「继续 / 开新对话」选择；任务收尾建议换会话、把交接写进本文档。

**环境坑**：
- python 用 `C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe -X utf8`，先设 `$env:PYTHONIOENCODING="utf-8"`（否则 GBK `UnicodeEncodeError`）。
- **含中文/引号/正则 `-c` 一律写 `tools\_pNN.py` 临时脚本再跑**，不要 `python -c`（PowerShell 会拆坏）。用完即删。
- **`Set-Content` 会写 BOM** → `SyntaxError: invalid non-printable character U+FEFF`；要重写 .py 一律用 `edit` 工具定点改，不要用 here-string + Set-Content。给多行 `opt(...)` 加参数要定位整块手改，别用正则。
- PowerShell 读中文文件用 `Get-Content -Encoding UTF8`（文件本身没坏）。
- 用字符串切片删方法时容易把相邻 def 粘成一行、连删类常量（曾报 `AttributeError: 'Game' object has no attribute 'LINE_CHANCE'/'SCENE'`）；同名方法会被后者覆盖（曾丢 `_maybe_story`）。
- **双参数函数被位置参数吞掉**：`opt()` 没有 `rq=None` 形参时 `rq(...)` 会被当成 `delayed` 传进去。改 helper 签名后立刻 dump 一个 json 看键名。
- **访问 GitHub / 外网前必须先告诉用户、等他说「开了」**；代理 `socks5h://127.0.0.1:7897`（博客推送用 `http.proxy/https.proxy=http://127.0.0.1:7897`）。已知可达 `api.github.com`/`codeload.github.com`/`raw.githubusercontent.com`；`github.com` 直连不可达。
- **改完源码必重启服务**（见 §1 的杀进程命令）。**`dsh_browser_open` 现在能连本地端口**（旧文说不能，已过期）——`http://127.0.0.1:8765/` 与静态站 `http://127.0.0.1:8780/` 都实测可开。
- **pnpm/node 都不能直接用 PATH**：node=`C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`、pnpm=`...\dependencies\pnpm\bin\pnpm.mjs`（`& $node $pnpm <cmd>`）。npm.ps1 会被 ExecutionPolicy 拦。
- **pnpm 11 的 build script 审批**：`[ERR_PNPM_IGNORED_BUILDS]` 让 `pnpm install` exit 1，必须在 `聚场\` 下跑一次 `& $node $pnpm approve-builds esbuild`（它写 `allowBuilds:` 进 `pnpm-workspace.yaml`）。只写 `onlyBuiltDependencies` 压不住。
- **PowerShell 的 `>` 重定向写出来是 UTF-16LE**，Node `JSON.parse` 报 `Unexpected token '�'`。让 Python 自己 `open(path,'w',encoding='utf-8',newline='\n')` 写，或 PowerShell 加 `-Encoding utf8`。

**改完数据的固定流程**：
```powershell
$env:PYTHONIOENCODING="utf-8"
& <python> -X utf8 tools\build_ota_memory.py   # 改了线索池才需要
& <python> -X utf8 tools\build_ota_recall.py   # 线索池的下游，必跑
& <python> -X utf8 tools\build_intro.py        # 改了序章才需要
& <python> -X utf8 tools\build_endings.py      # 改了判决表才需要
& <python> -X utf8 tools\validate_all.py       # 必须 0 problem（八组）
& <python> -X utf8 tools\gen_overview.py       # 重生成卡库总览.md
```
改数值 → 再跑 `economy_sandbox.py` 确认 11 结局仍可达；改序章初值 → 再跑 `check_intro_econ.py`。

**文案口味（都是被用户当场纠正过的）**：
- 第一人称 POV，`narrative` 是「我」的心算独白，**不能出现「你」**（对白里也不行，校验会抓）。
- 卡面只写情景 + 选项；**选完才跳一行数值变动**（回执，不是算前算盘）；每张卡是两难、无纯赚（≥2 个资源反向拉扯）。
- 延迟后果显式队列（「下周」时间型 / 「条件」型），周末统一结算。别写死真人名，用选角槽 `{{slot}}`。
- **她说的话必须像闲聊，不能像答题**（「我第一次来看你们，是朋友硬拉着来的」是病句级暴露）；细节藏在抱怨/回忆/自言自语里。重型线索三种情况句子结构差太远 → 走 `say_full` 每种各写一整句。
- **「她问」必须是她问我，不是自问自答**；但绝不出现「你还记得吗」这种点破的话，用「你说得出来吗」「我考考你」。21 张卡不能共用一句环境收尾 → `SAY_TAILS`/`ASK_TAILS` 每条各写一句。
- 地偶术语（已调研，别乱编）：xox=小偶像 / ota / to=top ota / 偶活 / **特典会** / **特典券**（切券）/ 拍切チェキ / 团切 / 电切 / 宿题切 / 无料 / 物料 / 常连 / 前世粉 / 噶比 / 盐对应↔神对应 / 钓师 / DD / 推·担 / stf / 起飞 / 远征 / 前管。**MC 在台词里一律写「live」或「现场」**（数值字段名 `mc` 保留）。
- **两个坑**：`base_state` 与 `choice.effect` 不能叠（叠了心理顶到 100，执念成魔/空心全线失效）；经济沙盒的 30/30 是「固定打法」的稳定不是「玩家能稳定拿到」，压线型结局在 ±30% 波动下滑向散场是可接受的，要收紧应动**事件强度/心理下限**而非继续调判定阈值。

## 6.19 改名《聚场》+ 深色主题残留修复（2026-11-16）

- 全项目 31 个文本文件 `撑场`→`聚场`；项目目录由 `撑场\` 改名为 `聚场\`，`tools/` 里写死的绝对路径同步替换；页面标题、终端 banner、DESIGN、交接、卡库总览均已更新。
- 修复「打开网站莫名其妙红黑」：`web/app.js` 普通屏分支原来只移除 `collapsing`，不移除 `collapse-end`，所以标签页到过「控制不了」结局后再渲染普通屏，纯黑/暗红主题会一直留着；现在两个类一起移除。
- 服务从 `聚场\game\server.py` 重启；验证 `validate_all` 八组 0、`node --check web/app.js` 过、`/` 标题「聚场」、body 背景 `rgb(233,241,250)`。

## 6.19.1 版聊 7 张卡全部删除（2026-11-16）

- 用户 m03971：原 7 张「版聊」卡语气不对（像写好的旁白/答题，不像微博私信），先查微博真实版聊/返切语气，然后全删。
- 调研结论：真实版聊多是短句、语气词、表情、夸舞台/妆发/返图、早午晚安；不熟时礼貌，熟了才敢说喜欢；偶像通常不逐条私信，多在公开微博/返切里回。卡里「你发一句 → 她引一句 → 三选一」的结构本身可用，问题在语气太文、关系推进太快。
- 已做：`data/cards/chat.json` 的 `cards` 清空（保留 `_meta` 说明），卡库 128→121；`push_midweek()` 抽不到版聊卡会落「今晚没人说话，我看了两眼就睡了」的过场，不报错。
- 验证：`validate_all` 八组 0（121 卡）、`_smoke_loop` 3/3（263/240/244 步）、`gen_overview` TOTAL 115；重启后 `/api/state` 恢复玩家第 4 周存档。
- 待办：按新语气重写版聊卡（另起任务，不再沿用旧 7 张）。

## 6.19.2 版聊卡重写第一版（12 张，2026-11-16）

- 方向被用户当场纠正（m04088）：**玩家是偶像，发消息的是观众**。旧版把说话人写反了（偶像发日常、玩家回），全部作废重写。
- 真实性红线（用户 m04062/m04091/m04095/m04098 逐条否掉）：偶像不会公开发和 OTA 的合照；不写送伞、半夜外卖、后台图；观众不会私信问「返图能不能发」；不把暧昧说破（「想约我啊」）；不过分直白卖惨。
- 最终 12 张（`data/cards/chat.json`）：便利店、手幅、直播、歌单、群里夸、冷、加班、做饭、猫、失眠、生日、考试。统一为「观众一条短句 → 偶像三选一（接住/打趣/推回去）」，`casting.speaker` + `min_stickiness` 40–50；每个选项都有真实负数或 BAD 上涨，不会纯赚。
- 校验：`validate_all` 八组 0、`_smoke_loop` 3/3（251/273/267 步）、`_check_order` 0；卡库 133。
- 待办：真机/浏览器实走到版聊屏看气泡与引用是否自然；以后加卡继续按此方向与红线。

## 6.19.3 版聊卡按微博私信语气重写（15 张，2026-11-16）

- 方向：观众发一条短消息 → 偶像（玩家）三选一回。回复统一「回：」开头，走微博私信口语：短、带语气词、可以反问/打岔，不解释、不把暧昧说破。
- 合并来源：§6.19.2 的 12 张 + 此前预览里没被点名奇怪的 3 张（嗓子、头发、妆花了）；第三排、排练室、截图三张按用户要求删去。
- 每个选项都带至少一个真实负数（psyche/stamina），避免纯赚；首跑抓到 chat_live_wait/chat_third_row 两处 PUREPROFIT，已补 stamina -1。
- 校验：validate_all 八组 0（total_cards=136）、_smoke_loop 3/3（251/273/267）、_check_order 0；卡库 136。

## 6.19.4 恋爱线节奏 / 亲密前置 / 被撞破提前结局（2026-11-16）

- 用户 m04230：「和队友恋爱我感觉还没亲密上呢就结束了 而且就算写被撞破 你应该在那张卡前面先写我们在干亲密的事情 而且被撞破也没有提前结局」。
- 诊断：`weeks_total=8`；恋爱线 5 拍（心动→靠近→越界→确认→收场），`line_stage()` 一周只放一拍，`draw_line` 只有 45% 落率，200 seed 探针里收场几乎到不了（最终 stage 4 仅 7/61，139 局根本没进恋爱线）。确认拍只写到「差点吻」；`finale_caught` 开头也没有任何亲密动作。
- 提前结局 bug：`rc_take_her_hand` 同时写 `romance_caught` 与 `romance_public`，`judge()` 按 early 顺序判 flag，毕业日（n14）先命中，把「后来」（n15）遮掉；而且两个 flag 都只在季末 judge 时生效，撞破当场不结束。
- 已改代码：
  - `game/loop.py`：`_romance_if_main()`——一旦 `mainline=romance`，每周开头必推一拍（不再等骰子）；`_maybe_story(force_finale=...)`；`_start_week` 末周若 romance stage<4 则强制排收场；`choose_story` 选项带 `romance_caught`/`romance_public` 时立刻 `_finish()` 并返回。
  - 收场拍（stage 4）选项都不带 `advance`，原来不记 `story`，导致末周反复排「决赛前夜」；现在 `st["stage"] >= 4` 也记进度。
  - 撞破优先：`close_call` 或 `romance_risk` 在 flags 里时，收场必选 `finale_caught`；否则在三个收场变体里随机。
  - `game/engine.py`：新增 `romance_line(world)`。
- 文案：`confirm_almost_kiss` 改成真的吻（「嘴唇碰到一起，很轻，又谁都没退」）；`confirm_she_decides` 末尾加「她低头在我嘴角碰了一下」；`finale_caught` 开头改成休息室反锁、化妆台边吻到一半被小满拧门撞破；`finale_night_before` 补一个很轻的吻；`rc_take_her_hand` 的 flags 只留 `romance_caught`。
- 验证：`validate_all` total_cards=136、八组 0；`_smoke_loop` 3/3（251 步「用完」/ **177 步「后来」周 6** / 267 步「散场」）；`_check_order` 0；`py_compile` 过；服务已重启，`/api/state` 200 读回第 3 周存档。
- 现状：恋爱线一旦成了主线，节奏是每周一拍；撞过线/差点被抓过的玩家会在收场直接进「被撞破」并当场结季（最早第 6 周）；没踩风险的走「决赛前夜」/「运营办公室」，按选项自己选公开/秘密/离开。

## 6.19.5 重线提前结局 / 私联节奏（2026-11-16）

- 用户 m04467：「现在还有什么问题要修吗 重线私联线有没有类似的问题」→ 审计后确认重线有同类 bug，私联终局本身没有，但节奏有同类观感问题；用户说「行 都改吧」。
- 重线 bug：`storyline_zhong.json` 第四拍「最后一封信」里 `zl_answer_all`「把自己所有能说的都告诉她」只写 `final_intimate`；`choose_story` 的当场结季集合里只有 `romance_caught`/`romance_public`，所以「我只是太爱你了」要等第 8 周 judge，而这一拍最早第 5 周就能到。
  - 修：`game/loop.py` `choose_story` 的立即 `_finish()` 集合改为 `{"romance_caught", "romance_public", "final_intimate"}`。
- 私联节奏：`_shiren_if_crossed()` 原来只在「剩余拍数 > 剩余周数」时插队，越线早的档会退回 45% 抽卡，中间几拍可能整周不出现（收场仍有兜底，不丢结局）。
  - 修：越线且主线已落在私联时，每周开头必推一拍；主线是别的线或已到裂痕时仍返回空，由 `line_stage` 自行判断。
- 审计结论（记录，避免重复查）：
  - 私联收场三问走完，`_after_finale` 的 `phase=="done"` 会真的 `_finish()`，不会拖到季末。
  - 「唯一」与「控制不了」互斥：`choose_card` 里 `cut_clean` 写 `final_collapse` 并进失控演出，else 写 `truly_seen`，同一张卡只进一个分支；judge 顺序里 truly_seen 在前也不会遮。
  - 重线其余拍不写提前结局 flag；`final_cautioned`/`zhong_cut_off` 只影响资源与后续选项。
- 验证：`py_compile` 过；`validate_all` 八组 0；`_smoke_loop` 3/3（251「用完」/177「后来」周 6/267「散场」）；`_check_order` 6 seed 0；临时探针 160 seed 里有 3 局走到「最后一封信」并选 `zl_answer_all`，**选的那周 = 结束那周**（w8/w7/w6）且结局都是「我只是太爱你了」；私联探针 200 seed 里越线后排拍变成连续周（w2→w3→w4→w5→w6），收场仍在第 8 周；服务重启（新 job）`/api/state` 200，读回第 3 周存档。
- 现状：三条剧情线的「提前结局」现在都在写 flag 的当场结季；私联从越线那周起每周一拍。

## 6.19.6 收场拷问补线索 + 简介与攻略（2026-11-16）

- 用户 m04623 质疑「私联拷问三道题前面是不是都出现过，会不会根本没线索出三道题」。审计答案：**会**。300 seed、97 次收场里 quiz<3 有 18 次（18.6%），最少只有 1 题；根因是 `finale_clue_pool` 只认已经出场的 `ota_say` 细节，而私联可能第 6/7 周才越线，剩下的特典根本不够说出三件事。零线索时 `apply_finale_outcome(0,0)` 会直接判「用完」。
- 修：`game/loop.py:_ensure_finale_clues(need=3)`——收场开头若可用细节不足 3 条，从未出场的 `ota_memory` 里补足，写进 `s["clues"]`（state=said、truth），把她的 `say` 原句（`{truth}` 已填）接在收场开场白后面，成为一段「最后一场之前，她把以前说过的零碎又数了一遍」。`_begin_finale` 先调它再 `finale_quiz_cards`。
- 直接构造状态验证：0 条线索 → 收场补到 3 条、quiz=3、开场屏 5 行（开场白 + 引导句 + 3 句细节）；1 条线索时补到 3 条。`py_compile` 过、`validate_all` 八组 0、`_smoke_loop` 3/3（251 用完 / 177 后来周6 / 267 散场）。
- 新增 `简介与攻略.md`：短/长简介、八周流程、三条线打法、10 条季末 + 6 条提前结局表、设计巧思（专属 OTA、真话系统、主动退出、失控演出、版聊、二周目、记事本）。专属 OTA 概率：6 原型 × 40 名字 × 24,000 细节组合 = **1 / 5,760,000（约 0.0000174%）**。

## 6.19.7 周 1 导读挪到建完角色后（2026-11-16）

- 用户 m05005：「那个第一次时讲解这只代表着态度有时候会抢卡位 把他放到建完角色之后第一个吧」。
- 问题：`game/loop.py:_start_week()` 在第 1 周开场把「六天不会一分钟一分钟写给你看……它们不是全部，是态度。」塞进「第 1 周」正文，和第 1 周的事件/卡共享开头，观感上像占掉了一个位置。
- 改动：新增 `Game._week_intro()` 单独推这一屏；`set_name()`（一周目）与 `choose_stance()`（二周目）在建完角色/选完姿态后、`_start_week()` 之前调用它；`start_week()` 和 `_start_week()` 里第 1 周追加这段正文的代码删掉。
- 验证：直接构造 `Game` 检查队列——一周目顺序为「海报上印的是「XX」→ 导读屏 → 第 1 周」；二周目为「姿态确认 → 导读屏 → 第 1 周」。`py_compile` 过、`validate_all` 八组 0、`_smoke_loop` 3/3（252 用完 / 178 后来周6 / 268 散场）；服务重启（job `pwsh-0f263dc40d4e4f1c`），`/api/state` 200 读回第 3 周存档。


## 6.19.8 C+A 界面改造：2×3 行动格 / 像素小人 / 午夜场灯光（2026-11-16）

- 用户 m05115：「c+a吧 还有我觉得日常选项按钮做的太大了 能不能变成2*3表格这样的 还有你觉得我做一个像素小人形象放上面怎么样」。
- C（像素街机）保留原蓝白像素底：标题加像素下划线展开动画、选项逐条上浮（`--i` 递增延迟）、数字涨跌沿用原有弹窗动画。
- 日常行动屏：`#options.act-grid` 只在 `step.type==="choice" && step.kind==="act"` 时启用，2 列 × 3 行；按钮高 88→移动端 82、字号 15.5→14.5，desc 折行；`mc` 显示名缩为「练营业话术」（旧存档队列里的长标签由 `web/app.js` 渲染时兜底替换，不改存档）。
- 像素小人：`web/index.html` 加 `#idol` 容器（`#stage` 内、标题上方）；`web/app.js` 用 12×18 字符画生成内联 SVG（发/肤/眼/嘴/裙/丝带/靴全走 CSS 变量），按体力<35 切 `tired`、心理<35 切 `low`、人气≥50 切 `shine`；状态文案「站都站不太稳 / 笑不太出来 / 有点撑不住 / 台下有人举牌了 / 还撑得住」；idle 上下浮动、live 屏加速、眨眼/汗滴/腮红/星星。没取名前隐藏。
- A（午夜场）：`body.live-stage` 与 `body.ending-stage`（排除 `.collapse-end`/`.collapsing`）切深色追光；上台屏标题、HUD、选项、弹窗一起换色；结局屏回响卡/游戏之外一并适配。失控纯黑仍是最后赢家，且 `collapse-end` 下隐藏小人。
- 用户 m05445 反馈暖红「怪怪的」→ A 主题整体改青绿赛博：`--bg:#050d10`、`--paper:#0a171a`、`--accent:#23e6c2`、`--accent-d:#86f7e2`、`--warm:#55f0d4`，HUD/标题/选项/弹窗/回响卡边框同步；8px 网格线改青绿，并加固定扫描线 `body::after`（`repeating-linear-gradient`，`mix-blend-mode:multiply`，排除失控段），小人 live 裙色/丝带也改 `#23e6c2/#9af7ff`。
- 顺手修：`game/server.py:_load_game()` 读档时原来只恢复 `state`，没把 `state["name"]/name_style` 补回 `Game.name`，导致每次重启后快照 `name=null`（像素小人被误判为没取名而隐藏，部分文案也可能拿不到名字）。现在读档后补回；重启后 `/api/state` 里 `name` 是小糖，小人正常显示。
- 验证：`node --check web/app.js` 过；浏览器实测日常屏 `display:grid`、两列各 333.5px（720 宽）、按钮 88px、六个短标签正确；模拟 live 屏 body 变 `live-stage`（背景 rgb(5,13,16)、文字 rgb(232,255,249)、按钮 rgb(8,24,26)/边框 rgb(38,86,79)），模拟普通结局变 `ending-stage` 深色，模拟「控制不了」变 `collapse-end` 且 `#idol` 隐藏；`py_compile` 过、`validate_all` 八组 0（136 卡）、`_smoke_loop` 3/3（252/178/268）。
- 现状：服务 `pwsh-d0996756c1a441df` 在 8765 运行，读回玩家第 1 周存档（名字小糖），头像正常；旧存档队列里仍是旧标签，靠前端映射显示短名，新生成步骤走引擎里的新 label。

## 6.20 TS 移植（上云前置）：engine + loop 全部对账通过（2026-11-16）

**为什么做**：A 方案拍板（用户 m01202「A吧」/ m01488 问我选哪条 / m01491「那你搬吧 随时写handoff」）——把 `game/*.py` 翻成 TypeScript，让整个游戏变成纯静态站，直接上 Cloudflare Pages，零服务端成本。Pyodide 实测能原样跑 Python（加载 2946ms / 13MB WASM / Python 3.12.7），但主游玩场景是手机、jsdelivr 从国内不稳，所以 Python 侧只留下当**对账标准答案**，不进玩家浏览器。

**现在的状态：引擎与流程两层都对通了，还剩前端接入 + 部署。**

三个对账测试，都要用捆绑 node（`C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe`）：

```powershell
cd 聚场
& $node --experimental-strip-types app\test\rng.test.ts    # ✓ 84 项（6 个种子）
& $node --experimental-strip-types app\test\trace.test.ts  # ✓ 9369 项（4 种子 × 8 周）
& $node --experimental-strip-types app\test\loop.test.ts   # ✓ 85115 项（4 种子、938 屏）
& $node $pnpm exec tsc --noEmit                            # exit 0
```

**已落地的文件**：
- `app/src/core/rng.ts`（278 行）——CPython `random.Random` 的 MT19937 精确移植（`getrandbits` 按 CPython 位拼法、`sample` 的 `setsize=21` 双路径、`choices` 无权重走 `floor(random()*n)`）。`app/test/rng_expected.json` 是 Python 侧生成的 6 种子参考值。
- `app/src/core/engine.ts`（约 2170 行）——`game/engine.py` 全量移植，函数改 camelCase。数据层从「读盘」改成 `loadFiles(files)` / `loadWorld(files?)`，`RawFiles` 是 `相对路径 -> JSON`，浏览器 fetch 与测试 readFileSync 都能喂。
- `app/src/core/bill.ts`（78 行）/ `types.ts`（176 行）。
- `app/src/core/loop.ts`（约 2320 行）——`game/loop.py` 的 `Game` 类全量移植（70 个方法、4600 字文案）。
- `tools/trace_dump.py`（每周状态）/ `tools/loop_trace.py`（**逐屏**）——两个 Python 侧录标准答案的脚本，产出 `app/test/trace_expected.json`（145070 bytes）/ `loop_expected.json`（1229314 bytes）。

**这轮踩过、以后别再踩的四个坑**：
1. **PowerShell 的 `>` 重定向写出来是 UTF-16LE**，Node `JSON.parse` 直接报 `Unexpected token '�'`。两个 dump 脚本都改成收 `sys.argv[1]` 路径参数、`open(..., encoding="utf-8", newline="\n")` 自己写文件。所有「Python 生成 JSON 给 TS 读」的场合都照这个来。
2. **`for` 循环与手写 `i += 1` 叠加**：对账脚本的按钮下标是「屏幕序号 + 1」（`_choose(g, cur, n)` 前先 `n += 1`），测试侧写成 `i += 1; choose(g, cur, i)` 会被 `for` 的 `i++` 再叠一次、隔屏跳过。
3. **Python 的空 dict 是 falsy，JS 的 `{}` 是真值**。`E.cast()` 在卡没声明 `casting` 时返回 `{}`，`if (!slots)` 就漏掉了「把卡声明的每个槽都指给今天留下来的人」那段 fallback，特典回执的 `face` 会从人名掉成场所名（`第零排` → `散场以后`）。`loop.ts` 里专门加了 `emptySlots()`。
4. **`round(x, n)` 不能用「乘 10^n 再 Math.round」**。`0.1949999999999999 * 100 = 19.49999999999999` 看着像正好 `.5`，用容差判 `.5` 会误判成中点、按银行家舍入推成 `0.20`，Python 给 `0.19` —— 整个 `template` 曲线就差 0.01。`engine.ts` 的 `pyRound()` 改成把 double 拆成「尾数 × 2^指数」的精确有理数、用 BigInt 做整数除法舍入，`loop.ts` 直接复用它（别两边各写一份）。

**前端那层**：见 §6.21——已经改吃 `loop.ts` 的 `Game` 了，旧的 `web/app.js` 已删。

**还没做的**：`game/policy.py` 不移植（只 `auto_play` 用，且那段是死代码）。

---

## 6.21 前端接 TS 引擎：变纯静态站，浏览器实测跑完一整季（2026-11-16）

**做完的标志**：`vite build` 出 486KB 的 `dist/`，用 `python -m http.server` 起静态服务就能从开局玩到结局，**不起 Python 后端**。

**核心取舍：只换 `api()`，不动界面。** `web/app.js` 有八个 `/api/*` 调用点（`:398 gallery` / `:482 journal` / `:500,777 new` / `:668,752 advance` / `:732 state` / `:741 choose`），全塞在一个 `api()` 函数里。所以把 `app.js` 复制成 `app/src/ui.js`、只改 `api()` 的函数体调本地 `call()`，那 806 行界面逻辑一行没动。**这条能省掉八处改动、也省掉一整轮回归**，以后改界面就改 `app/src/ui.js`。

**新增的文件**：
- `app/src/boot.ts`（317 行）——替代 `game/server.py` 那一层。`loadDataFiles()` 用 `import.meta.glob("../../data/*.json", {eager:true})` 打三组（顶层 / `cards/` / `storylines/`），`结局.md` 走 `query:"?raw"`；导出唯一的 `call(path, body)`，内部按路径分派到 `payload/advance/choose/new/gallery/journal`，形状与 HTTP 版一致（失败返回 `{error}`）。
- `app/src/ui.js`——`web/app.js` 的原样副本，只改两处：开头 `import { call } from "./boot.ts"`；`url(sprites/idol_${style}.png)` 改成 `url(idol_${style}.png)`（`publicDir` 直接指向 `web/sprites`，产物铺在站点根）。**故意留 .js**，不为过 strict typecheck 去动 800 行。
- `app/src/main.ts`——一行 `import "./ui.js";`。
- `vite.config.ts`——`root: web`、`publicDir: web/sprites`、`base: "./"`、`outDir: ../dist`。
- `web/index.html` 只改一行：`<script src="app.js">` → `<script type="module" src="../app/src/main.ts">`。

**存档与图鉴搬进 localStorage**：键 `ju-chang.save.v1` / `ju-chang.gallery.v1`。`dumpDoc/restoreDoc` 用 `JSON.stringify` 的 replacer/reviver 处理 `state.flags` 那个 `Set`（存成 `{__set:[...]}`），并把 `g.rng.getstate()` 一起存——**不存 rng 状态读档后就分叉了**。`restoreDoc` 先 `new Game(FILES, seed)`（构造函数会重铺序章）再用存档字段覆盖，最后 `g.rng.setstate()`。

**踩过的三个坑**：
1. **`PyRandom` 不收 null**：`freshGame(null)` 会炸。第一版 `newGame()` 先 `freshGame(null)` 再重掷 seed，导致两局状态错位（存档里的 seed 和实际在跑的那局不是一个）——改成先定 `SEED` 再 `freshGame(SEED)`。
2. **`seed === ""` 的比较过不了 tsc**（TS2367，number 与 string 无重叠）。`boot.ts:252` 改成 `seed == null ? rollSeed() : Number(seed)`。
3. **pnpm 11 的构建脚本审批**：只写 `pnpm-workspace.yaml` 的 `onlyBuiltDependencies` 压不住 `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild`，`pnpm install` 直接 exit 1。要跑 `pnpm approve-builds esbuild`，它会在 yaml 里写 `allowBuilds:\n  esbuild: true`。顺带加了 `verifyDepsBeforeRun: false` 和 `packages: ["."]`。

**浏览器实测（`localhost:8780`，`http://127.0.0.1:8780/`，`python -m http.server 8780 --directory dist`）**：
- 开局 → 取名（王道系 → 星奈）→ 立绘 `idol_sweet.png` 生效 → 版聊 → 事件卡 → act 六选一循环 → 第 1 周结算「卖出 16 张券，进账 1280 块；场租和分成 160 块」全对，控制台零报错。
- 连点 130+ 屏跑完一整季，落到结局「后来」（恋爱线被撞破的提前结局，第 6 周），回响面板、`结局.md` 正文（1199 字）都正常。
- 存档落盘验证：`ju-chang.save.v1` 13871 字节、`over:true`；刷新后**照样停在结局屏**（读档正确）。图鉴 `{"endings":{"后来":{"count":1,...}}}`。
- 重开验证：点记事本里的「重开这一季」（`#quick-restart`，两段式）→ 回到第 1 周，**图鉴里的「后来」保留**。
- 记事本验证：整季每周一行（`恋爱 · 第1拍` … `第5拍`），「影响结局的事」六条。

**两个假问题，别再查**：
1. `dsh_browser_state` 的文本预览会吃掉长文本开头的 `s`，看起来像 `{{ta}}` 没替换成 `staff`。**实际 DOM 是对的**（`dsh_browser_execute` 读 `#body p` 的 `textContent` 确认过）。
2. `dsh_browser_do` 的 `#next` 常常报「target is not reachable: …not button 继续」，但**前一步其实已经生效**（`#next` 在选项屏是隐藏的）。判断方法：`dsh_browser_execute` 读 `#title`/`#options`，变了就是成功，别重试。

**构建命令**（pnpm 的 exec 前会自动 install，所以别用 npm）：
```powershell
$node="C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
$pnpm="C:\Users\kk\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\pnpm\bin\pnpm.mjs"
cd 聚场; & $node $pnpm exec vite build     # 486KB / gzip 158KB
```

**下一步就是部署**：`dist/` 是纯静态，可以直接 `wrangler pages deploy dist` 或把 GitHub 仓库接进 Cloudflare Pages（构建命令 `pnpm build`、输出目录 `dist`）。仓库 `voidvainkk/ju-chang` 已推到 GitHub。

---

## 6.22 已上线 + 三个界面问题（2026-11-17 凌晨）

**线上地址**：<https://ju-chang.pages.dev/>（自定义域名 <https://diocosplay.dpdns.org/>，A 记录 `104.21.12.196` / `172.67.195.162`，实测 200）。**以后更新就是推仓库**：`git push origin main` → Cloudflare 收 webhook → `pnpm build` → 自动部署，1–2 分钟，不用再碰控制台。部署细节见 `DEPLOY.md`。

⚠️ **`localStorage` 按域名隔离**——`ju-chang.pages.dev` 的存档在 `diocosplay.dpdns.org` 下看不到。建议固定用一个地址玩，别两边来回切。

**用户提的三个问题与修法：**

**① 立绘不随选的风格变，永远是王道系。**
根因：`app/src/core/loop.ts:500 snapshot()` 返回的字段里**没有 `name_style`**。Python 版也是 `snapshot()` 不含、由 `server.py:124 _dump_game()` 单独补的，搬家时漏了这层。前端 `app/src/ui.js:124` 是 `IDOL_STYLES.includes(s.name_style) ? s.name_style : "sweet"` → 永远拿到 `undefined` → 永远退回 sweet。
修法：**不要动 `snapshot()`**（那是 85115 项逐屏对账的基准，多一个字段就全红）。改在 `app/src/boot.ts` 的 `payload()` 里补一行：
```ts
const snap = g.snapshot();
if (snap) (snap as any).name_style = g.name_style;
```

**② 版聊卡回复之后没有对方的下一步反馈，只有一句 desc（「把话推回去」）。**
根因：`data/cards/chat.json` 15 张卡 45 个 option **全都只写了 `id/label/desc/immediate`，一张都没有 `note`**。而 `app/src/core/loop.ts:1139` 的回执组装是 `body = [this._fill(o.note || o.desc || "就这样吧。")]` → 只剩 desc。
修法：给 45 个 option 全量补 `note`（语气照其他卡的 73 条 note 走：「对方当场怎么接」）。例：
- `chat_store_seen/a` → 「他回：「你头发是湿的，一眼就认出来了。」」
- `chat_banner_text/b` → 「「肉麻的才有人看啊。」——说完还是问了句到底写什么好」
- `chat_live_wait/b` → 「「哦。」过了会儿补一句「那我睡了。」」

**③ OTA 表从横跨整行改成右上角小方块，默认收起。**
- `web/index.html`：`#ota-panel` 从 HUD 下的独立一段**搬进 `#hud`**，放进新的 `.hud-tools` 层（`#toggle` 左边）；`class="fold"` 默认收起；`<button id="ota-fold">OTA</button>`，删掉原来的 `<header>`。
- `web/style.css`：`.hud-tools{display:flex;align-items:center;gap:8px;flex:none}`；`#ota-panel header{display:none}`；**展开态用绝对定位盖出来**——`#ota-panel:not(.fold){position:absolute;right:0;top:100%;z-index:20;width:min(84vw,340px);margin-top:6px}`，因为它现在是「随时查的侧面板」，不该把正文往下推。窄屏 `width:min(88vw,320px)`。
- `app/src/ui.js` 的 `applyOtaFold`：键名 `chengchang.otafold` → `ju-chang.otafold`；按钮文字 `OTA` / `OTA ✕` + 同步 `aria-expanded`；**默认值反过来**：`localStorage.getItem(KEY) !== "0"`（没存过就收起，原来是 `=== "1"` 默认展开）。

**实测（`python -m http.server 8780 --directory dist`）**：
- ③ 收起态 `panelRect=[949,15,44,24]`、`inHud:true`、`#ota-table display:none`、`#stage` 顶部仍在 363（正文没被推开）；点开后 `rect=[713,58,340,288]`、`right:1053` 与 HUD 右边缘对齐、5 行数据，`localStorage["ju-chang.otafold"]="0"`。
- ① 把存档 `name_style` 从 `sweet` 改成 `night` 后刷新 → `backgroundImage` = `url(".../idol_night.png")`，`#idol-name`="柚子"。
- ② 点「手幅」卡第二项，回执出现「「肉麻的才有人看啊。」——说完还是问了句到底写什么好」。

**注意**：改 `chat.json` 的文案后 `app/test/loop_expected.json` 会全红，必须重生成标准答案：
```powershell
& $py tools\loop_trace.py app\test\loop_expected.json   # 1230361 bytes
```
再跑 `& $node --experimental-strip-types app\test\loop.test.ts` → 应回到 `✓ loop: 85115 项全对`。**改任何玩家可见的文案都要走这一步。**

## 6.23 四项：代词中性化 / 弹窗小方块 / 星期汉字 / 话题文案（2026-11-17 凌晨）

用户原话：「话题改回今天的营业太奇怪了 还不如说今天的舞台呢 还有我想把那种加好感弹窗也做成小方块在右下角 然后星期几的数字统一改成汉字 然后有时候ota性别会错乱 所以把他/她直接改成ta吧」。

### ① 线索卡第三选项：「今天的营业」→「今天的舞台」

`tools/build_ota_recall.py:92` 的 `say_cold`：`"label": "把话题拐回今天的营业"` → `"把话题拐回今天的舞台"`。desc 本来就是「今天最后一首你们跳得真好」，不用改。重生成后 `data/cards/ota_recall.json` 里新 label 21 次、旧文案 0 次。

### ② 数值弹窗：右下角小方块，黏性/关系收进「+N」展开

- `app/src/ui.js:270 popup()`：主数值放 `<div class="pmain">`；黏性（`.pota`）与队友关系（`.pmate`）不为空时追加 `<button class="pmore" aria-expanded="false">+N</button>` + `<div class="pextra">`；每次重设 `box.classList.remove("hidden", "open")`；点 `.pmore` 切 `open` 类、文字在 `+N` / `收起` 之间换。
- `web/style.css` 的 `#pop` 整段重写：`right:16px`、`bottom:calc(96px + env(safe-area-inset-bottom,0px))`、`min-width:96px`、`max-width:min(58vw,220px)`、`padding:6px 8px`、`font-size:12px`；`#pop.open{max-width:min(78vw,300px)}` + `#pop.open .pextra{display:block}`；手机断点 `right:12px`、`#pop.open{max-width:min(84vw,320px)}`。
- **实测**：收起态 `105×72`、`right:16 / bottom:96`；点开 `+1` → `137×108`、`.pextra` 从 `none` 变 `block`、按钮文字变「收起」，仍然贴在右下角。

### ③ 星期几改汉字

两侧必须同步（Python 是对账标准答案）：
- `app/src/core/loop.ts:691` 后加 `const DAY_CN = ["", "一", "二", "三", "四", "五", "六", "日"];`，`title` 改 `` `周${DAY_CN[day] || day}，晚上做点什么` ``。
- `game/loop.py:480` 后加 `DAY_CN = ("", "一", "二", "三", "四", "五", "六", "日")`，`title` 改 `"周%s，晚上做点什么" % DAY_CN[day]`。
- day 只取 1–6（游戏是周一到周六，没有周日）。「第 N 周」那类是周数不是星期几，用户没要求，**没动**。
- **实测**：行动屏标题显示「周二，晚上做点什么」。

### ④ 指向 OTA 的「他/她」全部改「ta」

新建 `tools/neutralize_pronouns.py`（可 import 也可 CLI，`--dry` 只看不改）：
- `neutralizer(text)`：先把「他/她」「她/他」并列收成 ta；`GUARD = {"其他","吉他","他处","利他"}` 用 `\x01XX\x01` 占位保护；`PLURAL = {"他们":"ta们","她们":"ta们"}`；再 `replace("他","ta").replace("她","ta")`；最后还原占位。
- `walk(obj)` 递归处理 dict/list 里所有**值**字符串（键名不动——线索 key「她们散了」故意保留）；`detect_indent()` 照原文件缩进写回（有的文件 `indent=1`、有的 `indent=2`）。
- 两个生成器接入：`tools/build_ota_memory.py` 与 `tools/build_ota_recall.py` 的写盘处改成 `json.dump(_neutralize(doc), f, ...)`，以后重生成不会再冒出「他/她」。

**改动的文件**：`data/ota_memory.json`（332→1）、`data/cards/ota_recall.json`（501→1）、`data/cards/ota.json`（50→0）、`data/cards/chat.json`（8→0）、`data/cards/shiroi.json`（29→0）。残余那个 1 是 dict 键「她们散了」，其 value 已变成「后来ta们自己散了」。

**为什么只改这五个文件（关键判断，别扩大）**：OTA 性别是 `game/engine.py:261 _gender_for()` 按原型掷的（女友粉→女、男友粉→男、其余 `rng.choice(["女","女","男"])`），所以**只有指向 OTA 的代词才会打架**。主角固定女（用「我」）、队友阿棠/露露/小满固定女、`private.json` 搬器材的男生固定男 —— 这些**故意没动**。`storylines/*.json` 也没动（shiren 的「她」多指小满/运营；zhong 的 chaser 虽是 OTA，但 137 处混着整段人称，改动收益不抵风险）；`结局.md`、`endings.json`、`endings_lore.json` 同样没动（「他」有 12 处指运营/路人，blind replace 会错）。

### 验证与重生成

改 truth 文案会连带影响基准，**两份都要重生成**：
```powershell
& $py tools\loop_trace.py app\test\loop_expected.json    # 1230647 bytes
& $py tools\trace_dump.py app\test\trace_expected.json    # truth「她们散了」→「ta们散了」
```
结果：`validate_all.py` 八组全 0（CARD 136 / STORY 14 / MEMORY 21）；`✓ rng: 84 项`、`✓ trace: 9369 项`、`✓ loop: 85115 项`；`typecheck` exit 0；`build` → 33 modules、`index-Cahs8-8e.js` 486.45 kB（gzip 158.56）、`index-NjKaVal-.css` 29.15 kB。




## 6.24 剧情线三处修正：同拍重播 / 专属 OTA 串台 / 线上标签（2026-11-17 凌晨）

用户原话：「私联线触发有时候有bug 连着触发了两次 而且有时候两条线专属的ota会混乱 恋爱线有一次我在第四拍的时候又遇到了第一拍剧情 锁线感觉没做好 以后把这三条线上的卡右上角打个tag吧」。

### 根因：不是 stage 回退，是「同拍换卡重播」

审计（40 局 × first/last/rand 三种点击策略）：`stage 回退 = 0`、`同周同线两次 = 0`，但**同线相邻同 stage = 65 次**（romance 45 / shiren 20 / zhong 0），其中 shiren 有 6 次是**同一张卡连播**。典型样本：`cross_wechat_red → give_work → cross_wechat_red`。

原因在 `game/loop.py:1824 choose_story()`（对应 `app/src/core/loop.ts:2206 chooseStory()`）：

```python
if lid_id == "zhong" or o.get("advance") or st["stage"] >= 4:
    s["story"][lid_id] = {"stage": st["stage"]}
```

只有带 `advance` 的选项才记进度。玩家选了 stage1–3 里「不推进」的选项（`give_work` / `pity_distance` / `ca_quiet` / `xa_stepout` / `ya_pretend` / `stop_here` 等）时进度原地不动，下周 `line_stage()` 算出的 `nxt` 还是同一 stage → 同一拍换一张卡再演一遍。私联线越线后 `_shiren_if_crossed()` **不等骰子、每周必推**，所以重播在私联线上最扎眼——就是用户说的「连着触发了两次」。

### ① 推开就安静两拍（两侧同步）

`game/loop.py:1827` / `app/src/core/loop.ts:2210` 补 `else` 分支：

```python
else:
    # 没推进 = 玩家把这条线推开了，推开就该安静几拍，
    # 而不是下周原地重播（私联越线后每周必推，所以看得最明显）。
    E.line_cool(s, lid_id, 2)
```

`line_cool` 是现成的（`engine.py:1258`，写 `_line_cool[lid] = week + 2`，`line_stage` 在 `engine.py:1248` 检查）。

### ② 同一拍恢复时换一张没演过的卡

`game/loop.py:1740` / `app/src/core/loop.ts:2108` 抽 variant 时加了去重：

```python
seen = (s.get("_line_seen") or {}).get(lid_id) or []
pool = [x for x in st["variants"] if x["id"] not in seen] or st["variants"]
v = self.rng.choice(pool)
s["_line_seen"][lid_id] = (seen + [v["id"]])[-8:]
```

只保留最近 8 张，避免数组无限长。

### ③ 专属 OTA 串台：chaser 排除 is_storyline

排查 40 局 × 3 策略**没复现**串台（`重线 chaser = shiren_prota` 共 0 局、`私联主角出现在重线/恋爱` 共 0 局），但代码里有明确隐患：**私联对象 `stick` 硬写 75**（`engine.py:366`），而 chaser 是 `max(stick)` 选出来的——她一旦进 `s["ota"]`，就永远是最高的那个，重线会把她当「一直来的那个人」。修法是所有 chaser 选取点加 `not o.get("is_storyline")` 过滤，共三处：

- `game/engine.py:1233 _remember_chaser()`；
- `game/loop.py:1772 _line_slots()` 的 zhong 分支与末尾兜底；
- `app/src/core/engine.ts:1415 _rememberChaser()` 与 `app/src/core/loop.ts:2143 _lineSlots()` 同步。

### ④ 三条线的卡右上角打 tag

前端消费已有的 `step.line_name`（`loop.ts:2119` 输出，`{shiren:"私联",zhong:"重线",romance:"恋爱"}`）：

- `app/src/ui.js:44` 加 `LINE_TAG_CLASS = { 私联: "line-shiren", 重线: "line-zhong", 恋爱: "line-romance" }`；
- `app/src/ui.js:570` 的角标段加第三分支（版聊 → 回考 → 剧情线，互斥）；
- `web/style.css:131` 加三个配色：私联 `#a3283f` 白字（危险）、重线 `#5a3080` 白字（压过来）、恋爱 `#f6d9e3` 深粉字。
- tag 沿用现有 `.corner-tag` 的绝对定位（`top:24px;right:0`），`#stage.has-tag #title{padding-right:70px}` 自动生效。

### 验证

- 重生成基准：`& $py tools\loop_trace.py app\test\loop_expected.json`（1229621 bytes）、`& $py tools\trace_dump.py app\test\trace_expected.json`（145039 bytes）。
- `& $py tools\validate_all.py` 八组全 0。
- `✓ rng: 84 项` / `✓ trace: 9369 项` / `✓ loop: 85007 项（4 个种子、945 屏）`——屏数从 938 涨到 945（多了安静两周的局）。
- `typecheck` exit 0；`build` → 33 modules、`index-BQafIPzu.js` 487.01 kB（gzip 158.74）、`index-C6kcTScL.css` 29.37 kB。
- 40 局 × 3 策略复测：**同线同卡相邻 = 0**（原 6）、同线同 stage 相邻 = 40（全是安静 2 周后回来，间隔正好 2 周）、stage 倒退 = 0。结局分布里「后来」45 / 「用完」22 / 「现生快乐」20 / 「执念成魔」12 / 「散场」10，其余各 1–4 局，没有新结局断供。
- 浏览器实测（8792）：版聊卡右上角 `corner-tag chat`「版聊」（`rect=[979,387,44,24]`、右边与 `#stage` 右边 1023 对齐）；重线卡 `corner-tag line-zhong`「重线」紫底白字、`titlePad=70px` 生效。

---

## 6.25 私联踩空改「她一直表白」+ 主角随机挑（2026-11-17 凌晨）

用户看了 §6.24 后改方向，原话：「我觉得私联线如果不advance要不写ota发私信表白的卡吧 不要加两周冷却 然后一直不往后一直表白就这样 然后我希望不一定要粘性最大的当主角 也可以随机找一个不会走的」。**§6.24 的「①推开就安静两拍（line_cool）」方案已作废**——用户要的不是冷却，而是「你越不往前，她越追着表白」。确认过的两个细节：表白卡=**带选项的卡**（2–3 个回应，影响黏性/炎上）；主角=**chaser 和私联 TA 两处都改**成随机挑。

### ① 撤销 line_cool，改成私信表白卡循环
- `game/loop.py:1855 choose_story()` / `app/src/core/loop.ts:2242 chooseStory()`：原 `else` 分支的 `E.line_cool(s, lid_id, 2)` 改成「私联踩空 → `confessed = True`」（不写 story、不加冷却）。其它线（恋爱/重线）不推进仍什么也不做。
- **断线选项不表白**：`o.flags` 里有 `line_closed`/`romance_giveup` 时仍 `E.line_cool(s, lid_id, 2)`；表白卡插在 `_finish()` / closed 判断**之后**，即 `if confessed and not closed:` 才 `push_front(self._confess_step(slots))`（Python :1884-1889 / TS :2273-2280）。表白卡插队首 → 回执屏之后立刻成为下一屏。
- `_confess_step(slots)`（Python :1774）/ `_confessStep(slots)`（TS `static lineName` 后）：从 `world.cards` 里筛 `type == "私联表白"`，避开 `_last_confess` 做三张轮换，`rng.choice` → `_render_card` → 挂 `_card`/`_slots`/`face=ta.name`。**一直不往前就一直表白**，只有明确断线或用推进选项才停。
- 新数据 `data/cards/confess.json`：3 张（`confess_late_shot` 凌晨截图 / `confess_rain_note` 雨夜语音 / `confess_one_more` 说完就删），每张 3 选项（回 / 冷 / 推开），`immediate` 都带负面项（避 validate_all「纯赚」规则）；`gate="仅私联踩空时由流程插入"` 是恒假条件（不在资源表/flags 里），**永不进普通抽卡池**，只能由流程显式推。`{{ta}}` 占位由 `_fill` 填真实名字。

### ② 主角不再固定 max(stick)，改成高黏性里随机挑
- `game/engine.py:327 protagonist()` / `app/src/core/engine.ts` 同名函数整体重写：**不再凭空造 `id=shiren_prota`/`stick=75` 的新 OTA**，改成从 `s.ota` 里排除 `is_storyline` → 按 stick 降序取前 3 → `rng.choice` → 选中者写 `is_storyline=True`、`s._prota = p`，**整季固定**。
- **关键**：选中后补一套 `_prota_preset(mem_def, rng)` 的 memory（`setdefault`，不覆盖已有值）——`{{cat_name}}`/`{{home}}` 占位符和终局拷问都靠 `s._prota.memory`，漏了就整屏填「对方」。这是本轮最大风险点，已靠 trace/loop 对账守住。
- chaser 同步随机：`game/engine.py:1212 _remember_chaser()` 加 `rng` 参数（调用点 `game/loop.py:1752`、`game/engine.py:1693 do_week`），`app/src/core/engine.ts` 同名函数 + `runSeason` 调用点、`app/src/core/loop.ts:2120 _maybeStory()` 都传 `rng`；`_lineSlots()` 的 zhong 分支与兜底（Python :1798 / TS 对应处）也改成 stick 降序前 3 + `rng.choice`。**选完写死不换**（`if not s._chaser`），整线稳定。

### 存档 / 随机序列
- 存档 `boot.ts:63` 整体序列化 `g.state`，`_prota` / `_last_confess` 都在 state 上，刷新后完整恢复，私联对象不会中途换人。
- 随机选角会消耗 rng，所以**两份基准必须重生成**，对账项数随之变化（属预期，不是分叉）。

### 验证（全绿）
- 重生成基准：`& $py tools\loop_trace.py app\test\loop_expected.json`（1127890 bytes）、`& $py tools\trace_dump.py app\test\trace_expected.json`（144577 bytes）。
- `& $py tools\validate_all.py` 八组全 0（`total_cards = 139` = 136 + 3 表白卡）。
- `✓ rng: 84 项` / `✓ trace: 9290 项` / `✓ loop: 77880 项（4 个种子、853 屏）`——项数比 §6.24 少，是随机选角改了 rng 序列、跑局路径变了。
- 表白卡在 Python 标准答案 seed0 第 75 屏触发（结局「唯一」），face = 真实 OTA「第零排」而非旧的 `shiren_prota` → 随机选角生效；三套对账全绿 → TS 与 Python 同路径、终局拷问 memory 未崩。
- `typecheck` exit 0；`build` → 34 modules、`index-Bv17sJ0d.js` 490.89 kB（gzip 160.07）、`index-C6kcTScL.css` 29.37 kB。
- 浏览器冒烟（8793）：自动播放 130 步无控制台报错，角标「恋爱/版聊/重线」正常。

### 遗留观察（未改）
`game/engine.py:1024 warm_ota()` 仍会把 `is_storyline` 的私联主角放进周末特典会名单，但她从不作为 speaker 出现（探针 speaker 0 次）。此轮没动；若要求「周末也完全不出现」，单独改 `warm_ota()` 排除即可。

---

## 6.26 恋爱线重做：风险累积 + 「谈一谈」独立幕 + 撞破改掷骰（2026-11-17 晚）

承接 2026-11-17 白天那场会话（session-33d7b1b9，标题「查看 Handoff 并接手聚场」）——那轮把恋爱线大改写进了工作区但**没跑完校验/没提交/没写 handoff**，本轮接手补完。用户 4 项设计意图（原话见对话）：「越线必被撞破 → 越线后应该有个谈一谈，无视风险才可能被撞破」「方案 A：恋爱线选项更暧昧、撞破改概率事件；打算以后公开→走到毕业日、只看当下→大概率被撞破」「单独开一幕戏，拖着以后还会有谈一谈的机会」；暧昧文案用户已拍板「力度都不错就这样写上去」。

### 诊断（为什么要改）
旧逻辑「越线必被撞破」是一票否决：越界拍写的 `close_call`/`romance_risk` flag 全仓无法清除，收场判定 `if "close_call" in fl or "romance_risk" in fl` 一命中就强制进 `finale_caught`（「后来」），毕业日线直接没戏；「帘子后面」卡变成「想推进就必踩坑」。

### 改了什么（Python 标准答案 + TS 两侧对称）
**数据**（`data/storylines/storyline_romance.json`，由 `tools/build_romance.py` 生成）：
- 四拍 12 变体 narrative 全部暧昧化重写（身体距离/呼吸/欲言又止），重点越界与确认两拍；POV 铁律保持第一人称（引号外不得出现「你」）。
- romance line 新增 `ln.talks` 三变体（`talk_rooftop`/`talk_backstage`/`talk_practice_room`），每变体 4 选项：`talk_public`→`romance_public_intent`、`talk_now`→`romance_now_intent`、`talk_wait`/`talk_avoid`→`romance_risk`，全 `advance=0`，带第一人称 `note`。talks 直接挂在 line 对象上（`StoryLine` 接口有 `[k:string]:any`），**不用改 loadWorld / types.ts / World 接口**。

**状态/引擎**（`game/engine.py` + `app/src/core/engine.ts`）：BASE 加 `romance_risk=0`、clamp 计数类循环加 `romance_risk`、`apply_story_flags()` 里 `if "romance_risk" in flags: s["romance_risk"] += 1`（TS `applyStoryFlags` 对应 :575-578）——risk 是可抵消的数值，不再是不可清除的 flag 死刑。

**流程**（`game/loop.py` + `app/src/core/loop.ts`，对称）：
- 新 `_maybe_romance_talk()` / `chooseRomanceTalk()`（TS :2104 / :1578）：确认关系后（`romance_confirmed` in flags）、未做一次性表态（无 `romance_public_intent`/`romance_now_intent`）、每周最多一次（`_rtalk_week`）、末周 forceFinale 跳过；三变体轮换避开 `_last_rtalk`；不占抽线骰子、不写 story 进度。落子走 `applyOption` + **`applyStoryFlags`**（关键：risk 数值在这里累积，普通 chooseTalk 不调它）。
- `chooseCard`/`choose_card` 分流、`current()` 的 pending 恢复、`_maybeStory` 开头拦截，两侧都加了 `rtalk` 通道。
- **收场掷骰**（TS :2112-2128 / Python `_maybe_story` stage4 分支）：`risk=trunc(romance_risk)`；`romance_public_intent`→撞破概率 `risk>=3?20:0`%；`romance_now_intent`→`min(90,60+10*risk)`%；其余（含一直没表态）→`min(90,50+15*risk)`%；`rng.random()*100 < caughtPct` 才进 `finale_caught`，否则走正常季末结局。即「公开意图≈走到毕业日、只看当下≈大概率被撞破、拖着不表态风险越攒越高」。

### 验证（全绿）
- `& $py tools\validate_all.py` 八组全 0（`total_cards = 139`）。注意 validate_all **只查 stages/variants，不查 talks**——talks 的 POV/文案靠 loop 对账守。
- 重生成基准（改了 loop 逻辑与文案，必须重生成）：`& $py tools\trace_dump.py app\test\trace_expected.json`（145189 bytes）、`& $py tools\loop_trace.py app\test\loop_expected.json`（1300638 bytes）。
- `✓ rng: 84 项` / `✓ trace: 9326 项` / `✓ loop: 89652 项（4 个种子、984 屏）`——项数比 §6.25 涨（loop 77880→89652、屏数 853→984），证明 rtalk 卡被脚本走到且两侧同步。
- `typecheck` exit 0；`build` → 34 modules、`index-DY5qSD0r.js` 499.18 kB（gzip 162.45）、`index-C6kcTScL.css` 29.37 kB。
- 浏览器冒烟（4173 本地 preview）：无控制台报错，开局→起名（王道/摇滚/和风/地雷四系按钮）→进入周末数值屏正常推进。

### 改动文件（本轮提交）
`app/src/core/engine.ts`、`app/src/core/loop.ts`、`app/test/loop_expected.json`、`app/test/trace_expected.json`、`data/storylines/storyline_romance.json`、`game/engine.py`、`game/loop.py`、`tools/build_romance.py`。临时备份 `tools/build_romance.py.bak-romance` 已删。

---

## 6.27 重线文案现实合理性改写 + 收口拍「结局藏变体」修复（2026-11-17 深夜）

承接用户看完重线完整剧情后的意见（m00916 逐字）：「请券不合理 把券都收着也不合理 从头到尾回也有点奇怪 六页被取消关注了很奇怪 偶像是不会关注粉丝的吧 她不排队了也不好 还是单纯写她在旁边偷听比较好 坐在同一家店招呼过去也很奇怪 最后一拍塑料袋不如换成很精致的礼物」。用户随后否决了两版草案（m00950「留着券还是很奇怪 换个主题得了」「精致礼物怎么会装这堆垃圾」、m00964「病态加料一点不好，前面那版改上去吧」），**最终定稿=第二版（m00958"可以"）+ 结局分支，不加病态加料**；结局.md 第 11 篇江南文风正文不动。

### 诊断（为什么要改结局分支）
旧重线 4 拍、每拍 3 变体随机上 1（`game/loop.py:1829-1831` rng.choice 从没演过的里挑）。前三拍殊途同归；**第四拍 stage3 是收口拍（所有选项 advance=4），但只有变体 C `zz_letter_final` 的第三选项 `zl_answer_all` 写 `final_intimate`**（→提前结局「我只是太爱你了」），另两个变体 A `zz_bag`/B `zz_floor` 所有选项都不写提前结局 flag。故 **2/3 概率抽不到变体 C 就永远触发不了该结局**，且无回头路——与恋爱线「帘子后面」同类坑。另：三变体的 `soft/hard/report/move` delayed 都写了「超话发出来了」，却只有一条真写 intimate，flag 与文案错配。

### 改了什么（只改 `tools/build_zhong.py` → 重生成 `data/storylines/storyline_zhong.json`，数值/flag 结构不动，只加减 flag）
**7 处文案现实合理性改写**：①拍0变体A去掉递券改「第 19 次见面我数着呢/第 20 次我记住她了」；②拍0变体C「她收着所有用过的券」→「她记得我随口说过的话」（握麦克风手冷那句抱怨，她一句不差记下来，选项问「那些话还记得多少」）；③拍1变体A「从头到尾回」→「认真读完了，挑几段回她」；④拍1变体C「取消关注」→「不理我」（偶像不会关注粉丝）；⑤拍2变体A「她不排队了」→「照常排队买券，但排完队还站在旁边听」；⑥拍2变体C「招呼一起吃」→「隔着桌子点头回个招呼」；⑦stage3 标题「楼下那个塑料袋」→「楼下那个盒子」，变体A「没写名字的礼物」=灰蓝缎带纸盒+叠整齐的深灰围巾（呼应"冬天后台冷"）+相框装拍立得（后台机位恐怖点保留），变体B快递柜「袋子」→「缠缎带的小盒子」。

**结局分支修复（收口三变体各配齐三出口，结局由玩家做了什么决定、不由抽到哪个变体决定）**：当面摊牌/问清=`final_intimate`（只是太爱你了）；上报/搬家/断联=`final_cautioned`（交季末）；收下/回避/拖延=中性（交季末 zhongs）。具体：变体A `zb_wait`（坐楼下等她）加 `final_intimate`；变体B `zf_neighbor` 从「跟阿姨说清楚」改成「下楼当面问门牌号」加 `final_intimate`；变体C `zl_answer_all` 不动（原已 intimate）。`soft/hard/report/move` 的 delayed 改成不再写「超话发出来」（改为「没有发出来/她没有再回/她没有再出现」）。POV 铁律：选项 label/desc 引号外不得有「你」——三处新 label 已修正（"我记住她了"/"那些话还记得多少"/"『不会不理你，别多想』"加引号）。

### 验证（全绿）
- `& $py tools\build_zhong.py` 重生成 json（stages 4、每拍 [3,3,3,3]）；`final_intimate` 在 json :852/:914/:1025、`final_cautioned` 在 :824/:886/:997——三变体出口齐全。
- `& $py tools\validate_all.py` 八组全 0（139 卡 / 14 stage / 21 线索）。
- 重生成基准：`trace_expected.json` 145189 bytes、`loop_expected.json` **1300683 bytes**（§6.26 为 1300638，重线新文案进了逐屏）。
- `✓ rng 84 / ✓ trace 9326 / ✓ loop 89652 项（4 种子、984 屏）` 全对；`typecheck` exit 0；`build` 34 modules（`index-BL9UDEYh.js` 499.98 kB / gzip 162.66）。
- 浏览器冒烟（4173 preview）：清 localStorage 存档后重新开局，新文案正常上屏（开局「二十二点三十分」段），无控制台报错。

### 改动文件（本轮提交）
`tools/build_zhong.py`、`data/storylines/storyline_zhong.json`、`app/test/loop_expected.json`、`app/test/trace_expected.json`、`HANDOFF.md`。
