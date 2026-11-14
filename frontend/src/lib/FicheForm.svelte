<script>
  // Saisie d'une fiche : nom affiché à la une, prénom (pour « Exemplaire de … »), date de naissance,
  // autres noms (tels qu'écrits dans la réservation de Home Assistant).
  // Saisie assistée : en tapant le nom, les contacts de carnet sont proposés ; un toucher remplit la fiche.
  import { onDestroy } from 'svelte'
  import BookUser from '@lucide/svelte/icons/book-user'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import { dateLongue } from '$lib/format.js'
  let { valeur = {}, bouton = 'Créer la fiche', onvalider, onannuler = null } = $props()
  const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
  const nomDeDepart = valeur.nom ?? ''
  let propositions = $state([])
  let choisi = $state(false)
  let indice = $state('')
  let minuteur = null
  let nom = $state(valeur.nom ?? '')
  let prenom = $state(valeur.prenom ?? '')
  let naissance = $state(valeur.naissance ?? '')
  let alias = $state((valeur.alias ?? []).join(', '))
  let erreur = $state('')
  let envoi = $state(false)

  function chercher() {
    clearTimeout(minuteur)
    if (choisi || valeur.naissance) return       // fiche existante ou contact déjà choisi : rien à proposer
    minuteur = setTimeout(async () => {
      try { propositions = nom.trim().length >= 2 ? (await api.get(`/api/carnet/suggestions?q=${encodeURIComponent(nom.trim())}`)).suggestions : [] }
      catch { propositions = [] }
    }, 250)
  }
  function prendre(p) {
    nom = p.nom
    prenom = p.prenom || ''
    const autres = alias.split(',').map((a) => a.trim()).filter(Boolean)
    const cle = (x) => x.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
    for (const n of [nomDeDepart, p.nom_ha]) if (n && cle(n) !== cle(p.nom) && !autres.some((a) => cle(a) === cle(n))) autres.push(n)
    alias = autres.join(', ')
    if (p.naissance) { naissance = p.naissance; indice = '' }
    else indice = p.jour ? `Carnet : le ${p.jour === 1 ? '1er' : p.jour} ${MOIS[p.mois - 1]}, année inconnue : complète la date.` : 'Carnet ne connaît pas la date de naissance.'
    propositions = []
    choisi = true
  }
  function dateDe(p) {
    if (p.naissance) return `né·e le ${dateLongue(p.naissance)}`
    if (p.jour) return `le ${p.jour === 1 ? '1er' : p.jour} ${MOIS[p.mois - 1]}, année inconnue`
    return 'date inconnue'
  }
  chercher()
  onDestroy(() => clearTimeout(minuteur))

  async function valider(e) {
    e.preventDefault()
    envoi = true
    erreur = ''
    try {
      await onvalider({ nom, prenom, naissance, alias: alias.split(',').map((a) => a.trim()).filter(Boolean) })
    } catch (err) {
      erreur = err.message
    }
    envoi = false
  }
</script>

<form onsubmit={valider} class="grid gap-3 sm:grid-cols-2">
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Nom à la une</span>
    <input required bind:value={nom} oninput={() => { choisi = false; chercher() }} placeholder="Prénom Nom" autocomplete="off"
           class="h-10 rounded-lg border bg-background px-3" />
  </label>
  {#if propositions.length}
    <div class="rounded-xl border bg-background p-2 sm:col-span-2" role="group" aria-label="Contacts de carnet">
      <p class="mb-1 flex items-center gap-1.5 px-1 text-xs text-muted-foreground"><BookUser class="size-3.5" aria-hidden="true" />Dans carnet</p>
      <ul class="grid gap-1">
        {#each propositions as p}
          <li><button type="button" onclick={() => prendre(p)} class="w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary">
            <b>{p.nom}</b> <span class="text-muted-foreground">· {dateDe(p)}</span></button></li>
        {/each}
      </ul>
    </div>
  {/if}
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Prénom (« Exemplaire de … »)</span>
    <input bind:value={prenom} placeholder="le premier mot du nom" class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Date de naissance</span>
    <input required type="date" bind:value={naissance} class="h-10 rounded-lg border bg-background px-3" />
    {#if indice}<span class="text-xs text-primary">{indice}</span>{/if}
  </label>
  <label class="grid gap-1 text-sm">
    <span class="text-muted-foreground">Autres noms dans les réservations</span>
    <input bind:value={alias} placeholder="séparés par des virgules" class="h-10 rounded-lg border bg-background px-3" />
  </label>
  <div class="flex flex-wrap items-center gap-2 sm:col-span-2">
    <Button type="submit" disabled={envoi}>{bouton}</Button>
    {#if onannuler}<Button type="button" variant="outline" onclick={onannuler}>Annuler</Button>{/if}
    {#if erreur}<span class="text-sm text-destructive" role="alert">{erreur}</span>{/if}
  </div>
</form>
