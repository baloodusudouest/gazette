// 0.17 : file d'attente de l'IA du PC, commune à toute la page : l'IA traite une demande à la fois. Un bouton IA
// touché pendant qu'une analyse tourne ajoute sa demande à la suite de la liste en cours.
export const fileIa = $state({ enCours: '', attente: [] })
let chaine = Promise.resolve()

/** Ajoute `tache` (fonction async) à la file ; rend sa promesse. `nom` : ce qui s'affiche (« Brève 2 »…). */
export function enfiler(nom, tache) {
  fileIa.attente = [...fileIa.attente, nom]
  const p = chaine.then(async () => {
    const i = fileIa.attente.indexOf(nom)
    fileIa.attente = fileIa.attente.filter((_, j) => j !== i)
    fileIa.enCours = nom
    try { return await tache() } finally { fileIa.enCours = '' }
  })
  chaine = p.catch(() => {})
  return p
}
