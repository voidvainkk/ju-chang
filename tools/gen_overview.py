# -*- coding: utf-8 -*-
import json, os, re

base = r'C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\cards'
NAME = {'money':'钱','stamina':'体力','psyche':'心理','fame':'人气','stage':'舞台稳定',
'ota_all':'全体黏性','ota_jelly':'盐渍水母','ota_row0':'第零排','ota_sleepy':'今天也不困',
'ota_earphone':'蓝色耳机线','ota_film':'过期胶卷',
'relation_A':'阿棠','relation_B':'露露','relation_C':'小满','relation_all':'全体队友',
'enjou':'炎上','kaibox':'开盒','shiroi':'跟踪','banzi':'板子','shiren':'私联',
# 重线的两个内部量，玩家看不见，总览里也不许露出变量名
'zhongs':'〔她攒下的·不可见〕','zhong':'〔重线进度〕'}

# 选角槽 select -> 人话
SEL = {'gender':'性别','fan_type':'粉籍','archetype':'类型','min_stickiness':'黏性≥','private_contact':'已私联'}

def nm(k): return NAME.get(k, k)

def mk_label(key, sd):
    mk = ((sd.get('_meta') or {}).get('memory_key') or {})
    mk = {**mk, **(sd.get('memory_key') or {})}
    v = mk.get(key, key)
    if isinstance(v, dict):
        return v.get('q') or v.get('label') or key
    return v

def mk_labels(keys, sd):
    if not keys:
        return ''
    if isinstance(keys, str):
        keys = [keys]
    return '、'.join(mk_label(k, sd) for k in keys)

def choice_pools(sd):
    # 返回 {placeholder: [pool...]}，供 fill_story 显示随机池；记忆点池既可在顶层，也可在 _meta 里
    src = dict(sd.get('memory_key') or {})
    src.update((sd.get('_meta') or {}).get('memory_key') or {})
    out = {}
    for k, v in src.items():
        if isinstance(v, dict) and v.get('kind') == 'choice':
            out[k] = v.get('pool', [])
    return out

def slot_desc(sl):
    parts = []
    sel = sl.get('select', {})
    for k in ('gender','fan_type','archetype'):
        if k in sel: parts.append(str(sel[k]))
    if 'min_stickiness' in sel: parts.append('黏性≥%d' % sel['min_stickiness'])
    if sel.get('private_contact'): parts.append('已私联')
    tags = '/'.join(parts) if parts else '任意'
    hatch = '' if sel.get('private_contact') else ('，无则孵化新人' if sl.get('allow_hatch') else '')
    return '［%s：%s%s］' % (sl['slot'], tags, hatch)

def eff(d, slotmap):
    if not d: return '—'
    out = []
    for k, v in d.items():
        if k.startswith('@'):
            label = slotmap.get(k[1:], k[1:]) + '黏性'
            out.append('%s%+d' % (label, v))
        else:
            out.append('%s%+d' % (nm(k), v))
    return '、'.join(out)

def fill_narrative(nar, slotmap):
    # {{slot}} -> 〔slot：条件〕   {{slot.ta}} -> 他/她
    def rep(m):
        key = m.group(1)
        if key.endswith('.ta'):
            return 'TA'
        return '〔%s〕' % slotmap.get(key, key).replace('黏性','').strip()
    return re.sub(r'\{\{([^}]+)\}\}', rep, nar)

def fill_story(s, sd):
    # 剧情线文案里的 {{ta}} / {{ta.ta}} / {{ta.arche}}；choice 记忆点占位 {{cat_name}} 等显示为随机池
    if not s:
        return s
    pools = choice_pools(sd)
    def rep(m):
        key = m.group(1)
        if key == 'ta':
            return '［TA］'
        if key == 'ta.ta':
            return '他/她'
        if key == 'ta.arche':
            return '［原型］'
        if key == 'partner':
            return '［搭档］'
        if key == 'partner.ta':
            return '他/她'
        if key in pools:
            return '〔%s｜随机其一：%s〕' % (mk_label(key, sd), '、'.join(pools[key]))
        return '〔%s〕' % key
    return re.sub(r'\{\{([^}]+)\}\}', rep, s)

files = ['daily.json','ota.json','team.json','external.json','private.json','shiroi.json','ambient.json','positive.json','ota_recall.json','chat.json']
n = 0
lines = []
for f in files:
    d = json.load(open(os.path.join(base, f), encoding='utf-8'))
    lines.append('\n## %s（%d 张）\n' % (d['_meta'].get('category', f), len(d['cards'])))
    for c in d['cards']:
        n += 1
        gate = c.get('gate', '—')
        casting = c.get('casting', [])
        slotmap = {}
        casts = []
        for sl in casting:
            # 记录槽名到显示词（用 select 的第一项）
            sel = sl.get('select', {})
            disp = sel.get('archetype') or sel.get('fan_type') or sel.get('gender') or '客'
            slotmap[sl['slot']] = disp
            casts.append(slot_desc(sl))
        cast_line = ('　选角：' + '　'.join(casts)) if casts else ''
        lines.append('**%d. %s**　〔%s〕%s\n' % (n, c['title'], gate, cast_line))
        if c.get('narrative'):
            lines.append('> %s\n' % fill_narrative(c['narrative'], slotmap))
        if 'options' not in c:  # ambient 境遇卡
            s = '触发即生效：' + eff(c.get('effect', {}), slotmap)
            if c.get('delayed'):
                s += '　｜　延迟：' + '；'.join(eff(x.get('effect', {}), slotmap) for x in c['delayed'])
            lines.append('　→ %s' % s)
            if c.get('note'):
                lines.append('　（%s）' % c['note'])
            lines.append('')
            continue
        for o in c.get('options', []):
            s = '　- **%s**　→　%s' % (o['label'], eff(o.get('immediate', {}), slotmap))
            if o.get('delayed'):
                dl = []
                for x in o['delayed']:
                    cond = x.get('condition', '')
                    dl.append('%s%s' % ((cond + ' 时：') if cond else '', eff(x.get('effect', {}), slotmap)))
                s += '　｜　延迟：' + '；'.join(dl)
            if o.get('rq_drop'):
                s += '　｜　**本线索作废**（她不会再问）'
            elif o.get('rq_lock'):
                s += '　｜　锁定真值'
            elif o.get('rq_pick'):
                s += '　｜　' + ('答对' if (o['rq_pick'] or {}).get('choice') == 'true' else '答错')
            lines.append(s)
        lines.append('')

total = n

# ---------- 记忆回考线索池 ----------
MEM_PATH = os.path.join(os.path.dirname(base), 'ota_memory.json')
CLUE_LABEL = {}
mem_lines = []
try:
    MD = json.load(open(MEM_PATH, encoding='utf-8'))
except FileNotFoundError:
    MD = None
if MD:
    for c in MD['clues']:
        CLUE_LABEL[c['key']] = '、'.join(c['set'])
    LV = {'light': '轻 +2/−3', 'mid': '中 +4/−5', 'heavy': '重 +6/−8'}
    mem_lines.append('\n# 记忆回考线索池（%d 条）\n' % len(MD['clues']))
    mem_lines.append('> %s\n' % MD['_meta'].get('design_note', ''))
    mem_lines.append('_%s_\n' % MD['_meta'].get('freq', ''))
    for lv in ('light', 'mid', 'heavy'):
        cs = [c for c in MD['clues'] if c['level'] == lv]
        if not cs:
            continue
        mem_lines.append('\n## %s（%d 条）\n' % (LV[lv], len(cs)))
        for c in cs:
            mem_lines.append('\n### %s　[%s]\n' % (c['key'], '、'.join(c['set'])))
            mem_lines.append('- 她说：%s\n' % c['say'].replace('{truth}', '〔本局真值×1〕'))
            for a in c['ask']:
                mem_lines.append('  - 回考问法：%s\n' % a)
            rb = c['react_bad']
            rg = c.get('react_good', {})
            arch_name = MD['_meta'].get('archetypes', {})
            mem_lines.append('  - 答对（%s）：%s\n' % ('、'.join(c['set']), rg.get('gravity', '')))
            mem_lines.append('  - 答错（重力系）：%s\n' % rb['gravity'])
            mem_lines.append('  - 答错（其他原型）：%s\n' % '；'.join(
                '%s：%s' % (arch_name.get(k, k), v) for k, v in rb.items() if k != 'gravity'))
            mem_lines.append('')

# ---------- 剧情线（线性剧情） ----------
STORY_DIR = os.path.join(os.path.dirname(base), 'storylines')
import glob as _glob
story_files = sorted(_glob.glob(os.path.join(STORY_DIR, '*.json')))
story_lines = []
for sf in story_files:
    sd = json.load(open(sf, encoding='utf-8'))
    meta = sd.get('_meta', {})
    story_lines.append('\n# 剧情线：%s（线性，%d 拍）\n' % (meta.get('name', os.path.basename(sf)), len(sd.get('stages', []))))
    if meta.get('design_note'):
        story_lines.append('> %s\n' % meta['design_note'])
    memo = {**((meta.get('memory_key') or {})), **((sd.get('memory_key') or {}))}
    if memo:
        items = []
        for k, v in memo.items():
            lab = (v.get('label') or v.get('q') or k) if isinstance(v, dict) else v
            items.append(lab)
        story_lines.append('\n_本线记忆点（人设碎片，加深对 TA 的认识）：%s_\n' % '；'.join(items))
    adv_label = {'shiroi': '恐惧', 'romance': '心动', 'zhong': '靠近'}.get(meta.get('id'),
                 meta.get('advance_name') or '热度')
    for st in sd.get('stages', []):
        story_lines.append('\n## 第 %d 拍：%s　〔%s〕\n' % (st['stage'], st['title'], st.get('gate', '—')))
        if st.get('note'):
            story_lines.append('_%s_\n' % fill_story(st['note'], sd))
        for vi, var in enumerate(st.get('variants', []), 1):
            story_lines.append('\n### 变体 %d：%s\n' % (vi, var['title']))
            story_lines.append('> %s\n' % fill_story(var.get('narrative', ''), sd))
            for o in var.get('options', []):
                seg = '　- **%s**　→　%s' % (fill_story(o['label'], sd), eff(o.get('immediate', {}), {}))
                if o.get('advance'):
                    seg += '　｜　%s+%d' % (adv_label, o['advance'])
                if o.get('learns'):
                    seg += '　｜　记住记忆点:【%s】' % mk_labels(o['learns'], sd)
                if o.get('flags'):
                    seg += '　｜　标记:' + ','.join(o['flags'])
                if o.get('rq'):
                    seg += '　｜　回考:【%s】' % CLUE_LABEL.get(o['rq'].get('clue'), o['rq'].get('clue'))
                for dl in o.get('delayed', []):
                    cond = dl.get('condition', '')
                    for _k, _v in (('zhongs', '〔她攒下的·不可见〕'), ('zhong ', '〔重线进度〕 ')):
                        cond = cond.replace(_k + ' ', _v).replace(_k, _v)
                    seg += '　｜　延迟：%s%s' % ((cond + ' 时：') if cond else '', eff(dl.get('effect', {}), {}))
                story_lines.append(seg)
                if o.get('note'):
                    story_lines.append('　　（%s）' % fill_story(o['note'], sd))
            story_lines.append('')
    fin = sd.get('finale')
    if fin:
        story_lines.append('\n## 收场　〔%s〕\n' % (fin.get('gate', '—')))
        if fin.get('intro'):
            story_lines.append('> %s\n' % fill_story(fin['intro'], sd))
        quiz = fin.get('quiz', {})
        if quiz:
            story_lines.append('**拷问**：%s（抽 %d 道，答对≥%d=真·被看见，否则假·工具）\n'
                               % (quiz.get('note', ''), quiz.get('draw', 3), quiz.get('pass_threshold', 2)))
        for oc in fin.get('outcomes', []):
            story_lines.append('- 结果【%s】〔%s〕：%s　（%s）'
                               % (oc['label'], oc.get('condition', ''), eff(oc.get('effect', {}), {}), oc.get('note', '')))
        story_lines.append('\n**最后的选择**：\n')
        for fc in fin.get('final_choices', []):
            seg = '　- **%s**　→　%s' % (fc['label'], eff(fc.get('immediate', {}), {}))
            for dl in fc.get('delayed', []):
                cond = dl.get('condition', '')
                seg += '　｜　延迟：%s%s' % ((cond + ' 时：') if cond else '', eff(dl.get('effect', {}), {}))
            story_lines.append(seg)
        story_lines.append('')

txt = ('# 《聚场》卡库总览（卡片 %d 张 + 剧情线 %d 条，供审核）\n\n'
 '数值记号：＋为涨、－为跌。炎上/开盒/跟踪/板子 四项越高越糟。\n'
 '选角：〔槽位：条件〕表示运行时从符合该条件的 OTA 里选人填入；「无则孵化新人」= 没有符合的就新生成一个。\n'
 '剧情线：一条线=固定阶段串，每拍 3 个剧情变体随机上 1；触发按条件不按日历（门槛到了当周必出）。推进条各有名字：「热度」=私联线的玩家投入增量（回消息/见面），热度不够则卡住；「靠近」=重线的她越走越近，玩家越心软她攒得越快，而且这个数看不见；「心动」=队友恋爱线的回应热度，冷淡则断线。\n' % (total, len(story_files)))
# ---------- 序章 ----------
intro_lines = []
intro_path = os.path.join(os.path.dirname(base), 'intro.json')
if os.path.exists(intro_path):
    idoc = json.load(open(intro_path, encoding='utf-8'))
    grp = idoc.get('group', {})
    intro_lines.append('\n# 序章（开场，约一分钟）\n')
    intro_lines.append('> %s\n' % idoc['_meta'].get('design_note', ''))
    intro_lines.append('\n_团名：%s（粉丝叫：%s）_\n' % (grp.get('name', ''), '、'.join(grp.get('nickname') or [])))
    intro_lines.append('\n_%s_\n' % grp.get('history', ''))
    intro_lines.append('\n## 正文\n')
    for para in idoc.get('text', []):
        intro_lines.append('\n%s\n' % para)
    intro_lines.append('\n## 第一场之前（三选一）\n')
    intro_lines.append('_%s_\n' % idoc.get('before_quote', ''))
    LV = {}
    for c in idoc.get('choices', []):
        eff = c.get('effect') or {}
        seg = '、'.join('%s%s' % (NAME.get(k, k), ('%+d' % v)) for k, v in eff.items())
        intro_lines.append('\n- **%s**　%s　→　%s\n' % (c['label'], c.get('desc', ''), seg))
        if c.get('after'):
            intro_lines.append('  - %s\n' % c['after'])
    for line in idoc.get('after_quote', []):
        intro_lines.append('\n%s\n' % line)
    bs = idoc.get('base_state') or {}
    intro_lines.append('\n_序章结算：钱 %s · 体力 %s · 心理 %s · 人气 %s · 舞唱 live %s/%s/%s_\n' % (
        bs.get('money'), bs.get('stamina'), bs.get('psyche'), bs.get('fame'),
        bs.get('dance'), bs.get('sing'), bs.get('mc')))

# ---------- 判决表 ----------
END_NAME = {'money_drop': '末场特典收入在掉', 'max_share': '单个人占收入比例',
            'beibao': '有过包养式收入', 'true_cog': '真实认知（真温度）',
            'template': '模板化程度', 'relavg': '队友关系均值', 'chose_leave': '最后一周选了离开',
            'rent_missed': '欠过租', 'ota_ge40_count': '黏性≥40 的人数',
            'true_talk': '说过真话的次数', 'max_single': '本季最高单场',
            'last_live': '最后一周选了再跳一场', 'played_while_collapsing': '垮着状态还上台'}
end_lines = []
end_path = os.path.join(os.path.dirname(base), 'endings.json')
if os.path.exists(end_path):
    edoc = json.load(open(end_path, encoding='utf-8'))
    end_lines.append('\n# 结局判决表（%d 个 = 季末 %d + 提前结束 %d）\n' % (
        edoc['_meta']['counts']['total'], edoc['_meta']['counts']['season'], edoc['_meta']['counts']['early']))
    end_lines.append('> 判定顺序自上而下，第一条命中的就是结局。来源：%s\n' % edoc['_meta'].get('source', ''))

    def leaf(f, spec):
        """spec 可能是 {'>=': 90} 或 {'>=': 0.6, 'beibao': True} 这类混合，拆成两段拼。"""
        nm = END_NAME.get(f) or NAME.get(f, f)
        if isinstance(spec, dict):
            return '且'.join('%s %s%s' % (nm, op, ('是' if val is True else '否' if val is False else val))
                            for op, val in spec.items())
        return '%s = %s' % (nm, '是' if spec is True else '否' if spec is False else spec)

    def cond_text(cond):
        if not cond:
            return '（保底，永远命中）'
        parts = []
        for k, v in cond.items():
            if k == 'any':
                parts.append('（' + ' 或 '.join('且'.join(leaf(f, sp) for f, sp in alt.items()) for alt in v) + '）')
            elif k in ('not_baoshou', 'no_rent_missed'):
                parts.append('未满足守住本心' if k == 'not_baoshou' else '没有欠过租')
            else:
                parts.append(leaf(k, v))
        return ' 且 '.join(parts)

    end_lines.append('\n## 季末（按顺序判定）\n')
    for e in edoc.get('flow', []):
        end_lines.append('\n### %d · %s　%s\n' % (e['n'], e['name'], ('〔%s〕' % '、'.join(e['tags'])) if e.get('tags') else ''))
        end_lines.append('- 条件：%s\n' % cond_text(e.get('cond')))
        end_lines.append('- 为什么是它：%s\n' % e.get('why', ''))
    end_lines.append('\n## 提前结束（由剧情线 flag 直接触发）\n')
    for e in edoc.get('early', []):
        t = e.get('trigger') or {}
        end_lines.append('\n- **%d · %s**　`%s`（%s）— %s\n' % (e['n'], e['name'], t.get('flag'), t.get('from'), e.get('why')))
    end_lines.append('\n## 结算面板（六类可数，只回放不判定）\n')
    for pc in edoc.get('panel_counts', []):
        end_lines.append('- %s\n' % pc.get('label'))

lines = lines + intro_lines + story_lines + mem_lines + end_lines
open(r'C:\Users\kk\Documents\deepseek-harness\default-workspace\聚场\data\卡库总览.md', 'w', encoding='utf-8').write(txt + '\n' + '\n'.join(lines))
print('TOTAL', total)
