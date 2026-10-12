#!/usr/bin/env node
/**
 * content-visualizer 内联打包器
 * ───────────────────────────────────────────────────────────────
 * 把走 CDN 的可视化页 → 零外部依赖的内联自包含单文件。
 * 用途：凡是要部署飞书妙搭 / 发祥书手机看的页面，先跑这个再发，
 *       否则手机无代理加载不出国际 CDN（unpkg/jsdelivr）会整页白屏。
 *
 * 用法：
 *   node inline-build.js <源HTML> [输出HTML]
 *   - 不给输出路径时默认写 <源>.inline.html
 *   - 想原地覆盖：把输出路径填成和源一样
 *
 * 依赖：node + npx esbuild（脚本自动调用，首次会现下 esbuild）
 * 产物：~1.6MB 单文件，performance 资源请求 0，手机离线可开。
 *
 * 做了两件事：
 *   1) 把 6 个 CDN <script src> 替换成内联（库缓存在 ~/.cache/content-visualizer-libs/，首次下载后复用）
 *   2) 去掉 3MB Babel —— 提取 type="text/babel" 的 JSX，用 esbuild 预编译成纯 JS 再内联（手机秒开、无浏览器转译延迟/失败风险）
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execSync } = require("child_process");

const SRC = process.argv[2];
if (!SRC || !fs.existsSync(SRC)) {
  console.error("用法: node inline-build.js <源HTML路径> [输出HTML路径]");
  console.error("源 HTML 须是 content-visualizer template.html 改出来的（含 6 个 CDN script + type=text/babel 段）");
  process.exit(1);
}
const OUT = process.argv[3] || SRC.replace(/\.html$/i, "") + ".inline.html";

const CACHE = path.join(os.homedir(), ".cache", "content-visualizer-libs");
fs.mkdirSync(CACHE, { recursive: true });

// 库 URL / 缓存文件名 / template.html 里对应的 <script> 标签（必须逐字一致才能匹配替换）
const LIBS = [
  { file: "react.js",      url: "https://unpkg.com/react@18/umd/react.production.min.js",
    tag: '<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>' },
  { file: "react-dom.js",  url: "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js",
    tag: '<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>' },
  { file: "prop-types.js", url: "https://unpkg.com/prop-types@15/prop-types.min.js",
    tag: '<script crossorigin src="https://unpkg.com/prop-types@15/prop-types.min.js"></script>' },
  { file: "recharts.js",   url: "https://cdn.jsdelivr.net/npm/recharts@2.12.7/umd/Recharts.min.js",
    tag: '<script crossorigin src="https://cdn.jsdelivr.net/npm/recharts@2.12.7/umd/Recharts.min.js"></script>' },
  { file: "lucide.js",     url: "https://unpkg.com/lucide@latest/dist/umd/lucide.js",
    tag: '<script crossorigin src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>' },
  { file: "tailwind.js",   url: "https://cdn.tailwindcss.com",
    tag: '<script src="https://cdn.tailwindcss.com"></script>' },
];
// 匹配任意版本的 Babel standalone 标签（@latest / 锁版本 @7.26.4 等都剥掉，JSX 已由 esbuild 预编译）
const BABEL_RE = /<script[^>]*\ssrc="https?:\/\/[^"]*@babel\/standalone[^"]*"[^>]*><\/script>/gi;

// 内联进 <script> 前，把内容里的 </script> 转义掉，避免提前闭合脚本块
const guard = s => s.replace(/<\/script>/gi, "<\\/script>");

// 1) 确保库已缓存（缺失或异常小就重下；走系统代理，没代理直连也通）
for (const lib of LIBS) {
  const p = path.join(CACHE, lib.file);
  if (!fs.existsSync(p) || fs.statSync(p).size < 500) {
    console.error("↓ 下载", lib.file);
    execSync(`curl -sL ${JSON.stringify(lib.url)} -o ${JSON.stringify(p)}`, { stdio: "inherit" });
    if (!fs.existsSync(p) || fs.statSync(p).size < 500) {
      console.error("✗ 下载失败:", lib.url, "（检查网络/代理）"); process.exit(1);
    }
  }
}

let html = fs.readFileSync(SRC, "utf8");

// 2) 提取 JSX → esbuild 编译成纯 JS（去 Babel）
const m = html.match(/<script type="text\/babel"[^>]*>([\s\S]*?)<\/script>/);
if (!m) { console.error("✗ 没找到 <script type=text/babel> 段，确认这是 content-visualizer 页面"); process.exit(1); }
const jsxPath = path.join(CACHE, "_app.jsx");
const jsPath  = path.join(CACHE, "_app.compiled.js");
fs.writeFileSync(jsxPath, m[1]);
console.error("⚙ esbuild 编译 JSX");
execSync(`npx --yes esbuild ${JSON.stringify(jsxPath)} --jsx=transform --target=es2017 --outfile=${JSON.stringify(jsPath)}`, { stdio: "inherit" });
const appJs = guard(fs.readFileSync(jsPath, "utf8"));

// 3) 逐个把 CDN <script src> 替换成内联（用函数 replacement，避免库代码里的 $ 被当替换模式）
for (const lib of LIBS) {
  if (html.indexOf(lib.tag) === -1) { console.error("⚠ 未找到标签（跳过）:", lib.file); continue; }
  const code = guard(fs.readFileSync(path.join(CACHE, lib.file), "utf8"));
  html = html.replace(lib.tag, () => "<script>\n" + code + "\n</script>");
}
html = html.replace(BABEL_RE, () => "");                                               // Babel 不再需要
html = html.replace(/<script type="text\/babel"[^>]*>[\s\S]*?<\/script>/, () => "<script>\n" + appJs + "\n</script>"); // JSX 段 → 编译后 JS

fs.writeFileSync(OUT, html);

const ext = (html.match(/<script[^>]*\ssrc="https?:\/\//g) || []).length;
console.error("───");
console.log("输出:", OUT);
console.log("大小:", (html.length / 1024 / 1024).toFixed(2), "MB");
console.log("剩余外部 <script src>:", ext, ext === 0 ? "✓ 零外部依赖" : "✗ 还有外链，需检查");
if (ext !== 0) process.exit(1);
