// Shared by the arrival dialog and the generated, agent-readable /welcome/ page.
// Change the version when the purpose or acknowledgment materially changes.
export const welcomeVersion = '2026-11-18-campaign-presidency';
export const welcomeTitle = 'Welcome to TopicLLM.';
export const welcomeLetter = `
<p class="welcome-salutation">Dear researcher,</p>
<p>TopicLLM began with a question in my dissertation research at <strong>The University of Texas at Austin</strong>: what were alcohol companies posting about on social media during the COVID-19 pandemic?</p>
<p>Topic models can find patterns across thousands of texts. Qualitative research explains what those patterns mean. We wanted a clear computational workflow that brought these approaches together and kept researchers responsible for interpretation.</p>
<p>The <a href="https://arxiv.org/abs/2210.00707" target="_blank" rel="noopener"><em>Theme and Topic</em> framework (Gillies, Murthy, Brenton &amp; Olaniyan, 2022)</a> informed this work. TopicLLM makes the process executable: discover topics, propose names, synthesize themes, independently evaluate a classifier and estimate theme prevalence.</p>
<h3>One research program. A method you can build on.</h3>
<p>The dissertation used this approach across two studies. Study 1 identified themes in alcohol companies’ Twitter posts. Study 2 applied a selected theme to a larger corpus of general users’ posts and examined its relationship to potential exposure to brand messages. This repository develops the topic-to-prevalence workflow as reusable software; it does not implement every analysis in the dissertation.</p>
<p>“Twitter” and “tweets” preserve the terminology of the research period; the platform is now called X. The method can be adapted to other social media or text corpora, with appropriate sampling, domain-specific interpretation and fresh validation.</p>
<h3>Explore as a human. Implement with an agent.</h3>
<p>Explore the method here, then fork the repository or install the Python package. Your coding agent runs maintained scripts and model calls, keeps the evidence and prepares it for review. Researchers interpret themes in the context of their literature. Review and validation gates keep those decisions in human hands; agents must not invent results or approvals.</p>
<p>The <strong>dissertation and two papers show the research in action</strong>. They remain available for you and your agent to read; the underlying dissertation datasets are not distributed here. The hands-on demonstration applies the method to a separate, familiar public corpus: <strong>34,416 posts from Donald Trump’s public Twitter account, beginning with his June 16, 2015 campaign launch and ending with the archive on January 8, 2021.</strong>.</p>
<p>We discover topics during the campaign, develop human-defined themes, and test their measurement in presidential posts. You can inspect the entire chain, including where the classifier falls short: it did not meet the declared evaluation criteria. Its presidential assignments are an explicitly unvalidated illustration of the workflow. The standalone methods paper reports these limitations and connects each step to executable code.</p>
<p>This is a walkthrough of the methodology on new data, not a reproduction of the dissertation findings. Explore the model's output, try naming and classification, and practice interpreting themes. A research analysis still needs actual researcher review and independent validation. Probabilistic methods and changes in models, software or seeds can produce different outputs.</p>
<h3>An open invitation, with clear scientific boundaries.</h3>
<p>The dissertation and study preprints are available for you and your agents. The studies were revised and accepted under dissertation committee supervision, which is distinct from journal peer review. TopicLLM has not yet been independently replicated by other researchers; this release invites that work.</p>
<p>My hope in releasing the code, data and papers is that others will test, challenge and extend this work. Whether you are an undergraduate or a tenured professor, I am happy to help you get started. Feedback on the website, repository and method is welcome.</p>
<p>Thank you for your time, curiosity and care.</p>
<div class="welcome-signature"><strong>Jacob E. Thomas</strong><span>Creator of TopicLLM</span><a href="mailto:jethomasphd@gmail.com">Get in touch ↗</a><a href="https://github.com/jethomasphd/TopicLLM/issues" target="_blank" rel="noopener">Share feedback on GitHub ↗</a></div>
`;
