// 0.17 : relecture élément par élément, commune à la Gazette et à La Récidive.
// Un élément validé garde l'empreinte de son contenu : s'il change ensuite, il revient à valider.

/** Empreinte courte et stable d'une valeur (espaces regroupés, pour suivre ce que le serveur range). */
export function empreinte(valeur) {
  const s = JSON.stringify(valeur ?? '').replace(/\s+/g, ' ').trim()
  let h = 5381
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0
  return (h >>> 0).toString(36)
}
