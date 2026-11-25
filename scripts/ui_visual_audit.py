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
        result=client.post(base+"/season/simulate-week",json={})
        result.raise_for_status()
        week=result.json()["week"]
        prefix=f"/stats/college/{sid}"
        pages={"home":"/stats/","season":prefix+"/",
            "team":prefix+"/team/"+quote(names[0],safe=""),
            "coach":prefix+"/coach/"+quote(names[0],safe="")+"/head_coach",
            "game":prefix+"/game/"+str(week)+"/0",
            "luck":prefix+"/luck","my-team":"/stats/my-team/"}
        report=[]
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for theme,width,height in [("viperball",1440,960),("viperball",390,844),("bloomberg",1440,960)]:
                context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1)
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
                    page.screenshot(path=str(out/f"{label}-{theme}-{width}.png"),full_page=False)
                    overflow=page.evaluate("Math.max(0,document.documentElement.scrollWidth-window.innerWidth)")
                    report.append({"page":label,"theme":theme,"viewport":width,"horizontal_overflow_px":overflow})
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
