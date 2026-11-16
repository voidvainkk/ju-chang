# 部署到 Cloudflare Pages（连 GitHub 自动部署）

这份是从零到尾的操作步骤。照着填，第一次大约 10 分钟，之后每次 `git push` 自动重新发布。

**前置**：GitHub 仓库已经在了 —— <https://github.com/voidvainkk/ju-chang>（public，默认分支 `main`）。

---

## 0. 先认清这套东西长什么样

| 项 | 值 |
|---|---|
| 仓库根目录 | 就是 `聚场\` 本身（`package.json`、`web/`、`app/` 都在根上） |
| 构建命令 | `pnpm build` |
| 输出目录 | `dist` |
| Node | 22 或更高（Vite 6 的要求，Cloudflare 默认就够） |
| pnpm | 10 或 11 都行（lockfile v9.0 两版都验过） |
| 环境变量 | **不需要任何** |
| 后端 / 数据库 | **没有**，纯静态文件 |
| 产物大小 | 约 700 KB（js 486 KB + css 28 KB + index 3 KB + 四张立绘 191 KB） |

`dist/` 已经在 `.gitignore` 里，不用提交构建产物 —— Cloudflare 会自己跑 `pnpm build`。

---

## 1. 建 Pages 项目

1. 打开 <https://dash.cloudflare.com/>，登录你买了域名的那个账号。
2. 左侧栏找 **Workers & Pages**（有的界面叫 **Compute (Workers)** 下面挂着 Pages）。
3. 点 **Create**（蓝色按钮）→ 切到 **Pages** 标签页 → **Connect to Git**。
4. 第一次会要求授权 GitHub：
   - 点 **Connect GitHub**；
   - 弹窗里选 **Only select repositories**，勾中 `voidvainkk/ju-chang`（不要选 All repositories，没必要给全部权限）；
   - 点 **Install & Authorize**。
5. 回到 Cloudflare，列表里出现 `ju-chang`，选中它 → **Begin setup**。

> 如果第 4 步点完没反应，多半是浏览器拦了弹窗，或者 GitHub 那边要求二次确认。去 GitHub 的 **Settings → Applications → Cloudflare Pages** 里看一眼是否已授权。

---

## 2. 填构建设置（这一屏最重要）

**Project name**：`ju-chang`
> 它决定默认域名 `ju-chang.pages.dev`。想换名字就现在改，建好之后改名字要删项目重建。

**Production branch**：`main`

**Build settings**：
- **Framework preset**：选 **None**（不要选 Vite —— 预设会写成 `npm run build`，我们用的是 pnpm）
- **Build command**：`pnpm build`
- **Build output directory**：`dist`
- **Root directory**：**留空**

展开 **Environment variables (advanced)**，加两条：

| Variable name | Value |
|---|---|
| `NODE_VERSION` | `22` |
| `PNPM_VERSION` | `10` |

> 这两条不是必须的（不写大概率也能过），但写上是把构建环境钉死。以后 Cloudflare 悄悄升默认版本、导致某天构建突然挂了的时候，有这两条就不用查。

---

## 3. 点 Save and Deploy

第一次构建大约 30–60 秒。日志里应该看到：

```
Detected the following tools from environment: nodejs@22.x, pnpm@10.x
Installing project dependencies: pnpm install
Running build command: pnpm build
vite v6.4.6 building for production...
✓ 33 modules transformed.
../dist/index.html                   3.28 kB
../dist/assets/index-*.css          28.44 kB
../dist/assets/index-*.js          485.51 kB
✓ built in ~600ms
Success: Your site was deployed!
```

看到 **Success** 就是成了，域名是 `https://ju-chang.pages.dev`。

---

## 4. 验收（四项，缺一项都说明没对）

打开 `https://ju-chang.pages.dev`：

1. **标题「二十二点三十分」+ 一段团名来历的长文**，右上角 HUD 是 `1700 钱 / 100 体力 / 66 心理 / 12 人气`，第 1 周。
2. 点「继续」三次，出现 **四个风格选项**（王道系 / 摇滚系 / 和风系 / 地雷系）。选一个 → 出现三个候选名字 → 选一个 → 左边出现**像素立绘**。
3. 立绘不能是空白方块。是空白就说明 `idol_*.png` 没铺上去（看第 6 节）。
4. 一直点到第 1 周结束，能看到「第 1 周结算」面板 + 周末 Live 分数。刷新页面，进度还在（存在浏览器 localStorage，键名 `ju-chang.save.v1`）。

---

## 5. 绑自己的域名（可选）

1. 项目页 → **Custom domains** → **Set up a custom domain**。
2. 填一个子域，比如 `idol.你的域名.com`，点 **Continue**。
3. 因为域名本来就在这个 Cloudflare 账号下，它会自动加一条 CNAME，**点 Activate domain** 就完事，不用去别处改 DNS。
4. 等 1–2 分钟，证书签发完就能访问。

> ⚠️ **一个真实的坑**：存档在 `localStorage`，它是**按域名隔离的**。你在 `ju-chang.pages.dev` 上玩的进度，换到 `idol.你的域名.com` 之后看不到，反过来也一样。绑域名之前先想好最终用哪个地址玩。

如果域名不在 Cloudflare：去你的 DNS 服务商加一条 `CNAME → ju-chang.pages.dev`，再回 Cloudflare 点 **Activate domain** 等验证。

---

## 6. 常见故障对照表

| 现象 | 原因 | 怎么修 |
|---|---|---|
| 构建报 `ERR_PNPM_OUTDATED_LOCKFILE` | lockfile 和 `package.json` 不一致 | 本地跑 `pnpm install` 后把 `pnpm-lock.yaml` 一起提交 |
| 构建报 `Ignored build scripts: esbuild` 然后 exit 1 | pnpm 拦了 esbuild 的 postinstall | 已经修好了（`pnpm-workspace.yaml` 里同时写了 `onlyBuiltDependencies` 和 `allowBuilds`）。要是又出现，把 `PNPM_VERSION` 定成 `10` |
| 页面白屏，控制台 `Failed to load module script` | 构建命令用成了 `npm run build` 但没装依赖，或输出目录填错 | 确认 Build command 是 `pnpm build`、output 是 `dist` |
| 页面能开但**立绘是空白** | 四张 `idol_*.png` 没进产物 | 它们靠 `vite.config.ts` 的 `publicDir`（指向 `web/sprites`）铺到站点根。检查 `dist/` 里有没有 `idol_sweet.png` 等四张 |
| 文案变成 `{{ta}}` 这种占位符 | `data/` 里的 json 没进 bundle | 看构建日志 `33 modules transformed`，正常应该是这个数。少了说明 `import.meta.glob` 那几条匹配路径拼错了 |
| 点「继续」没反应 | 引擎抛异常被 `call()` 吞了 | 开浏览器 F12 → Console 看报错。所有 `/api/*` 已经换成本地调用，报错会直接带栈 |
| 改了代码但线上没变 | 没 push，或 push 的不是 `main` | 看 Deployments 列表最新一条的 commit 是不是你推的那个 |
| 构建成功但内容是旧的 | 浏览器缓存了 `index.html` | Cloudflare 对 `assets/` 下带 hash 的文件长期缓存，`index.html` 是短缓存。强制刷新 `Ctrl+Shift+R` |

---

## 7. 以后怎么更新

```powershell
cd 聚场
git add -A
git commit -m "改了什么"
git push origin main
```

推上去 Cloudflare 自动构建，40 秒后线上就是新版。

**推送前建议本地先跑一遍**，尤其是改过文案的时候 —— `app/test/loop.test.ts` 有 85115 项逐屏对账，改错一个字会立刻红：

```powershell
& $node -v                      # 确认 node 在
pnpm test                       # rng 84 + trace 9369 + loop 85115
pnpm typecheck
pnpm build
```

---

## 8. 免费额度（够用）

| 项 | 免费额度 | 我们用了多少 |
|---|---|---|
| 静态请求 / 带宽 | **不限** | — |
| 构建次数 | 每月 500 次 | 每次 push 一次，随便用 |
| 单文件大小 | 25 MiB | 最大 485 KB |
| 文件数 | 20,000 | 7 个 |

没有服务器、没有数据库，所以不存在「闲置被停机」或「月度账单」这种事。

---

## 附：不走 GitHub 的手动部署（备用，用不上）

```powershell
cd 聚场
pnpm build
& $node $pnpm dlx wrangler pages deploy dist --project-name ju-chang
```

这条要 `wrangler login` 走一遍浏览器授权。你选了 GitHub 自动部署，正常情况下不需要它。
