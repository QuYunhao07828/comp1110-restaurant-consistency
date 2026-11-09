// Isolated browser-export/ingestion round trip. No student or study labels.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python=process.env.RUNTIME_PYTHON_BINARY;
assert(python,'Set RUNTIME_PYTHON_BINARY to the configured bundled Python executable.');
const context=vm.createContext({document:{querySelector(){throw Error('No DOM access in pure export test')}},
  fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(root,'site/dist/review.js'),'utf8'),context,{filename:'review.js'});
const pairs=Array.from({length:60},(_,i)=>({pair_id:`ISOLATED_PAIR_${i}`,candidate_id:`fixture-candidate-${i}`}));
const reason='ISOLATED FIXTURE, NOT A REAL REVIEW: 中文 "引号"\nsecond line';
const labels=Object.fromEntries(pairs.map(p=>[p.pair_id,{decision:'Uncertain',reviewer_name:'Isolated fixture reviewer',
  evidence_and_reason:reason,reviewed_at:'2020-01-02T00:00:00Z'}]));
const admin=Object.fromEntries(pairs.map(p=>[p.pair_id,{candidate_id:p.candidate_id}]));
const original=JSON.stringify(labels);
const py=`import csv,io,json,sys
sys.path.insert(0,sys.argv[1])
from ingest_reviews import validate
data=json.load(sys.stdin)
rows=list(csv.DictReader(io.StringIO(data['csv'].lstrip('\\ufeff'))))
result=validate(rows,data['admin'])
assert len(result)==60
assert result['ISOLATED_PAIR_0']['evidence_and_reason']==data['reason']
print(json.dumps({'valid_n':len(result)}))
`;
function ingest(csv,expected=admin){return spawnSync(python,['-X','utf8','-c',py,path.join(root,'scripts')],
  {input:JSON.stringify({csv,admin:expected,reason}),encoding:'utf8'});}
const csv=context.serializeReviewCSV(pairs,labels);
assert(csv.startsWith('\ufeff"pair_id","candidate_id",'));
let result=ingest(csv);
assert.equal(result.status,0,result.stderr);
assert.equal(JSON.parse(result.stdout).valid_n,60);
assert.equal(JSON.stringify(labels),original,'Export must not mutate supplied labels.');
assert.equal(context.isCompleteReview(labels[pairs[0].pair_id]),true);
assert.equal(context.isCompleteReview({...labels[pairs[0].pair_id],reviewed_at:''}),false);
assert.equal(context.isCompleteReview({...labels[pairs[0].pair_id],decision:'Other'}),false);
const changed=structuredClone(admin);changed[pairs[0].pair_id].candidate_id='different-fixture-ID';
result=ingest(csv,changed);
assert.notEqual(result.status,0,'A changed candidate ID must be rejected by the importer.');
const incomplete=structuredClone(labels);delete incomplete[pairs[0].pair_id];
result=ingest(context.serializeReviewCSV(pairs,incomplete));
assert.notEqual(result.status,0,'Incomplete labels must not become a complete review.');
console.log(JSON.stringify({isolated_pairs_round_tripped:60,candidate_ID_guard_verified:true,
  missing_review_rejected:true,unicode_quotes_and_newlines_preserved:true,missing_date_not_complete:true,
  labels_unchanged:true,study_labels_created:0}));
