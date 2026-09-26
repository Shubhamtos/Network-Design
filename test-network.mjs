import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(process.argv[2]||'work/frontend');
const {default:loadHighs}=await import(pathToFileURL(path.join(root,'vendor/highs.mjs')));
const {buildLP,decode,metrics}=await import(pathToFileURL(path.join(root,'engine.mjs')));
const data=JSON.parse(fs.readFileSync(path.join(root,'data.json')));
const highs=await loadHighs();let passed=0;
function solve(s,fixed){return highs.solve(buildLP(data,s,fixed),{output_flag:false,mip_rel_gap:.0001,time_limit:60});}
function check(s,r){assert.equal(r.Status,'Optimal');let m=metrics(data,decode(data,s,r));assert.deepEqual(m.errors,[]);assert.ok(Math.abs(m.total-r.ObjectiveValue)<1e-4);return m;}
for(const s of data.scenarios){
 assert.deepEqual(metrics(data,s).errors,[]);let r=solve(s);check(s,r);assert.ok(Math.abs(r.ObjectiveValue-s.workbookCost)<.001);passed++;
 let fixed=solve(s,data.scenarios[0].modules);assert.equal(fixed.Status,s.id==='c'?'Infeasible':'Optimal');if(fixed.Status==='Optimal')check(s,fixed);passed++;
 console.log(s.id,r.ObjectiveValue,fixed.Status);
}
const base=data.scenarios[0];
for(const change of [{rate:0},{cementRate:0,clinkerRate:0},{demand:base.demand.map(v=>v*.9)},{moduleChoices:base.modules.map(String)},{moduleChoices:['-1',...Array(9).fill('auto')]},{cementLimit:700,clinkerLimit:1200}]){const s={...base,...change};check(s,solve(s));passed++;}
for(const change of [{demand:Array(12).fill(100)},{moduleChoices:Array(10).fill('-1')},{cementLimit:0,clinkerLimit:0}]){assert.equal(solve({...base,...change}).Status,'Infeasible');passed++;}
for(const change of [{rate:NaN},{life:0},{life:2.5},{factor:Infinity},{demand:Array(12).fill(0)},{demand:[-1,...base.demand.slice(1)]},{moduleChoices:['bad']}]){assert.throws(()=>buildLP(data,{...base,...change}));passed++;}
assert.throws(()=>decode(data,base,{Columns:{},ObjectiveValue:0}));passed++;
console.log(`${passed} model checks passed`);
