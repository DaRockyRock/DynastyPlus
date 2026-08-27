import ArticleCard from './ArticleCard.jsx';
import { article } from '../fixtures.js';

export default {
  title: 'Domain/ArticleCard',
  component: ArticleCard,
  parameters: { layout: 'padded' },
};

export const Default = { render: () => <div style={{ width: 460 }}><ArticleCard article={article} /></div> };

export const Recruiting = {
  render: () => (
    <div style={{ width: 460 }}>
      <ArticleCard article={{ ...article, category: 'Recruiting', accent: '#22c55e', headline: 'Five-star WR sets official visit', outlet: 'RecruitWire', reporter: 'Theo Marsh', reliability: 82 }} />
    </div>
  ),
};
