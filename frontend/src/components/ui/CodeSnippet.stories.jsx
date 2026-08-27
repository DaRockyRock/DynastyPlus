import CodeSnippet from './CodeSnippet.jsx';

export default {
  title: 'UI/CodeSnippet',
  component: CodeSnippet,
  parameters: { layout: 'padded' },
};

export const Command = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <CodeSnippet label="Start Dynasty+ Tools">python run.py</CodeSnippet>
    </div>
  ),
};

export const Url = {
  render: () => (
    <div style={{ maxWidth: 520 }}>
      <CodeSnippet>http://127.0.0.1:5050</CodeSnippet>
    </div>
  ),
};
