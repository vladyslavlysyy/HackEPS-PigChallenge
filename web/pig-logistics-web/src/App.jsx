import React, { useEffect, useRef, useState, useMemo } from 'react';
import {
  Truck, TrendingUp, AlertTriangle, DollarSign, Activity,
  Calendar, MapPin, Navigation, Layers, Scale, Clock
} from 'lucide-react';
import simulationData from './data/resultats_simulacio.json';
import videoLogistics from './data/video_logistics.mp4';

const REAL_SIMULATION_DATA = simulationData;

const SLAUGHTERHOUSE = {
  id: "S01", name: "Escorxador Central Vic", lat: 41.93, lon: 2.25, capacity: 2000
};

const getFarmColor = (pigsReady) => {
  if (pigsReady <= 50) return '#22c55e';
  if (pigsReady <= 100) return '#eab308';
  return '#ef4444';
};

const getSlaughterhouseColor = (processed, capacity) => {
  const pct = (processed / capacity) * 100;
  if (pct < 50) return '#22c55e';
  if (pct < 90) return '#eab308';
  return '#ef4444';
};

function App() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [selectedDay, setSelectedDay] = useState(1);
  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const [showMap, setShowMap] = useState(false);

  useEffect(() => {
    if (!showMap) return;
    const loadLeaflet = async () => {
      if (window.L) {
        setLeafletLoaded(true);
        return;
      }
      if (!document.getElementById('leaflet-css')) {
        const link = document.createElement('link');
        link.id = 'leaflet-css';
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
      }
      if (!document.getElementById('leaflet-js')) {
        const script = document.createElement('script');
        script.id = 'leaflet-js';
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.async = true;
        script.onload = () => setLeafletLoaded(true);
        document.body.appendChild(script); 
      } else {
        setLeafletLoaded(true);
      }
    };
    loadLeaflet();
  }, [showMap]);
  

  const farmsMap = useMemo(() => {
    if (!showMap) return {};
    const farms = {};
    if (REAL_SIMULATION_DATA.ubicacions_granges) {
      REAL_SIMULATION_DATA.ubicacions_granges.forEach(granja => {
        farms[granja.id] = {
          id: granja.id,
          lat: granja.lat,
          lon: granja.lon,
          // Errores que no afectan al comportamento del programa
          inventory: Math.floor(Math.random() * 2000) + 1000,
          pigs_ready: Math.floor(Math.random() * 150)
        };
      });
    }
    return farms;
  }, [showMap]);

  const dailyData = useMemo(() => {
    if (!showMap) return [];
    return REAL_SIMULATION_DATA.activitat_diaria.filter(d => d.dia === selectedDay && d.camio_id !== "DESCANS");
  }, [selectedDay, showMap]);

  const dailyMetrics = useMemo(() => {
    if (!showMap) return { profit: 0, pigs: 0, cost: 0, penalties: 0, weight: 0, distance: 0, time: 0, trips: 0, avgTripCost: 0, avgTripTime: 0, utilizationPct: 0 };
    const totals = dailyData.reduce((acc, curr) => ({
      profit: acc.profit + (curr.ingressos - curr.cost_viatge),
      pigs: acc.pigs + curr.porcs_totals,
      cost: acc.cost + curr.cost_viatge,
      penalties: acc.penalties + curr.penalitzacions,
      weight: acc.weight + curr.pes_total,
      distance: acc.distance + curr.distancia_total,
      time: acc.time + curr.temps_total,
      trips: acc.trips + 1
    }), { profit: 0, pigs: 0, cost: 0, penalties: 0, weight: 0, distance: 0, time: 0, trips: 0 });

    const avgTripCost = totals.trips > 0 ? totals.cost / totals.trips : 0;
    const avgTripTime = totals.trips > 0 ? totals.time / totals.trips : 0;
    const totalCapacity = totals.trips * 20000;
    const utilizationPct = totals.trips > 0 ? (totals.weight / totalCapacity) * 100 : 0;

    return { ...totals, avgTripCost, avgTripTime, utilizationPct };
  }, [dailyData, showMap]);

  useEffect(() => {
    if (
      showMap &&
      leafletLoaded &&
      mapContainerRef.current &&
      mapContainerRef.current.offsetWidth > 0 &&
      mapContainerRef.current.offsetHeight > 0 &&
      window.L
    ) {
      const L = window.L;
      let map = mapInstanceRef.current;

      if (!map) {
        map = L.map(mapContainerRef.current, {
          zoomControl: false,
          attributionControl: false
        }).setView([SLAUGHTERHOUSE.lat, SLAUGHTERHOUSE.lon], 9);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
          maxZoom: 19, attribution: ''
        }).addTo(map);
        mapInstanceRef.current = map;

        setTimeout(() => {
          map.invalidateSize();
        }, 300);
      }

      setTimeout(() => { map.invalidateSize(); }, 500);
      map.eachLayer((layer) => { if (!layer._url) map.removeLayer(layer); });

      const createIcon = (color, size = 12, isTruck = false) => L.divIcon({
        className: 'custom-icon',
        html: `<div style="position: relative; width: ${size}px; height: ${size}px;"><div style="background-color: ${color}; width: 100%; height: 100%; border-radius: 50%; border: 2px solid ${isTruck ? '#0f172a' : 'white'}; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div></div>`,
        iconSize: [size, size], iconAnchor: [size / 2, size / 2]
      });

      const processed = dailyMetrics.pigs;
      const capacity = SLAUGHTERHOUSE.capacity;
      const shColor = getSlaughterhouseColor(processed, capacity);
      const utilizationSh = Math.round((processed / capacity) * 100);
      const liveWeightTotal = dailyMetrics.weight;
      const carcassWeightTotal = liveWeightTotal * 0.78;
      const avgLive = processed > 0 ? (liveWeightTotal / processed).toFixed(1) : 0;
      const avgCarcass = processed > 0 ? (carcassWeightTotal / processed).toFixed(1) : 0;

      let shStatusText = "< 50% ple";
      if (utilizationSh >= 50) shStatusText = "50-90% ple";
      if (utilizationSh > 90) shStatusText = "PLE!";

      L.marker([SLAUGHTERHOUSE.lat, SLAUGHTERHOUSE.lon], { icon: createIcon(shColor, 24) }).addTo(map)
        .bindTooltip(`
          <div style="font-family: sans-serif; min-width: 150px;">
            <strong style="font-size: 14px; color: #0f172a;">🏭 ${SLAUGHTERHOUSE.name}</strong><hr style="margin:5px 0; border-color: #ddd;"/>
            <div style="display:grid; grid-template-columns: 1fr auto; gap: 5px; font-size: 12px; color: #475569;">
              <span>Sacrificats:</span> <b>${processed}</b>
              <span>Pes Viu Total:</span> <b>${(liveWeightTotal / 1000).toFixed(1)} t</b>
              <span>Pes Canal Total:</span> <b>${(carcassWeightTotal / 1000).toFixed(1)} t</b>
              <span>Mitjana Viu:</span> <b>${avgLive} kg</b>
              <span>Mitjana Canal:</span> <b>${avgCarcass} kg</b>
              <span>Capacitat:</span> <b style="color:${shColor}">${shStatusText}</b>
            </div>
          </div>
        `, { direction: 'top', className: 'custom-tooltip-sh' });

      const activeFarmIds = new Set();
      dailyData.forEach(r => r.parades.forEach(p => activeFarmIds.add(p)));

      Object.values(farmsMap).forEach(farm => {
        const isActive = activeFarmIds.has(farm.id);
        let color = getFarmColor(farm.pigs_ready);
        let statusText = "Pocs porcs esperant (0-50)";
        if (farm.pigs_ready > 50) statusText = "Mitjà (51-100)";
        if (farm.pigs_ready > 100) statusText = "Molts (>100)";

        if (!isActive) color = '#94a3b8';

        const marker = L.marker([farm.lat, farm.lon], { icon: createIcon(color, isActive ? 14 : 8) }).addTo(map);
        if (isActive) {
          marker.bindTooltip(`
            <div style="font-family: sans-serif;">
              <strong style="color:#0f172a;">🐷 ${farm.id}</strong><br/>
              Inventari: ${farm.inventory}<br/>
              A recollir: <b>${farm.pigs_ready}</b><br/>
              <span style="color:${color}; font-weight:bold;">${statusText}</span>
            </div>
          `, { direction: 'top' });
        }
      });

      dailyData.forEach((route, idx) => {
        const pathCoords = [[SLAUGHTERHOUSE.lat, SLAUGHTERHOUSE.lon]];
        route.parades.forEach(pid => { if (farmsMap[pid]) pathCoords.push([farmsMap[pid].lat, farmsMap[pid].lon]); });
        pathCoords.push([SLAUGHTERHOUSE.lat, SLAUGHTERHOUSE.lon]);
        const routeColors = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#10b981'];
        const color = routeColors[idx % routeColors.length];
        const truckCap = 20000;
        const loadStatus = route.pes_total > (truckCap * 0.9) ? "Traslladat a plena càrrega" : "Traslladat amb espai lliure";
        const avgWeightPig = route.porcs_totals > 0 ? (route.pes_total / route.porcs_totals).toFixed(1) : 0;

        L.polyline(pathCoords, {
          color: color, weight: 4, opacity: 0.8, lineCap: 'round'
        }).addTo(map).bindTooltip(`
          <div style="font-family: sans-serif;">
            <strong>🚛 Viatge ${route.camio_id}</strong><hr style="margin:4px 0;"/>
            Càrrega: <b>${route.pes_total.toFixed(0)} kg</b><br/>
            Porcs: <b>${route.porcs_totals}</b><br/>
            Pes Viu Mitjà: <b>${avgWeightPig} kg</b><br/>
            Granges: <b>${route.parades.length}</b><br/>
            Estat: <i>${loadStatus}</i><br/>
            Cost: <b>${route.cost_viatge.toFixed(1)} €</b>
          </div>
        `, { sticky: true });
      });
    }
  }, [leafletLoaded, dailyData, farmsMap, dailyMetrics, showMap]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0f172a] text-white font-sans overflow-hidden">
      {/* =========================
          PANTALLA INICIAL
          ========================= */}
            {/* PANTALLA INICIAL */}
            {!showMap && (
        <div className="relative h-full w-full flex items-center justify-center bg-gradient-to-br from-[#0f172a] via-[#1e293b] to-[#0f172a]">
          {/* Patrón de fondo animado */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute inset-0" style={{
              backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)',
              backgroundSize: '40px 40px'
            }}></div>
          </div>

          <video
            autoPlay loop muted playsInline preload="metadata"
            src={videoLogistics}
            className="absolute inset-0 w-full h-full object-cover z-0"
          >
            <source src={videoLogistics} type="video/mp4" />
          </video>

          <div className="absolute inset-0 bg-gradient-to-b from-[#0f172a]/70 via-[#0f172a]/50 to-[#0f172a]/70 z-10" />

          {/* Botón central con animación */}
          <div className="relative z-20 flex flex-col items-center gap-8">
            <div className="text-center space-y-4 animate-fade-in">
              <h1 className="text-6xl md:text-7xl font-extrabold text-white tracking-tight">
                PIG<span className="text-blue-400">LOGISTICS</span>
              </h1>
              <p className="text-gray-300 text-lg md:text-xl font-light tracking-wide">
                Sistema de Gestió Logística Intel·ligent
              </p>
            </div>
            
            <button
              onClick={() => setShowMap(true)}
              className="group relative px-12 py-5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-xl font-bold rounded-2xl shadow-2xl transition-all duration-300 flex items-center gap-4 overflow-hidden transform hover:scale-105 hover:shadow-blue-500/50"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              <Truck size={32} className="relative z-10 animate-bounce-slow" />
              <span className="relative z-10">Generar Mapa</span>
            </button>
          </div>
        </div>
      )}

      {/* =========================
          SEGUNDA PANTALLA - MAPA
          ========================= */}
      {showMap && (
        <>
          {/* NAVBAR  */}
          <nav className="h-16 flex-none flex justify-between items-center px-8 bg-[#1e293b] border-b border-white/5 shadow-lg z-30">
            <div className="flex items-center gap-3">
           
              <h1 className="text-xl font-bold tracking-wider text-white">PIG<span className="text-blue-400">LOGISTICS</span></h1>
            </div>

            <div className="flex items-center gap-6 bg-[#0f172a] px-6 py-2 rounded-xl border border-white/5 shadow-inner">
              <div className="flex items-center gap-2 text-blue-400"><Calendar size={18} /><span className="text-xs font-bold uppercase tracking-widest">Dia Simulació</span></div>
              <span className="text-xl font-bold text-white w-8 text-center">{selectedDay}</span>
              <input type="range" min="1" max="15" value={selectedDay} onChange={(e) => setSelectedDay(parseInt(e.target.value))} className="w-32 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"/>
            </div>
          </nav>

          {/* CONTENIDO ORIGINAL (sidebar + mapa) */}
          <main className="flex-grow flex flex-col lg:flex-row p-6 gap-6 h-[calc(100vh-64px)]">
            <div className="w-full lg:w-4/12 flex flex-col gap-6 h-full overflow-y-auto custom-scrollbar pr-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-white/5">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><Truck size={12}/> Porcs Lliurats</p>
                  <p className="text-2xl font-bold text-white">{dailyMetrics.pigs}</p>
                </div>
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-white/5">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><DollarSign size={12}/> Benefici</p>
                  <p className="text-2xl font-bold text-green-400">{dailyMetrics.profit.toLocaleString(undefined, { maximumFractionDigits: 0 })} €</p>
                </div>
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-white/5">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><Scale size={12}/> Cost Mitjà</p>
                  <p className="text-xl font-bold text-white">{dailyMetrics.avgTripCost.toFixed(1)} €</p>
                </div>
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-white/5">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><Clock size={12}/> Temps Mitjà</p>
                  <p className="text-xl font-bold text-white">{dailyMetrics.avgTripTime.toFixed(1)} h</p>
                </div>
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-white/5">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><Activity size={12}/> Ús Camions</p>
                  <p className="text-xl font-bold text-blue-400">{dailyMetrics.utilizationPct.toFixed(1)}%</p>
                </div>
                <div className="bg-[#1e293b] p-4 rounded-2xl border border-red-500/20">
                  <p className="text-gray-400 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1"><AlertTriangle size={12}/> Sancions</p>
                  <p className="text-xl font-bold text-red-400">{dailyMetrics.penalties.toFixed(0)} €</p>
                </div>
              </div>

              <div className="flex-grow bg-[#1e293b] rounded-3xl p-1 border border-white/5 overflow-hidden flex flex-col shadow-lg min-h-[300px]">
                <div className="p-4 border-b border-white/5 flex items-center justify-between bg-[#0f172a]/50">
                  <h3 className="text-sm font-bold text-gray-300 flex items-center gap-2"><Navigation size={16} className="text-blue-400"/> Rutes del Dia</h3>
                  <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-1 rounded-full font-mono">{dailyData.length}</span>
                </div>
                <div className="overflow-y-auto p-4 space-y-3 custom-scrollbar flex-grow">
                  {dailyData.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                      <p>Dia de descans</p>
                    </div>
                  ) : dailyData.map((route, idx) => (
                    <div key={idx} className="p-4 bg-[#0f172a] hover:bg-[#334155] rounded-xl border border-white/5 cursor-pointer transition group">
                      <div className="flex justify-between items-center mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-white">{route.camio_id}</span>
                          <span className="text-[10px] bg-gray-700 px-1.5 rounded text-gray-300">{route.tipus_camio}</span>
                        </div>
                        <span className="text-[10px] font-mono text-gray-400">{-route.cost_viatge.toFixed(0)} €</span>
                      </div>
                      <div className="text-xs text-gray-400 mb-2 flex flex-wrap gap-1">
                        {route.parades.map((p, i) => (
                          <span key={i} className="bg-blue-500/10 text-blue-300 px-1 rounded">{p}</span>
                        ))}
                        <span className="text-gray-600">➝ Escorxador</span>
                      </div>
                      <div className="flex justify-between text-[10px] text-gray-500 border-t border-white/5 pt-2">
                        <span>🐷 {route.porcs_totals} porcs</span>
                        <span>⚖️ {route.pes_total.toFixed(0)} kg</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="w-full lg:w-8/12 h-full relative flex items-center justify-center">
              <div className="relative w-full h-full bg-white rounded-[2rem] border border-white/10 shadow-2xl overflow-hidden flex flex-col">
                <div className="h-14 bg-white border-b border-gray-200 flex justify-between items-center px-6 z-10 shadow-sm">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold tracking-widest text-gray-800 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                      MAPA DE RUTES
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 font-mono">Catalunya Central</div>
                </div>
                <div className="flex-grow relative w-full bg-gray-100 z-0">
                  {!leafletLoaded && <div className="absolute inset-0 flex items-center justify-center text-blue-500 z-50 bg-white">Carregant Mapa...</div>}
                  <div ref={mapContainerRef} style={{ height: '100%', width: '100%' }} />
                </div>
                <div className="absolute bottom-6 right-6 bg-white/90 backdrop-blur p-4 rounded-xl border border-gray-200 shadow-xl z-[500]">
                  <h4 className="text-[10px] font-bold text-gray-800 uppercase mb-2">Estat Granges</h4>
                  <div className="space-y-1 text-[10px] text-gray-600">
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[#22c55e]"></span> Pocs (0-50)</div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[#eab308]"></span> Mitjà (51-100)</div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[#ef4444]"></span> Molts (&gt;100)</div>
                  </div>
                </div>
              </div>
            </div>
          </main>
        </>
      )}
    </div>
  );
}

export default App;
