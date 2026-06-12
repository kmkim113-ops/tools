# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_HTML = os.path.join(BASE_DIR, "foreign_flow.html")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://finance.naver.com/",
}

def fetch_list(url, pages=2):
    items = []
    for page in range(1, pages + 1):
        try:
            res = requests.get(f"{url}&page={page}", headers=HEADERS, timeout=15)
            res.encoding = "euc-kr"
            soup = BeautifulSoup(res.text, "html.parser")

            # 모든 테이블 시도
            table = soup.find("table", {"class": "type_2"})
            if not table:
                table = soup.find("table")
            if not table:
                print(f"  ⚠️ 페이지{page} 테이블 없음, 상태코드={res.status_code}")
                continue

            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                if len(tds) < 5:
                    continue
                name_tag = row.find("a")
                if not name_tag:
                    continue

                name = name_tag.text.strip()
                href = name_tag.get("href", "")
                code = href.split("code=")[-1].split("&")[0] if "code=" in href else ""

                texts = [td.text.strip().replace(",", "").replace("%", "").replace("+", "") for td in tds]

                try:
                    cur_price = int(texts[1]) if texts[1].lstrip("-").isdigit() else 0
                except:
                    cur_price = 0

                try:
                    change_pct = float(texts[3]) if texts[3].replace(".", "").replace("-", "").isdigit() else 0.0
                except:
                    change_pct = 0.0

                # 등락 방향
                td2_html = str(tds[2])
                if "상승" in td2_html or 'class="up"' in td2_html or "red" in td2_html:
                    direction = "up"
                    change_pct = abs(change_pct)
                elif "하락" in td2_html or 'class="dn"' in td2_html or "blue" in td2_html:
                    direction = "down"
                    change_pct = -abs(change_pct)
                else:
                    direction = "flat"

                try:
                    net_amt = int(texts[5]) if texts[5].lstrip("-").isdigit() else 0
                except:
                    net_amt = 0

                if name and code:
                    items.append({
                        "name": name, "code": code,
                        "cur_price": cur_price, "change_pct": change_pct,
                        "direction": direction, "net_amt": abs(net_amt),
                    })
        except Exception as e:
            print(f"  페이지{page} 오류: {e}")
    return items

def fetch_all():
    print("📡 데이터 수집 중...")
    buy_list  = fetch_list("https://finance.naver.com/sise/foreign_buy.naver?sosok=0")[:20]
    sell_list = fetch_list("https://finance.naver.com/sise/foreign_sell.naver?sosok=0")[:20]
    print(f"  ✅ 순매수 {len(buy_list)}개 / 순매도 {len(sell_list)}개")
    return buy_list, sell_list

def cards_html(items, tab):
    if not items:
        return "<div class='empty'>데이터 없음</div>"
    max_amt = max((i["net_amt"] for i in items), default=1) or 1
    html = ""
    for idx, item in enumerate(items, 1):
        pct = item["change_pct"]
        d = item["direction"]
        sign = "+" if d == "up" else ""
        arrow = "▲" if d == "up" else "▼" if d == "down" else "–"
        bar_w = max(4, round((item["net_amt"] / max_amt) * 48))
        amt = item["net_amt"]
        amt_s = f"{amt/100:.1f}억" if amt >= 100 else f"{amt}백만"
        price_s = f"{item['cur_price']:,}원" if item["cur_price"] else "–"
        label = "순매수" if tab == "buy" else "순매도"
        url = f"https://finance.naver.com/item/main.naver?code={item['code']}"
        html += f"""
        <div class="card" onclick="window.open('{url}','_blank')">
          <div class="rank">{idx}</div>
          <div class="card-info">
            <div class="stock-name">{item['name']}</div>
            <div class="stock-meta">{price_s} · {label} {amt_s}</div>
            <div class="bar-wrap"><div class="bar-fill {d}" style="width:{bar_w}px"></div></div>
          </div>
          <div class="card-right">
            <div class="price-change {d}">{sign}{pct:.2f}%</div>
            <div class="net-amount">{arrow} 등락</div>
          </div>
        </div>"""
    return html

def build_html(buy_list, sell_list, date_str, time_str):
    bc = cards_html(buy_list, "buy")
    sc = cards_html(sell_list, "sell")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>외국인 수급 {date_str}</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  :root{{--bg:#0d1117;--surface:#161b22;--surface2:#1c2230;--border:#30363d;
    --buy:#1eba6a;--buy-dim:#0d3d25;--sell:#f85149;--sell-dim:#3d1515;
    --text:#e6edf3;--text-dim:#8b949e;--accent:#58a6ff;
    --font:'Apple SD Gothic Neo','Noto Sans KR',sans-serif}}
  body{{background:var(--bg);color:var(--text);font-family:var(--font);padding:12px}}
  header{{display:flex;justify-content:space-between;align-items:center;padding:12px 4px 16px}}
  header h1{{font-size:17px;font-weight:700}}
  .date-badge{{font-size:12px;color:var(--text-dim);background:var(--surface2);padding:4px 10px;border-radius:20px;border:1px solid var(--border)}}
  .update-bar{{display:flex;align-items:center;gap:8px;margin-bottom:14px;padding:10px 12px;background:var(--surface);border-radius:10px;border:1px solid var(--border)}}
  .update-bar span{{font-size:12px;color:var(--text-dim);flex:1}}
  .update-time{{color:var(--accent)!important;font-weight:600!important}}
  .tabs{{display:flex;gap:6px;margin-bottom:14px}}
  .tab{{flex:1;padding:10px 0;text-align:center;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;border:1.5px solid var(--border);background:var(--surface);color:var(--text-dim)}}
  .tab.buy.active{{background:var(--buy-dim);border-color:var(--buy);color:var(--buy)}}
  .tab.sell.active{{background:var(--sell-dim);border-color:var(--sell);color:var(--sell)}}
  .section-label{{font-size:11px;color:var(--text-dim);margin-bottom:8px;padding-left:2px}}
  .card-list{{display:flex;flex-direction:column;gap:8px}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:13px 14px;display:flex;align-items:center;gap:12px;cursor:pointer}}
  .card:active{{background:var(--surface2)}}
  .rank{{font-size:12px;color:var(--text-dim);width:18px;text-align:center;flex-shrink:0}}
  .card-info{{flex:1;min-width:0}}
  .stock-name{{font-size:14px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .stock-meta{{font-size:11px;color:var(--text-dim);margin-top:3px}}
  .card-right{{text-align:right;flex-shrink:0}}
  .price-change{{font-size:15px;font-weight:700}}
  .price-change.up{{color:var(--buy)}}.price-change.down{{color:var(--sell)}}.price-change.flat{{color:var(--text-dim)}}
  .net-amount{{font-size:11px;color:var(--text-dim);margin-top:2px}}
  .bar-wrap{{width:48px;height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:5px}}
  .bar-fill{{height:100%;border-radius:2px}}.bar-fill.up{{background:var(--buy)}}.bar-fill.down{{background:var(--sell)}}
  .panel{{display:none}}.panel.active{{display:block}}
  .notice{{font-size:11px;color:var(--text-dim);text-align:center;margin-top:14px;line-height:1.6}}
  .empty{{text-align:center;padding:40px;color:var(--text-dim);font-size:13px}}
</style>
</head>
<body>
<header>
  <h1>🌏 외국인 수급</h1>
  <span class="date-badge">{date_str}</span>
</header>
<div class="update-bar">
  <span>장 마감 후 자동 업데이트</span>
  <span class="update-time">✓ {time_str} 기준</span>
</div>
<div class="tabs">
  <div class="tab buy active" onclick="switchTab('buy')">▲ 순매수</div>
  <div class="tab sell" onclick="switchTab('sell')">▼ 순매도</div>
</div>
<div id="buy-panel" class="panel active">
  <div class="section-label">외국인 순매수 상위 TOP {len(buy_list)}</div>
  <div class="card-list">{bc}</div>
</div>
<div id="sell-panel" class="panel">
  <div class="section-label">외국인 순매도 상위 TOP {len(sell_list)}</div>
  <div class="card-list">{sc}</div>
</div>
<p class="notice">※ 네이버 금융 기준 · 종목 탭하면 네이버 주식으로 이동<br>※ 등락률은 당일 종가 기준</p>
<script>
function switchTab(t){{
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(e=>e.classList.remove('active'));
  document.querySelector('.tab.'+t).classList.add('active');
  document.getElementById(t+'-panel').classList.add('active');
}}
</script>
</body>
</html>"""

def main():
    kst = datetime.utcnow() + timedelta(hours=9)
    date_str = kst.strftime("%Y.%m.%d")
    time_str = kst.strftime("%H:%M")
    buy_list, sell_list = fetch_all()
    html = build_html(buy_list, sell_list, date_str, time_str)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 저장 완료: {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
