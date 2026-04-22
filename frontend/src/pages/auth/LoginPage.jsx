import { useMemo, useState } from "react";
import Card from "../../components/ui/Card";
import ActionButton from "../../components/ui/ActionButton";
import { useAuth } from "../../context/AuthContext";
import { validateLoginForm } from "../../lib/validators";

export default function LoginPage({ onOpenRegister }) {
  const { login, forcedReason, clearForcedReason } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
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
      password: form.password,
    };
    const validationErrors = validateLoginForm(payload);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) return;

    setIsSubmitting(true);
    try {
      await login(payload);
      clearForcedReason();
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
          <h2>Вход в GPUFlow</h2>
          <p>Используйте рабочую учётную запись для доступа к GPU-очереди и JupyterHub.</p>
        </div>

        {forcedReason ? <div className="auth-alert">{forcedReason}</div> : null}
        {requestError ? <div className="auth-alert auth-alert-error">{requestError}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input
              type="text"
              value={form.username}
              onChange={(event) => handleChange("username", event.target.value)}
              autoComplete="username"
              placeholder="demo"
            />
            {errors.username ? <span className="field-error">{errors.username}</span> : null}
          </label>

          <label>
            Пароль
            <div className="password-input-wrap">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) => handleChange("password", event.target.value)}
                autoComplete="current-password"
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
            {isSubmitting ? "Вход..." : "Войти"}
          </ActionButton>
        </form>

        <div className="auth-footer">
          <span>Нет аккаунта?</span>
          <button type="button" onClick={onOpenRegister}>Зарегистрироваться</button>
        </div>
      </Card>
    </div>
  );
}
