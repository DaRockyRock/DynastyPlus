import ArticleReader from './ArticleReader.jsx';
import { AppContext } from '../../context/AppContext.jsx';

// ArticleReader is a connected component (it reads `pointer` from AppContext and
// can fetch the expansion on demand). For the catalog we supply a minimal context
// and a fully pre-generated `detail` so it renders the reader layout without any
// network call.
const withApp = (Story) => (
  <AppContext.Provider value={{ pointer: { year: 2026, week: 1 } }}>
    <div className="view"><Story /></div>
  </AppContext.Provider>
);

export default {
  title: 'Domain/ArticleReader',
  component: ArticleReader,
  decorators: [withApp],
  parameters: { layout: 'fullscreen' },
};

// A pull quote is always lifted from the body. The detail below intentionally
// repeats the quote inside the second paragraph so the story exercises the
// de-duplication: the reader strips the echoed sentence and shows the line only
// once, as the bold callout.
const detail = {
  title: 'BIG TEN TITLE RACE WIDE OPEN: FIVE TEAMS WITH LEGITIMATE PLAYOFF HOPES',
  category: 'Big Ten Preview',
  accent: '#3b6fd4',
  dek: 'Ohio State is favored, but Michigan, Penn State, and others have real pathways to the postseason.',
  outlet: 'The Press Box',
  reporter: 'Dana Reyes',
  timestamp: '5h ago',
  sections: [
    'The Big Ten enters 2026 with more parity than in recent years. Ohio State remains the consensus favorite to win the conference at short odds, but Michigan\'s roster continuity and Penn State\'s defensive depth give the league multiple teams capable of competing for a playoff spot. Wisconsin, Minnesota, and even Iowa will look to surprise in what could be the most balanced season in the conference in years.',
    'In a league where three or four teams can make the playoff, every weekend becomes a referendum on a resume. The margin between a No. 4 seed and a January at home has rarely been thinner, and the schedule makers did the contenders no favors.',
    'Penn State returns nine starters on a defense that finished top ten nationally a year ago. If the offense takes even a modest step forward, the Nittany Lions have the profile of a team that plays deep into the postseason.',
    'For Michigan, the question is continuity at quarterback. The staff believes it has answered it. The rest of the conference is not so sure.',
  ],
  pull_quote: 'In a league where three or four teams can make the playoff, every weekend becomes a referendum on a resume.',
  quotes: [
    { speaker: 'Marcus Whitfield', role: 'QB, Penn State', text: 'We are not worried about the noise. We control how we prepare and how we play on Saturday, and the rest sorts itself out.' },
    { speaker: 'League sources', role: 'conference insider', text: 'People around the league will tell you this is the deepest the Big Ten has been at the top in a decade.' },
  ],
  stats: [
    { label: 'Nebraska scoring offense (2025)', value: 'Top 15 nationally' },
    { label: 'DeShawn Carter rushing yards (2025)', value: '1,041 yards, leads Big Ten' },
    { label: 'Marcus Whitfield passing (2025)', value: '2,418 yards, 22 TD, 4 INT' },
    { label: 'Conference title odds', value: '+320' },
  ],
  betting: {
    game: { matchup: 'OSU vs MICH', spread: 'OSU -6.5', total: 'O/U 52.5', moneyline: '-260 / +210' },
    futures: [
      { label: 'Penn State to make the Playoff', value: '+140' },
      { label: 'Michigan to win the Big Ten', value: '+450' },
    ],
  },
  elements: ['quotes', 'stats', 'betting'],
  source: 'mock',
};

export const FullArticle = {
  args: { article: { headline: detail.title, accent: detail.accent, detail }, onBack: () => {} },
};

// A leaner national item: body and a pull quote, no stats or betting rail.
export const TextOnly = {
  args: {
    article: {
      headline: detail.title,
      accent: '#8b5cf6',
      detail: {
        ...detail,
        accent: '#8b5cf6',
        category: 'National',
        stats: [],
        betting: null,
        quotes: [],
        elements: [],
      },
    },
    onBack: () => {},
  },
};
