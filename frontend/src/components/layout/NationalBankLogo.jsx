export default function NationalBankLogo({ className = "", title = "Национальный Банк" }) {
  return (
    <img
      className={className}
      src="/National_Bank_of_Kazakhstan_logo.svg.png"
      alt={title}
      title={title}
      loading="eager"
      decoding="async"
    />
  );
}
