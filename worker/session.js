const hex=bytes=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
export async function hash(value){return hex(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));}
export async function sign(value, secret){
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return hex(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(value)));
}
export async function equal(a,b){return await hash(a)===await hash(b);}
export async function session(request,env){
  const raw=(request.headers.get('Cookie')||'').split(';').map(x=>x.trim()).find(x=>x.startsWith('__Host-topicllm='))?.split('=')[1];
  if(!raw)return null;
  const [version,id,expires,signature]=raw.split('.');
  if(version!=='v1'||!/^[0-9a-f-]{36}$/.test(id)||!/^\d+$/.test(expires)||Number(expires)<=Date.now()/1000||Number(expires)>Date.now()/1000+90000)return null;
  return await equal(signature||'',await sign(`${version}.${id}.${expires}`,env.RESEARCH_ACCESS_TOKEN))?id:null;
}
export async function issueSession(env){
  const id=crypto.randomUUID(),payload=`v1.${id}.${Math.floor(Date.now()/1000)+86400}`;
  return `${payload}.${await sign(payload,env.RESEARCH_ACCESS_TOKEN)}`;
}
