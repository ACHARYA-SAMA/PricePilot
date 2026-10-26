/* Actual local-browser acceptance checks. Requires Playwright and Chromium. */
const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const path = require('node:path')

async function main() {
  const out = path.resolve(__dirname, '../output/verification/browser')
  await fs.mkdir(out, { recursive: true })
  const browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true })
  const page = await context.newPage()
  const evidence = { checks: [], consoleErrors: [], pageErrors: [], failedRequests: [], downloads: [], screenshots: [] }
  page.on('console', m => { if (m.type() === 'error') evidence.consoleErrors.push(m.text()) })
  page.on('pageerror', e => evidence.pageErrors.push(e.message))
  page.on('requestfailed', r => { if (!r.failure()?.errorText.includes('ERR_ABORTED')) evidence.failedRequests.push({ url: r.url(), error: r.failure()?.errorText }) })
  const shot = async name => { const file = name + '.png'; await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo({top:0,behavior:'instant'}) }); await page.waitForTimeout(100); await page.screenshot({ path: path.join(out,file), fullPage: true }); evidence.screenshots.push(file) }
  const route = async id => { await page.evaluate(id => { location.hash = '/' + id }, id); await page.locator('h1').waitFor(); await page.waitForTimeout(350) }
  const response = (endpoint, predicate = () => true) => page.waitForResponse(r => r.url().includes('/api/v1/' + endpoint) && r.request().method() === 'POST' && predicate(r), { timeout: 30000 })
  const postJson = async (pending, action) => {
    await action(); const r = await pending; assert.equal(r.status(),200,await r.text()); return r.json()
  }
  const upload = async text => {
    const pending = response('datasets/validate')
    await page.getByLabel('Choose dataset CSV', { exact: true }).setInputFiles({ name:'browser-observations.csv', mimeType:'text/csv', buffer:Buffer.from(text) })
    const result = await pending; assert.equal(result.status(),200,await result.text()); return result.json()
  }
  try {
    await page.goto(process.env.PRICEPILOT_URL || 'http://127.0.0.1:5173/')
    await page.getByRole('button', { name:'Analyze Sample Data', exact:true }).waitFor()
    const samplePending = response('optimization/run')
    const optimum = await postJson(samplePending, () => page.getByRole('button',{name:'Analyze Sample Data',exact:true}).click())
    assert.ok(Math.abs(optimum.optimal_price-95.98332850384918)<1e-5)
    await page.getByText('Recommended ticket price',{exact:true}).waitFor()
    evidence.checks.push({flow:'sample analysis',optimum:optimum.optimal_price,revenue:optimum.optimal_realized_revenue})
    await shot('desktop-overview')
    for (const id of ['dataset','regression','diagnostics','walkthrough','about']) {
      await route(id); assert.ok((await page.locator('h1').innerText()).length>0)
      if (id === 'walkthrough') { assert.ok(await page.locator('.katex').count()>0); assert.equal(await page.locator('.katex-error').count(),0) }
      await shot('desktop-'+id)
    }
    await route('optimization')
    await page.getByLabel('Maximum price (₹)',{exact:true}).fill('140')
    await page.getByLabel('Event capacity (optional)',{exact:true}).fill('200')
    const constrained = await postJson(response('optimization/run'), () => page.getByRole('button',{name:'Run optimization',exact:true}).click())
    assert.ok(Math.abs(constrained.optimal_price-140)<1e-7)
    assert.ok(Math.abs(constrained.optimal_realized_revenue-28000)<1e-7)
    assert.ok(constrained.iterations.length>0)
    evidence.checks.push({flow:'capacity and bounds',optimum:constrained.optimal_price,revenue:constrained.optimal_realized_revenue,newtonStatus:constrained.newton_status})
    await page.getByRole('heading',{name:'Actual numerical iterations'}).waitFor()
    await shot('desktop-optimization')
    await route('simulator')
    const firstSim = await postJson(response('scenarios/evaluate',r => r.request().postDataJSON().prices[0] === 100), () => page.getByLabel('Ticket price (₹)',{exact:true}).fill('100'))
    const secondSim = await postJson(response('scenarios/evaluate',r => r.request().postDataJSON().prices[0] === 120), () => page.getByLabel('Ticket price (₹)',{exact:true}).fill('120'))
    assert.notEqual(firstSim.scenarios[0].realized_revenue,secondSim.scenarios[0].realized_revenue)
    await page.getByRole('heading',{name:'Scenario comparison',exact:true}).waitFor()
    evidence.checks.push({flow:'simulator updates',at100:firstSim.scenarios[0],at120:secondSim.scenarios[0]})
    await shot('desktop-simulator')
    await route('regression')
    await page.getByRole('radio').first().check()
    await route('optimization')
    assert.equal(await page.getByRole('heading',{name:'Actual numerical iterations'}).count(),0)
    await postJson(response('optimization/run'),()=>page.getByRole('button',{name:'Run optimization',exact:true}).click())
    evidence.checks.push({flow:'model selection invalidates optimization',passed:true})
    await route('reports')
    for (const [label,file] of [['Download PDF','browser-report.pdf'],['Download predictions CSV','browser-predictions.csv'],['Download analysis JSON','browser-analysis.json'],['Download chart SVG','browser-chart.svg'],['Download residuals CSV','browser-residuals.csv'],['Download scenarios CSV','browser-scenarios.csv'],['Download chart PNG','browser-chart.png'],['Download cleaned CSV','browser-cleaned.csv']]) {
      const downloadPending = page.waitForEvent('download')
      await page.getByRole('button',{name:label,exact:true}).click()
      const download = await downloadPending
      await download.saveAs(path.join(out,file))
      assert.equal(await download.failure(),null)
      evidence.downloads.push(file)
    }
    const exported = JSON.parse(await fs.readFile(path.join(out,'browser-analysis.json'),'utf8'))
    assert.equal(exported.configuration.model_type,'linear')
    assert.equal(exported.configuration.p_max,140)
    assert.equal(exported.configuration.capacity,200)
    assert.equal(exported.observations.length,80)
    assert.ok((await fs.readFile(path.join(out,'browser-report.pdf'))).subarray(0,5).toString().startsWith('%PDF-'))
    evidence.checks.push({flow:'all eight downloads and active export settings',passed:true})
    await shot('desktop-reports')

    // All routes at representative tablet and phone widths; tables scroll in containers.
    for (const viewport of [{width:768,height:1024},{width:390,height:844}]) {
      await page.setViewportSize(viewport)
      for (const id of ['overview','dataset','regression','optimization','simulator','diagnostics','walkthrough','reports','about']) {
        await route(id)
        const dimensions = await page.evaluate(()=>({width:innerWidth,body:document.documentElement.scrollWidth}))
        assert.ok(dimensions.body <= dimensions.width+2,`${id} overflow ${JSON.stringify(dimensions)}`)
        await shot(`${viewport.width}-${id}`)
      }
      const menu = page.getByRole('button',{name:'Open navigation',exact:true})
      if (await menu.isVisible()) await menu.click()
      await page.locator('nav').getByRole('link',{name:'Dataset Studio',exact:true}).click()
      await page.getByRole('heading',{name:'Dataset Studio',exact:true}).waitFor()
      evidence.checks.push({flow:'responsive routes and navigation',viewport,passed:true})
    }
    await page.setViewportSize({width:1440,height:1000})
    await route('dataset')
    const problematic = await postJson(response('datasets/validate'),()=>page.getByRole('button',{name:/Problematic Data/}).click())
    assert.ok(problematic.rejected_rows>0)
    assert.ok(problematic.issues.some(i=>i.severity==='error'))
    const before = problematic.valid_rows
    await page.getByLabel('ticket_price row 7',{exact:true}).fill('110')
    await page.getByRole('button',{name:'Add record',exact:true}).click()
    await page.getByLabel('event_id row 14',{exact:true}).fill('MANUAL-14')
    await page.getByLabel('ticket_price row 14',{exact:true}).fill('160')
    await page.getByLabel('tickets_sold row 14',{exact:true}).fill('90')
    const repaired = await postJson(response('datasets/validate'),()=>page.getByRole('button',{name:'Apply & validate',exact:true}).click())
    assert.ok(repaired.valid_rows > before)
    evidence.checks.push({flow:'invalid sample, editable rejected row, add record, revalidation',before,after:repaired.valid_rows,rejected:repaired.rejected_rows})
    await shot('invalid-data-recovery')

    const custom = 'identifier,fee,count\nA,50,400\nB,100,300\nC,150,200\nD,200,100\n'
    await upload(custom)
    await page.locator('summary').filter({hasText:'Map different CSV column names'}).click()
    for (const [target,source] of [['event_id','identifier'],['ticket_price','fee'],['tickets_sold','count']]) await page.getByLabel(target,{exact:true}).fill(source)
    const mapped = await postJson(response('datasets/validate'),()=>page.getByRole('button',{name:'Apply mapping & validate',exact:true}).click())
    assert.equal(mapped.valid_rows,4)
    evidence.checks.push({flow:'explicit CSV column mapping',valid:mapped.valid_rows})

    const insufficient = await upload('event_id,ticket_price,tickets_sold\nA,100,30\nB,100,31\nC,100,32\n')
    assert.equal(insufficient.linear_eligible,false)
    await route('regression')
    assert.equal(await page.getByRole('button',{name:'Fit & compare models',exact:true}).isDisabled(),true)
    await shot('insufficient-data')
    await route('dataset')
    await upload('event_id,ticket_price,tickets_sold\nA,50,400\nB,100,300\nC,150,200\nD,200,100\n')
    await route('regression')
    await postJson(response('regression/fit'),()=>page.getByRole('button',{name:'Fit & compare models',exact:true}).click())
    await route('optimization')
    const reference = await postJson(response('optimization/run'),()=>page.getByRole('button',{name:'Run optimization',exact:true}).click())
    assert.ok(Math.abs(reference.optimal_price-125)<1e-7)
    assert.ok(Math.abs(reference.optimal_realized_demand-250)<1e-7)
    assert.ok(Math.abs(reference.optimal_realized_revenue-31250)<1e-7)
    evidence.checks.push({flow:'insufficient-data recovery and exact linear browser reference',price:reference.optimal_price,demand:reference.optimal_realized_demand,revenue:reference.optimal_realized_revenue})
    await shot('linear-reference')

    // A constant demand gives R''=0: Newton fails, while boundary comparison remains valid.
    await route('dataset')
    await upload('event_id,ticket_price,tickets_sold\nA,100,30\nB,110,30\nC,120,30\nD,130,30\n')
    await route('regression')
    await postJson(response('regression/fit'),()=>page.getByRole('button',{name:'Fit & compare models',exact:true}).click())
    await route('optimization')
    const failedNewton = await postJson(response('optimization/run'),()=>page.getByRole('button',{name:'Run optimization',exact:true}).click())
    assert.equal(failedNewton.newton_converged,false)
    assert.ok(failedNewton.newton_status.includes('derivative'))
    assert.ok(Math.abs(failedNewton.optimal_price-130)<1e-7)
    await page.getByText('Did not converge',{exact:true}).waitFor()
    evidence.checks.push({flow:'Newton failure displayed with separate boundary result',status:failedNewton.newton_status,price:failedNewton.optimal_price})
    await shot('newton-failure-boundary-result')
    assert.deepEqual(evidence.pageErrors,[])
    assert.deepEqual(evidence.failedRequests,[])
    assert.deepEqual(evidence.consoleErrors,[])
    console.log(JSON.stringify({checks:evidence.checks,consoleErrors:evidence.consoleErrors,pageErrors:evidence.pageErrors,failedRequests:evidence.failedRequests,downloads:evidence.downloads,screenshots:evidence.screenshots.length},null,2))
  } catch (error) {
    evidence.failure = {message:error.message,stack:error.stack}
    await shot('failure').catch(()=>{})
    throw error
  } finally {
    await fs.writeFile(path.join(out,'browser-evidence.json'),JSON.stringify(evidence,null,2))
    await browser.close()
  }
}
main().catch(error=>{ console.error(error); process.exitCode=1 })
