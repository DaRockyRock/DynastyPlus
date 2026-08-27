import ClassGradeCard from './ClassGradeCard.jsx';

export default {
  title: 'Domain/ClassGradeCard',
  component: ClassGradeCard,
  parameters: { layout: 'padded' },
};

export const Default = {
  render: () => (
    <div style={{ width: 460 }}>
      <ClassGradeCard grade={{ grade: 'B+', summary: 'Nebraska treated the portal as a scalpel rather than a sledgehammer, prioritizing two high-floor starters over volume.' }} />
    </div>
  ),
};
