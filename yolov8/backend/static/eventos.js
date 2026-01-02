document.addEventListener("DOMContentLoaded", () => {
    // --- Referencias a elementos del DOM ---
    const video = document.getElementById('video-stream');
    const salirButton = document.getElementById('salir');
    const loginUrl = "ingreso.html";
    const statusText = document.getElementById('status-text');
    
    // --- Lógica para el streaming de video en tiempo real ---
    if (video) {
        // Conectamos el elemento <video> directamente a la URL del stream de FastAPI.
        video.src = "http://127.0.0.1:8000/video_feed";
        video.play(); // Esto inicia la reproducción del stream.
        
        // El resto del código de escaneo con setInterval ya no es necesario.
        // La detección, el seguimiento y el conteo ocurren en el servidor.
        
        // Opcional: Manejar el estado de la conexión
        video.addEventListener('loadstart', () => {
            if (statusText) statusText.textContent = "Conectando al stream...";
        });
        
        video.addEventListener('error', (e) => {
            console.error("Error al conectar al stream de video:", e);
            if (statusText) {
                statusText.textContent = "Error: No se pudo conectar al stream de video.";
                statusText.classList.add('text-red-500');
            }
        });
        
        video.addEventListener('canplay', () => {
            if (statusText) statusText.textContent = "Conexión establecida.";
        });
    }

    // --- Botón salir ---
    if (salirButton) {
        salirButton.addEventListener("click", () => {
            // No es necesario detener el stream de la cámara, ya que el navegador
            // lo cerrará automáticamente al salir de la página.
            window.location.href = loginUrl;
        });
    }

    // --- El resto de tu lógica para formularios y tooltips se mantiene igual ---
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

    const infoIcons = document.querySelectorAll('.info-icon');
    infoIcons.forEach(icon => {
        const tooltip = icon.closest('.relative').querySelector('.info-tooltip');
        icon.addEventListener('mouseenter', () => {
            tooltip.classList.add('visible');
        });
        icon.addEventListener('mouseleave', () => {
            tooltip.classList.remove('visible');
        });
    });

    // --- Funciones auxiliares para formularios ---
    async function registrarUsuario(form, mensaje) {
        const formData = new FormData(form);
        const usuario = {
            nombre: formData.get("nombre"),
            email: formData.get("email"), 
            password: formData.get("password"),
            edad: parseInt(formData.get("edad"))
        };

        try {
            const response = await fetch("http://127.0.0.1:8000/usuarios", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
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
            const response = await fetch("http://127.0.0.1:8000/ingreso", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(loginData)
            });

            const data = await response.json();
            console.log("Respuesta de FastAPI:", data);

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


// Mantenemos la función para los contadores, ya que se actualiza cada 2 segundos.
async function actualizarContadores() {
    try {
        const response = await fetch("http://127.0.0.1:8000/get_analisis");
        const data = await response.json();

        document.getElementById("total-count").textContent = data.total || 0;
        document.getElementById("buenos-count").textContent = data.por_etiqueta["sano"] || 0;
        document.getElementById("sarna-count").textContent = data.por_etiqueta["sarna-negra"] || 0;
        document.getElementById("antracnosis-count").textContent = data.por_etiqueta["antracnosis"] || 0;

    } catch (error) {
        console.error("Error al obtener contadores:", error);
    }
}

// Llamar la función cada 2 segundos para mantener actualizado el panel
setInterval(actualizarContadores, 2000);