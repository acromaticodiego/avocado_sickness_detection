// Logica de los formularios de ingreso y registro.
//
// Este archivo solo lo cargan ingreso.html y registro.html. El panel principal
// (principal.html) funciona con React en app.jsx, asi que todo lo que habia
// aqui sobre el video, el selector de camara, el umbral de confianza y los
// contadores estaba duplicado y muerto: esas paginas no tienen esos elementos.

document.addEventListener("DOMContentLoaded", () => {
    const registroForm = document.getElementById("registroForm");
    const registroMensaje = document.getElementById("mensaje");
    if (registroForm) {
        registroForm.addEventListener("submit", (e) => {
            e.preventDefault();
            registrarUsuario(registroForm, registroMensaje);
        });
    }

    const loginForm = document.getElementById("loginForm");
    const loginMensaje = document.getElementById("loginMensaje");
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            e.preventDefault();
            loginUsuario(loginForm, loginMensaje);
        });
    }

    async function registrarUsuario(form, mensaje) {
        const formData = new FormData(form);
        const usuario = {
            nombre: formData.get("nombre"),
            email: formData.get("email"),
            password: formData.get("password"),
            edad: parseInt(formData.get("edad"))
        };

        try {
            const response = await fetch("/usuarios", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(usuario)
            });

            if (response.ok) {
                const data = await response.json();
                mensaje.textContent = `Usuario ${data.nombre} registrado con éxito!`;
                mensaje.style.color = "green";
                form.reset();
            } else {
                const error = await response.json();
                mensaje.textContent = `Error: ${error.detail}`;
                mensaje.style.color = "red";
            }
        } catch (err) {
            console.error("Error al conectar con el servidor:", err);
            mensaje.textContent = "No se pudo conectar al servidor.";
            mensaje.style.color = "red";
        }
    }

    async function loginUsuario(form, mensaje) {
        const formData = new FormData(form);
        const loginData = {
            username: formData.get("username"),
            password: formData.get("password")
        };

        try {
            const response = await fetch("/ingreso", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(loginData)
            });

            const data = await response.json();
            if (response.ok) {
                window.location.href = "principal.html";
            } else {
                mensaje.textContent = data.detail || "Usuario no encontrado";
            }
        } catch (err) {
            console.error("Error de conexión:", err);
            mensaje.textContent = "No se pudo conectar con el servidor";
        }
    }
});
