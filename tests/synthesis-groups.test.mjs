import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const group=vm.runInNewContext(readFileSync(new URL('../dtm_pipeline/synthesis_logic.js',import.meta.url),'utf8')+';SynthesisGroups');
test('many-to-one synthesis retains every topic, rationale and draft definition, and invalidates approval',()=>{
 const state={topics:{0:{theme:'A',notes:'first rationale',exclude:false},1:{theme:'B',notes:'second rationale',exclude:false},2:{theme:'C',notes:'unaffected',exclude:false}},definitions:{A:{definition:'first meaning',include:'first boundary'},B:{definition:'second meaning',exclude:'second boundary'}},confirm_1:true,confirm_2:true};
 group.combine(state,['0','1'],'Shared theme');
 assert.equal(Object.keys(state.topics).length,3);assert.equal(group.names(state).length,2);
 assert.equal(state.topics[0].theme,state.topics[1].theme);assert.equal(state.topics[1].notes,'second rationale');
 assert.match(state.definitions['Shared theme'].definition,/first meaning/);assert.match(state.definitions['Shared theme'].definition,/second meaning/);
 assert.equal(state.definitions['Shared theme'].include,'first boundary');assert.equal(state.definitions['Shared theme'].exclude,'second boundary');
 assert.equal(state.definitions.A.definition,'first meaning');assert.equal(state.confirm_1,false);assert.equal(state.confirm_2,false);
 assert.equal(state.topics[2].theme,'C');
});
test('invalid group requests cannot mutate a map',()=>{
 const state={topics:{0:{theme:'A',exclude:false}},definitions:{},confirm_1:true};const original=JSON.stringify(state);
 for(const [ids,name] of [[['99'],'A'],[['0'],' '],[[],'A'],[['0','0'],'A']]){assert.throws(()=>group.combine(state,ids,name));assert.equal(JSON.stringify(state),original);}
});
