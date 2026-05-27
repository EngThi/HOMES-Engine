const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');

const executablePath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ||
  execFileSync('which', ['chromium'], { encoding: 'utf8' }).trim();

const checks = [];
function ok(name, value) {
  checks.push([name, Boolean(value)]);
  console.log(`${value ? 'PASS' : 'FAIL'} ${name}`);
}

(async () => {
  const browser = await chromium.launch({
    executablePath,
    headless: true,
    args: ['--disable-dev-shm-usage', '--disable-gpu', '--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('https://54-162-84-165.sslip.io/engine-demo', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(1000);
  const text = await page.locator('body').textContent();
  ok('engine-demo title', text.includes('HOMES-Engine'));
  ok('engine-demo runtime', text.includes('runtime: modular capabilities loaded'));
  ok('engine-demo profile', text.includes('profile: default policy active'));
  ok('engine-demo mcp', text.includes('mcp: Hub tool surface online'));
  ok('engine-demo capability', text.includes('agent.profile_summary'));

  const profile = await (await page.request.get('https://homes.chefthi.hackclub.app/api/sensors/engine/profile')).json();
  ok('profile endpoint', profile.profile && profile.profile.id === 'default');
  ok('profile permissions', profile.profile && profile.profile.policy_summary && profile.profile.policy_summary.allow_count === 10);

  const projects = await (await page.request.get('https://homes.chefthi.hackclub.app/api/projects?type=render_video&limit=20')).json();
  const ids = projects.projects.map((project) => project.id);
  ok('hub pinned first', ids[0] === 'homes_ecosystem_cinematic_pinned');
  ok('hub hides old bad jobs', !['vid_1777826013780', 'vid_1777640382737', 'vid_1777578112832'].some((id) => ids.includes(id)));

  await browser.close();
  if (!checks.every(([, passed]) => passed)) process.exit(1);
})();
