const { useState, useEffect, useCallback, useRef } = React;

// --- Iconos SVG personalizados para evitar dependencias pesadas ---
const AvocadoIcon = ({ className = "w-6 h-6" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M12 2C7.5 2 4 6.5 4 12c0 5 3.5 10 8 10s8-5 8-10c0-5.5-3.5-10-8-10z" fill="rgba(132, 204, 22, 0.25)" stroke="#a3e635"/>
    <circle cx="12" cy="13" r="4" fill="#78350f" stroke="#ca8a04" strokeWidth="1.5"/>
    <circle cx="11.2" cy="12.2" r="1.2" fill="#fef08a" opacity="0.6"/>
  </svg>
);

const CameraIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
    <circle cx="12" cy="13" r="3"/>
  </svg>
);

const RefreshIcon = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
  </svg>
);

const CheckCircleIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
    <polyline points="22 4 12 14.01 9 11.01"/>
  </svg>
);

const AlertTriangleIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
    <line x1="12" y1="9" x2="12" y2="13"/>
    <line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);

const FlameIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 3.5z"/>
  </svg>
);

const UploadIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
  </svg>
);

const LogOutIcon = ({ className = "w-5 h-5" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
  </svg>
);

const SnapshotIcon = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="4"/>
  </svg>
);

// --- Componente Principal de la Aplicación ---
function AvocadoVisionApp() {
  const [counts, setCounts] = useState({ total: 0, por_etiqueta: { sano: 0, "sarna-negra": 0, antracnosis: 0 } });
  const [camaraActual, setCamaraActual] = useState(1);
  const [camarasDisponibles, setCamarasDisponibles] = useState([0, 1]);
  const [confianza, setConfianza] = useState(55);
  const [isStreaming, setIsStreaming] = useState(true);
  const [streamUrl, setStreamUrl] = useState("/video_feed");
  const [isOnline, setIsOnline] = useState(true);
  const [isResetting, setIsResetting] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadedResult, setUploadedResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [toastMsg, setToastMsg] = useState("");

  const videoImgRef = useRef(null);

  // Mostrar mensaje temporal (Toast)
  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(""), 3500);
  };

  // 1. Obtener lista de cámaras
  const fetchCamaras = useCallback(async () => {
    try {
      const res = await fetch("/camaras");
      if (res.ok) {
        const data = await res.json();
        setCamaraActual(data.camara_actual ?? 1);
        if (data.camaras_disponibles && data.camaras_disponibles.length > 0) {
          setCamarasDisponibles(data.camaras_disponibles);
        }
      }
    } catch (e) {
      console.warn("No se pudo obtener cámaras:", e);
    }
  }, []);

  // 2. Obtener contadores cada 2 segundos
  const fetchContadores = useCallback(async () => {
    try {
      const res = await fetch("/get_analisis");
      if (res.ok) {
        const data = await res.json();
        setCounts(data);
        setIsOnline(true);
      }
    } catch (e) {
      setIsOnline(false);
    }
  }, []);

  useEffect(() => {
    fetchCamaras();
    fetchContadores();
    const interval = setInterval(fetchContadores, 2000);
    return () => clearInterval(interval);
  }, [fetchCamaras, fetchContadores]);

  // 3. Cambiar cámara
  const handleCambiarCamara = async (nuevoIndice) => {
    const idx = parseInt(nuevoIndice, 10);
    try {
      const res = await fetch(`/camaras/seleccionar/${idx}`, { method: "POST" });
      if (res.ok) {
        setCamaraActual(idx);
        setStreamUrl(`/video_feed?t=${Date.now()}`);
        showToast(`Conectado a Cámara Índice ${idx}`);
      } else {
        showToast("Error al conectar a la cámara.");
      }
    } catch (err) {
      showToast("Error de conexión al cambiar cámara.");
    }
  };

  // 4. Cambiar sensibilidad YOLO
  const handleCambiarConfianza = async (valor) => {
    const num = parseInt(valor, 10);
    setConfianza(num);
    const decimal = (num / 100).toFixed(2);
    try {
      await fetch(`/confianza?valor=${decimal}`, { method: "POST" });
    } catch (err) {
      console.error("Error al actualizar confianza:", err);
    }
  };

  // 5. Reiniciar contadores
  const handleReiniciarContadores = async () => {
    setIsResetting(true);
    try {
      const res = await fetch("/reiniciar_contadores", { method: "POST" });
      if (res.ok) {
        setCounts({ total: 0, por_etiqueta: { sano: 0, "sarna-negra": 0, antracnosis: 0 } });
        showToast("¡Contadores reiniciados a cero con éxito!");
      }
    } catch (e) {
      showToast("Error al reiniciar contadores.");
    } finally {
      setIsResetting(false);
    }
  };

  // 6. Tomar foto/snapshot
  const handleTomarSnapshot = () => {
    if (!videoImgRef.current) return;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = videoImgRef.current.naturalWidth || 640;
      canvas.height = videoImgRef.current.naturalHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(videoImgRef.current, 0, 0, canvas.width, canvas.height);
      const link = document.createElement("a");
      link.download = `aguacate_inspeccion_${Date.now()}.jpg`;
      link.href = canvas.toDataURL("image/jpeg");
      link.click();
      showToast("Instantánea guardada correctamente.");
    } catch (e) {
      showToast("No se pudo capturar instantánea (CORS local).");
    }
  };

  // 7. Subir imagen estática para análisis individual
  const handleSubirImagen = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/procesar_imagen", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setUploadedResult(data.archivo_resultado);
        showToast("Imagen procesada correctamente por YOLOv8.");
      } else {
        showToast("Error al procesar la imagen subida.");
      }
    } catch (err) {
      showToast("Error de conexión al subir imagen.");
    } finally {
      setIsUploading(false);
    }
  };

  // Cálculos porcentuales
  const total = counts.total || 0;
  const sanos = counts.por_etiqueta?.sano || 0;
  const sarna = counts.por_etiqueta?.["sarna-negra"] || 0;
  const antracnosis = counts.por_etiqueta?.antracnosis || 0;

  const pctSanos = total > 0 ? Math.round((sanos / total) * 100) : 0;
  const pctSarna = total > 0 ? Math.round((sarna / total) * 100) : 0;
  const pctAntracnosis = total > 0 ? Math.round((antracnosis / total) * 100) : 0;

  return (
    <div className="min-h-screen flex flex-col justify-between p-4 md:p-6 max-w-7xl mx-auto">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-6 right-6 z-50 bg-emerald-950 border border-emerald-500/60 text-emerald-200 px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 animate-fade-in backdrop-blur-md">
          <CheckCircleIcon className="w-5 h-5 text-emerald-400" />
          <span className="text-sm font-medium">{toastMsg}</span>
        </div>
      )}

      {/* --- NAVBAR SUPERIOR --- */}
      <header className="glass-panel rounded-2xl p-4 mb-6 shadow-xl flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 bg-gradient-to-br from-lime-600/30 to-emerald-950/60 border border-lime-500/40 rounded-xl shadow-inner">
            <AvocadoIcon className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl md:text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-lime-400 via-emerald-300 to-green-200">
                Avocato
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-lime-950/80 border border-lime-500/40 text-lime-400 rounded-full">
                YOLOv8 AI
              </span>
            </div>
            <p className="text-xs text-emerald-300/70">Detección y Clasificación Fitosanitaria del Aguacate en Tiempo Real</p>
          </div>
        </div>

        {/* Status & Controles de Barra */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Indicador de conexión */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-xs">
            <span className={`w-2.5 h-2.5 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse-dot" : "bg-red-500"}`}></span>
            <span className="text-emerald-200 font-semibold">{isOnline ? "En Línea" : "Sin Conexión"}</span>
          </div>

          {/* Selector de cámara */}
          <div className="flex items-center space-x-2 bg-emerald-950/70 border border-emerald-600/30 px-3 py-1.5 rounded-xl text-xs">
            <CameraIcon className="w-4 h-4 text-lime-400" />
            <span className="text-emerald-300 font-medium hidden sm:inline">Cámara:</span>
            <select
              value={camaraActual}
              onChange={(e) => handleCambiarCamara(e.target.value)}
              className="bg-emerald-900/60 text-lime-200 text-xs rounded-lg px-2 py-1 border border-emerald-500/30 focus:outline-none focus:border-lime-400 cursor-pointer"
            >
              {camarasDisponibles.map((idx) => (
                <option key={idx} value={idx}>
                  {idx === 1 ? "Cámara USB (Externa)" : idx === 0 ? "Cámara PC (Integrada)" : `Cámara ${idx}`}
                </option>
              ))}
            </select>
          </div>

          {/* Botón Subir Foto para prueba */}
          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-800/50 hover:bg-emerald-700/60 border border-emerald-500/30 text-emerald-200 text-xs font-semibold transition"
          >
            <UploadIcon className="w-4 h-4 text-lime-300" />
            <span>Subir Foto</span>
          </button>

          {/* Botón Salir */}
          <button
            onClick={() => (window.location.href = "ingreso.html")}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-red-950/50 hover:bg-red-900/60 border border-red-500/30 text-red-300 text-xs font-semibold transition"
          >
            <LogOutIcon className="w-4 h-4" />
            <span>Salir</span>
          </button>
        </div>
      </header>

      {/* --- CONTENIDO PRINCIPAL: 2 COLUMNAS --- */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start flex-1">
        
        {/* COLUMNA IZQUIERDA: VISOR DE VIDEO Y CONTROLES (7 COLUMNAS) */}
        <section className="lg:col-span-7 flex flex-col space-y-4">
          <div className="glass-card rounded-2xl p-4 video-glow relative overflow-hidden flex flex-col">
            
            {/* Header del Video */}
            <div className="flex items-center justify-between mb-3 px-1">
              <div className="flex items-center space-x-2">
                <span className="flex h-2.5 w-2.5 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-lime-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-lime-500"></span>
                </span>
                <h2 className="text-sm font-bold uppercase tracking-wider text-lime-400">
                  Flujo de Video en Vivo
                </h2>
              </div>
              <div className="flex items-center space-x-2 text-xs text-emerald-400/80 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/40">
                <span>YOLOv8 Tracking</span>
                <span>•</span>
                <span>640×480</span>
              </div>
            </div>

            {/* Contenedor del Stream de Video */}
            <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-black/70 border-2 border-emerald-500/30 flex items-center justify-center group shadow-inner">
              {isStreaming ? (
                <img
                  ref={videoImgRef}
                  id="video-stream"
                  src={streamUrl}
                  alt="Streaming de Aguacate en Vivo"
                  className="w-full h-full object-contain"
                  onError={() => setIsOnline(false)}
                  onLoad={() => setIsOnline(true)}
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-emerald-400/60 space-y-2">
                  <CameraIcon className="w-12 h-12 stroke-[1.5]" />
                  <p className="text-sm">Transmisión pausada</p>
                </div>
              )}

              {/* Marca de agua de marca */}
              <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/10 text-[11px] font-medium text-emerald-300 pointer-events-none">
                {camaraActual === 1 ? "Cámara USB 1" : "Cámara PC 0"}
              </div>
            </div>

            {/* BARRA DE HERRAMIENTAS DEBAJO DEL VIDEO */}
            <div className="mt-4 pt-3 border-t border-emerald-800/30 flex flex-wrap items-center justify-between gap-3 text-xs">
              
              {/* Slider de Filtro de Confianza */}
              <div className="flex items-center space-x-3 bg-emerald-950/60 border border-emerald-700/30 px-3.5 py-2 rounded-xl">
                <label htmlFor="conf-slider" className="text-emerald-200 font-semibold flex items-center space-x-1.5">
                  <span>Filtro Confianza:</span>
                </label>
                <input
                  id="conf-slider"
                  type="range"
                  min="30"
                  max="90"
                  step="5"
                  value={confianza}
                  onChange={(e) => handleCambiarConfianza(e.target.value)}
                  className="w-24 sm:w-28 cursor-pointer accent-lime-400"
                />
                <span className="font-mono font-bold text-lime-300 bg-lime-950/80 px-2 py-0.5 rounded border border-lime-500/40">
                  {confianza}%
                </span>
              </div>

              {/* Botones de acción del video */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setIsStreaming(!isStreaming)}
                  className={`px-3 py-2 rounded-xl font-semibold border transition flex items-center space-x-1.5 ${
                    isStreaming
                      ? "bg-emerald-900/40 border-emerald-600/30 hover:bg-emerald-800/50 text-emerald-200"
                      : "bg-lime-600/40 border-lime-500/40 hover:bg-lime-500/50 text-lime-100"
                  }`}
                  title={isStreaming ? "Pausar video" : "Reanudar video"}
                >
                  <span>{isStreaming ? "Pausar" : "Reanudar"}</span>
                </button>

                <button
                  onClick={handleTomarSnapshot}
                  className="px-3 py-2 rounded-xl bg-emerald-900/40 hover:bg-emerald-800/60 border border-emerald-600/30 text-emerald-200 font-semibold transition flex items-center space-x-1.5"
                  title="Descargar foto del frame actual"
                >
                  <SnapshotIcon />
                  <span className="hidden sm:inline">Capturar</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* COLUMNA DERECHA: DASHBOARD DE CLASIFICACIÓN Y CALIDAD (5 COLUMNAS) */}
        <section className="lg:col-span-5 flex flex-col space-y-4">
          
          {/* TARJETA PRINCIPAL: TOTALES */}
          <div className="glass-card rounded-2xl p-5 border-l-4 border-l-lime-400 flex items-center justify-between shadow-xl">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-300/80">
                Aguacates Evaluados
              </span>
              <div className="flex items-baseline space-x-3 mt-1">
                <span className="text-4xl font-extrabold text-white tracking-tight font-mono">
                  {total}
                </span>
                <span className="text-xs text-lime-400 font-medium">Unidades en lote</span>
              </div>
            </div>
            <button
              onClick={handleReiniciarContadores}
              disabled={isResetting}
              className="px-3.5 py-2 rounded-xl bg-red-600/20 hover:bg-red-600/40 border border-red-500/40 text-red-200 text-xs font-bold transition flex items-center space-x-1.5 shadow"
            >
              <RefreshIcon className={isResetting ? "animate-spin" : ""} />
              <span>Reiniciar Conteo</span>
            </button>
          </div>

          {/* GRID DE LAS 3 CONDICIONES FITOSANITARIAS */}
          <div className="grid grid-cols-1 gap-3.5">
            
            {/* 1. AGUACATE SANO */}
            <div className="glass-card rounded-2xl p-4 border border-emerald-500/25 bg-gradient-to-r from-emerald-950/40 to-emerald-900/20 hover:border-emerald-400/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300">
                    <CheckCircleIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-emerald-200">Aguacates Buenos</h3>
                    <p className="text-xs text-emerald-400/70">Aptos para exportación y consumo</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-extrabold text-emerald-300 font-mono">{sanos}</span>
                  <span className="block text-[11px] text-emerald-400/90 font-semibold">{pctSanos}%</span>
                </div>
              </div>
            </div>

            {/* 2. ROÑA NEGRA (SARNA) */}
            <div className="glass-card rounded-2xl p-4 border border-amber-500/25 bg-gradient-to-r from-amber-950/40 to-amber-900/20 hover:border-amber-400/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-amber-500/20 border border-amber-400/40 text-amber-300">
                    <AlertTriangleIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-amber-200">Roña Negra (Sarna)</h3>
                    <p className="text-xs text-amber-300/70">Lesión fúngica superficial de cáscara</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-extrabold text-amber-300 font-mono">{sarna}</span>
                  <span className="block text-[11px] text-amber-400/90 font-semibold">{pctSarna}%</span>
                </div>
              </div>
            </div>

            {/* 3. ANTRACNOSIS */}
            <div className="glass-card rounded-2xl p-4 border border-red-500/25 bg-gradient-to-r from-red-950/40 to-red-900/20 hover:border-red-400/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-red-500/20 border border-red-400/40 text-red-300">
                    <FlameIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-red-200">Antracnosis</h3>
                    <p className="text-xs text-red-300/70">Pudrición profunda en pulpa del fruto</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-extrabold text-red-300 font-mono">{antracnosis}</span>
                  <span className="block text-[11px] text-red-400/90 font-semibold">{pctAntracnosis}%</span>
                </div>
              </div>
            </div>

          </div>

          {/* BARRA DE DISTRIBUCIÓN PORCENTUAL DEL LOTE */}
          <div className="glass-card rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-300/80">
                Distribución de Calidad
              </span>
              <span className="text-xs font-semibold text-lime-400">
                {total > 0 ? `${pctSanos}% Calidad A` : "Esperando datos..."}
              </span>
            </div>

            {/* Barra apilada */}
            <div className="w-full h-3 bg-emerald-950 rounded-full overflow-hidden flex border border-emerald-800/40">
              {total > 0 ? (
                <>
                  <div style={{ width: `${pctSanos}%` }} className="bg-emerald-500 h-full transition-all duration-500" title={`Sanos: ${pctSanos}%`} />
                  <div style={{ width: `${pctSarna}%` }} className="bg-amber-500 h-full transition-all duration-500" title={`Roña Negra: ${pctSarna}%`} />
                  <div style={{ width: `${pctAntracnosis}%` }} className="bg-red-500 h-full transition-all duration-500" title={`Antracnosis: ${pctAntracnosis}%`} />
                </>
              ) : (
                <div className="w-full h-full bg-emerald-900/30" />
              )}
            </div>

            {/* Leyenda */}
            <div className="flex items-center justify-between text-[11px] mt-2.5 text-emerald-300/70">
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Sanos ({pctSanos}%)</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span>Roña ({pctSarna}%)</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                <span>Antracnosis ({pctAntracnosis}%)</span>
              </span>
            </div>
          </div>

        </section>
      </main>

      {/* --- MODAL PARA SUBIR Y PROCESAR FOTO INDIVIDUAL --- */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full rounded-2xl p-6 border border-emerald-500/40 shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <UploadIcon className="w-5 h-5 text-lime-400" />
                <h3 className="text-lg font-bold text-emerald-200">Análisis Individual de Foto</h3>
              </div>
              <button
                onClick={() => {
                  setUploadModalOpen(false);
                  setUploadedResult(null);
                }}
                className="text-gray-400 hover:text-white text-lg font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-emerald-300/80 mb-4">
              Sube una foto de un aguacate desde tu computador para someterla a inferencia con recortes y detección YOLOv8.
            </p>

            <div className="border-2 border-dashed border-emerald-600/40 rounded-xl p-6 text-center hover:border-lime-400/60 transition bg-emerald-950/30">
              <input
                type="file"
                accept="image/*"
                onChange={handleSubirImagen}
                className="hidden"
                id="modal-file-upload"
              />
              <label htmlFor="modal-file-upload" className="cursor-pointer flex flex-col items-center">
                <UploadIcon className="w-10 h-10 text-lime-400 mb-2" />
                <span className="text-sm font-semibold text-lime-200">Haz clic para seleccionar una foto</span>
                <span className="text-xs text-emerald-400/60 mt-1">Soporta JPG, PNG, WEBP</span>
              </label>
            </div>

            {isUploading && (
              <div className="flex items-center justify-center space-x-2 my-4 text-xs text-lime-300">
                <RefreshIcon className="w-4 h-4 animate-spin" />
                <span>Procesando imagen con modelo YOLO...</span>
              </div>
            )}

            {uploadedResult && (
              <div className="mt-4">
                <p className="text-xs font-bold text-emerald-300 mb-2">Resultado de la Detección:</p>
                <div className="rounded-xl overflow-hidden border border-emerald-500/40 bg-black/60 max-h-64 flex items-center justify-center">
                  <img src={uploadedResult} alt="Resultado de Detección" className="max-h-64 object-contain" />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- FOOTER INFERIOR --- */}
      <footer className="mt-6 text-center text-xs text-emerald-400/40 py-2">
        <p>Sistema Inteligente de Detección de Enfermedades en Aguacate • Avocato</p>
      </footer>
    </div>
  );
}

// Montar la aplicación en el DOM
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<AvocadoVisionApp />);

