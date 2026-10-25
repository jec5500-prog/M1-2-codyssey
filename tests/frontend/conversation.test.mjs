import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

const html=readFileSync('frontend/index.html','utf8');
const app=readFileSync('frontend/app.js','utf8');
const settle=async()=>{for(let i=0;i<12;i++)await new Promise(r=>setImmediate(r));};
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const detail=(id)=>({id,title:`대화 ${id}`,messages:[{role:'user',content:`질문 ${id}`,tools_used:[]}]});

async function setup(overrides={}) {
  const dom=new JSDOM(html,{url:'http://localhost:5500',runScripts:'outside-only'});
  const w=dom.window;const calls=[];
  w.APP_CONFIG={API_BASE_URL:'http://localhost:8000'};
  w.confirm=()=>true;
  w.HTMLElement.prototype.scrollIntoView=()=>{};
  w.fetch=async(url,opts={})=>{
    const path=new URL(url).pathname;calls.push({path,method:opts.method});
    if(overrides[path])return new Response(JSON.stringify(await overrides[path](opts)),{status:200});
    const bodies={
      '/health':{status:'ok'},
      '/api/conversations':[{id:'A',title:'대화 A',updated_at:'2026-01-01',message_count:1},{id:'B',title:'대화 B',updated_at:'2026-01-01',message_count:1}],
      '/api/data':[],
      '/api/data/summary':{count:0},
    };
    return new Response(JSON.stringify(bodies[path]??{}),{status:200});
  };
  w.eval(app);w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  await settle();
  return {dom,w,calls,click:(selector)=>w.document.querySelector(selector).click()};
}

test('late previous conversation never replaces the latest selection',async()=>{
  const a=deferred(),b=deferred();
  const s=await setup({'/api/conversations/A':()=>a.promise,'/api/conversations/B':()=>b.promise});
  try {
    s.click('[data-id="A"] .conv-main');s.click('[data-id="B"] .conv-main');
    b.resolve(detail('B'));await settle();a.resolve(detail('A'));await settle();
    assert.equal(s.w.document.querySelector('#topbarTitle').textContent,'대화 B');
    assert.match(s.w.document.querySelector('#messages').textContent,/질문 B/);
  } finally {s.dom.window.close();}
});

test('new conversation invalidates an unfinished history request',async()=>{
  const a=deferred();const s=await setup({'/api/conversations/A':()=>a.promise});
  try {
    s.click('[data-id="A"] .conv-main');s.click('#newChatBtn');
    a.resolve(detail('A'));await settle();
    assert.equal(s.w.document.querySelector('#topbarTitle').textContent,'새 대화');
  } finally{s.dom.window.close();}
});

test('cannot delete conversation while an AI request is running',async()=>{
  const pending=deferred();const s=await setup({'/api/chat':()=>pending.promise});
  try {
    s.w.document.querySelector('#chatInput').value='질문';s.click('#sendBtn');
    s.click('[data-id="A"] [data-action="delete"]');await settle();
    assert.equal(s.calls.some(c=>c.method==='DELETE'),false);
    pending.resolve({reply:'답변',conversation_id:'new',tool_calls_used:[]});await settle();
  } finally{s.dom.window.close();}
});
