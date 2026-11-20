export const session=()=>JSON.parse(localStorage.getItem('dye-session')||'null');
export async function api(path,method='GET',body){
 const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(session()?{Authorization:'Bearer '+session().token}:{})},body:body?JSON.stringify(body):undefined});
 const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
export const setSession=x=>localStorage.setItem('dye-session',JSON.stringify(x));
