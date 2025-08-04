document.getElementById("loginForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  console.log("Intento de login:", email, password);
  // Aquí llamarías a tu lógica del controller o store
});
