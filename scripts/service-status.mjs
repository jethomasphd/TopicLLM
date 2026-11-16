// Supply the operator token privately in the environment. Output is aggregates only.
const token=process.env.TOPICLLM_RESEARCH_TOKEN;
if(!token)throw new Error('Privately set TOPICLLM_RESEARCH_TOKEN before checking operator status.');
const origin=process.env.TOPICLLM_URL||'https://topicllm.dev';
const response=await fetch(new URL('/api/admin/status',origin),{headers:{Authorization:`Bearer ${token}`}});
if(!response.ok)throw new Error(`Status check failed: HTTP ${response.status}.`);
console.log(JSON.stringify(await response.json(),null,2));
