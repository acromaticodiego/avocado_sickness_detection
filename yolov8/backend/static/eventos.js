document.addEventListener("DOMContentLoaded", () => {
    // --- Referencias a elementos del DOM ---
    const video = document.getElementById('video-stream');
    const salirButton = document.getElementById('salir');
    const loginUrl = "ingreso.html";
    const statusText = document.getElementById('status-text');
    const selectCamara = document.getElementById('select-camara');
    
    // --- Lógica para el streaming de video en tiempo real ---
    if (video) {
        // Solo asignar src si el elemento no tiene ya /video_feed asignado en el HTML
        if (!video.getAttribute("src") || video.getAttribute("src") === "") {
            video.src = "/video_feed";
        }

        video.onerror = () => {
            console.error("Error al conectar al stream de video");
            if (statusText) {
                statusText.textContent = "Error: No se pudo conectar al stream de video.";
                statusText.classList.add('text-red-500');
            }
        };

        video.onload = () => {
            if (statusText) {
                statusText.textContent = "Conexión establecida.";
                statusText.classList.remove('text-red-500');
            }
        };
    }

    // --- Selector dinámico de cámaras ---
    if (selectCamara) {
        // Cargar cámaras disponibles desde el backend
        fetch("/camaras")
            .then(res => res.json())
            .then(data => {
                if (data.camaras_disponibles && data.camaras_disponibles.length > 0) {
                    selectCamara.innerHTML = "";
                    data.camaras_disponibles.forEach(idx => {
                        const opt = document.createElement("option");
                        opt.value = idx;
                        opt.textContent = idx === 1 ? `Cámara USB (Índice ${idx})` :
                                          idx === 0 ? `Cámara PC / Integrada (Índice ${idx})` :
                                          `Cámara Externa (Índice ${idx})`;
                        if (idx === data.camara_actual) {
                            opt.selected = true;
                        }
                        selectCamara.appendChild(opt);
                    });
                }
            })
            .catch(err => console.warn("No se pudo obtener lista de cámaras:", err));

        // Evento al cambiar de cámara en el select
        selectCamara.addEventListener("change", async (e) => {
            const nuevoIndice = e.target.value;
            try {
                const res = await fetch(`/camaras/seleccionar/${nuevoIndice}`, { method: "POST" });
                if (res.ok) {
                    // Recargar stream con timestamp para evitar cache
                    if (video) {
                        video.src = `/video_feed?t=${Date.now()}`;
                    }
                } else {
                    alert("No se pudo cambiar a la cámara seleccionada.");
                }
            } catch (err) {
                console.error("Error al cambiar cámara:", err);
            }
        });
    }

    // --- Control de umbral de confianza (sensibilidad) ---
    const sliderConfianza = document.getElementById("confianza-slider");
    const valConfianza = document.getElementById("confianza-val");
    if (sliderConfianza && valConfianza) {
        sliderConfianza.addEventListener("input", (e) => {
            valConfianza.textContent = `${e.target.value}%`;
        });

        sliderConfianza.addEventListener("change", async (e) => {
            const valorDecimal = (parseFloat(e.target.value) / 100).toFixed(2);
            try {
                await fetch(`/confianza?valor=${valorDecimal}`, { method: "POST" });
                console.log("Confianza actualizada:", valorDecimal);
            } catch (err) {
                console.error("Error al actualizar umbral de confianza:", err);
            }
        });
    }

    // --- Botón reiniciar conteo ---
    const btnReset = document.getElementById("btn-reiniciar-conteo");
    if (btnReset) {
        btnReset.addEventListener("click", async () => {
            try {
                const res = await fetch("/reiniciar_contadores", { method: "POST" });
                if (res.ok) {
                    document.getElementById("total-count").textContent = "0";
                    document.getElementById("buenos-count").textContent = "0";
                    document.getElementById("sarna-count").textContent = "0";
                    document.getElementById("antracnosis-count").textContent = "0";
                }
            } catch (err) {
                console.error("Error al reiniciar contadores:", err);
            }
        });
    }

    // --- Botón salir ---
    if (salirButton) {
        salirButton.addEventListener("click", () => {
            window.location.href = loginUrl;
        });
    }

    // --- Formularios de registro y login ---
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
            const response = await fetch("/usuarios", {
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
            const response = await fetch("/ingreso", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
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

// Mantenemos la función para los contadores, actualizada cada 2 segundos
async function actualizarContadores() {
    try {
        const response = await fetch("/get_analisis");
        if (!response.ok) return;
        const data = await response.json();

        const totalEl = document.getElementById("total-count");
        const buenosEl = document.getElementById("buenos-count");
        const sarnaEl = document.getElementById("sarna-count");
        const antracnosisEl = document.getElementById("antracnosis-count");

        if (totalEl) totalEl.textContent = data.total || 0;
        if (buenosEl && data.por_etiqueta) buenosEl.textContent = data.por_etiqueta["sano"] || 0;
        if (sarnaEl && data.por_etiqueta) sarnaEl.textContent = data.por_etiqueta["sarna-negra"] || 0;
        if (antracnosisEl && data.por_etiqueta) antracnosisEl.textContent = data.por_etiqueta["antracnosis"] || 0;

    } catch (error) {
        console.error("Error al obtener contadores:", error);
    }
}

// Llamar la función cada 2 segundos para mantener actualizado el panel
setInterval(actualizarContadores, 2000);