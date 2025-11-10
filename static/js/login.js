const loginPanel = document.getElementById('loginPanel');
        const registerPanel = document.getElementById('registerPanel');

        function showRegister() {
    loginPanel.classList.remove('active');
    registerPanel.classList.add('active');

    // Ocultar mazo de cartas
    const cardContainer = document.querySelector('.card-container');
    if (cardContainer) cardContainer.style.display = 'none';
}

function showLogin() {
    registerPanel.classList.remove('active');
    loginPanel.classList.add('active');

    // Mostrar mazo de cartas
    const cardContainer = document.querySelector('.card-container');
    if (cardContainer) cardContainer.style.display = 'flex';
}


        // Construir phone completo con +57 antes de enviar
        document.addEventListener('DOMContentLoaded', function () {
          const registerForm = document.querySelector('#registerPanel form[action="/register"]');
          if (registerForm) {
            registerForm.addEventListener('submit', function (e) {
              const local = document.getElementById('phone_local');
              const full = document.getElementById('phone_full');
              if (local && full) {
                const digits = (local.value || '').replace(/\D/g, '');
                if (!digits) return;
                full.value = '+57' + digits;
              }
            });
          }
        });

        // Generar usuario sugerido automáticamente
        document.getElementById("first_name").addEventListener("input", suggestUsername);
        document.getElementById("last_name").addEventListener("input", suggestUsername);

        function suggestUsername() {
            const first = document.getElementById("first_name").value.trim().toLowerCase();
            const last = document.getElementById("last_name").value.trim().toLowerCase();
            if (first && last) {
                const randomNum = Math.floor(Math.random() * 1000);
                document.getElementById("register_username").value = first + "." + last + randomNum;
            }
        }

        // Validación de contraseña
        function validatePassword() {
          const password = document.getElementById("register_password").value;
          const repeat = document.getElementById("register_password_repeat").value;
          const errorDiv = document.getElementById("passwordError");
          const repeatErrorDiv = document.getElementById("repeatPasswordError");
          const helpDiv = document.getElementById("passwordHelp");
          const regex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$/;

          let valid = true;

          if (!regex.test(password)) {
            helpDiv.style.display = "block";
            errorDiv.style.display = "none";
            valid = false;
          } else {
            helpDiv.style.display = "none";
            errorDiv.style.display = "none";
          }

          if (password !== repeat) {
            repeatErrorDiv.style.display = "block";
            valid = false;
          } else {
            repeatErrorDiv.style.display = "none";
          }

          return valid;
        }

        // Mostrar mensaje en tiempo real al escribir
        document.getElementById("register_password").addEventListener("input", function() {
          const password = this.value;
          const helpDiv = document.getElementById("passwordHelp");
          const regex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$/;
          if (!regex.test(password)) {
            helpDiv.style.display = "block";
          } else {
            helpDiv.style.display = "none";
          }
        });

        document.getElementById("register_password_repeat").addEventListener("input", function() {
          const password = document.getElementById("register_password").value;
          const repeat = this.value;
          const errorDiv = document.getElementById("repeatPasswordError");
          if (repeat && password !== repeat) {
            errorDiv.style.display = "block";
          } else {
            errorDiv.style.display = "none";
          }
        });

        // Opcional: también valida al escribir en el primer campo
        document.getElementById("register_password").addEventListener("input", function() {
          const password = this.value;
          const repeat = document.getElementById("register_password_repeat").value;
          const errorDiv = document.getElementById("repeatPasswordError");
          if (repeat && password !== repeat) {
            errorDiv.style.display = "block";
          } else {
            errorDiv.style.display = "none";
          }
        });

        function togglePassword(inputId, icon) {
          const input = document.getElementById(inputId);
          const eye = icon.querySelector('.eye-icon:not(.eye-off)');
          const eyeOff = icon.querySelector('.eye-icon.eye-off');
          if (input.type === "password") {
            input.type = "text";
            eye.style.display = "none";
            eyeOff.style.display = "inline";
          } else {
            input.type = "password";
            eye.style.display = "inline";
            eyeOff.style.display = "none";
          }
        }

        document.getElementById("register_email").addEventListener("input", function() {
          const email = this.value;
          const errorDiv = document.getElementById("emailError");
          if (!email) {
            errorDiv.style.display = "none";
            return;
          }
          fetch('/check_email', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email})
          })
          .then(res => res.json())
          .then(data => {
            if (data.exists) {
              errorDiv.textContent = "Este correo ya está registrado.";
              errorDiv.style.display = "block";
            } else {
              errorDiv.style.display = "none";
            }
          });
        });

        document.getElementById("register_username").addEventListener("input", function() {
          const username = this.value;
          const errorDiv = document.getElementById("usernameError");
          const suggestionsDiv = document.getElementById("usernameSuggestions");
          if (!username) {
            errorDiv.style.display = "none";
            suggestionsDiv.style.display = "none";
            return;
          }
          fetch('/check_username', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username})
          })
          .then(res => res.json())
          .then(data => {
            if (data.exists) {
              errorDiv.textContent = "Este usuario ya existe";
              errorDiv.style.display = "block";
              if (data.suggestions && data.suggestions.length > 0) {
                suggestionsDiv.textContent = "Sugerencias: " + data.suggestions.join(", ");
                suggestionsDiv.style.display = "block";
              } else {
                suggestionsDiv.style.display = "none";
              }
            } else {
              errorDiv.style.display = "none";
              suggestionsDiv.style.display = "none";
            }
          });
        });

        function showForgotModal() {
          document.getElementById('forgotModal').style.display = 'flex';
          document.getElementById('forgotMessage').textContent = '';
          document.getElementById('forgot_email').value = '';
          document.getElementById('forgotForm').style.display = 'block';
          document.getElementById('forgotSuccess').style.display = 'none';
        }
        function closeForgotModal() {
          document.getElementById('forgotModal').style.display = 'none';
        }
        
  function submitForgot(event) {
  event.preventDefault();

  const email = document.getElementById('forgot_email').value;
  const submitButton = document.getElementById('forgotSubmit');
  const btnText = submitButton.querySelector('.btn-text');
  const spinner = submitButton.querySelector('.spinner');

  // Mostrar spinner y ocultar texto del botón
  btnText.style.display = 'none';
  spinner.style.display = 'inline-block';

  fetch('/forgot_password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email})
  })
  .then(res => res.json())
  .then(data => {
    // Ocultar spinner y mostrar texto del botón de nuevo
    spinner.style.display = 'none';
    btnText.style.display = 'inline';

    if (data.success) {
      // Oculta el formulario y muestra el mensaje de éxito
      document.getElementById('forgotForm').style.display = 'none';
      const successDiv = document.getElementById('forgotSuccess');
      successDiv.textContent = "¡Listo! Se ha enviado un correo para restablecer tu contraseña. Por favor revisa tu bandeja de entrada.";
      successDiv.style.display = 'flex';
    } else {
      // Muestra el mensaje de error debajo del input
      const messageDiv = document.getElementById('forgotMessage');
      messageDiv.style.color = 'red';
      messageDiv.textContent = data.message;
    }
  })
  .catch(() => {
    // En caso de error de red
    spinner.style.display = 'none';
    btnText.style.display = 'inline';
    const messageDiv = document.getElementById('forgotMessage');
    messageDiv.style.color = 'red';
    messageDiv.textContent = "Ocurrió un error. Intenta de nuevo más tarde.";
  });
}


// ======== RECORDAR CREDENCIALES ========
document.addEventListener("DOMContentLoaded", () => {
  const usernameInput = document.getElementById("login_username");
  const passwordInput = document.getElementById("login_password");
  const rememberCheckbox = document.getElementById("rememberMe");
  const loader = document.getElementById('globalLoader');

  // Evitar error si no existe (por seguridad)
  if (!usernameInput || !passwordInput || !rememberCheckbox) return;

  // Cargar datos guardados (si existen)
  const savedUsername = localStorage.getItem("savedUsername");
  const savedPassword = localStorage.getItem("savedPassword");

  if (savedUsername && savedPassword) {
    usernameInput.value = savedUsername;
    passwordInput.value = savedPassword;
    rememberCheckbox.checked = true;
  }

  // Guardar o eliminar credenciales al enviar el formulario
  const loginForm = document.querySelector('form[action="/login"]');
  if (loginForm) {
    loginForm.addEventListener("submit", () => {
      if (rememberCheckbox.checked) {
        localStorage.setItem("savedUsername", usernameInput.value);
        localStorage.setItem("savedPassword", passwordInput.value);
      } else {
        localStorage.removeItem("savedUsername");
        localStorage.removeItem("savedPassword");
      }
      // Mostrar overlay inmediatamente
      if (loader) loader.classList.add('show');
    });

    // También si el usuario presiona Enter en los campos
    [usernameInput, passwordInput].forEach(el => {
      el.addEventListener('keydown', (e)=>{
        if (e.key === 'Enter') {
          if (loader) loader.classList.add('show');
        }
      });
    });
  }

});


