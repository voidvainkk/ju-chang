import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  // 界面还是原来那套 web/，只是脚本入口换成 app/src/main.ts
  root: fileURLToPath(new URL("./web", import.meta.url)),
  // 立绘精灵图直接铺到站点根：界面里写的是 url(idol_sweet.png)
  publicDir: fileURLToPath(new URL("./web/sprites", import.meta.url)),
  base: "./",
  build: {
    outDir: fileURLToPath(new URL("./dist", import.meta.url)),
    emptyOutDir: true,
    target: "es2022",
    // 两个页面：游戏本页 + 游戏外的音乐室
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("./web/index.html", import.meta.url)),
        music: fileURLToPath(new URL("./web/music.html", import.meta.url)),
      },
    },
  },
  server: { fs: { allow: [here] } },
});
