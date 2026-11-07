import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dir=path.resolve(root,process.argv[2]||'outputs/assisted_review_2026-11-02');
const evidence=JSON.parse(await fs.readFile(path.join(dir,'evidence.json'),'utf8'));
const districtSettings={
 'Sha Tin':['ShaTin','ST','沙田'],
 'Central and Western':['CentralWestern','CW','中西区'],
 'Wan Chai':['WanChai','WC','湾仔'],
 'Yau Tsim Mong':['YauTsimMong','YM','油尖旺']
};
const settings=districtSettings[evidence.district];
if(!settings)throw Error('Unknown submitted-plan district.');
const [stem,prefix,districtTitle]=settings;
const output=path.join(dir,`${stem}_AI_Assisted_Review.xlsx`);
for(const p of [output,path.join(dir,'triage.json')]){
 if(await fs.access(p).then(()=>true).catch(()=>false))throw Error('Output already exists; use a new directory.');
}
const curation=JSON.parse(await fs.readFile(path.join(dir,'assessments.json'),'utf8'));
const overrides=new Map(curation.overrides.map(r=>[`${r.branch_id}|${r.source}`,r]));
const refs=new Map(curation.external_sources.map(r=>[r.id,r]));
const forbidden=new Set(evidence.deferred_pilot_tasks.map(r=>r.branch_id));
const taskKeys=new Set(evidence.cases.map(r=>`${r.branch_id}|${r.source}`));
if(overrides.size!==curation.overrides.length||curation.overrides.some(r=>!taskKeys.has(`${r.branch_id}|${r.source}`)))throw Error('Unknown or duplicate curation task.');
const tasks=evidence.cases.map((r,i)=>{
  if(forbidden.has(r.branch_id)||[r.human_decision,r.human_name,r.human_date,r.human_evidence].some(Boolean))throw Error('Protected case or filled human fields.');
  const assessment=overrides.get(`${r.branch_id}|${r.source}`);
  const selected=(assessment?.selected_ids||[]).map(id=>{
    const found=r.records.find(v=>v.id===id);if(!found)throw Error('Missing selected evidence ID');return found;
  });
  const shortlist=[...selected,...r.records.filter(v=>v.was_in_saved_top12),...r.records.slice(0,4)]
    .filter((v,j,a)=>a.findIndex(q=>q.id===v.id)===j);
  if((assessment?.external||[]).some(id=>!refs.has(id)))throw Error('Unknown supplementary source.');
  return {...r,case_id:`${prefix}${String(i+1).padStart(2,'0')}`,suggestion:assessment?.suggestion||'AI未确认对应',
    selected_ids:selected.map(v=>v.id),reason:assessment?.reason||(curation.case_notes[r.branch_id]||'未形成充分分店身份依据。'),
    question:assessment?.question||'',external:(assessment?.external||[]).map(id=>refs.get(id)),shortlist};
});
if(tasks.length!==40||evidence.deferred_pilot_tasks.length!==10)throw Error('Task counts differ.');
const wb=Workbook.create();
const main=wb.worksheets.add('Main review'),details=wb.worksheets.add('Evidence'),pilot=wb.worksheets.add('Pilot tasks');
const navy='#183E59',amber='#FFF2CC';
function base(s,title){s.showGridLines=false;s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#172B3D'};}
function table(s,headers,rows,widths,height=82){
  const last=String.fromCharCode(64+headers.length),end=7+rows.length;
  s.getRange(`A7:${last}${end}`).values=[headers,...rows];
  const all=s.getRange(`A7:${last}${end}`);all.format.font={name:'Arial',size:11,color:'#172B3D'};all.format.wrapText=true;all.format.verticalAlignment='top';
  s.getRange(`A7:${last}7`).format={fill:navy,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:36,verticalAlignment:'center',horizontalAlignment:'center'};
  s.getRange(`A8:${last}${end}`).format.rowHeight=height;
  widths.forEach((w,i)=>s.getRange(`${String.fromCharCode(65+i)}7:${String.fromCharCode(65+i)}${end}`).format.columnWidth=w);
  s.freezePanes.freezeRows(7);s.freezePanes.freezeColumns(2);
  return end;
}
base(main,`${districtTitle}餐厅 AI 辅助核对`);
main.getRange('A4:B5').values=[['快照日期','2026-10-23'],['人工信息填齐','']];
main.getRange('D4:E5').values=[['AI初筛任务',40],['独立人工标签新增',0]];
main.getRange('G4:H5').values=[['试点任务延后',10],['辅助整理日期',evidence.prepared_client_date]];
main.getRange('A6').values=[['I至L列供你补充；AI建议不能充当独立人工验证，详细记录及来源见Evidence页。']];
table(main,['分店ID','餐厅','来源','目标地址','AI建议','建议记录ID','证据与限制','待补资料','人工结果','人工依据或更正ID','核对人','实际日期','填写状态'],
  tasks.map(r=>[r.branch_id,r.name,r.source,r.address_zh,r.suggestion,r.selected_ids.join('; '),r.reason,r.question,'','','','','']),
  [21,26,13,48,24,43,64,55,24,58,18,18,24],72);
main.getRange('I8:L47').format.fill=amber;
main.getRange('I8:I47').dataValidation={rule:{type:'list',values:['Confirmed','Uncertain','No counterpart confirmed']}};
main.getRange('L8:L47').setNumberFormat('yyyy-mm-dd');
for(let i=8;i<=47;i++)main.getRange(`M${i}`).formulas=[[`=IF(AND(OR(I${i}="Confirmed",I${i}="Uncertain",I${i}="No counterpart confirmed"),J${i}<>"",K${i}<>"",L${i}<>""),"已填写待管理员复核","待确认")`]];
main.getRange('B5').formulas=[['=COUNTIFS(M8:M47,"已填写待管理员复核")']];
base(details,'候选原始字段与补充来源');
details.getRange('A4').values=[['每个任务保留原前12条，并加入扩展检索样例及建议记录。完整检索证据保存在随附evidence.json。']];
details.getRange('A5').values=[['Overture的通用文档链接不是单店详情页。以源快照文件与记录ID追溯；实时网页不是10月23日历史事实。']];
const drows=tasks.flatMap(r=>[
  ...r.shortlist.map(c=>[r.case_id,r.name,r.source,c.id,c.name,c.address,c.phones.join('; '),c.distance_m,c.was_in_saved_top12?'原前12条':'扩展检索',c.url||'',c.aliases.join(' | ')]),
  ...r.external.map(v=>[r.case_id,r.name,'补充网页',v.id,v.kind,v.fact,'',null,v.observed,v.url,v.temporal_limit])
]);
table(details,['任务','目标餐厅','证据来源','记录ID','候选名称','候选地址或网页事实','电话','距离 米','范围或观察日期','来源链接','名称变体或时间限制'],drows,[10,26,15,43,35,65,21,14,23,60,58],64);
base(pilot,'五家试点的十项任务');
pilot.getRange('A4').values=[['尚无已验证规则固定记录；这里不预填AI判断，也不计为已完成人工漏检搜索。']];
table(pilot,['分店ID','餐厅','来源','阶段','人工搜索人','搜索范围与证据','找到的记录ID','实际日期'],
 evidence.deferred_pilot_tasks.map(r=>[r.branch_id,r.name,r.source,'规则固定后进行','','','','']),[21,32,14,29,20,65,43,19],58);
pilot.getRange('E8:H17').format.fill=amber;
wb.recalculate();
if(main.getRange('B5').values[0][0]!==0)throw Error('Blank human inputs counted complete');
main.getRange('I8').values=[['Confirmed']];wb.recalculate();
if(main.getRange('B5').values[0][0]!==0)throw Error('Decision without evidence/name/date counted complete');
main.getRange('I8').values=[['']];wb.recalculate();
if(main.getRange('B5').values[0][0]!==0)throw Error('Temporary test input not cleared');
const qaDir=path.join(root,'tmp','assisted_review_qa',stem);
await fs.mkdir(qaDir,{recursive:true});
for(const [name,range,suffix] of [['Main review','A1:H10','main'],['Main review','I7:M10','inputs'],['Evidence','A1:H10','evidence'],['Pilot tasks','A1:H10','pilot']]){
 const p=await wb.render({sheetName:name,range,scale:1.1,format:'png'});
 await fs.writeFile(path.join(qaDir,suffix+'.png'),new Uint8Array(await p.arrayBuffer()));
}
const check=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:2000});
await fs.writeFile(path.join(qaDir,'errors.ndjson'),check.ndjson);
await fs.writeFile(path.join(dir,'triage.json'),JSON.stringify({scope:evidence.scope,source_snapshot_date:evidence.source_snapshot_date,
  independent_labels_created:0,human_confirmations:0,pilot_tasks_deferred:10,
  tasks:tasks.map(r=>({case_id:r.case_id,branch_id:r.branch_id,name:r.name,source:r.source,suggestion:r.suggestion,selected_ids:r.selected_ids,
    reason:r.reason,question:r.question,external:r.external,expanded_record_n:r.expanded_record_n,human_decision:'',human_name:'',human_date:'',human_evidence:''}))},null,2));
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(output);
console.log(JSON.stringify({output,tasks:tasks.length,evidenceRows:drows.length,pilotTasks:10,humanInputsFilled:0,formulaErrorScan:check.ndjson}));
process.exit(0);
