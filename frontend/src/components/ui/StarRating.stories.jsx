import StarRating from './StarRating.jsx';

export default {
  title: 'UI/StarRating',
  component: StarRating,
  parameters: { layout: 'centered' },
  argTypes: { value: { control: { type: 'range', min: 0, max: 5 } } },
};

export const FiveStar = { args: { value: 5 } };
export const FourStar = { args: { value: 4 } };
export const ThreeStar = { args: { value: 3 } };

export const Scale = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {[5, 4, 3, 2].map((v) => <StarRating key={v} value={v} />)}
    </div>
  ),
};
