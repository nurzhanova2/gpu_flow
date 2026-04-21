export default function ActionButton({ children, tone = "default", size = "md", onClick, type = "button" }) {
  return (
    <button type={type} onClick={onClick} className={`action-btn action-btn-${tone} action-btn-${size}`}>
      {children}
    </button>
  );
}
