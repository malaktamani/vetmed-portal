const DATA = {
  specialites: [
    { id:"vetmed", label:"Médecine Vétérinaire", desc:"Cours, TD, TP et résumés pour toutes les années", icon:"🐾", c1:"#7c6af7", c2:"#4ecdc4", active:true },
    { id:"pharma", label:"Pharmacie", desc:"Bientôt disponible", icon:"💊", c1:"#f7c06a", c2:"#f7756a", active:false },
    { id:"medecine", label:"Médecine Générale", desc:"Bientôt disponible", icon:"🩺", c1:"#4ecdc4", c2:"#6af7b0", active:false },
  ],
  annees: [
    { id:"1a", label:"1ère année", icon:"🌱", sub:"Fondamentaux" },
    { id:"2a", label:"2ème année", icon:"📗", sub:"Approfondissement" },
    { id:"3a", label:"3ème année", icon:"📘", sub:"Clinique 1" },
    { id:"4a", label:"4ème année", icon:"📙", sub:"Clinique 2" },
    { id:"5a", label:"5ème année", icon:"📕", sub:"Spécialisation" },
    { id:"6a", label:"6ème année", icon:"🎓", sub:"Stage final" },
  ],
  semestres: [
    { id:"s1", label:"Semestre 1", icon:"🍂", sub:"Automne / Hiver" },
    { id:"s2", label:"Semestre 2", icon:"🌸", sub:"Printemps / Été" },
  ],
  ressources: [
    { id:"cours",   label:"Cours",   icon:"📖", sub:"Cours magistraux" },
    { id:"td",      label:"TD",      icon:"✏️",  sub:"Travaux dirigés" },
    { id:"tp",      label:"TP",      icon:"🔬", sub:"Travaux pratiques" },
    { id:"resumes", label:"Résumés", icon:"📝", sub:"Fiches de révision" },
  ],
  modules: {
    "1a-s1": {
      cours:   ["Anatomie","Biochimie","Chimie","Cytologie","Génétique","Histologie","Zoologie"],
      td:      ["Biochimie","Chimie","Cytologie","Génétique"],
      tp:      ["Anatomie","Biochimie","Chimie","Histologie","Zoologie"],
      resumes: ["Biochimie","Cytologie","Histologie"]
    },
    "1a-s2": {
      cours:   ["Anatomie","Biochimie","Biologie moléculaire","Biophysique","Cytologie","Embryologie","Ethnologie","Éthologie et bien-être","Physiologie","Français"],
      td:      ["Biochimie","Biophysique","Cytologie","Embryologie"],
      tp:      ["Anatomie","Biochimie","Éthologie et bien-être"],
      resumes: ["Biochimie","Biologie moléculaire","Biophysique","Cytologie","Embryologie","Éthologie et bien-être"]
    },
    "2a-s1": {
      cours:   ["Alimentation","Amélioration génétique et biotechnologie (AGB)","Anatomie 2","Biostatistiques","Ethnologie spéciale","Immuno-vaccinologie","Physiologie 2","Physiologie de la reproduction"],
      td:      ["Alimentation","AGB","Biostatistiques","Immuno-vaccinologie","Physiologie 2","Physiologie de la reproduction"],
      tp:      ["Alimentation","Ethnologie spéciale"],
      resumes: ["Alimentation","Amélioration génétique et biotechnologie (AGB)","Anatomie 2","Biostatistiques","Ethnologie spéciale","Immuno-vaccinologie","Physiologie 2","Physiologie de la reproduction"]
    },
    "2a-s2": {
      cours:   ["Alimentation","Anatomie 2","Anglais scientifique","Bactériologie générale","Bio-informatique","Elevage et productions animales (EPA)","Histologie spéciale","Physiologie de la reproduction","Virologie générale"],
      td:      ["Alimentation","Physiologie de la reproduction","Virologie générale"],
      tp:      ["Bactériologie générale","EPA","Histologie spéciale"],
      resumes: ["Alimentation","Anatomie 2","Anglais scientifique","Bactériologie générale","Bio-informatique","Elevage et productions animales (EPA)","Histologie spéciale","Physiologie de la reproduction","Virologie générale"]
    },
    "3a-s1": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "3a-s2": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "4a-s1": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "4a-s2": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "5a-s1": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "5a-s2": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "6a-s1": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
    "6a-s2": { cours:["À compléter"], td:[], tp:[], resumes:["À compléter"] },
  },
  fichiers: {}
};
