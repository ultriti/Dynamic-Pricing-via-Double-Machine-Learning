export default function StatCard({ label, value, note, icon: Icon }) {
  return (
    <section className="panel stat-card">
      <div className="stat-card-top">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </section>
  );
}
