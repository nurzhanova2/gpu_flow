export default function ActionButton({
  children,
  tone = "default",
  size = "md",
  onClick,
  type = "button",
  disabled = false,
  className = "",
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`action-btn action-btn-${tone} action-btn-${size} ${className}`.trim()}
    >
      {children}
    </button>
  );
}
