// Shared by the arrival dialog and the generated, agent-readable /welcome/ page.
// Change the version when the purpose or acknowledgment materially changes.
export const welcomeVersion = '2026-11-17';
export const welcomeTitle = 'Welcome to TopicLLM.';
export const welcomeLetter = `
<p class="welcome-salutation">Dear researcher,</p>
<p>TopicLLM began with a question in my dissertation research at <strong>The University of Texas at Austin</strong>: what were alcohol companies posting about on social media during the COVID-19 pandemic?</p>
<p>Topic models can find patterns across thousands of texts. Qualitative research explains what those patterns mean. We wanted a clear computational workflow that brought these approaches together and kept researchers responsible for interpretation.</p>
<p>The <a href="https://arxiv.org/abs/2210.00707" target="_blank" rel="noopener"><em>Theme and Topic</em> framework (Gillies, Murthy, Brenton &amp; Olaniyan, 2022)</a> informed this work. TopicLLM makes the process executable: discover topics, propose names, synthesize themes, validate a classifier and compare theme prevalence.</p>
<h3>One research program. A method you can build on.</h3>
<p>The dissertation used this approach across two studies. Study 1 identified themes in alcohol companies’ Twitter posts. Study 2 applied a selected theme to a larger corpus of general users’ posts and examined its relationship to potential exposure to brand messages. This repository maintains the Study 1 topic-to-prevalence workflow; it does not implement every analysis in the dissertation.</p>
<p>“Twitter” and “tweets” preserve the terminology of the research period; the platform is now called X. The method can be adapted to other social media or text corpora, with appropriate sampling, domain-specific interpretation and fresh validation.</p>
<h3>Explore as a human. Implement with an agent.</h3>
<p>Explore the method here, then fork the repository or install the Python package. Your coding agent runs maintained scripts and model calls, keeps the evidence and prepares it for review. Researchers interpret themes in the context of their literature. Review and validation gates keep those decisions in human hands; agents must not invent results or approvals.</p>
<p>The demonstration uses <strong>original, author-released Study 1 brand data</strong>. It is an illustrative modern rerun. Topic models and LLMs include probabilistic steps, so seeds, models and software versions can change groupings or labels. The dissertation remains the source for the historical findings.</p>
<h3>An open invitation, with clear scientific boundaries.</h3>
<p>The dissertation and study preprints are available for you and your agents. The studies were revised and accepted under dissertation committee supervision, which is distinct from journal peer review. TopicLLM has not yet been independently replicated by other researchers; this release invites that work.</p>
<p>My hope in releasing the code, data and papers is that others will test, challenge and extend this work. Whether you are an undergraduate or a tenured professor, I am happy to help you get started. Feedback on the website, repository and method is welcome.</p>
<p>Thank you for your time, curiosity and care.</p>
<div class="welcome-signature"><strong>Jacob E. Thomas</strong><span>Creator of TopicLLM</span><a href="mailto:jethomasphd@gmail.com">Get in touch ↗</a><a href="https://github.com/jethomasphd/TopicLLM/issues" target="_blank" rel="noopener">Share feedback on GitHub ↗</a></div>
`;
