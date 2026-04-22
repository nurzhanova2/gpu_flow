import { useMemo, useState } from "react";
import Card from "../../components/ui/Card";
import ActionButton from "../../components/ui/ActionButton";
import { useAuth } from "../../context/AuthContext";
import { validateRegisterForm } from "../../lib/validators";

const initialState = {
  username: "",
  full_name: "",
  email: "",
  team: "",
  password: "",
};

export default function RegisterPage({ onOpenLogin }) {
  const { register } = useAuth();
  const [form, setForm] = useState(initialState);
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const hasErrors = useMemo(() => Object.values(errors).some(Boolean), [errors]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
    setRequestError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = {
      username: form.username.trim(),
      full_name: form.full_name.trim(),
      email: form.email.trim().toLowerCase(),
      team: form.team.trim(),
      password: form.password,
    };
    const validationErrors = validateRegisterForm(payload);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      await register(payload);
    } catch (error) {
      setRequestError(`${error.code}: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-screen">
      <Card className="auth-card">
        <div className="auth-head">
          <h2>Регистрация</h2>
          <p>Создайте учётную запись пользователя для запуска сессий и работы с очередью.</p>
        </div>

        {requestError ? <div className="auth-alert auth-alert-error">{requestError}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input type="text" value={form.username} onChange={(event) => handleChange("username", event.target.value)} placeholder="new.user" />
            {errors.username ? <span className="field-error">{errors.username}</span> : null}
          </label>

          <label>
            Полное имя
            <input type="text" value={form.full_name} onChange={(event) => handleChange("full_name", event.target.value)} placeholder="Иван Иванов" />
            {errors.full_name ? <span className="field-error">{errors.full_name}</span> : null}
          </label>

          <label>
            Email
            <input type="email" value={form.email} onChange={(event) => handleChange("email", event.target.value)} placeholder="user@company.com" />
            {errors.email ? <span className="field-error">{errors.email}</span> : null}
          </label>

          <label>
            Команда
            <input type="text" value={form.team} onChange={(event) => handleChange("team", event.target.value)} placeholder="NLP" />
            {errors.team ? <span className="field-error">{errors.team}</span> : null}
          </label>

          <label>
            Пароль
            <div className="password-input-wrap">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) => handleChange("password", event.target.value)}
                placeholder="********"
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                title={showPassword ? "Скрыть пароль" : "Показать пароль"}
              >
                &#128065;
              </button>
            </div>
            {errors.password ? <span className="field-error">{errors.password}</span> : null}
          </label>

          <ActionButton tone="primary" type="submit" disabled={isSubmitting || hasErrors}>
            {isSubmitting ? "Создание..." : "Создать аккаунт"}
          </ActionButton>
        </form>

        <div className="auth-footer">
          <span>Уже зарегистрированы?</span>
          <button type="button" onClick={onOpenLogin}>Войти</button>
        </div>
      </Card>
    </div>
  );
}
