"""Small semantic Playwright driver and authenticated API corroboration."""
from pathlib import Path
from playwright.sync_api import Page

class Driver:
    def __init__(self,page: Page, base_url: str, api_url: str | None):
        self.page=page
        self.base_url=base_url.rstrip('/')
        self.api_url=api_url.rstrip('/') if api_url else None
        self.logs=[]
        page.on('console',lambda m: self.logs.append(m.text[:300]) if m.type=='error' else None)
        page.on('pageerror',lambda e: self.logs.append(str(e)[:300]))

    def visit(self,path: str):
        self.page.goto(self.base_url+path,wait_until='domcontentloaded',timeout=15000)

    def enter_demo(self):
        self.visit('/')
        self.page.get_by_role('button',name='Enter Demo').click(timeout=8000)
        self.page.wait_for_url('**/dashboard',timeout=15000)
        self.page.get_by_role('heading',name='Your accounts').wait_for(timeout=15000)

    def api(self,path: str) -> dict:
        if not self.api_url:
            raise RuntimeError('API corroboration unavailable: supply --api-url')
        response=self.page.context.request.get(self.api_url+path,timeout=12000)
        if not response.ok:
            raise RuntimeError(f'API corroboration {path} HTTP {response.status}')
        return response.json()

    def screenshot(self,output_dir: Path,name: str) -> str:
        shots=output_dir/'screenshots'
        shots.mkdir(parents=True,exist_ok=True)
        path=shots/f'{name}.png'
        self.page.screenshot(path=str(path),full_page=True,timeout=10000)
        return f'screenshots/{name}.png'

    def dom(self) -> str:
        return self.page.locator('body').inner_text(timeout=5000)[:8000]
