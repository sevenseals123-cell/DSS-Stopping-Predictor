import streamlit as st
import math
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Advanced Stopping Predictor", page_icon="⚓", layout="wide")

footer_style = """
    <style>
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f6; color: #31333F; 
    text-align: center; padding: 10px; font-size: 14px; font-weight: bold; border-top: 2px solid #0073e6; z-index: 100; }
    .stProgress > div > div > div > div { background-color: #0073e6; }
    </style>
    <div class="footer"><p>© 2026 - Développé par Cpt. Dialmy | Marine Pilot</p></div>
"""

st.title("⚓ Advanced Kinetic Stopping Predictor")
st.write("Simulateur d'arrêt avec intégration du vent, du courant, et du délai de réponse machine.")

# --- SIDEBAR : PROFIL DU NAVIRE ---
st.sidebar.header("🚢 Profil du Navire")
type_navire = st.sidebar.selectbox("Type", ["Porte-conteneurs (Grand)", "Pétrolier / VLCC", "Méthanier (LNGC)", "Vraquier"])

params = {
    "Pétrolier / VLCC": (0.85, 330.0, 60.0, 20.0, 300000, 25000, 0.8),
    "Porte-conteneurs (Grand)": (0.65, 399.0, 59.0, 15.0, 200000, 60000, 2.5),
    "Méthanier (LNGC)": (0.75, 290.0, 46.0, 12.0, 100000, 30000, 1.8),
    "Vraquier": (0.82, 290.0, 45.0, 14.0, 120000, 15000, 1.0)
}
cb_def, lpp_def, b_def, t_def, disp_def, p_def, fardage_def = params.get(type_navire, params["Vraquier"])

disp_t = st.sidebar.number_input("Déplacement (Tonnes)", value=disp_def, step=5000)
lpp = st.sidebar.number_input("Lpp (m)", value=lpp_def)
breadth = st.sidebar.number_input("Largeur (m)", value=b_def)
draft = st.sidebar.number_input("Tirant d'eau (m)", value=t_def)
cb = st.sidebar.slider("Coefficient Cb", 0.50, 0.95, cb_def, step=0.01)

puissance_moteur = st.sidebar.number_input("Puissance Moteur Max (kW)", value=p_def, step=1000)
max_astern_t = (puissance_moteur * 0.45 / 100) * 1.0

# --- MAIN DASHBOARD : ENVIRONNEMENT ---
st.header("🎯 Scénario & Environnement")
col1, col2, col3, col4 = st.columns(4)

with col1:
    v_sog_kn = st.slider("Vitesse Fond initiale SOG (kn)", 1.0, 12.0, 5.0, step=0.1)
    v_sog_ms = v_sog_kn * 0.51444
    dist_cible = st.number_input("Distance dispo. (m)", value=700, step=50)

with col2:
    profondeur = st.number_input("Profondeur (m)", value=draft * 1.2, min_value=draft * 1.01)
    h_t_ratio = profondeur / draft
    if h_t_ratio < 1.5:
        added_mass_coef = 1.10 + 0.4 * (1.5 - h_t_ratio)
        drag_multiplier = 1.0 + 1.5 * (1.5 - h_t_ratio)
        st.warning(f"⚠️ Shallow Water (h/T={h_t_ratio:.2f})")
    else:
        added_mass_coef = 1.10
        drag_multiplier = 1.0
        st.success(f"🌊 Deep Water (h/T={h_t_ratio:.2f})")

with col3:
    courant_kn = st.number_input("Courant Face (+ Face / - Arrière)", value=0.0, step=0.5)
    courant_ms = courant_kn * 0.51444
    st.caption("Un courant face aide à freiner.")

with col4:
    vent_kn = st.number_input("Vent Face (+ Face / - Arrière)", value=0.0, step=5.0)
    # Estimation de la force du vent en tonnes (simplifiée via facteur de fardage)
    force_vent_t = (vent_kn / 10.0)**2 * fardage_def * (1 if vent_kn > 0 else -1)
    st.caption(f"Fardage estimé : {force_vent_t:.1f} T")

st.divider()

# --- LES MOYENS D'ARRÊT ---
st.subheader("🛑 Configuration du Freinage")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**⚙️ Machine (Astern)**")
    delai_machine = st.slider("Délai de réponse (secondes)", 0, 180, 60, step=10, help="Temps avant que l'hélice ne batte en arrière.")
    pct_machine = st.slider("Ordre Machine (% Astern)", 0, 100, 50, step=10)
    force_machine_t = max_astern_t * (pct_machine / 100)

with c2:
    st.markdown("**🚜 Remorqueurs**")
    nb_tugs = st.number_input("Nb Tugs en freinage", 0, 4, 1)
    bp_tug = st.number_input("BP unitaire (T)", value=60)
    force_tugs_t = nb_tugs * bp_tug

with c3:
    st.markdown("**⚓ Ancres**")
    ancres = st.radio("Mouillage", ["Aucune", "1 Ancre (Draguée)", "2 Ancres"], horizontal=True)
    force_ancre_t = 0.0 if ancres == "Aucune" else (15.0 if ancres == "1 Ancre (Draguée)" else 30.0)

# --- MOTEUR PHYSIQUE (INTÉGRATION EULER) ---
masse_virtuelle_kg = disp_t * 1000 * added_mass_coef
surface_mouillee = lpp * (breadth + 2 * draft)
c_t = (0.003 + (0.002 * cb)) * drag_multiplier

# Variables de simulation
v_actuelle_ms = v_sog_ms
distance_parcourue = 0.0
t_sec = 0
dt = 1.0 # Pas de temps de 1 seconde
historique = []

while v_actuelle_ms > 0.05 and t_sec < 3600:
    # Vitesse Surface (STW) pour la traînée
    v_stw = max(0, v_actuelle_ms + courant_ms)
    
    # 1. Force Hydrodynamique (varie avec le carré de la vitesse)
    drag_n = 0.5 * 1025 * c_t * surface_mouillee * (v_stw**2)
    
    # 2. Force Machine (Nulle si on est dans le délai de réponse)
    engine_n = (force_machine_t * 9806.65) if t_sec >= delai_machine else 0.0
    
    # 3. Remorqueurs, Ancres et Vent (Forces constantes)
    tugs_n = force_tugs_t * 9806.65
    ancre_n = force_ancre_t * 9806.65
    wind_n = force_vent_t * 9806.65
    
    # Force totale de freinage (Si négative = le vent arrière pousse plus fort qu'on ne freine)
    total_braking_force_n = drag_n + engine_n + tugs_n + ancre_n + wind_n
    
    # Décélération a = F/m
    decel_ms2 = total_braking_force_n / masse_virtuelle_kg
    
    # Mise à jour des vecteurs
    v_actuelle_ms -= decel_ms2 * dt
    distance_parcourue += v_actuelle_ms * dt
    t_sec += dt
    
    # Enregistrement des données pour le graphique (toutes les 5 secondes)
    if t_sec % 5 == 0:
        historique.append({"Distance (m)": distance_parcourue, "Vitesse (noeuds)": max(0, v_actuelle_ms / 0.51444)})

df_graph = pd.DataFrame(historique)

# --- LE VERDICT ---
st.divider()
st.header("📊 Verdict de la Simulation")

r1, r2, r3 = st.columns(3)
with r1:
    st.metric("Distance d'arrêt totale", f"{int(distance_parcourue)} m")
with r2:
    st.metric("Marge de sécurité", f"{int(dist_cible - distance_parcourue)} m")
with r3:
    st.metric("Temps d'arrêt (Time to stop)", f"{int(t_sec/60)} min {int(t_sec%60)} s")

if distance_parcourue <= dist_cible:
    st.success(f"✅ **MANŒUVRE SÉCURISÉE :** Le navire casse son erre avec succès.")
    st.progress(min(distance_parcourue / dist_cible, 1.0))
else:
    st.error(f"❌ **DANGER :** Dépassement de la zone de sécurité (Impact à {v_actuelle_ms/0.51444:.1f} nœuds).")
    st.markdown(f"""<div style="width: 100%; height: 15px; background-color: #ff4b4b; border-radius: 5px;"></div>""", unsafe_allow_html=True)

# Graphique de Décélération
st.subheader("📉 Courbe de Décélération : Vitesse vs Distance")
if not df_graph.empty:
    st.line_chart(df_graph, x="Distance (m)", y="Vitesse (noeuds)", height=350, use_container_width=True)

# --- EXPORT DU RAPPORT ---
st.divider()
rapport_txt = f"""--- PASSAGE PLAN : KINETIC STOPPING PREDICTION ---
Navire: {type_navire} (Displacement: {disp_t} T)
Vitesse initiale SOG: {v_sog_kn} kn
Courant: {courant_kn} kn | Vent: {vent_kn} kn
Profondeur: {profondeur} m (h/T = {h_t_ratio:.2f})

CONFIGURATION FREINAGE:
- Machine: {pct_machine}% Astern (Délai réponse: {delai_machine} sec)
- Remorqueurs: {nb_tugs}x {bp_tug}T BP
- Ancres: {ancres}

RESULTATS:
- Distance d'arrêt calculée: {int(distance_parcourue)} mètres
- Marge vs Cible ({dist_cible}m): {int(dist_cible - distance_parcourue)} mètres
- Temps d'arrêt: {int(t_sec/60)} min {int(t_sec%60)} s
------------------------------------------------"""

st.download_button("📄 Télécharger le Rapport (Passage Plan)", data=rapport_txt, file_name="Passage_Plan_Stopping.txt", mime="text/plain")

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(footer_style, unsafe_allow_html=True)
