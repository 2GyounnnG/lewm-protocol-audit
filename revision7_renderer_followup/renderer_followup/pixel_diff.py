from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent;root=W.parent/'release_complete/C/outputs/diagnostics/render_probe';rows=[]
fig,ax=plt.subplots(3,3,figsize=(7.2,7.2),layout='constrained')
for i,fp in enumerate(sorted((root/'osmesa').glob('*.npy'))):
 a=np.load(fp);b=np.load(root/'egl'/fp.name);d=np.abs(a.astype(float)-b.astype(float));h,w=a.shape[:2]
 zones={};total=d.sum()
 for ry in range(3):
  for rx in range(3):
   z=d[ry*h//3:(ry+1)*h//3,rx*w//3:(rx+1)*w//3];zones[f'row{ry+1}_col{rx+1}']={'mean_absolute_rgb_byte_difference':float(z.mean()),'share_of_total_absolute_difference_pct':float(z.sum()/total*100)}
 q=np.quantile(d.mean(-1),.9);mask=d.mean(-1)>=q
 rows.append({'case':fp.stem,'mean_absolute_rgb_byte_difference':float(d.mean()),'max_absolute_rgb_byte_difference':float(d.max()),'different_pixels_pct':float(np.any(d,axis=-1).mean()*100),'spatial_grid_3x3':zones,'top_decile_pixel_error_share_pct':float(d[mask].sum()/total*100),'inputs':{str(fp):hashlib.sha256(fp.read_bytes()).hexdigest(),str(root/'egl'/fp.name):hashlib.sha256((root/'egl'/fp.name).read_bytes()).hexdigest()}})
 ax[i,0].imshow(a);ax[i,1].imshow(b);im=ax[i,2].imshow(d.mean(-1),vmin=0,vmax=20,cmap='magma');ax[i,0].set_ylabel(f'Case {i}',fontsize=9)
 for j in range(3):ax[i,j].set_xticks([]);ax[i,j].set_yticks([])
for j,t in enumerate(['OSMesa','EGL','Mean absolute RGB difference']):ax[0,j].set_title(t,fontsize=10)
fig.colorbar(im,ax=ax[:,2],label='RGB byte difference',shrink=.8)
fig.savefig(W/'PIXEL_DIFFERENCE.png',dpi=180);fig.savefig(W/'PIXEL_DIFFERENCE.pdf')
(W/'PIXEL_DIFFERENCE.json').write_text(json.dumps({'scope':'saved images only; no rendering/model execution','pixel_scale':'0..255 RGB bytes','regions':'fixed equally sized3x3 spatial grid; not semantic segmentation','cases':rows},indent=2))
print(json.dumps([{k:v for k,v in r.items() if k not in ['inputs','spatial_grid_3x3']} for r in rows],indent=2))
