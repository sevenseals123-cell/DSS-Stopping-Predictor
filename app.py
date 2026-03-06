import streamlit as st
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="Kinetic Stopping Predictor - Cpt. Dialmy", page_icon="⚓", layout="wide")

footer_style = """
    <style>
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f6; color: #31333F; 
    text-align: center; padding: 10px; font-size: 14px; font-weight: bold; border-top: 2px solid #0073e6; z-index: 100; }
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
    """)

# --- SIDEBAR : PROFIL DU NAVIRE ---
st.sidebar.header("🚢 Profil du Navire")
type_navire = st.sidebar.selectbox("Type", ["Porte-conteneurs (Grand)", "Pétrolier / VLCC", "Méthanier (LNGC)", "Vraquier"])

if type_navire == "Pétrolier / VLCC":
    cb_def, lpp_def, b_def, t_def, disp_def, p_def = 0.85, 330.0, 60.0, 20.0, 300000, 25000
elif type_navire == "Porte-conteneurs (Grand)":
    cb_def, lpp_def, b_def, t_def, disp_def, p_def = 0.65, 399.0, 59.0, 15.0, 200000, 60000
elif type_navire == "Méthanier (LNGC)":
    cb_def, lpp_def, b_def, t_def, disp_def, p_def = 0.75, 290.0, 46.0, 12.0, 100000, 30000
else:
    cb_def, lpp_def, b_def, t_def, disp_def, p_def = 0.82, 290.0, 45.0, 14.0, 120000, 15000

disp_t = st.sidebar.number_input("Déplacement Actuel (Tonnes)", value=disp_def, step=5000)
lpp = st.sidebar.number_input("Lpp (m)", value=lpp_def)
breadth = st.sidebar.number_input("Largeur (m)", value=b_def)
draft = st.sidebar.number_input("Tirant d'eau (m)", value=t_def)
cb = st.sidebar.slider("Coefficient Cb", 0.5, 0.95, cb_def)

puissance_moteur = st.sidebar.number_input("Puissance Moteur Max (kW)", value=p_def, step=1000)
# Force astern estimée (La puissance arrière est env. 40-50% de la puissance avant, rendement hélice en marche arrière faible)
# Règle empirique standard : ~1.0 Tonne astern pour 100 kW de puissance astern effective.
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
    
    # Physique Shallow Water
    if h_t_ratio < 1.5:
        st.warning(f"⚠️ **Shallow Water Effect Actif** (h/T = {round(h_t_ratio, 2)})")
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
    st.metric("Énergie Cinétique à dissiper", f"{int(energie_joules / 1000000)} MJ")
    st.caption(f"Masse navire + {round((added_mass_coef - 1) * 100)}% d'eau entraînée")

st.divider()

# --- LES MOYENS D'ARRÊT ---
st.subheader("🛑 Moyens d'Arrêt Configurables")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**🌊 Traînée Coque**")
    surface_mouillee = lpp * (breadth + 2 * draft)
    c_t = (0.003 + (0.002 * cb)) * drag_multiplier
    drag_max_n = 0.5 * 1025 * c_t * surface_mouillee * (v_ms**2) # En Newtons
    drag_max_t = drag_max_n / 9806.65
    drag_moyen_t = drag_max_t * 0.33 # Moyenne sur la décélération
    st.metric("Frein Hydrodynamique", f"{round(drag_moyen_t, 1)} T")
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
    st.metric("Poussée Inversée", f"{round(force_machine_t, 1)} T")

with c3:
    st.markdown("**🚜 Remorqueurs**")
    nb_tugs = st.number_input("Nb Tugs en freinage", 0, 4, 1)
    bp_tug = st.number_input("BP unitaire (T)", value=60)
    force_tugs_t = nb_tugs * bp_tug
    st.metric("Force d'Escorte", f"{round(force_tugs_t, 1)} T")

with c4:
    st.markdown("**⚓ Ancres**")
    ancres = st.radio("Mouillage", ["Aucune", "1 Ancre (Draguée)", "2 Ancres"])
    force_ancre_t = 0.0 if ancres == "Aucune" else (15.0 if ancres == "1 Ancre (Draguée)" else 30.0)
    st.metric("Frein Ancres", f"{round(force_ancre_t, 1)} T")

# --- LE VERDICT ---
st.divider()
st.header("📊 Verdict de la Manœuvre")

# F = W / d (Force en Newtons, puis conversion en Tonnes)
force_requise_n = energie_joules / dist_cible
force_requise_t = force_requise_n / 9806.65

force_dispo_totale_t = drag_moyen_t + force_machine_t + force_tugs_t + force_ancre_t

# Distance d'inertie pure (sans aide extérieure)
dist_inertie = (energie_joules) / (drag_moyen_t * 9806.65) if drag_moyen_t > 0 else 0

r1, r2 = st.columns(2)

with r1:
    st.metric(f"Force REQUISE pour stopper en {int(dist_cible)}m", f"{round(force_requise_t, 1)} T")
    st.metric("Force DISPONIBLE configurée", f"{round(force_dispo_totale_t, 1)} T")

with r2:
    if force_dispo_totale_t >= force_requise_t:
        utilisation_pct = (force_requise_t / force_dispo_totale_t) * 100
        st.success(f"✅ **ARRÊT SÉCURISÉ :** Le navire s'arrêtera confortablement avant les {int(dist_cible)}m.")
        st.subheader(f"Charge des moyens : {round(utilisation_pct)} %")
        st.progress(min(utilisation_pct / 100, 1.0))
    else:
        dist_reelle = (energie_joules) / (force_dispo_totale_t * 9806.65) if force_dispo_totale_t > 0 else dist_inertie
        st.error(f"❌ **DANGER D'IMPACT :** Forces de freinage insuffisantes.")
        st.subheader(f"Distance d'arrêt réelle : {int(dist_reelle)} m")
        st.write(f"⚠️ Il manque au moins {round(force_requise_t - force_dispo_totale_t, 1)} T de retenue pour réussir la manœuvre.")

st.info(f"💡 **Inertie pure :** Sans machine, sans remorqueur et sans ancre, la friction de l'eau arrêtera le navire en **{int(dist_inertie)} mètres**.")

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(footer_style, unsafe_allow_html=True)
