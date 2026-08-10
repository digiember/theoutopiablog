# 无何有 — 使用说明

一个静态博客。零依赖，只要有 Python 3 就能跑，不用装任何东西。

## 三件事

**写一篇**

```
python3 build.py new "标题"
```

会在 `posts/` 里建好文件，用任何编辑器打开写就行。不想要标题的话，`build.py new` 后面什么都不加，首页会拿日期当标题。

**生成**

```
python3 build.py
```

`site/` 目录就是整个网站。双击 `site/index.html` 可以直接在浏览器里看。

**上线**

把 `site/` 目录扔到任何静态托管上。见下面「部署」。

## 配置

`build.py` 开头有几行，只需要改这些：

| | |
|---|---|
| `SITE_TITLE` | 站名 |
| `SITE_URL` | 已设为 https://theoutopia.com |
| `DAYS_TO_PX` | 首页留白的比例，见下 |

## 文章格式

文件开头可以写几行 `key: value`，然后空一行，然后正文：

```
title: 标题
date: 2026-08-09

正文从这里开始。
```

- `title` 可以不写
- `date` 不写的话，从文件名 `2026-08-09-xxx.md` 里取
- 文件名以 `_` 开头的会被跳过，可以当草稿用
- 支持的 Markdown：标题、粗斜体、链接、图片、列表、引用、代码块、分隔线。够用了。
- 图片放 `static/` 里，正文写 `![](/xxx.jpg)`。`static/` 里的东西每次生成会原样拷到站点根目录。（`site/` 每次会被清空重建，别往里面放东西。）

## 首页的留白

首页上两条之间的空白，等于它们相隔的天数。停更三个月，页面上就真的空三个月。这是故意的——空白本身是内容的一部分，不是缺口。

嫌太夸张就把 `DAYS_TO_PX` 调小，改成 `0` 就变成普通的等距列表。

## 部署

已配好 GitHub Actions（`.github/workflows/deploy.yml`）。推送到 `main` 分支就自动生成并发布，不用手动跑 build.py，也不用提交 `site/` 目录（已在 .gitignore 里）。

首次需要在仓库里做两件事：
1. Settings → Pages → Source 选 **GitHub Actions**（不是 Deploy from a branch）
2. Settings → Pages → Custom domain 填 `theoutopia.com`，保存

然后去 Cloudflare 加 DNS 记录：四条 A 记录（Name 填 `@`）指向 185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153，一条 CNAME（Name 填 `www`）指向 `你的用户名.github.io`。**每条记录的云朵图标都点成灰色**（DNS only），SSL/TLS 模式设成 Full。

证书签好后回 GitHub 勾上 Enforce HTTPS。

## 几件不做的事

没有统计代码、没有评论、没有分享按钮、没有相关文章推荐、没有标签。都是故意留空的。想知道有没有人看，页脚留个邮箱就够了。

RSS 在 `/feed.xml`，已经接好了。真正长期读你的那几个人是从这里来的。

## 收尾

`posts/` 里那四篇是示例，写完第一篇就删掉。
