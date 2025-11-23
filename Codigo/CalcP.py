import pandas as pd
import numpy as np
import math
import random
import matplotlib.pyplot as plt
import seaborn as sns
import json  # Import necessari per a l'exportació

# --- 1. CONFIGURACIÓ I CONSTANTS ---

# Configuració de la Simulació
DIES_SETMANA = 7  # Setmana natural (Dilluns=0 ... Diumenge=6)
DIES_SIMULACIO = 15  # Simulem 15 dies (2 setmanes + 1 dilluns extra)
DATA_INICI = pd.Timestamp('2024-05-01')

# --- VARIABLES CLAU DE FLOTA I PREUS ---
NUM_CAMIONS_FLOTA = 3  # LIMIT REAL: Màxim de camions disponibles per dia
COST_CAMIO_FIXE_SETMANAL = 2000 # Cost de tenir el camió llogat (el facis servir o no)
PREU_BASE_KG = 1.56
PREU_MENJAR_KG = 0.35 

# Costos variables
COST_KM_PETIT = 1.15  # Camió 10T
COST_KM_GRAN = 1.25  # Camió 20T

# Penalitzacions (Percentatges)
PENALITZACIO_LLEU = 0.15  # 100-105kg o 115-120kg
PENALITZACIO_GREU = 0.20  # <100kg o >120kg
RANG_OPTIM = (105, 115)

# Capacitats Transport
CAPACITAT_CAMIO_PETIT = 10000  # kg
CAPACITAT_CAMIO_GRAN = 20000  # kg
VELOCITAT_MITJANA = 60  # km/h
TEMPS_CARREGA_PER_PORC = 0.5 / 60  # 0.5 minuts per porc en hores
MAX_HORES_DIA = 8

# --- DATA DEL CSV (Weight 1.xlsx - Weight.csv) ---
# Format: {setmana: {'mean': mitjana_kg, 'sd': desviacio_estandard}}
GROWTH_DATA = {
    10: {'mean': 29.7, 'sd': 3.9},
    11: {'mean': 33.4, 'sd': 4.6},
    12: {'mean': 37.8, 'sd': 5.4},
    13: {'mean': 42.6, 'sd': 6.3},
    14: {'mean': 47.9, 'sd': 7.4},
    15: {'mean': 53.5, 'sd': 8.4},
    16: {'mean': 59.3, 'sd': 9.5},
    17: {'mean': 65.3, 'sd': 10.6},
    18: {'mean': 71.3, 'sd': 11.8},
    19: {'mean': 77.4, 'sd': 12.9},
    20: {'mean': 83.4, 'sd': 14.0},
    21: {'mean': 89.2, 'sd': 15.2},
    22: {'mean': 94.8, 'sd': 16.3},
    23: {'mean': 100.0, 'sd': 17.5},
    24: {'mean': 104.8, 'sd': 18.7},
    25: {'mean': 109.1, 'sd': 19.8},
    26: {'mean': 112.8, 'sd': 21.0},
    27: {'mean': 120.695, 'sd': 21.8},
    28: {'mean': 126.18, 'sd': 22.9}
}

# --- DATA DEL CSV (Consumption 1.xlsx - Cumulative consumtion.csv) ---
# Format: {setmana: {'mean': consum_acumulat_mitja, 'sd': desviacio_acumulada}}
CUMULATIVE_INTAKE_DATA = {
    10: {'mean': 5.1, 'sd': 5.5},
    11: {'mean': 12.1, 'sd': 8.5},
    12: {'mean': 20.5, 'sd': 12.1},
    13: {'mean': 30.2, 'sd': 15.9},
    14: {'mean': 41.3, 'sd': 19.7},
    15: {'mean': 53.4, 'sd': 23.6},
    16: {'mean': 66.4, 'sd': 27.5},
    17: {'mean': 80.3, 'sd': 31.4},
    18: {'mean': 94.9, 'sd': 35.3},
    19: {'mean': 110.1, 'sd': 39.2},
    20: {'mean': 125.7, 'sd': 43.2},
    21: {'mean': 141.6, 'sd': 47.1},
    22: {'mean': 157.6, 'sd': 51.0},
    23: {'mean': 173.7, 'sd': 54.9},
    24: {'mean': 189.6, 'sd': 58.9},
    25: {'mean': 205.3, 'sd': 62.8},
    26: {'mean': 220.6, 'sd': 66.7},
    27: {'mean': 243.07, 'sd': 70.35},
    28: {'mean': 262.33, 'sd': 74.22}
}


# --- 2. CLASSES D'ENTITATS ---

class PorcBatch:
    """Representa un lot de porcs a una granja."""
    def __init__(self, id_lot, quantitat, edat_setmanes):
        self.id_lot = id_lot
        self.quantitat = quantitat
        self.edat_setmanes = edat_setmanes
        
        # Factor de consum propi d'aquest lot (Z-Score d'ingesta).
        self.z_score_intake = np.random.normal(0, 1)

        # Inicialització del pes basada en GROWTH_DATA
        if edat_setmanes in GROWTH_DATA:
            params = GROWTH_DATA[edat_setmanes]
            self.pes_mig = params['mean']
            self.desviacio_std = params['sd']
        else:
            self.pes_mig = 30 + (edat_setmanes * 4)
            self.desviacio_std = 5

        # Generem la distribució inicial de pesos individuals
        self.pesos_individuals = np.random.normal(self.pes_mig, self.desviacio_std, quantitat)
        self.pesos_individuals = np.sort(self.pesos_individuals)[::-1]

    def creixer_una_setmana(self):
        old_week = self.edat_setmanes
        new_week = old_week + 1
        
        if old_week in GROWTH_DATA and new_week in GROWTH_DATA:
            old_params = GROWTH_DATA[old_week]
            new_params = GROWTH_DATA[new_week]
            
            # Z-Score update per pes (manté la jerarquia dins del lot)
            z_scores = (self.pesos_individuals - old_params['mean']) / old_params['sd']
            self.pesos_individuals = z_scores * new_params['sd'] + new_params['mean']
            
            self.pes_mig = new_params['mean']
            self.desviacio_std = new_params['sd']
            self.edat_setmanes = new_week
        else:
            # Fallback si falten dades
            GUANY_ESTIMAT = 5.0
            self.edat_setmanes += 1
            self.pes_mig += GUANY_ESTIMAT
            self.pesos_individuals += GUANY_ESTIMAT

    def obtenir_consum_setmanal_per_porc(self):
        """
        Calcula el consum setmanal tenint en compte les dades ACUMULADES i la DESVIACIÓ ESTÀNDARD.
        """
        curr_week = self.edat_setmanes
        prev_week = curr_week - 1
        
        if curr_week not in CUMULATIVE_INTAKE_DATA or prev_week not in CUMULATIVE_INTAKE_DATA:
            return 15.0 # Valor per defecte segur
            
        curr_data = CUMULATIVE_INTAKE_DATA[curr_week]
        prev_data = CUMULATIVE_INTAKE_DATA[prev_week]
        
        cum_curr = curr_data['mean'] + (self.z_score_intake * curr_data['sd'])
        cum_prev = prev_data['mean'] + (self.z_score_intake * prev_data['sd'])
        
        consum_setmanal = cum_curr - cum_prev
        if consum_setmanal < 1.0: consum_setmanal = 1.0
        
        return consum_setmanal

    def obtenir_porcs_per_venda(self, max_kg_capacitat):
        pes_acumulat = 0
        seleccionats = []
        indexs_a_eliminar = []

        self.pesos_individuals = np.sort(self.pesos_individuals)[::-1]

        for i, pes in enumerate(self.pesos_individuals):
            if pes_acumulat + pes <= max_kg_capacitat:
                pes_acumulat += pes
                seleccionats.append(pes)
                indexs_a_eliminar.append(i)
            else:
                break

        self.pesos_individuals = np.delete(self.pesos_individuals, indexs_a_eliminar)
        self.quantitat = len(self.pesos_individuals)
        return pes_acumulat, len(seleccionats), seleccionats


class Granja:
    def __init__(self, id_granja, lat, lon, capacitat_total):
        self.id = id_granja
        self.location = (lat, lon)
        self.capacitat_total = capacitat_total
        self.lots = []
        self.visitada_aquesta_setmana = False
        self.menjar_consumit_acumulat = 0

    def afegir_lot(self, lot):
        self.lots.append(lot)

    def get_total_porcs(self):
        return sum(l.quantitat for l in self.lots)

    def calcular_consum_diari(self):
        """
        Calcula el cost diari d'alimentació.
        """
        cost_dia_total = 0
        
        for lot in self.lots:
            if lot.quantitat > 0:
                kg_setmana_per_porc = lot.obtenir_consum_setmanal_per_porc()
                kg_dia_per_porc = kg_setmana_per_porc / 7.0
                kg_dia_lot = kg_dia_per_porc * lot.quantitat
                cost_dia_total += (kg_dia_lot * PREU_MENJAR_KG)

        self.menjar_consumit_acumulat += cost_dia_total
        return cost_dia_total

    def te_porcs_per_venda(self):
        if self.get_total_porcs() == 0: return False
        max_pes = 0
        for lot in self.lots:
            if len(lot.pesos_individuals) > 0:
                current_max = np.max(lot.pesos_individuals)
                if current_max > max_pes:
                    max_pes = current_max
        return max_pes > 100


class Escorxador:
    def __init__(self, id_esc, lat, lon, capacitat_diaria):
        self.id = id_esc
        self.location = (lat, lon)
        self.capacitat_diaria = capacitat_diaria
        self.processats_avui = 0

    def reset_diari(self):
        self.processats_avui = 0

    def espai_disponible(self):
        return self.capacitat_diaria - self.processats_avui


# --- 3. FUNCIONS AUXILIARS ---

def calcular_distancia_km(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dy = (lat2 - lat1) * 111
    dx = (lon2 - lon1) * 85
    return math.sqrt(dx ** 2 + dy ** 2)


def calcular_benefici_lot(llista_pesos):
    ingressos = 0
    penalitzacions_total = 0

    for pes in llista_pesos:
        descompte = 0
        if 105 <= pes <= 115:
            descompte = 0
        elif (100 <= pes < 105) or (115 < pes <= 120):
            descompte = PENALITZACIO_LLEU
        else:
            descompte = PENALITZACIO_GREU

        valor_brut = pes * PREU_BASE_KG
        penalitzacio = valor_brut * descompte
        ingressos += (valor_brut - penalitzacio)
        penalitzacions_total += penalitzacio

    return ingressos, penalitzacions_total

def print_configuracion():
    print("\n" + "="*50)
    print("   PARÀMETRES DE LA SIMULACIÓ")
    print("="*50)
    print(f"Flota Disponible:      {NUM_CAMIONS_FLOTA} camions")
    print(f"Cost Fix Camió:        {COST_CAMIO_FIXE_SETMANAL} €/setmana")
    print(f"Cost Km (Gran/Petit):  {COST_KM_GRAN}/{COST_KM_PETIT} €/km")
    print(f"Preu Venda Porc:       {PREU_BASE_KG} €/kg")
    print(f"Cost Menjar:           {PREU_MENJAR_KG} €/kg")
    print(f"Capacitat Escorxador:  1800 cerdos/dia")
    print("="*50 + "\n")


# --- 4. GENERACIÓ D'ENTORN ---

def generar_entorn():
    lat_min, lat_max = 41.50, 42.10
    lon_min, lon_max = 0.50, 2.50
    
    lat_c = random.uniform(lat_min, lat_max)
    lon_c = random.uniform(lon_min, lon_max)
    
    print(f"📍 Ubicació aleatòria escorxador generada: Lat {lat_c:.4f}, Lon {lon_c:.4f}")

    escorxador = Escorxador("ESCO_CENTRAL", lat_c, lon_c, capacitat_diaria=1800)
    
    granges = []
    # HE AUGMENTAT A 60 GRANJES PERQUÈ HI HAGI ACTIVITAT TOTS ELS DIES
    for i in range(60): 
        lat = lat_c + random.uniform(-0.3, 0.3)
        lon = lon_c + random.uniform(-0.4, 0.4)
        
        g = Granja(f"GRANJA_{i + 1}", lat, lon, capacitat_total=2500)
        
        for j in range(4): # 4 lots per granja
            edat = random.randint(15, 24) 
            q = random.randint(150, 350)
            lot = PorcBatch(f"L_{i}_{j}", q, edat)
            g.afegir_lot(lot)
            
        granges.append(g)
        
    return escorxador, granges


# --- 5. LÒGICA DE SIMULACIÓ ---

def simular():
    print_configuracion()
    escorxador, granges = generar_entorn()
    registre_activitat = []

    for dia in range(1, DIES_SIMULACIO + 1):
        dia_setmana = (dia - 1) % DIES_SETMANA 
        escorxador.reset_diari()

        # 1. Biològic (Dilluns)
        if dia_setmana == 0:
            print(f"\n>> DILLUNS (Dia {dia}): Reset setmanal.")
            for g in granges: g.visitada_aquesta_setmana = False
            if dia > 1:
                print("   Aplicant corba de creixement (Weight.csv)...")
                for g in granges:
                    for lot in g.lots: lot.creixer_una_setmana()

        # 2. Alimentació
        cost_total_menjar_avui = 0
        for g in granges: 
            cost_total_menjar_avui += g.calcular_consum_diari()
        
        # 3. Logística (Laborables)
        if dia_setmana >= 5:
            print(f"Dia {dia} (Cap de setmana): Descans. Cost menjar: {cost_total_menjar_avui:.0f}€")
            registre_activitat.append({"dia": dia, "camio_id": "DESCANS", "porcs_totals": 0, "ingressos": 0, "cost_viatge": 0, "pes_total": 0, "penalitzacions": 0})
            continue 

        print(f"Dia {dia}: Laborable. Planificant rutes...")

        # Granges candidates per avui
        candidates = [g for g in granges if not g.visitada_aquesta_setmana and g.te_porcs_per_venda()]
        # Ordenar prioritat (porcs més grans primer)
        candidates.sort(key=lambda g: max([np.mean(l.pesos_individuals) for l in g.lots]), reverse=True)

        rutes_dia = []

        if not candidates:
             print("   -> Cap granja disponible per recollida avui.")
             # DIAGNÒSTIC PER L'USUARI
             visitades_amb_porcs = [g for g in granges if g.visitada_aquesta_setmana and g.te_porcs_per_venda()]
             sense_porcs = [g for g in granges if not g.te_porcs_per_venda()]
             print(f"      [Diagnòstic] Granges amb porcs però ja visitades (bloquejades fins dilluns): {len(visitades_amb_porcs)}")
             print(f"      [Diagnòstic] Granges sense porcs de talla comercial: {len(sense_porcs)}")

        
        # --- ESTAT DE LA FLOTA EN HORES (Nou sistema) ---
        # 0.0 hores usades per defecte a l'inici del dia per a cada camió (0, 1, 2)
        temps_camions = [0.0] * NUM_CAMIONS_FLOTA
        viajes_per_camio = [0] * NUM_CAMIONS_FLOTA # Per generar IDs T1_V1, T1_V2...

        # BUCLE DE PLANIFICACIÓ
        # Continuem mentre hi hagi granges, espai a l'escorxador i ALGUN camió tingui temps
        while len(candidates) > 0 and escorxador.espai_disponible() > 50:
            
            # Verificació ràpida: Si tots els camions superen les 8h, parem.
            if min(temps_camions) >= MAX_HORES_DIA:
                print("   -> Tota la flota ha arribat al límit d'hores diari.")
                break

            # --- CONSTRUCCIÓ DE RUTA POTENCIAL ---
            
            camio_tipus = "GRAN"
            capacitat_kg = CAPACITAT_CAMIO_GRAN
            cost_km = COST_KM_GRAN

            ruta_potencial = {
                "parades": [],
                "granjas_obj": [], 
                "porcs_totals": 0,
                "pes_total": 0,
                "distancia_total": 0,
                "temps_total": 0,
                "ingressos": 0,
                "penalitzacions": 0,
                "cost_viatge": 0
            }

            loc_actual = escorxador.location
            kg_disponibles_camio = capacitat_kg
            temps_acumulat = 0
            
            # Llista temporal de granges triades per a aquesta ruta concreta
            granjas_triades_ruta = [] 

            for parada_idx in range(3):
                # Condicions de parada
                if kg_disponibles_camio < 500: break
                if escorxador.espai_disponible() - ruta_potencial["porcs_totals"] <= 0: break
                
                # Busquem la millor següent granja (Nearest Neighbor) que no estigui ja triada
                disponibles = [c for c in candidates if c not in granjas_triades_ruta]
                
                if not disponibles: break

                disponibles.sort(key=lambda g: calcular_distancia_km(loc_actual, g.location))
                granja_objectiu = disponibles[0]

                dist = calcular_distancia_km(loc_actual, granja_objectiu.location)
                temps_viatge = dist / VELOCITAT_MITJANA
                
                # NOTA: No comprovem MAX_HORES aquí, ho fem al final quan tenim el total
                
                # Sortim del bucle de parades per gestionar-ho manualment a baix
                break 

            # --- REIMPLANTACIÓ LÒGICA DE SELECCIÓ I ASSIGNACIÓ ---
            
            # 1. Triar la millor granja inicial
            g_inicial = candidates[0] # Ja ordenada per prioritat
            
            # 2. Buscar veïns (fins a 2 més)
            ruta_candidata_granges = [g_inicial]
            candidates_restants = [c for c in candidates if c != g_inicial]
            
            loc_temp = g_inicial.location
            for _ in range(2): # Intentar afegir 2 més
                if not candidates_restants: break
                candidates_restants.sort(key=lambda g: calcular_distancia_km(loc_temp, g.location))
                vei = candidates_restants[0]
                # Distància extra raonable? (Ex: < 50km)
                if calcular_distancia_km(loc_temp, vei.location) < 100: 
                    ruta_candidata_granges.append(vei)
                    loc_temp = vei.location
                    candidates_restants.remove(vei)
            
            # Ara tenim una llista de 1, 2 o 3 granges [g1, g2, g3] que volem visitar.
            # Provem si aquesta ruta cap en algun camió. Si no, provem amb [g1, g2]. Si no, [g1].
            
            ruta_acceptada = False
            
            while len(ruta_candidata_granges) > 0:
                # Calcular temps estimat d'aquesta combinació (sense modificar lots)
                
                t_viatge = 0
                dist_total = 0
                curr = escorxador.location
                
                # Estimació porcs (per temps càrrega)
                num_porcs_est = 0
                kg_est = 0
                cap_temp = CAPACITAT_CAMIO_GRAN
                
                for g in ruta_candidata_granges:
                    dist = calcular_distancia_km(curr, g.location)
                    t_viatge += (dist / VELOCITAT_MITJANA)
                    dist_total += dist
                    curr = g.location
                    
                    # Estimem càrrega (sense borrar)
                    for lot in g.lots:
                        # Càlcul ràpid sense modificar
                        for p in lot.pesos_individuals:
                            if kg_est + p <= cap_temp:
                                kg_est += p
                                num_porcs_est += 1
                
                dist_tornada = calcular_distancia_km(curr, escorxador.location)
                t_viatge += (dist_tornada / VELOCITAT_MITJANA)
                dist_total += dist_tornada
                
                t_carrega = num_porcs_est * TEMPS_CARREGA_PER_PORC
                temps_total_estimat = t_viatge + t_carrega
                
                # BUSCAR CAMIÓ
                camio_id_trobat = -1
                for idx_c in range(NUM_CAMIONS_FLOTA):
                    if temps_camions[idx_c] + temps_total_estimat <= MAX_HORES_DIA:
                        camio_id_trobat = idx_c
                        break
                
                if camio_id_trobat != -1:
                    # --- ÈXIT: EXECUTEM LA RUTA ---
                    temps_camions[camio_id_trobat] += temps_total_estimat
                    viajes_per_camio[camio_id_trobat] += 1
                    
                    # Ara sí, executem la lògica "destructiva" de treure porcs i crear l'objecte ruta real
                    ruta_real = {
                        "dia": dia,
                        "camio_id": f"T{camio_id_trobat+1}_V{viajes_per_camio[camio_id_trobat]}", # ID Tipus T1_V2
                        "tipus_camio": "GRAN",
                        "parades": [],
                        "detalls_parades": [], # GUARDAR DETALLS DE CADA PARADA
                        "porcs_totals": 0,
                        "pes_total": 0,
                        "distancia_total": dist_total, # Usem la calculada
                        "temps_total": temps_total_estimat,
                        "ingressos": 0,
                        "penalitzacions": 0,
                        "cost_viatge": 0
                    }
                    
                    kg_recollits_real = 0
                    kg_disponibles = CAPACITAT_CAMIO_GRAN
                    
                    for g in ruta_candidata_granges:
                        ruta_real["parades"].append(g.id)
                        
                        # Lògica real de treure porcs
                        porcs_granja = 0
                        kg_granja = 0
                        pesos_granja = []
                        
                        for lot in g.lots:
                            espai = kg_disponibles - kg_granja
                            if espai <= 0: break
                            k, n, l = lot.obtenir_porcs_per_venda(espai)
                            
                            # Check limit escorxador (global)
                            if escorxador.espai_disponible() - (ruta_real["porcs_totals"] + n) < 0:
                                # Retallar excedent
                                sobran = (ruta_real["porcs_totals"] + n) - escorxador.espai_disponible()
                                n -= sobran
                                k = sum(l[:n])
                                l = l[:n]
                            
                            kg_granja += k
                            porcs_granja += n
                            pesos_granja.extend(l)
                        
                        if porcs_granja > 0:
                            rev, pen = calcular_benefici_lot(pesos_granja)
                            ruta_real["porcs_totals"] += porcs_granja
                            ruta_real["pes_total"] += kg_granja
                            ruta_real["ingressos"] += rev
                            ruta_real["penalitzacions"] += pen
                            ruta_real["detalls_parades"].append(f"{g.id} ({porcs_granja} porcs)")
                            
                            kg_disponibles -= kg_granja
                            
                            # Marcar visitada
                            g.visitada_aquesta_setmana = True
                            if g in candidates: candidates.remove(g)
                    
                    # Finalitzar ruta
                    load_factor = max(0.1, ruta_real["pes_total"] / CAPACITAT_CAMIO_GRAN)
                    ruta_real["cost_viatge"] = ruta_real["distancia_total"] * COST_KM_GRAN * load_factor
                    
                    escorxador.processats_avui += ruta_real["porcs_totals"]
                    rutes_dia.append(ruta_real)
                    ruta_acceptada = True
                    break # Sortim del while de reducció, ja hem fet la ruta
                
                else:
                    # NO CAP -> Provem traient l'última granja (ruta més curta)
                    if len(ruta_candidata_granges) > 1:
                        ruta_candidata_granges.pop() # Eliminem l'última i reintentem el bucle
                    else:
                        break
            
            if not ruta_acceptada:
                # Si hem sortit del while sense acceptar res, vol dir que la flota està plena
                print("   -> Flota saturada per avui (cap camió té temps per a la següent ruta mínima).")
                break

        # PRINT DE RUTES PER CONSOLA
        if len(rutes_dia) > 0:
            print(f"   -> S'han planificat {len(rutes_dia)} rutes:")
            for r in rutes_dia:
                benefici_ruta = r["ingressos"] - r["cost_viatge"]
                detall_text = " + ".join(r["detalls_parades"])
                print(f"      [🚚 {r['camio_id']}] {detall_text} | Total: {r['porcs_totals']} porcs ({r['pes_total']:.0f} kg) | Temps: {r['temps_total']:.1f}h | Benefici: {benefici_ruta:.2f}€")
            
            # MOSTRAR ÚS HORARI DELS CAMIONS
            us_h = [f"T{i+1}: {h:.1f}h" for i, h in enumerate(temps_camions)]
            print(f"      [🕒 Ús Horari] {', '.join(us_h)} (Max {MAX_HORES_DIA}h)")

        for r in rutes_dia: registre_activitat.append(r)
        if not rutes_dia and dia_setmana < 5:
            registre_activitat.append({"dia": dia, "camio_id": "SENSE_ACTIVITAT", "porcs_totals": 0, "ingressos": 0, "cost_viatge": 0, "pes_total": 0, "penalitzacions": 0})

    return pd.DataFrame(registre_activitat), granges, escorxador

# --- 6. EXPORTACIÓ JSON ---

def exportar_resultats_json(df, filename="resultats_simulacio.json"):
    dades = df.to_dict(orient='records')
    estructura_final = {
        "metadata": {
            "dies_simulats": DIES_SIMULACIO,
            "flota_utilitzada": NUM_CAMIONS_FLOTA,
            "data_inici": str(DATA_INICI.date())
        },
        "activitat_diaria": dades
    }
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(estructura_final, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Dades exportades correctament a: '{filename}'")
    except Exception as e:
        print(f"\n❌ Error guardant el JSON: {e}")


# --- 7. DASHBOARD ---

def generar_dashboard(df, granges, escorxador):
    df["benefici_net"] = df["ingressos"] - df["cost_viatge"]
    total_ingressos = df["ingressos"].sum()
    total_cost_transport = df["cost_viatge"].sum()
    total_cost_fixe = COST_CAMIO_FIXE_SETMANAL * 2 * NUM_CAMIONS_FLOTA
    total_alimentacio = sum(g.menjar_consumit_acumulat for g in granges)
    benefici_global = total_ingressos - total_cost_transport - total_cost_fixe - total_alimentacio

    print("\n" + "=" * 40)
    print("   DASHBOARD LOGÍSTICA PORCINA")
    print("=" * 40)
    print(f"Flota Utilitzada: {NUM_CAMIONS_FLOTA} camions")
    print(f"Total Porcs Lliurats: {df['porcs_totals'].sum():,.0f}")
    print(f"Total Ingressos Venda: {total_ingressos:,.2f} €")
    print(f"Total Penalitzacions: {df['penalitzacions'].sum():,.2f} €")
    print("-" * 30)
    print(f"Cost Transport Variable: {total_cost_transport:,.2f} €")
    print(f"Cost Transport Fixe: {total_cost_fixe:,.2f} €")
    print(f"Cost Alimentació: {total_alimentacio:,.2f} €")
    print("-" * 30)
    print(f"BENEFICI NET GLOBAL: {benefici_global:,.2f} €")
    print("=" * 40)

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    
    daily_pigs = df.groupby("dia")["porcs_totals"].sum().reindex(range(1, DIES_SIMULACIO + 1), fill_value=0)
    colors = ['skyblue' if i % 7 < 5 else 'lightgray' for i in range(DIES_SIMULACIO)]
    axs[0, 0].bar(daily_pigs.index, daily_pigs.values, color=colors)
    axs[0, 0].set_title("Porcs Processats (Gris=Cap de Setmana)")
    axs[0, 0].set_xticks(range(1, DIES_SIMULACIO + 1))
    
    # Línia de capacitat i escala Y dinàmica per mostrar el màxim
    cap_diaria = escorxador.capacitat_diaria
    axs[0, 0].axhline(y=cap_diaria, color='r', linestyle='--', label=f'Capacitat ({cap_diaria})')
    
    # Calculem el màxim entre les dades i la capacitat per ajustar l'eix Y
    max_y = max(daily_pigs.max(), cap_diaria)
    axs[0, 0].set_ylim(0, max_y * 1.1) # 10% de marge superior
    
    axs[0, 0].legend()

    df_clean = df[df["porcs_totals"] > 0]
    if not df_clean.empty:
        axs[0, 1].scatter(df_clean["cost_viatge"], df_clean["ingressos"], alpha=0.5)
        axs[0, 1].set_title("Eficiència per Viatge")
        axs[0, 1].set_xlabel("Cost (€)"); axs[0, 1].set_ylabel("Ingrés (€)")
    
    if not df_clean.empty:
        axs[1, 0].hist(df_clean["pes_total"], bins=20, color='orange')
        axs[1, 0].set_title("Distribució de Càrrega (kg)")

    # 4. MAPA DE RUTES (TOTS ELS DIES)
    escorxador_loc = escorxador.location 
    
    # Dibuixem elements estàtics
    axs[1, 1].scatter(escorxador_loc[1], escorxador_loc[0], c='red', s=200, marker='X', zorder=10, label='Escorxador')
    lats_g = [g.location[0] for g in granges]
    lons_g = [g.location[1] for g in granges]
    axs[1, 1].scatter(lons_g, lats_g, c='green', alpha=0.5, s=50, label='Granges')
    
    # Filtrem totes les rutes actives (no només dia 1)
    rutas_actives = df[df["porcs_totals"] > 0]
    count_rutas = 0
    
    # Paleta de colors per diferenciar dies
    cmap = plt.get_cmap('tab20')
    
    for idx, row in rutas_actives.iterrows():
        if isinstance(row['parades'], list) and len(row['parades']) > 0:
             ruta_lats = [escorxador_loc[0]]
             ruta_lons = [escorxador_loc[1]]
             
             for parada_id in row['parades']:
                 g_obj = next((g for g in granges if g.id == parada_id), None)
                 if g_obj:
                     ruta_lats.append(g_obj.location[0])
                     ruta_lons.append(g_obj.location[1])
             
             ruta_lats.append(escorxador_loc[0])
             ruta_lons.append(escorxador_loc[1])
             
             # Color basat en el dia
             dia_actual = row['dia']
             color_dia = cmap((dia_actual - 1) % 20)
             
             axs[1, 1].plot(ruta_lons, ruta_lats, color=color_dia, alpha=0.5, linestyle='-', marker='.', linewidth=1)
             count_rutas += 1

    axs[1, 1].set_title(f"Mapa de Rutes (Total: {count_rutas} rutes)")
    axs[1, 1].set_xlabel("Longitud")
    axs[1, 1].set_ylabel("Latitud")
    axs[1, 1].legend(loc='upper right')
    axs[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return df

if __name__ == "__main__":
    df_resultats, granges_estat_final, obj_escorxador = simular()
    exportar_resultats_json(df_resultats)
    generar_dashboard(df_resultats, granges_estat_final, obj_escorxador)