const {chromium}=require('playwright')
const assert=require('node:assert/strict')
const fs=require('node:fs/promises')
const path=require('node:path')
async function main(){
  const out=path.resolve(__dirname,'../output/verification/browser')
  const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})})
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true})
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',e=>{if(e.type()==='error')errors.push(e.text())})
  const post=(name,predicate=()=>true)=>page.waitForResponse(r=>r.url().includes('/api/v1/'+name)&&r.request().method()==='POST'&&predicate(r))
  const route=async id=>{await page.evaluate(id=>location.hash='/'+id,id);await page.waitForTimeout(200)}
  const shot=async file=>{await page.evaluate(()=>{document.activeElement?.blur();scrollTo({top:0,behavior:'instant'})});await page.waitForTimeout(100);await page.screenshot({path:path.join(out,file),fullPage:true})}
  const evidence={}
  try{
    await page.goto('http://127.0.0.1:5173/')
    let pending=post('optimization/run')
    await page.getByRole('button',{name:'Analyze Sample Data',exact:true}).click()
    const base=await(await pending).json()
    await route('regression')
    await page.getByRole('heading',{name:'Compare the demand fits',exact:true}).waitFor()
    await shot('extended-model-overlay.png')
    pending=post('diagnostics/evaluate')
    await route('diagnostics')
    const diagnostics=await(await pending).json()
    assert.equal(diagnostics.actual_vs_predicted.length,80)
    assert.equal(diagnostics.histogram.reduce((n,b)=>n+b.count,0),80)
    await page.getByRole('heading',{name:'Actual vs predicted demand',exact:true}).waitFor()
    await page.getByRole('heading',{name:'Residual distribution',exact:true}).waitFor()
    await shot('extended-diagnostics.png')
    await route('optimization')
    await page.getByRole('heading',{name:'Newton–Raphson convergence',exact:true}).waitFor()
    await shot('extended-convergence.png')
    await route('simulator')
    pending=post('scenarios/evaluate',r=>r.request().postDataJSON().prices[0]===100&&r.request().postDataJSON().demand_multiplier===1)
    await page.getByLabel('Ticket price (₹)',{exact:true}).fill('100')
    const original=await(await pending).json()
    pending=post('scenarios/evaluate',r=>r.request().postDataJSON().prices[0]===100&&r.request().postDataJSON().demand_multiplier===1.2)
    await page.getByLabel('Hypothetical demand multiplier',{exact:true}).fill('1.2')
    const adjusted=await(await pending).json()
    assert.ok(Math.abs(adjusted.scenarios[0].predicted_demand-original.scenarios[0].predicted_demand*1.2)<1e-8)
    assert.ok(Math.abs(adjusted.scenarios[0].difference_from_recommended_price-(100-base.optimal_price))<1e-8)
    assert.ok(adjusted.scenarios.some(s=>s.price===50))
    assert.ok(adjusted.scenarios.some(s=>s.price===base.optimal_price))
    await page.getByRole('heading',{name:'Compare scenario revenue',exact:true}).waitFor()
    await shot('extended-scenario-multiplier.png')
    await route('reports')
    for(const[label,file]of[['Download analysis JSON','multiplier-analysis.json'],['Download scenarios CSV','multiplier-scenarios.csv'],['Download PDF','multiplier-report.pdf']]){
      const download=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();await(await download).saveAs(path.join(out,file))
    }
    const exported=JSON.parse(await fs.readFile(path.join(out,'multiplier-analysis.json'),'utf8'))
    assert.equal(exported.scenario_configuration.demand_multiplier,1.2)
    assert.ok(Math.abs(exported.optimization.optimal_realized_revenue-base.optimal_realized_revenue)<1e-6)
    assert.ok(Math.abs(exported.scenarios.find(s=>s.price===100).realized_revenue-adjusted.scenarios[0].realized_revenue)<1e-6)
    const csv=await fs.readFile(path.join(out,'multiplier-scenarios.csv'),'utf8');assert.ok(csv.includes('Hypothetical demand multiplier 1.2'))
    await page.setViewportSize({width:390,height:844})
    for(const id of ['regression','diagnostics','optimization','simulator']){
      await route(id);await page.waitForTimeout(500)
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2))
      await shot('extended-mobile-'+id+'.png')
    }
    evidence.diagnostics={points:diagnostics.actual_vs_predicted.length,histogramCount:diagnostics.histogram.reduce((n,b)=>n+b.count,0)}
    evidence.scenarios={original:original.scenarios[0],adjusted:adjusted.scenarios[0],exportedMultiplier:exported.scenario_configuration.demand_multiplier,baseRevenue:exported.optimization.optimal_realized_revenue}
    evidence.mobileCharts=['regression','diagnostics','optimization','simulator']
    evidence.errors=errors
    assert.deepEqual(errors,[])
    await fs.writeFile(path.join(out,'browser-features-evidence.json'),JSON.stringify(evidence,null,2))
    console.log(JSON.stringify(evidence,null,2))
  }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1})
