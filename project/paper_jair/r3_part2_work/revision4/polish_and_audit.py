from pathlib import Path
import json,re,hashlib
W=Path(__file__).resolve().parent;P=W.parents[1]/'revision3_part2';p=P/'main.tex';s=p.read_text().replace('rad but prevent success','rad but prevents success').replace('applied any-step, block-boundary, and final-step labels','applied any-step, block-boundary, final-step, and sustained-window labels').replace('factor contrasts, the three success labels, occupancy','factor contrasts, arrival/endpoint/window labels, occupancy').replace('The literature inventory contains','The broader Step-0 candidate inventory (supplied in the materials) contains');p.write_text(s)
p=P/'tables/table_predictions_revision.tex';p.write_text(p.read_text().replace('an separately judged','a separately judged'))
p=P/'tables/table_reacher_termination_contrasts.tex';s=p.read_text().replace('Changes in the AP--LeWM contrast and five-configuration ranking after correction.','Fault-attribution diagnostics for the AP--LeWM contrast and five-configuration ranking; invalid continuation values do not characterize controller behavior.').replace('Old reset semantics','Invalid continuation');p.write_text(s)
# Centralise the remaining Reacher estimate cells, including prediction rows and diagnostic contrasts.
mac=json.loads((W/'EFFECTIVE_MACROS.json').read_text());maprows=json.loads((W/'REACHER_MACRO_CELL_MAP.json').read_text());idx=0
for file in re.findall(r'\\input\{(tables/[^}]+)\}',(P/'main.tex').read_text()):
 p=P/file;s=p.read_text();out=[]
 for no,line in enumerate(s.splitlines(),1):
  if ' & ' in line and ('Reacher' in line or file.endswith('table_reacher_termination_contrasts.tex')):
   cells=line.split(' & ')
   for i,c in enumerate(cells):
    tail=''
    if c.endswith(r' \\'):c=c[:-3];tail=r' \\'
    if re.fullmatch(r'[\d+.,\- \[\]()/]+',c) and re.search(r'\d',c):
     # Alphabetic macro suffixes only.
     key='RfourAuditCell'+chr(65+idx//26)+chr(65+idx%26);idx+=1;mac[key]=c;cells[i]='\\'+key+'{}'+tail;maprows.append({'macro':key,'table':file,'source_line':no,'value':c})
   line=' & '.join(cells)
  out.append(line)
 p.write_text('\n'.join(out)+'\n')
(P/'a3_results/revision4_numbers.tex').write_text('% Revision 4 single active macro source; old layers retained but not loaded.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in mac.items())+'\n');(W/'EFFECTIVE_MACROS.json').write_text(json.dumps(mac,indent=2)+'\n');(W/'REACHER_MACRO_CELL_MAP.json').write_text(json.dumps(maprows,indent=2)+'\n')
assert mac['APLeWMCubeAnyCI']=='+27.0 [+19.7, +34.7]'
assert mac['PublicSourceCount']=='12' and mac['FourTaskSourceCount']=='8'
assert mac['RfourReacherThreeAllTen']=='0.3' and mac['RfourReacherAPOccTen']=='57.4'
assert mac['ReacherHistoryFinalCI']=='+48.3 [+42.0, +55.0]'
# Check old PDF and bibliography remain exactly the prior sealed bytes.
base=json.loads((W/'BASELINE_FILES.json').read_text())
for n in ['JAIR_REVISION_3_PART2.pdf','refs.bib','SEAL.json']:
 assert hashlib.sha256((P/n).read_bytes()).hexdigest()==base[n],n
report={'status':'PASS','active_numeric_macro_file':'a3_results/revision4_numbers.tex','resolved_macros':len(mac),'centralised_Reacher_cells':len(maprows),'old_pdf_unchanged':True,'old_refs_bib_unchanged':True,'old_seal_retained_as_historical':True,'C1_zero_mismatches':True,'D_first25_equal':True,'Cube_AP_any_shared_interval':mac['APLeWMCubeAnyCI'],'table2_sources':12,'table2_allfour':8,'notes':['All statistical table-cell macros preserve the audited generated values. Protocol constants, labels, UTC and checksums are not estimated outcomes.','Platform BibTeX entry already existed but was uncited; adding the in-text citation makes it appear without changing any bibliography entry.','Step-0 gain inventory is broader than the 12-source displayed protocol table; manuscript now distinguishes them.']}
(W/'NUMBER_CONSISTENCY_REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
