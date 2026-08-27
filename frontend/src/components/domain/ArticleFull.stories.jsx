import ArticleFull from './ArticleFull.jsx';
import { article } from '../fixtures.js';

export default {
  title: 'Domain/ArticleFull',
  component: ArticleFull,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 560 }}><ArticleFull article={article} /></div> };
