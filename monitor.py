import asyncio, json, os
from datetime import datetime
from playwright.async_api import async_playwright

PRODUCTS = [
    {"id":1,  "url":"https://limestore.com/ru_ru/product/314644952374-raznocvetnyi", "name":"Шарф разноцветный"},
    {"id":2,  "url":"https://limestore.com/ru_ru/product/249815672638-svetlozeltyi", "name":"Футболка светло-желтая"},
    {"id":3,  "url":"https://limestore.com/ru_ru/product/314072896690-temnosinii", "name":"Джемпер темно-синий"},
    {"id":4,  "url":"https://limestore.com/ru_ru/product/314072896690-belyi", "name":"Джемпер белый"},
    {"id":5,  "url":"https://limestore.com/ru_ru/product/308423519779-cvetslonovoikosti", "name":"Платье слоновая кость"},
    {"id":6,  "url":"https://limestore.com/ru_ru/product/318974526270-pudrovobezevyi", "name":"Платье пудрово-бежевое"},
    {"id":7,  "url":"https://limestore.com/ru_ru/product/279547411970-sirenevorozovyi", "name":"Жилет сиренево-розовый"},
    {"id":8,  "url":"https://limestore.com/ru_ru/product/262675341542-seryi", "name":"Пуховик серый"},
    {"id":9,  "url":"https://limestore.com/ru_ru/product/275880767542-cernyi", "name":"Куртка черная"},
    {"id":10, "url":"https://limestore.com/ru_ru/product/295672443076-svetlorozovyi", "name":"Топ светло-розовый"},
    {"id":11, "url":"https://limestore.com/ru_ru/product/300853205578-svetlorozovyi", "name":"Топ светло-розовый"},
    {"id":12, "url":"https://limestore.com/ru_ru/product/269439187542-rozovyi", "name":"Кардиган розовый"},
    {"id":13, "url":"https://limestore.com/ru_ru/product/290241733102-vintaznyisinii", "name":"Джинсы винтажный синий"},
    {"id":14, "url":"https://limestore.com/ru_ru/product/254396692487-belyi", "name":"Футболка белая"},
    {"id":15, "url":"https://limestore.com/ru_ru/product/290258356102-svetlosinii", "name":"Джинсы светло-синие"},
    {"id":16, "url":"https://limestore.com/ru_ru/product/271827792316-iarkorozovyi", "name":"Топ ярко-розовый"},
    {"id":17, "url":"https://limestore.com/ru_ru/product/296693089694-molocnyi", "name":"Топ молочный"},
    {"id":18, "url":"https://limestore.com/ru_ru/product/298273095694-svetlorozovyi", "name":"Топ светло-розовый"},
    {"id":19, "url":"https://limestore.com/ru_ru/product/252956558160-krasnooranzevyi", "name":"Футболка красно-оранжевая"},
    {"id":20, "url":"https://limestore.com/ru_ru/product/257175794477-kamennyi", "name":"Брюки каменный цвет"},
    {"id":21, "url":"https://limestore.com/ru_ru/product/257215792477-kamennyi", "name":"Джоггеры каменный цвет"},
    {"id":22, "url":"https://limestore.com/ru_ru/product/311915080010-pylnolilovyi", "name":"Платье пыльно-лиловое"},
    {"id":23, "url":"https://limestore.com/ru_ru/product/310905079010-pylnolilovyi", "name":"Джемпер пыльно-лиловый"},
    {"id":24, "url":"https://limestore.com/ru_ru/product/304303443010-pylnolilovyi", "name":"Джемпер №304303"},
    {"id":25, "url":"https://limestore.com/ru_ru/product/304293442010-pylnolilovyi", "name":"Джемпер пыльно-лиловый"},
    {"id":26, "url":"https://limestore.com/ru_ru/product/306172667980-indigo", "name":"Джинсы индиго"},
    {"id":27, "url":"https://limestore.com/ru_ru/product/306162666980-indigo", "name":"Джинсы индиго"},
]

PREV_FILE = "prev_data.json"

async def parse_product(page, p):
    r = {"id": p["id"], "url": p["url"], "name": p.get("name", ""), "img": "",
         "price_orig": "", "price_curr": "", "in_stock": False, "sizes": [], "error": False}
    try:
        await page.goto(p["url"], timeout=40000, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        if not r["name"]:
            for sel in ["h1", "[class*='title']", "[class*='name']"]:
                try:
                    r["name"] = (await page.locator(sel).first.inner_text(timeout=3000)).strip()
                    if r["name"]: break
                except: pass
        try:
            r["img"] = await page.locator("img[class*='photo'], img[class*='image'], img[class*='product']").first.get_attribute("src", timeout=3000)
        except: pass
        for sel in ["[class*='old'], [class*='crossed'], [class*='before'], [class*='original']"]:
            try:
                t = await page.locator(sel).first.inner_text(timeout=2000)
                r["price_orig"] = t.replace("\u00a0","").replace(" ","").replace("₽","").strip()
                if r["price_orig"]: break
            except: pass
        for sel in ["[class*='current'], [class*='sale'], [class*='discount'], [class*='actual']", "[class*='price']"]:
            try:
                t = await page.locator(sel).first.inner_text(timeout=2000)
                cleaned = t.replace("\u00a0","").replace(" ","").replace("₽","").strip()
                if cleaned.isdigit():
                    r["price_curr"] = cleaned
                    break
            except: pass
        try:
            els = await page.locator("[class*='size']").all()
            available = []
            for el in els:
                txt = (await el.inner_text()).strip()
                if not txt or len(txt) > 15: continue
                cls = (await el.get_attribute("class")) or ""
                dis = await el.get_attribute("disabled")
                aria = await el.get_attribute("aria-disabled")
                if dis is None and aria != "true" and "unavail" not in cls and "disable" not in cls and "sold" not in cls:
                    available.append(txt)
            r["sizes"] = available
            r["in_stock"] = len(available) > 0
        except: pass
        if not r["sizes"]:
            try:
                r["in_stock"] = await page.locator("[class*='add-to-cart'], [class*='buy-btn'], button[class*='cart']").first.is_enabled(timeout=3000)
            except:
                r["in_stock"] = False
    except Exception as e:
        r["error"] = True
        if not r["name"]:
            r["name"] = p["url"].split("/")[-1]
    return r

def load_prev():
    if os.path.exists(PREV_FILE):
        with open(PREV_FILE, encoding="utf-8") as f:
            return {str(x["id"]): x for x in json.load(f)}
    return {}

def save_current(data):
    with open(PREV_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_changes(prev, curr):
    changes = []
    p = prev.get(str(curr["id"]))
    if not p:
        return changes
    try:
        if p.get("price_curr") and curr["price_curr"] and p["price_curr"] != curr["price_curr"]:
            ov, nv = int(p["price_curr"]), int(curr["price_curr"])
            arrow = "↓" if nv < ov else "↑"
            changes.append({"type": "price", "text": f"Цена {arrow}: {ov} → {nv} ₽", "dir": "down" if nv < ov else "up"})
    except: pass
    if p.get("in_stock") != curr["in_stock"]:
        if curr["in_stock"]:
            changes.append({"type": "stock", "text": "Появился в наличии", "dir": "new"})
        else:
            changes.append({"type": "stock", "text": "Пропал из наличия", "dir": "gone"})
    ps, cs = set(p.get("sizes", [])), set(curr.get("sizes", []))
    if ps != cs:
        added = cs - ps
        removed = ps - cs
        if added:   changes.append({"type": "sizes", "text": f"+ размеры: {', '.join(sorted(added))}", "dir": "sizes"})
        if removed: changes.append({"type": "sizes", "text": f"− размеры: {', '.join(sorted(removed))}", "dir": "sizes"})
    return changes
    def build_html(results, prev, dt_str):
    total = len(results)
    in_stock = sum(1 for r in results if r["in_stock"])
    out_stock = total - in_stock
    all_changes = [(r, get_changes(prev, r)) for r in results]
    changed_count = sum(1 for _, ch in all_changes if ch)
    ch_items = ""
    for r, ch in all_changes:
        for c in ch:
            name = r["name"] or r["url"].split("/")[-1]
            ch_items += f'>#{r["id"]} <a href="{r["url"]}" target="_blank">{name}</a> — {c["text"]}</li>\n'
    changes_block = f"<ul>{ch_items}</ul>" if ch_items else '<p class="no-changes">Изменений не обнаружено</p>'
    rows = ""
    for r, ch in all_changes:
        row_cls = "" if r["in_stock"] else "out-of-stock"
        stock_badge = ('<span class="badge in-stock">В наличии</span>' if r["in_stock"] else '<span class="badge out-of-stock">Нет в наличии</span>')
        sizes_str = ", ".join(r["sizes"]) if r["sizes"] else "—"
        badges = ""
        for c in ch:
            cls_map = {"down":"change-down","up":"change-up","new":"stock-new","gone":"stock-gone","sizes":"stock-sizes"}
            badges += f'<span class="badge {cls_map.get(c["dir"],"stock-sizes")}">{c["text"]}</span> '
        img_tag = f'<img src="{r["img"]}" class="thumb" alt="" loading="lazy">' if r["img"] else ""
        orig_tag = f'<div class="price-orig">{r["price_orig"]} ₽</div>' if r["price_orig"] else ""
        curr_tag = f'<div class="price-curr">{r["price_curr"]} ₽</div>' if r["price_curr"] else "—"
        err_tag = ' <span style="color:#ff3b30;font-size:11px">(ошибка)</span>' if r["error"] else ""
        name_val = r["name"] or r["url"].split("/")[-1]
        rows += f"""<tr class="{row_cls}"><td class="num">{r["id"]}</td><td class="thumb-cell"><a href="{r["url"]}" target="_blank">{img_tag}</a></td><td><a href="{r["url"]}" target="_blank">{name_val}</a>{err_tag}</td><td>{orig_tag}</td><td>{curr_tag}</td><td>{stock_badge}</td><td class="sizes">{sizes_str}</td><td>{badges}</td></tr>\n"""
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>LIME {dt_str}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f7;color:#1d1d1f;padding:24px}}.container{{max-width:1300px;margin:0 auto}}h1{{font-size:24px;font-weight:600;margin-bottom:4px}}.subtitle{{color:#86868b;font-size:14px;margin-bottom:20px}}.stats{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}.stat-card{{background:#fff;border-radius:12px;padding:16px 20px;flex:1;min-width:140px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}.stat-card .label{{font-size:12px;color:#86868b;text-transform:uppercase;letter-spacing:.5px}}.stat-card .value{{font-size:28px;font-weight:600;margin-top:4px}}.value.green{{color:#34c759}}.value.red{{color:#ff3b30}}.value.blue{{color:#007aff}}.changes{{background:#fff;border-radius:12px;padding:16px 20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}.changes h2{{font-size:16px;font-weight:600;margin-bottom:10px}}.changes ul{{list-style:none;padding:0}}.changes li{{padding:6px 0;font-size:14px;border-bottom:1px solid #f0f0f0}}.changes li:last-child{{border:none}}.no-changes{{color:#86868b;font-size:14px}}table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}th{{background:#1d1d1f;color:#fff;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;padding:12px 8px;text-align:left;white-space:nowrap}}td{{padding:8px;font-size:13px;border-bottom:1px solid #f0f0f0;vertical-align:middle}}tr:last-child td{{border-bottom:none}}tr:hover{{background:#fafafa}}tr.out-of-stock{{background:#fafafa}}tr.out-of-stock td{{color:#86868b}}tr.out-of-stock td a{{color:#86868b}}a{{color:#007aff;text-decoration:none}}a:hover{{text-decoration:underline}}.badge{{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:500;white-space:nowrap}}.badge.in-stock{{background:#e8f8ec;color:#1b7d36}}.badge.out-of-stock{{background:#fef0ef;color:#d63031}}.badge.change-down{{background:#e8f8ec;color:#1b7d36}}.badge.change-up{{background:#fef0ef;color:#d63031}}.badge.stock-new{{background:#e8f8ec;color:#1b7d36}}.badge.stock-gone{{background:#fef0ef;color:#d63031}}.badge.stock-sizes{{background:#fff3e0;color:#e65100}}.price-orig{{color:#86868b;text-decoration:line-through;font-size:12px}}.price-curr{{font-weight:600}}.sizes{{font-size:12px;color:#555}}.thumb{{width:56px;height:72px;object-fit:cover;border-radius:6px;display:block}}.thumb-cell{{width:64px;padding:6px 8px}}td.num{{text-align:center;width:32px;font-weight:500;color:#86868b}}</style>
</head><body><div class="container"><h1>LIME — Мониторинг товаров</h1><p class="subtitle">{dt_str}</p>
<div class="stats"><div class="stat-card"><div class="label">Всего товаров</div><div class="value blue">{total}</div></div><div class="stat-card"><div class="label">В наличии</div><div class="value green">{in_stock}</div></div><div class="stat-card"><div class="label">Нет в наличии</div><div class="value red">{out_stock}</div></div><div class="stat-card"><div class="label">Изменения</div><div class="value blue">{changed_count}</div></div></div>
<div class="changes"><h2>Изменения за сегодня</h2>{changes_block}</div>
<table><thead><tr><th>№</th><th></th><th>Товар</th><th>Было</th><th>Цена</th><th>Статус</th><th>Размеры</th><th>Изменения</th></tr></thead><tbody>{rows}</tbody></table></div></body></html>"""

async def main():
    prev = load_prev()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        results = []
        for prod in PRODUCTS:
            print(f"Проверка #{prod['id']}...")
            r = await parse_product(page, prod)
            results.append(r)
        await browser.close()
    now = datetime.now()
    dt_str = now.strftime("%d.%m.%Y %H:%M МСК")
    html = build_html(results, prev, dt_str)
    fname = f"lime_report_{now.strftime('%Y%m%d_%H%M')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Отчёт сохранён: {fname}")
    save_current(results)

if __name__ == "__main__":
    asyncio.run(main())
