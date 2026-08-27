import SectionTitle from './SectionTitle.jsx';
import SourcePill from './SourcePill.jsx';
import RegenerateButton from './RegenerateButton.jsx';

export default {
  title: 'UI/SectionTitle',
  component: SectionTitle,
  parameters: { layout: 'padded' },
};

export const Plain = { args: { children: 'Top Stories' } };

export const WithRight = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle right={<><SourcePill source="mock" /><RegenerateButton /></>}>
        Top Stories
      </SectionTitle>
    </div>
  ),
};

export const WithNote = {
  render: () => (
    <div style={{ width: 520 }}>
      <SectionTitle note="Ranked by the matchup algorithm">Marquee Matchups</SectionTitle>
    </div>
  ),
};
