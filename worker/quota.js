/* One globally addressed Durable Object serializes reservations across locations.
 * No raw prompts, provider credentials, email addresses or raw IPs are stored.
 * Short response receipts support delivery retries and expire after 30 minutes.
 * UTC day/month windows; uncertain requests retain their conservative charge. */
import {publicLimits} from './limits.js';
export class DemoQuota {
  constructor(state, env) { this.state=state; this.env=env; }
  async alarm(){
    const now=Date.now();
    await this.state.storage.transaction(async tx=>{
      const book=await tx.get('ledger');if(!book)return;
      for(const [key,value] of Object.entries(book.receipts))if(value.expires<=now)delete book.receipts[key];
      await tx.put('ledger',book);
      const remaining=Object.values(book.receipts);
      if(remaining.length)await this.state.storage.setAlarm(Math.max(now+1000,Math.min(...remaining.map(r=>r.expires))));
    });
  }
  async fetch(request) {
    const action=new URL(request.url).pathname;
    const input=request.method==='POST' ? await request.json() : {};
    const now=Date.now(), day=new Date(now).toISOString().slice(0,10), month=day.slice(0,7);
    const result=await this.state.storage.transaction(async tx=>{
      const book=await tx.get('ledger') || {buckets:{},identities:{},receipts:{}};
      for(const [key,value] of Object.entries(book.receipts)) {
        if(value.expires<now) delete book.receipts[key];
        else if(value.state==='pending' && value.started<now-120000) value.state='uncertain';
      }
      for(const key of Object.keys(book.identities)) if(!key.startsWith(day+':')) delete book.identities[key];
      for(const key of Object.keys(book.buckets)) if(!key.includes(':validation:')&&!key.includes(day)&&!key.endsWith(month)) delete book.buckets[key];
      const bucket=key=>book.buckets[key] ||= {charged:0,calls:0,success:0,errors:0,denied:0};
      // Upgrade the initial validation deployment without resetting its spend.
      if(!book.buckets['operator:validation:v1']&&book.buckets[`operator:month:${month}`]) {
        book.buckets['operator:validation:v1']={...book.buckets[`operator:month:${month}`]};
        await tx.put('ledger',book);
      }
      const scope=input.scope==='operator'?'operator':'public';
      const daily=bucket(`${scope}:day:${day}`), monthly=bucket(`${scope}:month:${month}`);
      if(action==='/status') {
        return {status:200,data:{utc_day:day,utc_month:month,buckets:book.buckets,pending:Object.values(book.receipts).filter(r=>r.state==='pending').length}};
      }
      if(action==='/settle') {
        const receipt=book.receipts[input.key];
        if(!receipt || receipt.state!=='pending') return {status:200,data:{settled:false}};
        const charged=Number.isSafeInteger(input.actual)&&input.actual>=0 ? input.actual : receipt.reserved;
        for(const key of receipt.buckets) {
          const b=book.buckets[key]; if(!b)continue;
          b.charged += charged-receipt.reserved;
          input.ok ? b.success++ : b.errors++;
        }
        receipt.state=input.ok?'complete':'failed'; receipt.response=input.response || null;receipt.http_status=input.http_status;
        if(charged>receipt.reserved) book.bound_breached=true;
        await tx.put('ledger',book);
        return {status:200,data:{settled:true}};
      }
      if(action!=='/reserve') return {status:404,data:{error:'Unknown quota operation.'}};
      const prior=book.receipts[input.key];
      if(prior) {
        if(prior.fingerprint!==input.fingerprint) return {status:409,data:{error:'Operation ID was reused with different inputs.',retryable:false}};
        if(prior.state==='pending') return {status:409,data:{error:'This request is already running.',retryable:true}};
        return {status:200,data:{cached:true,response:prior.response || {error:'The earlier request did not finish. Start a new example.',retryable:false},http_status:prior.http_status||503}};
      }
      const dayLimit=Number(this.env[scope==='public'?'DEMO_DAILY_USD':'OPERATOR_DAILY_USD']), monthLimit=Number(this.env[scope==='public'?'DEMO_MONTHLY_USD':'OPERATOR_MONTHLY_USD']);
      const sessionKey=`${day}:session:${input.session}`, ipKey=`${day}:ip:${input.ip}`;
      const session=book.identities[sessionKey] || 0, ip=book.identities[ipKey] || 0;
      const pending=Object.values(book.receipts).filter(r=>r.state==='pending' && r.scope===scope).length;
      const runId=this.env.OPERATOR_RUN_ID || 'v1';
      if(!/^[a-zA-Z0-9_-]{1,80}$/.test(runId))return {status:503,data:{error:'Invalid operator budget configuration.',retryable:false}};
      const lifetimeKey=`operator:validation:${runId}`;
      const lifetime=scope==='operator'?bucket(lifetimeKey):null;
      const lifetimeLimit=Number(this.env.OPERATOR_VALIDATION_USD||'5');
      const limits=publicLimits(this.env);
      let error=null,busy=false;
      if(book.bound_breached || !Number.isFinite(dayLimit)||!Number.isFinite(monthLimit)||dayLimit<=0||monthLimit<=0) error='Live examples are temporarily disabled.';
      else if(!Number.isSafeInteger(input.reserved)||input.reserved<=0) error='Invalid budget reservation.';
      else if(daily.charged+input.reserved>Math.round(dayLimit*1e9)||monthly.charged+input.reserved>Math.round(monthLimit*1e9)) error='The site’s shared live-service allowance is used up. The walkthrough and research briefing remain available.';
      else if(lifetime && (!Number.isFinite(lifetimeLimit)||lifetimeLimit<=0||lifetime.charged+input.reserved>Math.round(lifetimeLimit*1e9)))error='The one-time operator validation allowance is used up.';
      else if(scope==='public' && (session>=limits.sessionCallsPerDay||ip>=limits.ipCallsPerDay||daily.calls>=limits.siteCallsPerDay)) error='Your shared daily live-service allowance is used up. The walkthrough and research briefing remain available.';
      else if(pending>=(scope==='public'?limits.concurrentCalls:12)){error='Live examples are busy. Try again shortly.';busy=true;}
      if(error) {
        daily.denied++;monthly.denied++;await tx.put('ledger',book);
        return {status:429,data:{error,retryable:busy,...(busy?{retry_after:2}:{})}};
      }
      const keys=[`${scope}:day:${day}`,`${scope}:month:${month}`];
      if(lifetime)keys.push(lifetimeKey);
      for(const key of keys){const b=bucket(key);b.charged+=input.reserved;b.calls++;}
      if(scope==='public'){book.identities[sessionKey]=session+1;book.identities[ipKey]=ip+1;}
      book.receipts[input.key]={scope,fingerprint:input.fingerprint,reserved:input.reserved,buckets:keys,state:'pending',started:now,expires:now+1800000};
      await tx.put('ledger',book);
      if(this.state.storage.setAlarm)await this.state.storage.setAlarm(Math.min(...Object.values(book.receipts).map(r=>r.expires)));
      return {status:200,data:{allowed:true,remaining_session:scope==='public'?limits.sessionCallsPerDay-session-1:null}};
    });
    return Response.json(result.data,{status:result.status});
  }
}
