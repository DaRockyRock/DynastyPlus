import StorySlider from './StorySlider.jsx';
import { stories, markedStories } from '../fixtures.js';

export default {
  title: 'Domain/StorySlider',
  component: StorySlider,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 760 }}>
      <StorySlider stories={stories} watermarkEspnId={158} />
    </div>
  ),
};

export const SingleStory = {
  render: () => (
    <div style={{ width: 760 }}>
      <StorySlider stories={stories.slice(0, 1)} watermarkEspnId={158} />
    </div>
  ),
};

// Each story's `marks` drive the crisp top-right logo bug: a group cluster, a
// matchup VS, and a conference mark, respectively.
export const WithMarks = {
  render: () => (
    <div style={{ width: 760 }}>
      <StorySlider stories={markedStories} watermarkEspnId={158} />
    </div>
  ),
};

// National stories carry their own team's espn_id, so each slide shows that
// team's logo; the program story (no espn_id) keeps the user's watermark.
export const NationalMix = {
  render: () => (
    <div style={{ width: 760 }}>
      <StorySlider
        watermarkEspnId={158}
        stories={[
          { category: 'Program', accent: '#e41c38', scope: 'program',
            headline: 'New era at Nebraska: a fresh staff takes over',
            subheadline: 'The rebuild starts now.', lede: 'A new staff inherits a proud program.',
            byline: 'Dana Reyes, The Press Box' },
          { category: 'CFP watch', accent: '#3b82f6', scope: 'national', espn_id: 194,
            headline: 'Ohio State headlines the preseason top 25',
            subheadline: 'The Buckeyes open at No. 1.', lede: 'Ohio State sit atop the preseason poll.',
            byline: 'Marcus Hale, Saturday Authority' },
          { category: 'Heisman watch', accent: '#eab308', scope: 'national', espn_id: 2483,
            headline: 'Oregon leads a loaded chase',
            subheadline: 'The Ducks are right there.', lede: 'Oregon headline the contenders.',
            byline: 'Camille Booker, The Rundown' },
        ]}
      />
    </div>
  ),
};
