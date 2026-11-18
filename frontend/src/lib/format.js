// Petites mises en forme communes aux écrans.
const MOIS = ['janv.', 'févr.', 'mars', 'avril', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
const MOIS_LONG = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']

export function dateCourte(iso) {
  if (!iso) return ''
  const [a, m, j] = iso.slice(0, 10).split('-').map(Number)
  return `${j === 1 ? '1er' : j} ${MOIS[m - 1]}${a !== new Date().getFullYear() ? ' ' + a : ''}`
}
export function dateLongue(iso) {
  if (!iso) return ''
  const [a, m, j] = iso.slice(0, 10).split('-').map(Number)
  return `${j === 1 ? '1er' : j} ${MOIS_LONG[m - 1]} ${a}`
}
export const ETATS = {
  a_preparer: { nom: 'à préparer', ton: 'muted' },
  en_preparation: { nom: 'en préparation…', ton: 'muted' },
  a_relire: { nom: 'à relire', ton: 'primary' },
  approuve: { nom: 'approuvé', ton: 'valide' },
  vide: { nom: 'sans photo : la Gazette sert', ton: 'muted' },
}
export const PORTEES = { jour: 'le jour même', veille: 'la veille', semaine: 'la semaine', mois: 'le mois', autour: 'autour', annee: "l'année", vide: 'aucune' }
// 0.22 : nom court d'un modèle de l'IA pour un bouton : « qwen2.5:14b » → « qwen », « mistral-nemo » → « mistral »
export function nomCourt(modele) {
  const m = String(modele || '').split(':')[0]
  return m.match(/^[a-z]+/i)?.[0] || m
}
