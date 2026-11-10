/* Layout personalizable sin dependencias. Persistencia limitada a este navegador. */
(()=>{
 document.querySelectorAll('[data-nav]').forEach(b=>{const label={overview:'Vista general',devices:'Dispositivos',activity:'Actividad de control'}[b.dataset.nav];b.setAttribute('aria-label',label);b.title=label});
 const key='verdant-layout-v1',main=document.querySelector('main'),stats=document.querySelector('.stats'),workspace=document.querySelector('.workspace');
 const board=document.createElement('div');board.className='dashboard-board';board.id='dashboard-board';
 stats.before(board);
 const panels=[...stats.children,workspace.querySelector('.chart-card'),workspace.querySelector('.control'),main.querySelector('.notice'),main.querySelector('.devices')];
 const names=['Temperatura','Humedad del aire','Humedad de suelo','Iluminancia','Gráfica','Control','Alertas','Dispositivos'];
 const ids=['temperature','humidity','soil','light','chart','control','alerts','devices'];
 const grip='<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><circle cx="7" cy="4" r="1.2"/><circle cx="13" cy="4" r="1.2"/><circle cx="7" cy="10" r="1.2"/><circle cx="13" cy="10" r="1.2"/><circle cx="7" cy="16" r="1.2"/><circle cx="13" cy="16" r="1.2"/></svg>';
 // Las tarjetas originales eran botones. Se convierten a secciones para evitar
 // anidar el botón de movimiento dentro del botón de selección de variable.
 panels.forEach((original,i)=>{
  let panel=original;
  if(i<4){panel=document.createElement('section');panel.className=original.className;panel.dataset.var=original.dataset.var;panel.innerHTML=original.innerHTML;original.replaceWith(panel);const select=document.createElement('button');select.type='button';select.className='stat-selector';select.setAttribute('aria-label','Ver '+names[i]);while(panel.firstChild)select.append(panel.firstChild);panel.append(select);panel.onclick=e=>{if(document.body.classList.contains('editing')||e.target.closest('.drag-handle'))return;variable=panel.dataset.var;renderChart()};panels[i]=panel}
  panel.dataset.panel=ids[i];const handle=document.createElement('button');handle.type='button';handle.className='drag-handle';handle.innerHTML=grip+' Mover '+names[i];handle.setAttribute('aria-label','Mover '+names[i]);handle.title='Arrastra o usa las flechas izquierda y derecha';panel.prepend(handle);board.append(panel);
 });
 stats.remove();workspace.remove();
 const help=document.createElement('p');help.className='layout-help';help.id='layout-help';help.textContent='Arrastra los paneles desde su asa. También puedes enfocar «Mover» y usar ← o →. La distribución se guarda en este navegador.';board.before(help);
 const actions=document.createElement('div');actions.className='layout-actions';const exportButton=document.getElementById('export');exportButton.before(actions);actions.append(exportButton);
 const edit=document.createElement('button');edit.className='btn';edit.id='edit-layout';edit.type='button';edit.setAttribute('aria-pressed','false');edit.innerHTML=icon('grid')+' Personalizar';actions.prepend(edit);
 const reset=document.createElement('button');reset.className='btn';reset.id='reset-layout';reset.type='button';reset.textContent='Restaurar';reset.hidden=true;actions.append(reset);
 let editing=false,drag=null;
 function save(){try{localStorage.setItem(key,JSON.stringify({order:[...board.children].map(p=>p.dataset.panel),wide:board.querySelector('[data-panel="control"]').classList.contains('wide')}))}catch{toast('El navegador no permite guardar la distribución.',true)}}
 function loadLayout(){try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(!saved||!Array.isArray(saved.order))return;const current=new Map([...board.children].map(p=>[p.dataset.panel,p]));for(const id of [...new Set(saved.order)])if(current.has(id)){board.append(current.get(id));current.delete(id)}for(const p of current.values())board.append(p);setWide(saved.wide===true,false)}catch{}}
 function setWide(wide,persist=true){board.querySelector('[data-panel="control"]').classList.toggle('wide',wide);board.querySelector('[data-panel="chart"]').classList.toggle('narrow',wide);size.textContent=wide?'Control compacto':'Ampliar control';size.setAttribute('aria-pressed',String(wide));if(persist)save();requestAnimationFrame(draw)}
 const size=document.createElement('button');size.className='panel-resize';size.type='button';size.textContent='Ampliar control';size.setAttribute('aria-pressed','false');board.querySelector('[data-panel="control"]').append(size);size.onclick=()=>setWide(size.getAttribute('aria-pressed')!=='true');
 edit.onclick=()=>{editing=!editing;document.body.classList.toggle('editing',editing);edit.setAttribute('aria-pressed',String(editing));edit.innerHTML=icon(editing?'grid':'sliders')+(editing?' Terminar':' Personalizar');reset.hidden=!editing;if(!editing){save();toast('Distribución guardada en este navegador.')}requestAnimationFrame(draw)};
 reset.onclick=()=>{ids.forEach(id=>board.append(board.querySelector('[data-panel="'+id+'"]')));setWide(false);save();toast('Distribución original restaurada.');requestAnimationFrame(draw)};
 function clearTargets(){board.querySelectorAll('.drop-target').forEach(p=>p.classList.remove('drop-target'))}
 function endDrag(cancel=false){if(!drag)return;const {panel,target}=drag;if(!cancel&&target&&panel!==target){const list=[...board.children],from=list.indexOf(panel),to=list.indexOf(target);board.insertBefore(panel,from<to?target.nextSibling:target);save()}panel.classList.remove('panel-dragging');clearTargets();drag=null;requestAnimationFrame(draw)}
 for(const panel of panels){const handle=panel.querySelector('.drag-handle');handle.onkeydown=e=>{if(!editing||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();let prev=['ArrowLeft','ArrowUp'].includes(e.key),other=prev?panel.previousElementSibling:panel.nextElementSibling;if(!other)return;board.insertBefore(panel,prev?other:other.nextElementSibling);save();handle.focus();toast('Panel movido.');requestAnimationFrame(draw)};
 handle.onpointerdown=e=>{if(!editing||e.button!==0)return;e.preventDefault();drag={panel,target:null,startX:e.clientX,startY:e.clientY};panel.classList.add('panel-dragging');handle.setPointerCapture(e.pointerId)};
 handle.onpointermove=e=>{if(!drag||drag.panel!==panel)return;if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<5)return;let target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-panel]');clearTargets();drag.target=target&&target.parentElement===board&&target!==panel?target:null;if(drag.target)drag.target.classList.add('drop-target');if(e.clientY<90)window.scrollBy(0,-18);else if(e.clientY>innerHeight-90)window.scrollBy(0,18)};
 handle.onpointerup=()=>endDrag();handle.onpointercancel=()=>endDrag(true);handle.onlostpointercapture=()=>endDrag(true);
 }
 document.addEventListener('keydown',e=>{if(e.key==='Escape')endDrag(true)});loadLayout();
})();
