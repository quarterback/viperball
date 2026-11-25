"""Browser capture of actual in-process app responses with Playwright Chromium.

No fake HTML or fabricated standings. Route through the real FastAPI app so
screenshots are reproducible and production saves are not touched.
"""
from pathlib import Path
import json
import os
import random
import shutil
import sys
import tempfile
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def run():
    from fastapi.testclient import TestClient
    from playwright.sync_api import sync_playwright
    out=ROOT/"reports"/"ui-polish"
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["VIPERBALL_DB_PATH"]=str(Path(tmp)/"ui.db")
        import api.main as api
        random.seed(20261125)
        source=sorted((ROOT/"data"/"teams").glob("*.json"))
        selected=[source[round(i*(len(source)-1)/15)] for i in range(16)]
        league=Path(tmp)/"teams"; league.mkdir()
        names=[]
        for path in selected:
            shutil.copy(path,league/path.name)
            info=json.loads(path.read_text())["team_info"]
            names.append(info.get("school") or info["school_name"])
        api.TEAMS_DIR=str(league)
        client=TestClient(api.app)
        sid=client.post("/sessions",json={}).json()["session_id"]
        base=f"/sessions/{sid}"
        client.post(base+"/season",json={"name":"UI verification season","ai_seed":20261125,
            "human_teams":[names[0]],"games_per_team":12,"playoff_size":4,"bowl_count":0,
            "conferences":{"East":names[:8],"West":names[8:]}}).raise_for_status()
        client.post(base+"/season/portal/skip").raise_for_status()
        result=client.post(base+"/season/simulate-week",json={})
        result.raise_for_status()
        week=result.json()["week"]
        prefix=f"/stats/college/{sid}"
        pages={"home":"/stats/","season":prefix+"/",
            "schedule":prefix+"/schedule?week="+str(week),
            "team":prefix+"/team/"+quote(names[0],safe=""),
            "coach":prefix+"/coach/"+quote(names[0],safe="")+"/head_coach",
            "game":prefix+"/game/"+str(week)+"/0",
            "luck":prefix+"/luck","my-team":"/stats/my-team/"}
        report=[]
        with sync_playwright() as pw:
            configs=[("chromium","viperball",1440,960),("chromium","viperball",390,844),
                ("chromium","bloomberg",1440,960),("webkit","viperball",320,700),
                ("webkit","viperball",390,844),("webkit","sand",430,932)]
            for engine,theme,width,height in configs:
                browser=getattr(pw,engine).launch()
                context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1,
                    is_mobile=width<=768,has_touch=width<=768)
                context.add_init_script("localStorage.setItem('vb-theme',"+json.dumps(theme)+")")
                def route_request(route):
                    request=route.request
                    if request.url.startswith("http://testserver"):
                        resp=client.request(request.method,request.url,follow_redirects=True)
                        headers={k:v for k,v in resp.headers.items() if k.lower() not in ("content-length","content-encoding","transfer-encoding")}
                        route.fulfill(status=resp.status_code,headers=headers,body=resp.content)
                    else:
                        # Self-hosted fonts are the documented fallback.
                        route.abort()
                context.route("**/*",route_request)
                page=context.new_page()
                for label,path in pages.items():
                    response=page.goto("http://testserver"+path,wait_until="load")
                    assert response is not None and response.ok,(label,response.status if response else None)
                    page.locator("h1").first.wait_for()
                    page.evaluate("document.fonts.ready")
                    assert page.locator("html").get_attribute("data-theme")==theme
                    page.screenshot(path=str(out/f"{label}-{engine}-{theme}-{width}.png"),full_page=False)
                    overflow=page.evaluate("Math.max(0,document.documentElement.scrollWidth-window.innerWidth)")
                    report.append({"page":label,"browser":engine,"theme":theme,"viewport":width,"horizontal_overflow_px":overflow})
                    if label in ("season","schedule") and width<=768:
                        assert overflow<=1,(label,engine,width,overflow)
                        nav=page.locator(".mobile-section-nav").first
                        assert nav.is_visible()
                        assert nav.bounding_box()["height"]<=50
                        assert nav.get_by_role("link",name="Overview",exact=True).is_visible()
                        assert nav.get_by_role("link",name="Schedule",exact=True).is_visible()
                        active=nav.locator('a[aria-current="page"]').first
                        assert active.is_visible()
                        assert active.inner_text()==("Schedule" if label=="schedule" else "Overview")
                        assert not page.locator(".tabs-wrapper.has-mobile-sections > .tabs").first.is_visible()
                        nav.locator("summary").click()
                        assert nav.get_by_role("link",name="Players",exact=True).is_visible()
                        assert nav.get_by_role("link",name="Data",exact=True).count()==1
                        page.keyboard.press("Escape")
                        assert not nav.locator("details").evaluate("(el)=>el.open")
                        assert "games played" not in page.locator(".page-header").first.inner_text()
                    if label=="schedule" and width<=768:
                        row=page.locator(".matchup-row").first
                        assert row.is_visible()
                        for selector in (".matchup-away",".matchup-away-score",".matchup-home",".matchup-home-score",".matchup-box"):
                            cell=row.locator(selector)
                            assert cell.is_visible(),selector
                            box=cell.bounding_box()
                            assert box["x"]>=0 and box["x"]+box["width"]<=width+1,(selector,box,width)
                        assert row.locator(".matchup-away").bounding_box()["y"] < row.locator(".matchup-home").bounding_box()["y"]
                        assert abs(row.locator(".matchup-away-score").bounding_box()["x"]-row.locator(".matchup-home-score").bounding_box()["x"])<=1
                        assert row.locator(".matchup-box a").get_attribute("href").startswith(prefix+"/game/")
                        assert page.locator("#schedule-week").input_value()==str(week)
                        page.locator("#schedule-week").select_option("0")
                        page.locator(".schedule-filter button").click()
                        page.wait_for_url("**/schedule?week=0")
                        assert page.locator("#schedule-week").input_value()=="0"
                    if label=="home":
                        header=page.locator("th.sortable").first
                        header.focus()
                        page.keyboard.press("Enter")
                        assert header.get_attribute("aria-sort") in ("ascending","descending")
                context.close()
                browser.close()
        (out/"observations.json").write_text(json.dumps(report,indent=2))

if __name__=="__main__":
    run()
