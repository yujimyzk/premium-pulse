/* PREMIUM PULSE browser-only watchlist; never syncs to a server. */
(function(root){
  'use strict';
  const KEY='premium-pulse-watchlist-v1',MAX=60;
  const skuOK=s=>typeof s==='string'&&/^[A-Z0-9_.-]{4,32}$/.test(s);
  function normalize(entry){
    if(!entry||typeof entry!=='object')return null;
    const sku=String(entry.sku||'').trim().toUpperCase();
    if(!skuOK(sku))return null;
    const size=entry.size==null?'':String(entry.size);
    if(size&&!/^(?:2[0-9]|30)(?:\.[05])?$/.test(size))return null;
    const condition=['','new','used','unknown'].includes(entry.condition)?entry.condition:'';
    const target=entry.target===''||entry.target==null?null:Number(entry.target);
    if(target!==null&&(!Number.isSafeInteger(target)||target<1||target>100000000))return null;
    return {sku,size,condition,target};
  }
  function key(e){return [e.sku,e.size,e.condition].join('|')}
  function read(){
    try{const raw=root.localStorage.getItem(KEY);const parsed=JSON.parse(raw||'[]');
      if(!Array.isArray(parsed))return [];
      const out=[],seen=new Set();
      for(const item of parsed){const normalized=normalize(item);if(!normalized||seen.has(key(normalized)))continue;seen.add(key(normalized));out.push(normalized);if(out.length>=MAX)break}return out;
    }catch{return []}
  }
  function write(items){
    try{root.localStorage.setItem(KEY,JSON.stringify(items));return true}catch{return false}
  }
  function upsert(input){
    const item=normalize(input);if(!item)return {ok:false,message:'型番・サイズ・希望価格を確認してください'};
    const items=read(),idx=items.findIndex(r=>key(r)===key(item));
    if(idx<0&&items.length>=MAX)return {ok:false,message:'保存できる件数は最大60件です'};
    if(idx<0)items.unshift(item);else items[idx]=item;
    if(!write(items))return {ok:false,message:'ブラウザに保存できません。プライベートモードや保存設定を確認してください'};
    return {ok:true,item,items};
  }
  function remove(input){
    const item=normalize(input);if(!item)return false;
    return write(read().filter(r=>key(r)!==key(item)));
  }
  root.PPWatch={read,upsert,remove,normalize,key,limit:MAX};
})(window);
