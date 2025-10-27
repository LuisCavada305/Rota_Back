type AvatarProps = {
  name?: string | null;
  email?: string | null;        // fallback opcional
  src?: string | null;
  size?: number;
  className?: string;
};

function getInitials(name?: string | null, email?: string | null) {
  const n = (name ?? "").trim();
  if (n) {
    return n
      .split(/\s+/)                // quebra por espaços
      .slice(0, 2)                 // até 2 palavras
      .map(s => s[0]!.toUpperCase())
      .join("");
  }
  const e = (email ?? "").trim();
  if (e) return e.slice(0, 2)!.toUpperCase();
  return "?";
}

export default function Avatar({ name, email, src, size = 28, className }: AvatarProps) {
  const initials = getInitials(name, email);

  if (src) {
    return (
      <img
        src={src}
        alt={name ?? email ?? "Usuário"}
        width={size}
        height={size}
        className={`avatar-img ${className ?? ""}`}
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className={`avatar-fallback ${className ?? ""}`}
      style={{ width: size, height: size }}
      aria-label={name ?? email ?? "Usuário"}
      title={name ?? email ?? "Usuário"}
    >
      {initials}
    </div>
  );
}
