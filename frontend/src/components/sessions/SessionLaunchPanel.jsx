import { useEffect, useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import ActionButton from "../ui/ActionButton";

export default function SessionLaunchPanel({ profiles, onLaunch, onOpenLast, launchPending = false, openPending = false }) {
  const initial = profiles.find((profile) => profile.recommended)?.id || profiles[0]?.id;
  const [selectedProfile, setSelectedProfile] = useState(initial);

  useEffect(() => {
    if (!profiles.length) return;
    if (!selectedProfile || !profiles.some((profile) => profile.id === selectedProfile)) {
      setSelectedProfile(profiles.find((profile) => profile.recommended)?.id || profiles[0].id);
    }
  }, [profiles, selectedProfile]);

  return (
    <Card>
      <div className="panel-head">
        <h3>Запуск сессии</h3>
        <Badge tone="green">JupyterHub</Badge>
      </div>

      <p className="muted-text">Выберите вычислительный профиль для запуска рабочей среды.</p>

      <div className="profile-grid">
        {profiles.map((profile) => {
          const selected = profile.id === selectedProfile;
          return (
            <button
              key={profile.id}
              type="button"
              className={`profile-card ${selected ? "profile-card-selected" : ""}`}
              onClick={() => setSelectedProfile(profile.id)}
            >
              <div className="profile-head">
                <strong>{profile.label}</strong>
                <Badge tone={selected ? "green" : "neutral"}>{profile.tag}</Badge>
              </div>
              <p>{profile.description}</p>
              <div className="profile-meta">
                <span>{profile.icon}</span>
                <span>{profile.queue}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="launch-actions">
        <ActionButton tone="primary" onClick={() => onLaunch?.(selectedProfile)} disabled={launchPending || !selectedProfile}>
          {launchPending ? "Запуск..." : "Запустить новую сессию"}
        </ActionButton>
        <ActionButton tone="default" onClick={() => onOpenLast?.()} disabled={openPending}>
          {openPending ? "Открытие..." : "Открыть последний Notebook"}
        </ActionButton>
      </div>
    </Card>
  );
}
