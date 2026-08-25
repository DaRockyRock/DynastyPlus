// Elevated surface container. `as` allows a different semantic element.
export default function Card({ as: Tag = 'div', className = '', children, ...rest }) {
  return (
    <Tag className={['card', className].filter(Boolean).join(' ')} {...rest}>
      {children}
    </Tag>
  );
}
