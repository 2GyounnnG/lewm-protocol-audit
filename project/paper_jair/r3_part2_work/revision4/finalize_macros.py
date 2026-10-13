from pathlib import Path
import json,re,hashlib
W=Path(__file__).resolve().parent;P=W.parents[1]/'revision3_part2';mac=json.loads((W/'R4_NEW_MACROS.json').read_text());orig=dict(mac);sources=[]
def letters(i):
 s=''
 while i>=0:s=chr(65+i%26)+s;i=i//26-1
 return s
# Centralise the numeric Reacher cells in the active paper tables. Each cell is
# preserved byte-for-byte from its audited CSV-generated table; provenance is recorded.
main=(P/'main.tex').read_text();tables=re.findall(r'\\input\{(tables/[^}]+)\}',main)
num=0
for file in tables:
 p=P/file;text=p.read_text();new=[]
 dedicated=any(k in file for k in ['reacher_termination','reacher_microstep'])
 for lineno,line in enumerate(text.splitlines(),1):
  eligible=line.startswith('Reacher &') or (dedicated and any(line.startswith(m+' &') for m in ['LeWM one-frame','LeWM three-frame','Fast-LeWM','AP','AD-WM','AP minus LeWM: any','AP minus LeWM: final']))
  if eligible:
   cells=line.split(' & ')
   for i,cell in enumerate(cells):
    if not re.search(r'\d',cell):continue
    # Preserve row terminator outside the macro.
    end=''
    if i==len(cells)-1 and cell.endswith(r' \\'):cell=cell[:-3];end=r' \\'
    # Textual labels/checkpoint IDs and existing macros do not need new numeric aliases.
    if '\\' in cell or not re.fullmatch(r'[\d+.,\- \[\]()/]+',cell):continue
    name='RfourReacherCell'+letters(num);num+=1;mac[name]=cell
    sources.append({'macro':name,'table':file,'source_line':lineno,'value':cell,'source':'corrected analysis/generated table; fault-only rows explicitly use invalid old analysis'})
    cells[i]='\\'+name+'{}'+end
   line=' & '.join(cells)
  new.append(line)
 p.write_text('\n'.join(new)+'\n')
# All old macro layers are now resolved into this single active file.
(P/'a3_results/revision4_numbers.tex').write_text('% Revision 4 single active macro source. Prior layers preserved but not loaded.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in mac.items())+'\n')
(W/'REACHER_MACRO_CELL_MAP.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
(W/'EFFECTIVE_MACROS.json').write_text(json.dumps(mac,ensure_ascii=False,indent=2)+'\n')
print('Resolved macros',len(mac),'Reacher table cells centralised',num)
