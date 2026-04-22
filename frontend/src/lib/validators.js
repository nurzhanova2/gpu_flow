const USERNAME_REGEX = /^[a-zA-Z0-9_.-]+$/;

function validatePassword(password) {
  if (!password || password.length < 8 || password.length > 128) {
    return "Пароль должен быть от 8 до 128 символов";
  }
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return "Пароль должен содержать буквы и цифры";
  }
  return "";
}

export function validateLoginForm({ username, password }) {
  const errors = {};

  if (!username || !USERNAME_REGEX.test(username)) {
    errors.username = "Username: латиница, цифры, _, ., -";
  }

  const passwordError = validatePassword(password);
  if (passwordError) {
    errors.password = passwordError;
  }

  return errors;
}

export function validateRegisterForm({ username, full_name, email, team, password }) {
  const errors = validateLoginForm({ username, password });

  if (!full_name || full_name.trim().length < 2 || full_name.trim().length > 120) {
    errors.full_name = "ФИО: от 2 до 120 символов";
  }

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email || "");
  if (!emailValid) {
    errors.email = "Введите валидный email";
  }

  const teamLength = (team || "").trim().length;
  if (teamLength < 2 || teamLength > 80) {
    errors.team = "Команда: от 2 до 80 символов";
  }

  return errors;
}
