import RankCard from './RankCard.jsx';
import { pollEntries } from '../fixtures.js';

export default {
  title: 'Domain/RankCard',
  component: RankCard,
};

export const Default = {
  args: { entry: pollEntries[0], onOpen: () => {}, onCompare: () => {} },
};

export const UserTeam = {
  args: { entry: pollEntries[4], isUser: true, onOpen: () => {}, onCompare: () => {} },
};

export const PinnedForComparison = {
  args: { entry: pollEntries[2], compared: true, onOpen: () => {}, onCompare: () => {} },
};

export const WithoutCompare = {
  args: { entry: pollEntries[7], onOpen: () => {} },
};
