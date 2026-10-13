from pathlib import Path
import re,json,hashlib
W=Path(__file__).resolve().parent;P=W.parent/'revision3_part2';src=W.parent/'jair_kit/extracted/JAIR AuthorKit/JAIR_Example_Template/JAIR_Example_Template.tex'
s=src.read_text();s=s[s.index('\\section{Reproducibility Checklist for JAIR}'):];s=s[:s.index('\\end{document}')]
s=re.sub(r'(?m)^\s*%.*\n','',s);s=s.replace('\\section{Reproducibility Checklist for JAIR}','');s=s.replace('Select the answers that apply to your research -- one per item.','The following items reproduce the JAIR author-template checklist; answers describe the current local manuscript and material package.')
s=s.replace('If yes, please complete the list below.','')
s=s.replace('Does this paper make theoretical contributions? \n[yes/no]',r'Does this paper make theoretical contributions? \textbf{No.} The conditional items below are not applicable.')
s=s.replace('Does this paper include computational experiments? [yes/no]',r'Does this paper include computational experiments? \textbf{Yes.}')
s=s.replace('Does this work rely on one or more data sets (possibly obtained from a benchmark generator or similar software artifact)? \n[yes/no]',r'Does this work rely on one or more data sets (possibly obtained from a benchmark generator or similar software artifact)? \textbf{Yes.}')
answers=[
('Yes','Sections 1, 3 and the preregistered prediction table.'),('Yes','Sections 4--8 and the paired result tables.'),('Yes','Sections 3 and 9.'),('NA','No new AI method is introduced; the adapter mapping and evaluation logic are documented.'),('Yes','Sections 3 and 5, and Appendix A.'),
*([('NA','No theoretical contribution.')] * 6),
('Partially','Source and reproduction instructions are prepared locally; the public archival repository remains an author decision.'),('No','A license for the new audit code has not yet been selected.'),('No','A license for the new audit code has not yet been selected.'),('Partially','Unaggregated records are retained and packaged locally; public release and redistribution permissions remain pending.'),('No','A redistribution license has not yet been selected.'),('No','A redistribution license has not yet been selected.'),('Yes','The frozen case, planner-stream, checkpoint and bootstrap seeds are supplied.'),('Partially','GPU and software records are included; a complete cache/RAM inventory is not reported for every earlier machine.'),('Yes','Section 3.5 and Appendices D and F.'),('Yes','Cohort and checkpoint/stream tables report the run grid.'),('Yes','Excluded conditions, the revoked premature launch and all retained failures are documented.'),('Yes','Paired confidence intervals, per-stream/checkpoint tables and occupancy curves are reported.'),('Yes','The method mapping, protocol-factor table and frozen condition specifications supply settings.'),('Yes','The protocol-factor grid and scope changes are documented; no checkpoint training or retraining was performed.'),('Yes','Prespecified paired-bootstrap criteria assess the confirmatory contrasts; descriptive contrasts are identified as such.'),
('Partially','Derived audit records and case manifests are prepared locally; archive and license decisions are pending.'),('No','The derived-record license has not yet been selected.'),('No','The derived-record license has not yet been selected.'),('Yes','Section 2 and the source inventory cite the public benchmark and method sources.'),('Yes','Source URLs and asset hashes identify the publicly distributed input data.'),('Yes','The cohort, case selection, labels and derivation of audit records are documented.'),('Yes','Section 3 and the case/retrieval manifests describe preprocessing and episode-level exclusions.')]
pat=r'\[(?:yes|partially|no|NA)(?:/(?:yes|partially|no|NA))*\]'
assert len(re.findall(pat,s))==len(answers),(len(re.findall(pat,s)),len(answers))
i=iter(answers)
def replace(m):
 a,b=next(i);return r'\textbf{'+a+'}. '+b
s=re.sub(pat,replace,s)
s=s.replace('[Text here; please keep this brief.]','Public release has not occurred. Repository/DOI, licenses and redistribution scope require author approval before submission. These pending items are not marked complete merely because the local package exists.')
p=P/'tables/table_jair_checklist_official.tex';p.write_text(s+'\n')
main=P/'main.tex';t=main.read_text().replace('tables/table_jair_checklist.tex','tables/table_jair_checklist_official.tex');main.write_text(t)
(P/'JAIR_CHECKLIST_SOURCE.json').write_text(json.dumps({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'items_answered':len(answers),'license_items_unresolved':True},indent=2)+'\n')
