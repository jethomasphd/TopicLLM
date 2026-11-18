/* Shared, offline grouping logic. A group is a researcher decision, never an LLM vote. */
const SynthesisGroups = (() => {
  const fields = ['definition', 'include', 'exclude', 'examples'];
  function names(state) {
    return [...new Set(Object.values(state.topics).filter(t => !t.exclude && t.theme.trim()).map(t => t.theme.trim()))];
  }
  function invalidate(state) { state.confirm_1 = false; state.confirm_2 = false; }
  function combine(state, ids, target) {
    target = target.trim();
    if (!target || !ids.length || new Set(ids).size !== ids.length || ids.some(id => !Object.hasOwn(state.topics, id)))
      throw Error('Choose topics and enter a shared theme name.');
    const previous = [...new Set(ids.map(id => state.topics[id].theme.trim()).filter(Boolean))];
    const sources = [...new Set([target, ...previous])];
    const definition = {};
    for (const field of fields) {
      const entries = sources.map(name => [name, (state.definitions[name]?.[field] || '').trim()]).filter(([,text]) => text);
      // Keep every distinct piece of human writing. Researchers reconcile this draft before approval.
      const unique = entries.filter((entry, i) => entries.findIndex(([,text]) => text === entry[1]) === i);
      definition[field] = unique.length < 2 ? (unique[0]?.[1] || '') : unique.map(([name,text]) => '[' + name + ']\n' + text).join('\n\n');
    }
    state.definitions[target] = definition;
    for (const id of ids) { state.topics[id].theme = target; state.topics[id].exclude = false; }
    invalidate(state);
    return state;
  }
  return { names, combine, invalidate };
})();
