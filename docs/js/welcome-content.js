// Shared by the arrival dialog and the generated, agent-readable /welcome/ page.
// Change the version when the purpose or acknowledgment materially changes.
export const welcomeVersion = '2026-11-17';
export const welcomeTitle = 'Welcome to TopicLLM.';
export const welcomeLetter = `
<p class="welcome-salutation">Dear researcher,</p>
<p>TopicLLM began with a question in my dissertation research at <strong>The University of Texas at Austin</strong>: what were alcohol companies posting about on social media during the COVID-19 pandemic?</p>
<p>Answering it meant bringing two approaches together. Transformer-based topic models can find patterns across thousands of texts. Qualitative research can explain what those patterns mean in their social and scientific context. Each offers something the other cannot provide alone. We needed a computationally explicit workflow that kept researchers responsible for interpretation.</p>
<p>The <a href="https://arxiv.org/abs/2210.00707" target="_blank" rel="noopener"><em>Theme and Topic</em> framework (Gillies, Murthy, Brenton &amp; Olaniyan, 2022)</a> helped inform that approach by bringing topic modeling and qualitative interpretation together. TopicLLM offers a starting implementation: documented parameters, repeated LLM-assisted naming, researcher-led theme synthesis, classifier validation and an inspectable record of the analysis.</p>
<h3>One research program. A method you can build on.</h3>
<p>The dissertation used this approach across two studies. Study 1 identified themes in alcohol companies’ Twitter posts. Study 2 applied a selected theme to a larger corpus of general users’ posts and examined its relationship to potential exposure to brand messages. This repository maintains the Study 1 topic-to-prevalence workflow; it does not implement every analysis in the dissertation.</p>
<p>“Twitter” and “tweets” preserve the terminology of the research period; the platform is now called X. The method can be adapted to other social media or text corpora, with appropriate sampling, domain-specific interpretation and fresh validation.</p>
<h3>Explore as a human. Implement with an agent.</h3>
<p>Use this website to get a feel for the method and inspect its evidence. Then fork the repository or install the Python package and give your coding agent the documented workflow. The agent runs maintained Python scripts and recorded model calls, retains artifacts and prepares evidence for review. It must not invent results, annotations or approvals. Code-enforced review and validation gates pause the research workflow for decisions that belong to researchers, informed by their field’s literature.</p>
<p>The demonstration uses <strong>original, author-released Study 1 brand data</strong>. It is an illustrative modern rerun. Topic models and LLMs include probabilistic steps, so seeds, models and software versions can change groupings or labels. The dissertation remains the source for the historical findings.</p>
<h3>An open invitation, with clear scientific boundaries.</h3>
<p>The dissertation and the two study preprints are available for you and your agents to read. The dissertation studies were revised under committee supervision and accepted as part of the dissertation. That review is distinct from journal peer review; these materials are presented as dissertation research and preprints. The TopicLLM methodology has not yet been independently replicated by other researchers. Software checks and demonstration runs do not establish that independent scientific validation.</p>
<p>My hope in releasing the code, data and papers is that others will test, challenge and extend this work. Whether you are an undergraduate or a tenured professor, I am happy to help you get started. Feedback on the website, repository and method is welcome.</p>
<p>Thank you for your time, curiosity and care.</p>
<div class="welcome-signature"><strong>Jacob E. Thomas</strong><span>Creator of TopicLLM</span><a href="mailto:jethomasphd@gmail.com">Get in touch ↗</a><a href="https://github.com/jethomasphd/TopicLLM/issues" target="_blank" rel="noopener">Share feedback on GitHub ↗</a></div>
`;
