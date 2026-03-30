import asyncio, json, os
from datetime import datetime
from playwright.async_api import async_playwright

PRODUCTS = [
    {"id":1, "url":"https://limestore.com/ru_ru/product/314644952374-raznocvetnyj", "name":"Фарб разноцветный"},
    {"id":2, "url":"https://limestore.com/ru_ru/product/249815672638-svetlozeltyj", "name":"Футболка светло-желтая"},
    {"id":3, "url":"https://limestore.com/ru_ru/product/314072896698-temno-sinij", "name":"Джемпер темно-синий"},
    {"id":4, "url":"https://limestore.com/ru_ru/product/314072896690-belyj", "name":"Джемпер белый"},
    {"id":5, "url":"https://limestore.com/ru_ru/product/308423519779-cvetslonovjskosti", "name":"Платье слоновая кость"},
    {"id":6, "url":"https://limestore.com/ru_ru/product/318974526270-pudrovocherezovyj", "name":"Платье пудрово-бежевое"},
    {"id":7, "url":"https://limestore.com/ru_ru/product/279547411970-sirenevojrozovyj", "name":"Жилет сиренево-розовый"},
    {"id":8, "url":"https://limestore.com/ru_ru/product/262675341542-seryj", "name":"Худож серый"},
    {"id":9, "url":"https://limestore.com/ru_ru/product/275080767542-cernyj", "name":"Куртка черная"},
    {"id":10, "url":"https://limestore.com/ru_ru/product/295672443076-svetlorozovyj", "name":"Топ светло-розовый"},
    {"id":11, "url":"https://limestore.com/ru_ru/product/308053280570-svetlorozovyj", "name":"Топ светло-розовый"},
    {"id":12, "url":"https://limestore.com/ru_ru/product/269439187542-rozovyj", "name":"Кардиган розовый"},
    {"id":13, "url":"https://limestore.com/ru_ru/product/290241733102-vintazhyisinii", "name":"Джинсы винтажный синий"},
    {"id":14, "url":"https://limestore.com/ru_ru/product/251396692487-belyj", "name":"Футболка белая"},
    {"id":15, "url":"https://limestore.com/ru_ru/product/290250356102-svetlosinii", "name":"Джинсы светло-синие"},
    {"id":16, "url":"https://limestore.com/ru_ru/product/271827792316-larlorozovyj", "name":"Топ ярко-розовый"},
    {"id":17, "url":"https://limestore.com/ru_ru/product/296693089694-molocnyj", "name":"Топ молочный"},
    {"id":18, "url":"https://limestore.com/ru_ru/product/298273895694-svetlorozovyj", "name":"Топ светло-розовый"},
    {"id":19, "url":"https://limestore.com/ru_ru/product/252956556160-krasnooranzhevyj", "name":"Футболка красно-оранжевая"},
    {"id":20, "url":"https://limestore.com/ru_ru/product/257175794477-kamennyi", "name":"Брюки каменный цвет"},
    {"id":21, "url":"https://limestore.com/ru_ru/product/257215792477-kamennyi", "name":"Монтеры каменный цвет"},
    {"id":22, "url":"https://limestore.com/ru_ru/product/311915880010-pylolillovyj", "name":"Платье пыльно-лиловое"},
    {"id":23, "url":"https://limestore.com/ru_ru/product/310898790010-pylolillovyj", "name":"Джемпер пыльно-лиловый"},
    {"id":24, "url":"https://limestore.com/ru_ru/product/304303443010-pylolillovyj", "name":"Джемпер винтажный"},
    {"id":25, "url":"https://limestore.com/ru_ru/product/304293442010-pylolillovyj", "name":"Джемпер пыльно-лиловый"},
    {"id":26, "url":"https://limestore.com/ru_ru/product/306172667900-indigo", "name":"Джинсы индиго"},
    {"id":27, "url":"https://limestore.com/ru_ru/product/306162666900-indigo", "name":"Джинсы индиго"},
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
            r["img"] = await page.locator(".product-image img, [class*='image'] img").first.get_attribute("src", timeout=3000) or ""
        except: pass
        sel_price = ".product-price, [class*='price'], .price"
        price_els = await page.locator(sel_price).all()
        if price_els:
            texts = [await el.inner_text() for el in price_els]
            nums = []
            for t in texts:
                import re
                m = re.findall(r'\d[\d\s,.]*', t)
                if m:
                    nums.extend([x.replace(' ','').replace(',','.') for x in m if x.strip()])
            if nums:
                if len(nums)==1:
                    r["price_curr"] = nums[0]
                else:
                    r["price_orig"] = nums[0]
                    r["price_curr"] = nums[1]
        sel_stock = "[class*='stock'], [class*='available'], .in-stock, .availability"
        stock_els = await page.locator(sel_stock).all()
        if stock_els:
            stock_text = " ".join([await el.inner_text() for el in stock_els])
            r["in_stock"] = bool(stock_text and ("В наличии" in stock_text or "available" in stock_text.lower() or "stock" in stock_text.lower()))
        sel_size = "[class*='size'], .size-option, [class*='variant']"
        size_els = await page.locator(sel_size).all()
        if size_els:
            for el in size_els:
                txt = await el.inner_text()
                if txt.strip():
                    r["sizes"].append(txt.strip())
    except Exception as e:
        r["error"] = str(e)
    return r

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        results = []
        for p in PRODUCTS:
            res = await parse_product(page, p)
            results.append(res)
            print(f"[{p['id']}] {p.get('name','')} - Done")
        await browser.close()
    prev = {}
    if os.path.exists(PREV_FILE):
        with open(PREV_FILE) as f:
            prev_list = json.load(f)
            prev = {x["id"]:x for x in prev_list}
    with open(PREV_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>LIME Monitor {datetime.now().strftime("%Y-%m-%d %H:%M")}</title>
<style>
  body {{font-family:Arial,sans-serif;margin:20px;background:#f5f5f5;}}
  h1 {{color:#333;}}
  .product {{background:white;margin:10px 0;padding:15px;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.1);}}
  .product img {{max-width:150px;max-height:150px;float:left;margin-right:15px;}}
  .change {{color:red;font-weight:bold;}}
</style>
</head>
<body>
<h1>LIME Daily Monitor - {datetime.now().strftime("%Y-%m-%d %H:%M")}</h1>
"""
    for r in results:
        old = prev.get(r["id"])
        changes = []
        if old:
            if old.get("price_curr") != r["price_curr"]:
                changes.append(f"Цена: {old.get('price_curr','')} → {r['price_curr']}")
            if old.get("in_stock") != r["in_stock"]:
                changes.append(f"Наличие: {old.get('in_stock','')} → {r['in_stock']}")
            if set(old.get("sizes",[])) != set(r["sizes"]):
                changes.append(f"Размеры: {','.join(old.get('sizes',[]))} → {','.join(r['sizes'])}")
        change_html = "<div class='change'>" + "<br>".join(changes) + "</div>" if changes else ""
        html += f"""<div class='product'>
  {'<img src="'+r['img']+'">' if r['img'] else ''}
  <h3>{r['name']}</h3>
  <p><b>ID:</b> {r['id']} | <b>URL:</b> <a href="{r['url']}">{r['url']}</a></p>
  <p><b>Цена:</b> {r['price_orig']} → {r['price_curr']} | <b>В наличии:</b> {r['in_stock']}</p>
  <p><b>Размеры:</b> {', '.join(r['sizes']) if r['sizes'] else 'Не найдено'}</p>
  {change_html}
  {('<p style="color:red"><b>Error:</b> '+r['error']+'</p>') if r.get('error') else ''}
</div>
"""
    html += "</body></html>"
    with open("lime_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Report saved: lime_report.html")

if __name__ == "__main__":
    asyncio.run(main())
