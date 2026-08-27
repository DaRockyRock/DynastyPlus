import GuideStep from './GuideStep.jsx';
import CodeSnippet from '../ui/CodeSnippet.jsx';
import Callout from '../ui/Callout.jsx';
import { ExternalLinkIcon } from '../ui/icons.jsx';

// Provider-specific "how to connect" instructions. Pure copy + links; the form
// and test button live alongside it in the wizard.
const CONSOLE_URL = 'https://console.anthropic.com/settings/keys';

export default function SetupGuide({ provider }) {
  if (provider === 'local') {
    return (
      <div className="setup-guide">
        <ol className="guide-list">
          <GuideStep n={1} title="Run a model on your machine">
            Use a tool like Ollama, LM Studio, or llama.cpp to serve any model you like with an
            OpenAI-compatible API.
          </GuideStep>
          <GuideStep n={2} title="Find its address">
            Copy the server's base URL. With Ollama it looks like this:
            <CodeSnippet>http://localhost:11434/v1</CodeSnippet>
          </GuideStep>
          <GuideStep n={3} title="Enter the URL and model">
            Paste the base URL on the right, add the model you are running (for example llama3.1),
            and run a test.
          </GuideStep>
        </ol>
        <Callout tone="info" title="Works with any OpenAI-compatible server">
          That is the standard local model tools speak - Ollama, LM Studio, llama.cpp, vLLM and more.
        </Callout>
      </div>
    );
  }

  return (
    <div className="setup-guide">
      <ol className="guide-list">
        <GuideStep n={1} title="Open the Anthropic Console">
          Sign in or create an account, then add billing.
          <a className="guide-link" href={CONSOLE_URL} target="_blank" rel="noreferrer">
            console.anthropic.com <ExternalLinkIcon size={13} />
          </a>
        </GuideStep>
        <GuideStep n={2} title="Create an API key">
          Go to API Keys, create one, and copy it. It starts with sk-ant-.
        </GuideStep>
        <GuideStep n={3} title="Paste it and pick a model">
          Drop the key on the right and choose a model. Haiku is the fast, cheap default.
        </GuideStep>
      </ol>
      <Callout tone="info" title="Your key stays on this machine">
        It is saved locally in data/llm.json and used only to reach Anthropic.
      </Callout>
    </div>
  );
}
