// Place sur les pages : à partir de la mesure de Chromium (/api/livrets/{id}/mesure, faite sur le livret
// enregistré), estime en direct, pendant la frappe, si une page qui débordait tient de nouveau.
// Modèle : hauteur d'un bloc = partie fixe (marges, ligne de titre) + partie proportionnelle au nombre de signes,
// à la taille de texte où la page a été mesurée. Le verdict final reste la nouvelle mesure après « Enregistrer ».

const FIXE = { une: 34, breve: 4, p2: 45, chrono: 6, musique: 16, cinema: 16, mot: 34 } // px, relevés sur des pages mesurées
const MARGE = 1.05 // on demande un peu plus que le calcul, pour ne pas s'arrêter à une ligne près
const POIDS_TITRE = 1.4 // un signe de titre prend plus de place qu'un signe de texte

const sorte = (cle) => cle.split(':')[0]

function objet(cle, contenu, mot) {
  const [s, i] = cle.split(':')
  if (s === 'une') return contenu.une
  if (s === 'breve') return contenu.breves?.[+i]
  if (s === 'p2') return contenu.p2?.items?.[+i]
  if (s === 'chrono') return contenu.chrono?.[+i]
  if (s === 'musique' || s === 'cinema') return { texte: contenu[s] ?? '' }
  if (s === 'mot') return { texte: mot ?? '' }
  return null
}

/** Signes pondérés d'un bloc (null s'il est masqué ou absent). */
export function signes(cle, contenu, mot) {
  const o = objet(cle, contenu, mot)
  if (!o || o.masque) return null
  if (sorte(cle) === 'une') return POIDS_TITRE * (o.titre ?? '').length + (o.chapo ?? '').length
  return POIDS_TITRE * (o.titre ?? '').length + (o.texte ?? '').length
}

/** Signes visibles d'un bloc (titre + texte), pour le compteur. */
export function compte(cle, contenu, mot) {
  const o = objet(cle, contenu, mot)
  if (!o) return 0
  if (sorte(cle) === 'une') return (o.titre ?? '').length + (o.chapo ?? '').length
  return (o.titre ?? '').length + (o.texte ?? '').length
}

function hauteur(b, sAvant, sMaintenant) {
  if (sMaintenant === null) return 0 // masqué depuis la mesure
  const fixe = Math.min(FIXE[sorte(b.bloc)] ?? 0, b.h)
  if (!sAvant) return b.h
  return fixe + (b.h - fixe) * sMaintenant / sAvant
}

/**
 * mesure = { pages: [{page, deborde, exces, blocs: [{bloc, h}]}], contenu, mot } (contenu et mot au moment de la mesure).
 * Rend { pages: {n: {deborde, reste, ok}}, blocs: {cle: {page, rouge, vert, compte, aRetirer}}, tient(cle, f) }.
 */
export function etatPlace(mesure, contenu, mot) {
  const pages = {}, blocs = {}
  if (!mesure || !contenu) return { pages, blocs, tient: () => null }
  for (const p of mesure.pages) {
    if (!p.deborde) continue
    let reste = p.exces
    const infos = p.blocs.map((b) => {
      const sAvant = signes(b.bloc, mesure.contenu, mesure.mot)
      const sMaint = signes(b.bloc, contenu, mot)
      const h = hauteur(b, sAvant, sMaint)
      reste += h - b.h
      return { b, sAvant, sMaint, h }
    })
    pages[p.page] = { deborde: true, reste: Math.round(reste), ok: reste <= 0 }
    for (const { b, sAvant, sMaint, h } of infos) {
      const fixe = Math.min(FIXE[sorte(b.bloc)] ?? 0, b.h)
      const parSigne = sAvant ? (b.h - fixe) / sAvant : 0
      const aRetirer = reste > 0 && parSigne > 0 && sMaint !== null ? Math.ceil(MARGE * reste / parSigne) : 0
      blocs[b.bloc] = {
        page: p.page, h, b, sAvant, parSigne,
        rouge: reste > 0 && sMaint !== null, vert: reste <= 0 && sMaint !== null,
        compte: compte(b.bloc, contenu, mot),
        aRetirer: Math.min(aRetirer, Math.round(sMaint ?? 0)),
        seul: aRetirer > 0 && aRetirer < (sMaint ?? 0) * 0.9, // raccourcir ce bloc seul peut suffire
      }
    }
  }
  /** Une proposition f mise à la place du bloc `cle` ferait-elle tenir la page ? (null : pas de page en défaut) */
  function tient(cle, f) {
    const x = blocs[cle]
    if (!x) return null
    const p = pages[x.page]
    if (!p || p.ok) return null
    const sNouveau = POIDS_TITRE * (f.rubrique ?? '').length + (f.texte ?? '').length
    const fixe = Math.min(FIXE[sorte(cle)] ?? 0, x.b.h)
    const hNouveau = fixe + x.parSigne * sNouveau
    return p.reste + (hNouveau - x.h) <= 0
  }
  return { pages, blocs, tient }
}
