// Local progressive enhancement: drag/drop previews; server validates every ID.
(() => {
 const list=document.querySelector('#piece-list'),form=document.querySelector('#piece-reorder');
 if(!list||!form)return;
 let dragged;
 list.addEventListener('dragstart',event=>{
  dragged=event.target.closest('[data-position]');
  if(!dragged)return;
  event.dataTransfer.setData('text/plain',dragged.dataset.position);
 });
 list.addEventListener('dragover',event=>{if(dragged)event.preventDefault();});
 list.addEventListener('drop',event=>{
  event.preventDefault();const target=event.target.closest('[data-position]');
  if(!dragged||!target||target===dragged)return;
  list.insertBefore(dragged,target);
  const inputs=document.querySelector('#piece-order-inputs');inputs.replaceChildren();
  [...list.querySelectorAll('[data-position]')].forEach((row,index)=>{
   row.querySelector('.piece-number').textContent=`${index+1}.`;
   row.querySelector('input[name="at"]').value=index+1;
   const input=document.createElement('input');input.type='hidden';input.name='order';input.value=row.dataset.position;inputs.append(input);
  });dragged=null;
  form.dataset.preview='changed';
 });
 list.addEventListener('dragend',()=>{dragged=null;});
})();
