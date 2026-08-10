#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 posts/ 里的 Markdown 生成为 site/ 里的静态网页。

用法：  python3 build.py
零依赖，不用装任何东西。
"""

import os
import re
import html
import shutil
from datetime import date, datetime, timezone

# ─────────────────────────────────────────────
#  配置：只需要改这几行
# ─────────────────────────────────────────────

SITE_TITLE = "无何有"
SITE_URL = "https://theoutopia.com"   # 你的域名，末尾不要斜杠
AUTHOR = ""                            # 可留空
DESCRIPTION = ""                       # 可留空，用于 RSS

POSTS_DIR = "posts"
STATIC_DIR = "static"    # 图片等原样拷贝到站点根目录
OUT_DIR = "site"

# 首页里，两篇文章之间的留白 = 它们相隔的天数
DAYS_TO_PX = 3.0     # 一天几像素
GAP_MIN = 18         # 最小间距
GAP_MAX = 170        # 最大间距（免得停更一年把页面撑爆）


# ─────────────────────────────────────────────
#  一个很小的 Markdown 子集解析器
# ─────────────────────────────────────────────

def _inline(text):
    """行内语法：`代码` ![图] [链接] **粗** *斜*"""
    stash = []

    def keep(m):
        stash.append("<code>" + html.escape(m.group(1)) + "</code>")
        return "\x00%d\x00" % (len(stash) - 1)

    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
                  r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text


def markdown(src):
    """块级语法。够用就好，不追求完备。"""
    out = []
    lines = src.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # 代码块 ```
        if line.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            continue

        # 分隔线
        if re.fullmatch(r"(-{3,}|\*{3,})", line.strip()):
            out.append("<hr>")
            i += 1
            continue

        # 标题
        m = re.match(r"(#{1,4})\s+(.*)", line)
        if m:
            lv = len(m.group(1)) + 1          # 文章标题占了 h1
            lv = min(lv, 5)
            out.append("<h%d>%s</h%d>" % (lv, _inline(m.group(2).strip()), lv))
            i += 1
            continue

        # 引用
        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip())
                i += 1
            out.append("<blockquote>" + markdown("\n".join(buf)) + "</blockquote>")
            continue

        # 列表
        if re.match(r"\s*([-*]|\d+\.)\s+", line):
            ordered = bool(re.match(r"\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"\s*([-*]|\d+\.)\s+", "", lines[i], count=1))
                i += 1
            out.append("<%s>%s</%s>" % (
                tag, "".join("<li>%s</li>" % _inline(x) for x in items), tag))
            continue

        # 原样输出的 HTML
        if line.lstrip().startswith("<"):
            buf = []
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i])
                i += 1
            out.append("\n".join(buf))
            continue

        # 段落
        buf = []
        while i < len(lines) and lines[i].strip() \
                and not lines[i].startswith(("#", ">", "```")) \
                and not re.match(r"\s*([-*]|\d+\.)\s+", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + _inline("".join(buf) if _is_cjk("".join(buf))
                                   else " ".join(buf)) + "</p>")

    return "\n".join(out)


def _is_cjk(s):
    """中文换行不该补空格，英文该补。看哪种字多。"""
    cjk = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
    return cjk * 3 > len(s)


# ─────────────────────────────────────────────
#  读文章
# ─────────────────────────────────────────────

class Post:
    def __init__(self, path):
        raw = open(path, encoding="utf-8").read()
        meta, body = {}, raw

        # 头部：连续的 key: value，遇到空行结束
        head_lines = []
        rest = raw.split("\n")
        while rest and re.match(r"^[A-Za-z_]+\s*:", rest[0]):
            head_lines.append(rest.pop(0))
        for l in head_lines:
            k, v = l.split(":", 1)
            meta[k.strip().lower()] = v.strip()
        body = "\n".join(rest).strip()

        name = os.path.splitext(os.path.basename(path))[0]
        m = re.match(r"(\d{4}-\d{2}-\d{2})[-_]?(.*)", name)

        d = meta.get("date") or (m.group(1) if m else None)
        if not d:
            d = date.fromtimestamp(os.path.getmtime(path)).isoformat()
        self.date = datetime.strptime(d.strip()[:10], "%Y-%m-%d").date()

        self.slug = meta.get("slug") or (m.group(2) if m and m.group(2) else name)
        self.slug = self.slug.strip().strip("-") or self.date.isoformat()
        self.title = meta.get("title", "").strip()
        self.body = body
        self.html = markdown(body)

    @property
    def url(self):
        return "/%s/" % self.slug

    @property
    def display_title(self):
        # 没写标题的，用日期当标题。无题也是一种题。
        return self.title or self.date.strftime("%Y 年 %-m 月 %-d 日")


# ─────────────────────────────────────────────
#  模板
# ─────────────────────────────────────────────

BASE = """<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<link rel="alternate" type="application/rss+xml" title="{{SITE}}" href="/feed.xml">
<style>
:root{
  --ground:#efece5;
  --ink:#2b2924;
  --ink-soft:#5d594f;
  --ink-faint:#9a958a;
  --rule:#d8d3c8;
  --measure:34em;
}
@media (prefers-color-scheme:dark){
  :root{ --ground:#191816; --ink:#d6d1c6; --ink-soft:#9d988c;
         --ink-faint:#6b6659; --rule:#33312c; }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0;
  background:var(--ground);
  color:var(--ink);
  font-family:"Songti SC","Noto Serif CJK SC","Source Han Serif SC",
              "Source Han Serif",Georgia,"Times New Roman",serif;
  font-size:18px;
  line-height:1.9;
  text-rendering:optimizeLegibility;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:var(--measure);margin:0 auto;padding:11vh 1.5rem 22vh}

/* 站名：疏排，是全站唯一一处“设计” */
.sitename{
  display:block;
  font-size:.94rem;
  letter-spacing:.42em;
  text-indent:.42em;
  color:var(--ink-soft);
  text-decoration:none;
  margin-bottom:9vh;
}
.sitename:hover{color:var(--ink)}

/* 首页：条目之间的留白 = 相隔的天数 */
.index{list-style:none;margin:0;padding:0}
.index li{display:flex;gap:1.4em;align-items:baseline}
.index time{
  flex:none;
  font-size:.8rem;
  letter-spacing:.06em;
  color:var(--ink-faint);
  font-variant-numeric:tabular-nums;
}
.index a{
  color:var(--ink);
  text-decoration:none;
  border-bottom:1px solid transparent;
  padding-bottom:.1em;
}
.index a:hover{border-bottom-color:var(--rule)}
.year{
  font-size:.8rem;
  letter-spacing:.2em;
  color:var(--ink-faint);
  margin:0 0 1.6em;
  font-variant-numeric:tabular-nums;
}
.year:not(:first-child){margin-top:2.4em}

/* 文章 */
article h1{
  font-size:1.34rem;
  font-weight:normal;
  line-height:1.6;
  margin:0 0 .5em;
  letter-spacing:.02em;
}
.dateline{
  font-size:.8rem;
  letter-spacing:.06em;
  color:var(--ink-faint);
  margin:0 0 3.4em;
  font-variant-numeric:tabular-nums;
}
article p{margin:0 0 1.5em}
article h2,article h3,article h4{
  font-weight:normal;font-size:1.05rem;letter-spacing:.02em;margin:2.6em 0 .9em;
}
article a{color:var(--ink);text-decoration:none;
  border-bottom:1px solid var(--rule);padding-bottom:.08em}
article a:hover{border-bottom-color:var(--ink)}
article img{max-width:100%;height:auto;display:block;margin:2.4em auto}
blockquote{
  margin:2em 0;padding-left:1.4em;
  border-left:1px solid var(--rule);color:var(--ink-soft);
}
pre{
  overflow-x:auto;padding:1em 1.2em;
  background:rgba(128,120,100,.09);
  font-size:.84rem;line-height:1.75;
}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.86em}
pre code{font-size:1em}
hr{border:0;border-top:1px solid var(--rule);margin:3.4em 0}
ul,ol{padding-left:1.3em;margin:0 0 1.5em}
li{margin-bottom:.4em}

.foot{margin-top:9vh;font-size:.8rem;letter-spacing:.06em}
.foot a{color:var(--ink-faint);text-decoration:none}
.foot a:hover{color:var(--ink)}

a:focus-visible,.sitename:focus-visible{
  outline:1px solid var(--ink);outline-offset:4px;border-radius:1px}

@media(max-width:600px){
  body{font-size:17px;line-height:1.85}
  .wrap{padding:8vh 1.35rem 18vh}
  .index li{gap:1em}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
{{BODY}}
</div>
</body>
</html>
"""


def page(title, body):
    return (BASE.replace("{{TITLE}}", html.escape(title))
                .replace("{{SITE}}", html.escape(SITE_TITLE))
                .replace("{{BODY}}", body))


# ─────────────────────────────────────────────
#  生成
# ─────────────────────────────────────────────

def gap_for(days):
    return int(max(GAP_MIN, min(GAP_MAX, round(days * DAYS_TO_PX))))


def build():
    if not os.path.isdir(POSTS_DIR):
        os.makedirs(POSTS_DIR)

    posts = []
    for f in sorted(os.listdir(POSTS_DIR)):
        if f.endswith(".md") and not f.startswith(("_", ".")):
            posts.append(Post(os.path.join(POSTS_DIR, f)))
    posts.sort(key=lambda p: p.date, reverse=True)

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    # 首页
    rows, last_year, prev = [], None, None
    for p in posts:
        if p.date.year != last_year:
            rows.append('<li class="year">%d</li>' % p.date.year)
            last_year = p.date.year
            style = ""
        else:
            style = ' style="margin-top:%dpx"' % gap_for((prev.date - p.date).days)
        rows.append(
            '<li%s><time datetime="%s">%s</time>'
            '<a href="%s">%s</a></li>' % (
                style, p.date.isoformat(), p.date.strftime("%m.%d"),
                p.url, html.escape(p.display_title)))
        prev = p

    home = ('<span class="sitename">%s</span>\n<ul class="index">\n%s\n</ul>'
            % (html.escape(SITE_TITLE), "\n".join(rows)))
    if not posts:
        home = ('<span class="sitename">%s</span>\n'
                '<p style="color:var(--ink-faint)">还没有东西。'
                '在 posts/ 里放一个 .md 文件，再跑一次 build.py。</p>'
                % html.escape(SITE_TITLE))
    write(os.path.join(OUT_DIR, "index.html"), page(SITE_TITLE, home))

    # 文章页
    for p in posts:
        body = (
            '<a class="sitename" href="/">%s</a>\n'
            '<article>\n<h1>%s</h1>\n'
            '<p class="dateline">%s</p>\n%s\n</article>\n'
            '<p class="foot"><a href="/">← 回到目录</a></p>'
            % (html.escape(SITE_TITLE), html.escape(p.display_title),
               p.date.strftime("%Y.%m.%d"), p.html))
        d = os.path.join(OUT_DIR, p.slug)
        os.makedirs(d, exist_ok=True)
        write(os.path.join(d, "index.html"),
              page("%s — %s" % (p.display_title, SITE_TITLE), body))

    # static/ 里的东西原样拷进去（图片、favicon 之类）
    if os.path.isdir(STATIC_DIR):
        for name in os.listdir(STATIC_DIR):
            src = os.path.join(STATIC_DIR, name)
            dst = os.path.join(OUT_DIR, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    # RSS
    write(os.path.join(OUT_DIR, "feed.xml"), rss(posts))

    print("好了：%d 篇 → %s/" % (len(posts), OUT_DIR))


def rss(posts):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in posts[:30]:
        pub = datetime(p.date.year, p.date.month, p.date.day,
                       12, tzinfo=timezone.utc)
        items.append(
            "<item>\n<title>%s</title>\n<link>%s%s</link>\n"
            "<guid isPermaLink=\"true\">%s%s</guid>\n"
            "<pubDate>%s</pubDate>\n"
            "<description><![CDATA[%s]]></description>\n</item>"
            % (html.escape(p.display_title), SITE_URL, p.url,
               SITE_URL, p.url,
               pub.strftime("%a, %d %b %Y %H:%M:%S +0000"),
               p.html.replace("]]>", "]]&gt;")))
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
        '<title>%s</title>\n<link>%s/</link>\n'
        '<atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>\n'
        '<description>%s</description>\n<language>zh-cn</language>\n'
        '<lastBuildDate>%s</lastBuildDate>\n%s\n</channel>\n</rss>\n'
        % (html.escape(SITE_TITLE), SITE_URL, SITE_URL,
           html.escape(DESCRIPTION or SITE_TITLE), now, "\n".join(items)))


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def new(title=""):
    """python3 build.py new [标题]  →  新建一篇今天的草稿"""
    today = date.today().isoformat()
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", title).strip("-")
    path = os.path.join(POSTS_DIR, "%s-%s.md" % (today, slug))
    if os.path.exists(path):
        print("已经有这个文件了：" + path)
        return
    os.makedirs(POSTS_DIR, exist_ok=True)
    head = "title: %s\ndate: %s\n\n" % (title, today) if title \
        else "date: %s\n\n" % today
    write(path, head)
    print(path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "new":
        new(" ".join(sys.argv[2:]))
    else:
        build()
