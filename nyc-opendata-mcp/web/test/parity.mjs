// Compare the browser port (brief.js) with the Python package on the same live inputs.
// 1) python web/test/make_py_briefs.py   2) npm run parity
import fs from 'node:fs';
import proj4 from 'proj4';
import { createBrief } from '../brief.js';

const cases = JSON.parse(fs.readFileSync(new URL('./py_briefs.json', import.meta.url)));
const B = createBrief({ proj4 });
let fails = 0;
const close = (a, b, tol) => a === b || (typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) <= tol);
function check(name, a, b) {
  const ja = JSON.stringify(a), jb = JSON.stringify(b);
  if (ja !== jb) { fails++; console.log(`  FAIL ${name}\n    js: ${ja.slice(0, 400)}\n    py: ${jb.slice(0, 400)}`); }
}
for (const { input, brief: py } of cases) {
  const js = await B.srBrief(input);
  console.log(`case ${input.sr || input.address}`);
  check('point.source', js.point?.source, py.point?.source);
  if (!close(js.point?.lat, py.point?.lat, 1e-7) || !close(js.point?.lon, py.point?.lon, 1e-7)) { fails++; console.log('  FAIL point', js.point, py.point); }
  check('sr_lot', js.sr_lot, py.sr_lot);
  check('corners_rule', js.corners_rule, py.corners_rule);
  const cv = (b) => b.corners.map((c) => [c.cid, c.dir_label, c.within_radius, c.at_named_intersection, c.on_sr_lot, c.named_by_caller, c.bbl, c.ramps.map((r) => r.ramp).sort()]);
  check('corners', cv(js), cv(py));
  for (let i = 0; i < Math.min(js.corners.length, py.corners.length); i++)
    if (!close(js.corners[i].dist_ft, py.corners[i].dist_ft, 0.2)) { fails++; console.log('  FAIL dist', js.corners[i].cid, js.corners[i].dist_ft, py.corners[i].dist_ft); }
  check('ramp_program', js.ramp_program, py.ramp_program);
  check('facts', js.facts, py.facts);
  check('permits', js.permits.map((p) => [p.permitnumber, p.tags, p.in_force_on_complaint_date, p.issued_days_before_complaint]),
                   py.permits.map((p) => [p.permitnumber, p.tags, p.in_force_on_complaint_date, p.issued_days_before_complaint]));
  check('permit_queries', js.permit_queries, py.permit_queries);
  check('permit_links', js.permit_links, py.permit_links);
  check('capital', js.capital_projects, py.capital_projects);
  check('311', js.public_311_nearby.map((r) => r.unique_key), py.public_311_nearby.map((r) => r.unique_key));
  check('feeds', js.rules_these_facts_feed, py.rules_these_facts_feed);
  check('notes', js.notes, py.notes);
  check('errors', js.errors, py.errors);
}
console.log(fails ? `${fails} differences` : `all ${cases.length} cases match`);
process.exit(fails ? 1 : 0);
