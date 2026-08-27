import CodeSnippet from './CodeSnippet.jsx';

export default {
  title: 'UI/CodeSnippet',
  component: CodeSnippet,
  parameters: { layout: 'padded' },
};

export const Command = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <CodeSnippet label="Start your local server">claude-proxy --port 8787</CodeSnippet>
    </div>
  ),
};

export const Url = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <CodeSnippet>http://127.0.0.1:8787</CodeSnippet>
    </div>
  ),
};
