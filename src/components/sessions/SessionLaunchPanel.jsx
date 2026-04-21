import { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import ActionButton from "../ui/ActionButton";

export default function SessionLaunchPanel({ profiles }) {
  const initial = profiles.find((profile) => profile.recommended)?.id || profiles[0]?.id;
  const [selectedProfile, setSelectedProfile] = useState(initial);

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
        <ActionButton tone="primary">Запустить новую сессию</ActionButton>
        <ActionButton tone="default">Открыть последний Notebook</ActionButton>
      </div>
    </Card>
  );
}
