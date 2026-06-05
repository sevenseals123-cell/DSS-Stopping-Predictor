import streamlit as st
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="Kinetic Stopping Predictor - Cpt. Dialmy", page_icon="⚓", layout="wide")

footer_style = """
    <style>
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f6; color: #31333F; 
    text-align: center; padding: 10px; font-size: 14px; font-weight: bold; border-top: 2px solid #0073e6; z-index: 100; }
    .stProgress > div > div > div > div { background-color: #0073e6; }
    </style>
    <div class="footer"><p>© 2026 - Développé par Cpt. Dialmy | Marine Pilot</p></div>
"""

st.title("⚓ Kinetic Energy & Stopping Predictor")
st.write("Analyse dynamique des forces d'arrêt, de l'inertie et de l'effet Shallow Water en milieu portuaire.")

with st.expander("📚 Physique du Modèle (Work-Energy Theorem)"):
    st.markdown("""
    L'application repose sur le théorème de l'énergie cinétique : **L'énergie totale à dissiper doit être égale au travail des forces de freinage**.
    * **Énergie Cinétique ($E_k$)** : Calculée avec la masse virtuelle (Déplacement + Masse d'eau entraînée).
    * **Shallow Water Effect** : Si le ratio $h/T < 1.5$, la masse d'eau entraînée et la résistance de frottement augmentent drastiquement.
    * **Temps d'arrêt** : Estimé via les équations de cinématique de base en assumant une décélération moyenne constante.
    """)

# --- SIDEBAR : PROFIL DU NAVIRE ---
st.sidebar.header("🚢 Profil du Navire")
type_navire = st.sidebar.selectbox("Type", ["Porte-conteneurs (Grand)", "Pétrolier / VLCC", "Méthanier (LNGC)", "Vraquier"])

# Paramètres par défaut selon le type
params = {
    "Pétrolier / VLCC": (0.85, 330.0, 60.0, 20.0, 300000, 25000),
    "Porte-conteneurs (Grand)": (0.65, 399.0, 59.0, 15.0, 200000, 60000),
    "Méthanier (LNGC)": (0.75, 290.0, 46.0, 12.0, 100000, 30000),
    "Vraquier": (0.82, 290.0, 45.0, 14.0, 120000, 15000)
}
cb_def, lpp_def, b_def, t_def, disp_def, p_def = params.get(type_navire, params["Vraquier"])

disp_t = st.sidebar.number_input("Déplacement Actuel (Tonnes)", value=disp_def, step=5000)
lpp = st.sidebar.number_input("Lpp (m)", value=lpp_def)
breadth = st.sidebar.number_input("Largeur (m)", value=b_def)
draft = st.sidebar.number_input("Tirant d'eau (m)", value=t_def)
cb = st.sidebar.slider("Coefficient Cb", 0.50, 0.95, cb_def, step=0.01)

puissance_moteur = st.sidebar.number_input("Puissance Moteur Max (kW)", value=p_def, step=1000)
# Force astern estimée (Règle empirique standard)
max_astern_t = (puissance_moteur * 0.45 / 100) * 1.0

# --- MAIN DASHBOARD : LE SCÉNARIO ---
st.header("🎯 Scénario & Environnement")

col1, col2, col3 = st.columns(3)

with col1:
    v_initiale = st.slider("Vitesse initiale (kn)", 1.0, 12.0, 5.0, step=0.1)
    v_ms = v_initiale * 0.51444
    dist_cible = st.number_input("Distance d'arrêt cible (m)", value=700.0, step=50.0)

with col2:
    profondeur = st.number_input("Profondeur d'eau (h en m)", value=draft * 1.2, min_value=draft * 1.01)
    h_t_ratio = profondeur / draft
    
    if h_t_ratio < 1.5:
        st.warning(f"⚠️ **Shallow Water Actif** (h/T = {round(h_t_ratio, 2)})")
        added_mass_coef = 1.10 + 0.4 * (1.5 - h_t_ratio)
        drag_multiplier = 1.0 + 1.5 * (1.5 - h_t_ratio)
    else:
        st.success(f"🌊 **Deep Water** (h/T = {round(h_t_ratio, 2)})")
        added_mass_coef = 1.10
        drag_multiplier = 1.0

with col3:
    st.info("Bilan Énergétique (Masse Virtuelle)")
    masse_virtuelle_kg = disp_t * 1000 * added_mass_coef
    energie_joules = 0.5 * masse_virtuelle_kg * (v_ms**2)
    st.metric("Énergie Cinétique à dissiper", f"{energie_joules / 1_000_000:.1f} MJ")
    st.caption(f"Masse navire + {round((added_mass_coef - 1) * 100)}% d'eau entraînée")

st.divider()

# --- LES MOYENS D'ARRÊT ---
st.subheader("🛑 Moyens d'Arrêt Configurables")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**🌊 Traînée Coque**")
    surface_mouillee = lpp * (breadth + 2 * draft)
    c_t = (0.003 + (0.002 * cb)) * drag_multiplier
    drag_max_n = 0.5 * 1025 * c_t * surface_mouillee * (v_ms**2)
    drag_max_t = drag_max_n / 9806.65
    drag_moyen_t = drag_max_t * 0.33 # Moyenne sur la décélération
    st.metric("Frein Hydrodynamique", f"{drag_moyen_t:.1f} T")
    st.caption("Friction moyenne estimée")

with c2:
    st.markdown("**⚙️ Machine (Astern)**")
    moteur_dispo = st.toggle("Moteur Disponible", value=True)
    if moteur_dispo:
        pourcentage_machine = st.slider("Ordre Machine (% Astern)", 0, 100, 50, step=10)
        force_machine_t = max_astern_t * (pourcentage_machine / 100)
    else:
        st.error("🚨 DEAD SHIP")
        force_machine_t = 0.0
    st.metric("Poussée Inversée", f"{force_machine_t:.1f} T")

with c3:
    st.markdown("**🚜 Remorqueurs**")
    nb_tugs = st.number_input("Nb Tugs en freinage", 0, 4, 1)
    bp_tug = st.number_input("BP unitaire (T)", value=60)
    force_tugs_t = nb_tugs * bp_tug
    st.metric("Force d'Escorte", f"{force_tugs_t:.1f} T")

with c4:
    st.markdown("**⚓ Ancres**")
    ancres = st.radio("Mouillage", ["Aucune", "1 Ancre (Draguée)", "2 Ancres"])
    force_ancre_t = 0.0 if ancres == "Aucune" else (15.0 if ancres == "1 Ancre (Draguée)" else 30.0)
    st.metric("Frein Ancres", f"{force_ancre_t:.1f} T")

# --- LE VERDICT ---
st.divider()
st.header("📊 Analyse de la Manœuvre")

# Calcul des forces requises et disponibles
force_requise_n = energie_joules / dist_cible if dist_cible > 0 else 0
force_requise_t = force_requise_n / 9806.65
force_dispo_totale_t = drag_moyen_t + force_machine_t + force_tugs_t + force_ancre_t

# Sécurité anti-division par zéro
if force_dispo_totale_t <= 0.1:
    force_dispo_totale_t = 0.1

# Calculs de distance et de temps
dist_reelle = energie_joules / (force_dispo_totale_t * 9806.65)
dist_inertie = energie_joules / (drag_moyen_t * 9806.65) if drag_moyen_t > 0 else float('inf')

# Temps d'arrêt estimé ( t = 2d / v_i )
if v_ms > 0:
    temps_arret_sec = (2 * dist_reelle) / v_ms
    temps_arret_min = temps_arret_sec / 60
else:
    temps_arret_min = 0

r1, r2, r3 = st.columns(3)
with r1:
    st.metric(f"Force REQUISE ({int(dist_cible)}m)", f"{force_requise_t:.1f} T")
with r2:
    st.metric("Force DISPONIBLE", f"{force_dispo_totale_t:.1f} T", delta=f"{force_dispo_totale_t - force_requise_t:.1f} T de marge")
with r3:
    st.metric("⏱️ Temps d'arrêt estimé", f"{temps_arret_min:.1f} minutes")

# Visualisation dynamique de la distance
st.markdown("### Projection Spatiale")
if dist_reelle <= dist_cible:
    st.success(f"✅ **ARRÊT SÉCURISÉ :** Le navire s'arrêtera à **{int(dist_reelle)}m** (Marge : {int(dist_cible - dist_reelle)}m).")
    # Barre de progression personnalisée
    ratio = dist_reelle / dist_cible
    st.progress(ratio)
else:
    st.error(f"❌ **DANGER D'IMPACT :** Le navire dépassera la cible de **{int(dist_reelle - dist_cible)}m** (Arrêt total à {int(dist_reelle)}m).")
    # Barre pleine en rouge pour indiquer le dépassement
    st.markdown(f"""
        <div style="width: 100%; background-color: #f0f2f6; border-radius: 5px;">
            <div style="width: 100%; height: 15px; background-color: #ff4b4b; border-radius: 5px;"></div>
        </div>
    """, unsafe_allow_html=True)
    st.write(f"⚠️ **Déficit de freinage :** Il manque {force_requise_t - force_dispo_totale_t:.1f} T de retenue.")

st.info(f"💡 **Inertie pure (Blackout total) :** Seule la friction de l'eau arrêtera le navire en **{int(dist_inertie)} mètres**.")

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(footer_style, unsafe_allow_html=True)
